# SPDX-License-Identifier: Elastic-2.0
# Copyright (c) 2026 Mitch Kwiatkowski
# ARIS � Automated Regulatory Intelligence System
# Licensed under the Elastic License 2.0. See LICENSE in the project root.
"""
ARIS — Baseline Agent Tests
"""
import sys
import types
import json
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch


def setUpModule():
    for pkg, attrs in {
        'tenacity':      ['retry', 'stop_after_attempt', 'wait_exponential'],
        'anthropic':     ['Anthropic', 'APIError'],
        'sqlalchemy':    ['Column','String','Text','DateTime','Float','Boolean',
                          'JSON','Index','text','create_engine','Integer'],
        'sqlalchemy.orm':['DeclarativeBase','Session','sessionmaker'],
    }.items():
        if pkg not in sys.modules:
            m = types.ModuleType(pkg)
            for a in attrs:
                setattr(m, a,
                    type(a, (), {'__init__': lambda s,*a,**k: None})
                    if a[0].isupper() else (lambda *a,**k: None))
            sys.modules[pkg] = m
    sys.modules['tenacity'].retry = lambda **k: (lambda f: f)


# ── Helper: build a temporary baselines directory ─────────────────────────────

def _write_temp_baselines(tmp: Path):
    """Write a minimal but valid baselines directory for testing."""
    index = {
        "version": "1.0",
        "last_reviewed": "2025-01-01",
        "baselines": [
            {
                "id": "eu_ai_act",
                "file": "eu_ai_act.json",
                "jurisdiction": "EU",
                "title": "EU Artificial Intelligence Act",
                "short_name": "EU AI Act",
                "status": "In Force",
                "priority": "critical",
                "doc_id_patterns": ["EU-CELEX-32024R1689", "32024R1689", "eu.*ai.*act"]
            },
            {
                "id": "us_eo_14110",
                "file": "us_eo_14110.json",
                "jurisdiction": "Federal",
                "title": "Executive Order 14110",
                "short_name": "EO 14110",
                "status": "In Force",
                "priority": "high",
                "doc_id_patterns": ["EO-14110", "FR-2023-24283", "14110"]
            },
            {
                "id": "uk_ai_framework",
                "file": "uk_ai_framework.json",
                "jurisdiction": "GB",
                "title": "UK AI Regulatory Framework",
                "short_name": "UK AI Framework",
                "status": "Active",
                "priority": "high",
                "doc_id_patterns": ["UK-AI", "uk.*ai.*framework"]
            },
        ]
    }

    eu_ai_act = {
        "id": "eu_ai_act",
        "jurisdiction": "EU",
        "title": "EU Artificial Intelligence Act",
        "short_name": "EU AI Act",
        "status": "In Force",
        "overview": "Risk-based framework for AI systems in the EU.",
        "timeline": [
            {"date": "2024-08-01", "milestone": "Regulation enters into force"},
            {"date": "2025-02-02", "milestone": "Prohibited practices apply"},
            {"date": "2026-08-02", "milestone": "High-risk obligations apply"},
        ],
        "key_definitions": [
            {"term": "AI system",   "definition": "A machine-based system designed to operate with varying levels of autonomy.", "significance": "Broad definition covers most ML systems."},
            {"term": "High-risk AI","definition": "AI systems listed in Annex III.", "significance": "Triggers the most onerous obligations."},
        ],
        "prohibited_practices": [
            {"id": "eu-aia-prohibited-subliminal", "title": "Subliminal manipulation", "description": "AI systems using subliminal techniques to distort behaviour.", "applies_to": "All", "in_force_from": "2025-02-02"},
        ],
        "obligations_by_actor": {
            "providers_high_risk": [
                {"id": "eu-aia-prov-conformity", "title": "Conformity assessment", "description": "Conduct conformity assessment before market placement.", "deadline": "2026-08-02"},
                {"id": "eu-aia-prov-register",   "title": "EU database registration", "description": "Register high-risk AI in EU database.", "deadline": "2026-08-02"},
            ],
            "deployers_high_risk": [
                {"id": "eu-aia-dep-oversight", "title": "Human oversight", "description": "Ensure human oversight of high-risk AI systems.", "deadline": "2026-08-02"},
            ]
        },
        "penalty_structure": {
            "prohibited_practices": {"max_eur": 35000000, "max_pct_turnover": 7, "note": "Whichever is higher"},
        },
        "cross_references": [
            {"regulation": "EU GDPR", "relevance": "GDPR Article 22 applies alongside AI Act obligations."}
        ]
    }

    eo_14110 = {
        "id": "us_eo_14110",
        "jurisdiction": "Federal",
        "title": "Executive Order 14110",
        "short_name": "EO 14110",
        "status": "In Force",
        "overview": "Primary US federal AI policy instrument.",
        "key_directives": [
            {"section": "Section 4.1", "title": "Dual-use foundation model reporting", "description": "Developers of large models must report to the government."},
        ],
        "private_sector_implications": [
            "Large foundation model developers must report training runs.",
            "AI systems used in hiring face heightened civil rights scrutiny.",
        ]
    }

    uk_framework = {
        "id": "uk_ai_framework",
        "jurisdiction": "GB",
        "title": "UK AI Regulatory Framework",
        "short_name": "UK AI Framework",
        "status": "Active",
        "overview": "Pro-innovation, sector-specific approach.",
        "five_cross_sector_principles": [
            {"principle": "Safety", "description": "AI systems should be safe and robust."},
        ],
        "ico_ai_obligations": [
            {"obligation": "Lawful basis", "description": "All AI processing personal data needs a lawful basis.", "applies_to": "All AI systems processing UK personal data"},
        ]
    }

    (tmp / "index.json").write_text(json.dumps(index))
    (tmp / "eu_ai_act.json").write_text(json.dumps(eu_ai_act))
    (tmp / "us_eo_14110.json").write_text(json.dumps(eo_14110))
    (tmp / "uk_ai_framework.json").write_text(json.dumps(uk_framework))
    return tmp


class TestBaselineAgentLoading(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        _write_temp_baselines(self.tmp)
        # Clear cache before each test
        from agents import baseline_agent as ba_mod
        ba_mod.BaselineAgent._cache = None

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        from agents import baseline_agent as ba_mod
        ba_mod.BaselineAgent._cache = None

    def _agent(self):
        from agents import baseline_agent as ba_mod
        ba_mod._BASELINES_DIR = self.tmp
        ba_mod.BaselineAgent._cache = None
        return ba_mod.BaselineAgent()

    def test_loads_all_baselines(self):
        agent = self._agent()
        all_b = agent.get_all()
        self.assertEqual(len(all_b), 3)

    def test_baseline_ids_present(self):
        agent = self._agent()
        ids = {b["id"] for b in agent.get_all()}
        self.assertIn("eu_ai_act",      ids)
        self.assertIn("us_eo_14110",    ids)
        self.assertIn("uk_ai_framework",ids)

    def test_get_by_id(self):
        agent  = self._agent()
        result = agent.get_by_id("eu_ai_act")
        self.assertIsNotNone(result)
        self.assertEqual(result["jurisdiction"], "EU")
        self.assertIn("obligations_by_actor", result)
        self.assertIn("timeline", result)

    def test_get_by_id_missing(self):
        agent  = self._agent()
        result = agent.get_by_id("nonexistent_baseline")
        self.assertIsNone(result)

    def test_get_for_jurisdiction_eu(self):
        agent = self._agent()
        eu    = agent.get_for_jurisdiction("EU")
        self.assertEqual(len(eu), 1)
        self.assertEqual(eu[0]["id"], "eu_ai_act")

    def test_get_for_jurisdiction_federal(self):
        agent   = self._agent()
        federal = agent.get_for_jurisdiction("Federal")
        self.assertEqual(len(federal), 1)
        self.assertEqual(federal[0]["id"], "us_eo_14110")

    def test_get_for_jurisdiction_case_insensitive(self):
        agent = self._agent()
        eu    = agent.get_for_jurisdiction("eu")
        self.assertEqual(len(eu), 1)

    def test_get_for_jurisdictions_multi(self):
        agent = self._agent()
        multi = agent.get_for_jurisdictions(["EU", "Federal"])
        self.assertEqual(len(multi), 2)

    def test_get_for_unknown_jurisdiction(self):
        agent = self._agent()
        self.assertEqual(agent.get_for_jurisdiction("JP"), [])

    def test_coverage_summary(self):
        agent    = self._agent()
        coverage = agent.get_coverage_summary()
        self.assertEqual(coverage["total"], 3)
        self.assertIn("EU",      coverage["by_jurisdiction"])
        self.assertIn("Federal", coverage["by_jurisdiction"])
        self.assertIn("GB",      coverage["by_jurisdiction"])
        self.assertEqual(coverage["last_reviewed"], "2025-01-01")

    def test_missing_index_returns_empty(self):
        from agents import baseline_agent as ba_mod
        ba_mod._BASELINES_DIR = self.tmp / "nonexistent"
        ba_mod.BaselineAgent._cache = None
        agent = ba_mod.BaselineAgent()
        self.assertEqual(agent.get_all(), [])


class TestBaselineDocumentMatching(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        _write_temp_baselines(self.tmp)
        from agents import baseline_agent as ba_mod
        ba_mod._BASELINES_DIR = self.tmp
        ba_mod.BaselineAgent._cache = None
        self.agent = ba_mod.BaselineAgent()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        from agents import baseline_agent as ba_mod
        ba_mod.BaselineAgent._cache = None

    def test_match_eu_ai_act_by_id(self):
        doc    = {"id": "EU-CELEX-32024R1689", "jurisdiction": "EU", "title": "EU AI Act"}
        result = self.agent.match_document(doc)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "eu_ai_act")

    def test_match_eu_ai_act_by_title(self):
        doc    = {"id": "EU-SOME-OTHER-ID", "jurisdiction": "EU", "title": "EU AI Act implementing regulation"}
        result = self.agent.match_document(doc)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "eu_ai_act")

    def test_match_eo_by_pattern(self):
        doc    = {"id": "FR-2023-24283", "jurisdiction": "Federal", "title": "Executive Order on AI"}
        result = self.agent.match_document(doc)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "us_eo_14110")

    def test_no_match_wrong_jurisdiction(self):
        # EU document ID but Federal jurisdiction — should not match EU AI Act
        doc    = {"id": "EU-CELEX-32024R1689", "jurisdiction": "Federal", "title": "Something"}
        result = self.agent.match_document(doc)
        self.assertIsNone(result)

    def test_no_match_unknown_doc(self):
        doc    = {"id": "UNKNOWN-DOC-999", "jurisdiction": "EU", "title": "Some random document"}
        result = self.agent.match_document(doc)
        self.assertIsNone(result)


class TestBaselineFormatting(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        _write_temp_baselines(self.tmp)
        from agents import baseline_agent as ba_mod
        ba_mod._BASELINES_DIR = self.tmp
        ba_mod.BaselineAgent._cache = None
        self.agent = ba_mod.BaselineAgent()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        from agents import baseline_agent as ba_mod
        ba_mod.BaselineAgent._cache = None

    def test_format_for_gap_analysis_contains_obligations(self):
        block = self.agent.format_for_gap_analysis(["EU"])
        self.assertIn("EU AI Act",           block)
        self.assertIn("Conformity assessment",block)
        self.assertIn("Human oversight",      block)
        self.assertIn("BASELINE",             block)

    def test_format_for_gap_analysis_multi_jurisdiction(self):
        block = self.agent.format_for_gap_analysis(["EU", "Federal"])
        self.assertIn("EU AI Act",     block)
        self.assertIn("EO 14110",      block)

    def test_format_for_gap_analysis_empty_for_unknown_jur(self):
        block = self.agent.format_for_gap_analysis(["SG"])
        self.assertEqual(block, "")

    def test_format_includes_prohibitions(self):
        block = self.agent.format_for_gap_analysis(["EU"])
        self.assertIn("PROHIBITED",          block)
        self.assertIn("Subliminal",          block)

    def test_format_includes_deadlines(self):
        block = self.agent.format_for_gap_analysis(["EU"])
        self.assertIn("2026-08-02", block)

    def test_format_for_diff_context_eu_ai_act(self):
        doc = {"id": "EU-CELEX-32024R1689", "jurisdiction": "EU", "title": "EU AI Act Amendment"}
        ctx = self.agent.format_for_diff_context(doc)
        self.assertIn("BASELINE",             ctx)
        self.assertIn("EU AI Act",            ctx)
        self.assertIn("Conformity assessment",ctx)

    def test_format_for_diff_context_no_match(self):
        doc = {"id": "UNKNOWN-DOC", "jurisdiction": "EU", "title": "Random"}
        ctx = self.agent.format_for_diff_context(doc)
        self.assertEqual(ctx, "")

    def test_format_for_diff_context_includes_timeline(self):
        doc = {"id": "EU-CELEX-32024R1689", "jurisdiction": "EU", "title": "EU AI Act"}
        ctx = self.agent.format_for_diff_context(doc)
        self.assertIn("COMPLIANCE TIMELINE", ctx)
        self.assertIn("2026-08-02",          ctx)

    def test_format_for_diff_context_includes_definitions(self):
        doc = {"id": "EU-CELEX-32024R1689", "jurisdiction": "EU", "title": "EU AI Act"}
        ctx = self.agent.format_for_diff_context(doc)
        self.assertIn("KEY DEFINITIONS", ctx)
        self.assertIn("AI system",       ctx)


class TestBaselineObligationsExtraction(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        _write_temp_baselines(self.tmp)
        from agents import baseline_agent as ba_mod
        ba_mod._BASELINES_DIR = self.tmp
        ba_mod.BaselineAgent._cache = None
        self.agent = ba_mod.BaselineAgent()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        from agents import baseline_agent as ba_mod
        ba_mod.BaselineAgent._cache = None

    def test_get_obligations_eu(self):
        obls = self.agent.get_obligations_for_jurisdiction("EU")
        self.assertGreater(len(obls), 0)
        ids  = [o.get("id") for o in obls]
        self.assertIn("eu-aia-prov-conformity", ids)
        self.assertIn("eu-aia-dep-oversight",   ids)

    def test_obligations_include_metadata(self):
        obls = self.agent.get_obligations_for_jurisdiction("EU")
        for obl in obls:
            self.assertIn("baseline_id",      obl)
            self.assertIn("regulation_title", obl)
            self.assertIn("jurisdiction",     obl)
            self.assertIn("source",           obl)
            self.assertEqual(obl["source"],   "baseline")

    def test_get_obligations_empty_for_unknown(self):
        obls = self.agent.get_obligations_for_jurisdiction("SG")
        self.assertEqual(obls, [])


class TestRealBaselineFiles(unittest.TestCase):
    """
    Tests that run against the actual baseline files shipped with the application.
    These verify that all files are present, valid JSON, and contain required fields.
    """

    REQUIRED_FIELDS = ["id", "jurisdiction", "title", "status", "overview"]
    BASELINE_IDS    = [
        "eu_ai_act", "eu_gdpr_ai", "us_eo_14110", "us_nist_ai_rmf",
        "us_ftc_ai", "uk_ai_framework", "canada_aida",
        "illinois_aipa", "colorado_ai",
    ]

    def setUp(self):
        # Always restore the real baselines directory
        from agents import baseline_agent as ba_mod
        from pathlib import Path
        ba_mod._BASELINES_DIR  = Path(__file__).parent.parent / "data" / "baselines"
        ba_mod.BaselineAgent._cache = None

    def tearDown(self):
        from agents import baseline_agent as ba_mod
        ba_mod.BaselineAgent._cache = None

    def _real_agent(self):
        from agents import baseline_agent as ba_mod
        return ba_mod.BaselineAgent()

    def test_index_file_exists(self):
        from agents import baseline_agent as ba_mod
        index_path = ba_mod._BASELINES_DIR / "index.json"
        self.assertTrue(index_path.exists(), f"Index file missing: {index_path}")

    def test_all_baseline_files_exist(self):
        from agents import baseline_agent as ba_mod
        index_path = ba_mod._BASELINES_DIR / "index.json"
        if not index_path.exists():
            self.skipTest("index.json not present")
        with open(index_path) as f:
            index = json.load(f)
        for entry in index["baselines"]:
            fp = ba_mod._BASELINES_DIR / entry["file"]
            self.assertTrue(fp.exists(), f"Baseline file missing: {fp}")

    def test_all_baseline_files_valid_json(self):
        from agents import baseline_agent as ba_mod
        index_path = ba_mod._BASELINES_DIR / "index.json"
        if not index_path.exists():
            self.skipTest("index.json not present")
        with open(index_path) as f:
            index = json.load(f)
        for entry in index["baselines"]:
            fp = ba_mod._BASELINES_DIR / entry["file"]
            if fp.exists():
                try:
                    with open(fp) as fh:
                        data = json.load(fh)
                    self.assertIsInstance(data, dict, f"{fp} is not a JSON object")
                except json.JSONDecodeError as e:
                    self.fail(f"Invalid JSON in {fp}: {e}")

    def test_all_baselines_have_required_fields(self):
        agent = self._real_agent()
        for bid in self.BASELINE_IDS:
            b = agent.get_by_id(bid)
            if b is None:
                continue
            for field in self.REQUIRED_FIELDS:
                self.assertIn(field, b, f"Baseline '{bid}' missing field '{field}'")
                self.assertIsNotNone(b[field], f"Baseline '{bid}' has null '{field}'")

    def test_eu_ai_act_has_obligations(self):
        agent = self._real_agent()
        b     = agent.get_by_id("eu_ai_act")
        if b is None:
            self.skipTest("eu_ai_act baseline not present")
        self.assertIn("obligations_by_actor",  b)
        self.assertIn("providers_high_risk",   b["obligations_by_actor"])
        self.assertGreater(len(b["obligations_by_actor"]["providers_high_risk"]), 0)

    def test_eu_ai_act_has_prohibited_practices(self):
        agent = self._real_agent()
        b     = agent.get_by_id("eu_ai_act")
        if b is None:
            self.skipTest("eu_ai_act baseline not present")
        self.assertIn("prohibited_practices", b)
        self.assertGreater(len(b["prohibited_practices"]), 0)

    def test_eu_ai_act_has_timeline(self):
        agent = self._real_agent()
        b     = agent.get_by_id("eu_ai_act")
        if b is None:
            self.skipTest("eu_ai_act baseline not present")
        self.assertIn("timeline", b)
        dates = [t["date"] for t in b["timeline"]]
        self.assertIn("2026-08-02", dates)

    def test_agent_loads_real_files(self):
        agent = self._real_agent()
        all_b = agent.get_all()
        self.assertGreaterEqual(len(all_b), 8)

    def test_coverage_summary_real(self):
        agent    = self._real_agent()
        coverage = agent.get_coverage_summary()
        self.assertGreaterEqual(coverage["total"], 8)
        self.assertIn("EU",      coverage["jurisdictions"])
        self.assertIn("Federal", coverage["jurisdictions"])
        self.assertIn("GB",      coverage["jurisdictions"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
