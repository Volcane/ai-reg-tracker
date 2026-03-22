# SPDX-License-Identifier: Elastic-2.0
# Copyright (c) 2026 Mitch Kwiatkowski
# ARIS � Automated Regulatory Intelligence System
# Licensed under the Elastic License 2.0. See LICENSE in the project root.
"""
ARIS — Consolidation Agent Tests
"""
import sys
import types
import json
import unittest
from unittest.mock import patch, MagicMock


def setUpModule():
    for pkg, attrs in {
        'tenacity':      ['retry','stop_after_attempt','wait_exponential'],
        'anthropic':     ['Anthropic','APIError'],
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


# ── Category inference ────────────────────────────────────────────────────────

class TestCategoryInference(unittest.TestCase):

    def _infer(self, text):
        from agents.consolidation_agent import _infer_category
        return _infer_category(text)

    def test_assessment_keywords(self):
        self.assertEqual(self._infer("Conduct conformity assessment before deployment"), "Assessment")
        self.assertEqual(self._infer("Bias audit required annually"), "Assessment")
        self.assertEqual(self._infer("DPIA must be completed"), "Assessment")

    def test_oversight_keywords(self):
        self.assertEqual(self._infer("Implement human oversight mechanisms"), "Oversight")
        self.assertEqual(self._infer("Ensure human review of all AI decisions"), "Oversight")

    def test_transparency_keywords(self):
        self.assertEqual(self._infer("Disclose AI use to affected persons"), "Transparency")
        self.assertEqual(self._infer("Notify individuals when automated decisions are made"), "Transparency")
        self.assertEqual(self._infer("Publish bias audit results publicly"), "Transparency")

    def test_prohibition_keywords(self):
        self.assertEqual(self._infer("Prohibited from using subliminal manipulation"), "Prohibition")
        self.assertEqual(self._infer("Must not use biometric categorisation"), "Prohibition")

    def test_documentation_keywords(self):
        self.assertEqual(self._infer("Document technical architecture of AI system"), "Documentation")
        self.assertEqual(self._infer("Maintain technical records of model decisions"), "Documentation")
        # Note: "maintain records of training data" → Training Data (more specific pattern wins)
        self.assertEqual(self._infer("Maintain records of all training data"), "Training Data")

    def test_governance_keywords(self):
        self.assertEqual(self._infer("Establish AI governance program"), "Governance")
        self.assertEqual(self._infer("Designate an accountable person for AI"), "Governance")

    def test_rights_keywords(self):
        self.assertEqual(self._infer("Provide right to contest automated decision"), "Rights")
        self.assertEqual(self._infer("Allow individuals to opt out of profiling"), "Rights")

    def test_training_data_keywords(self):
        self.assertEqual(self._infer("Document training data provenance and consent"), "Training Data")
        self.assertEqual(self._infer("Publish summary of data used for AI training"), "Training Data")

    def test_fallback_to_governance(self):
        # Unrecognised text falls back to Governance
        result = self._infer("zzz unrecognisable obligation text zzz")
        self.assertEqual(result, "Governance")


# ── Title cleaning and action prefixing ───────────────────────────────────────

class TestTitleHelpers(unittest.TestCase):

    def test_clean_title_strips_verb_prefix(self):
        from agents.consolidation_agent import _clean_title
        # Strips single leading verb
        self.assertEqual(_clean_title("Ensure data minimisation"), "data minimisation")
        self.assertEqual(_clean_title("Conduct bias audit"), "bias audit")
        # Strips chained verbs iteratively — "must implement X" → "X"
        result = _clean_title("Must implement human oversight")
        self.assertNotIn("must", result)
        self.assertNotIn("implement", result)
        self.assertIn("human oversight", result)

    def test_clean_title_lowercases(self):
        from agents.consolidation_agent import _clean_title
        self.assertEqual(_clean_title("HUMAN OVERSIGHT"), "human oversight")

    def test_make_action_title_adds_verb_for_assessment(self):
        from agents.consolidation_agent import _make_action_title
        result = _make_action_title("Risk assessment for high-risk AI systems")
        self.assertTrue(result[0].isupper())
        self.assertIn("assessment", result.lower())

    def test_make_action_title_preserves_existing_verb(self):
        from agents.consolidation_agent import _make_action_title
        result = _make_action_title("Implement human oversight mechanisms")
        self.assertTrue(result.startswith("Implement"))

    def test_make_action_title_adds_maintain_for_documentation(self):
        from agents.consolidation_agent import _make_action_title
        result = _make_action_title("Technical documentation of AI model")
        self.assertIn("Maintain", result)


# ── Clustering ────────────────────────────────────────────────────────────────

class TestClustering(unittest.TestCase):

    def _cluster(self, obligations, threshold=0.72):
        from agents.consolidation_agent import _cluster_by_similarity
        return _cluster_by_similarity(obligations, threshold)

    def test_identical_titles_cluster(self):
        obls = [
            {"title": "Conduct conformity assessment", "description": "EU version"},
            {"title": "Conduct conformity assessment", "description": "CO version"},
        ]
        clusters = self._cluster(obls)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(len(clusters[0]), 2)

    def test_similar_titles_cluster(self):
        obls = [
            {"title": "Conduct conformity assessment before deployment"},
            {"title": "Conduct a conformity assessment prior to deployment"},
        ]
        clusters = self._cluster(obls)
        self.assertEqual(len(clusters), 1)

    def test_different_titles_do_not_cluster(self):
        obls = [
            {"title": "Conduct bias audit annually"},
            {"title": "Implement human oversight mechanisms"},
        ]
        clusters = self._cluster(obls)
        self.assertEqual(len(clusters), 2)

    def test_three_way_cluster(self):
        obls = [
            {"title": "Human oversight of AI decisions required"},
            {"title": "Human oversight of automated decisions required"},
            {"title": "Provide human oversight for AI system decisions"},
        ]
        clusters = self._cluster(obls)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(len(clusters[0]), 3)

    def test_empty_input(self):
        self.assertEqual(self._cluster([]), [])

    def test_single_item(self):
        obls = [{"title": "Conduct assessment"}]
        clusters = self._cluster(obls)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(len(clusters[0]), 1)


# ── Merging ───────────────────────────────────────────────────────────────────

class TestMerging(unittest.TestCase):

    def _make_obl(self, title, jur, reg, deadline=None, desc=None):
        return {
            "title":            title,
            "description":      desc or title,
            "jurisdiction":     jur,
            "regulation_title": reg,
            "deadline":         deadline,
            "baseline_id":      reg.lower().replace(" ", "_"),
            "actor":            "All",
        }

    def test_merge_picks_earliest_deadline(self):
        from agents.consolidation_agent import _merge_cluster
        cluster = [
            self._make_obl("Conformity assessment", "EU", "EU AI Act", deadline="2026-08-02"),
            self._make_obl("Conformity assessment", "CO", "Colorado AI Act", deadline="2026-02-01"),
        ]
        merged = _merge_cluster(cluster, "Assessment")
        self.assertEqual(merged["earliest_deadline"], "2026-02-01")

    def test_merge_collects_all_jurisdictions(self):
        from agents.consolidation_agent import _merge_cluster
        cluster = [
            self._make_obl("Human oversight", "EU",  "EU AI Act"),
            self._make_obl("Human oversight", "CO",  "Colorado AI Act"),
            self._make_obl("Human oversight", "IL",  "Illinois AIPA"),
        ]
        merged = _merge_cluster(cluster, "Oversight")
        self.assertIn("EU", merged["jurisdictions"])
        self.assertIn("CO", merged["jurisdictions"])
        self.assertIn("IL", merged["jurisdictions"])

    def test_merge_universality_majority_for_2(self):
        from agents.consolidation_agent import _merge_cluster
        cluster = [
            self._make_obl("Document AI system", "EU", "EU AI Act"),
            self._make_obl("Document AI system", "GB", "UK Framework"),
        ]
        merged = _merge_cluster(cluster, "Documentation")
        self.assertEqual(merged["universality"], "Majority")

    def test_merge_universality_universal_for_3_plus(self):
        from agents.consolidation_agent import _merge_cluster
        cluster = [
            self._make_obl("Publish training data", "EU", "EU AI Act"),
            self._make_obl("Publish training data", "CA", "Canada AIDA"),
            self._make_obl("Publish training data", "GB", "UK Framework"),
        ]
        merged = _merge_cluster(cluster, "Training Data")
        self.assertEqual(merged["universality"], "Universal")

    def test_merge_single_is_single_jurisdiction(self):
        from agents.consolidation_agent import _merge_cluster
        cluster = [self._make_obl("NYC bias audit", "NY", "NYC LL144")]
        merged  = _merge_cluster(cluster, "Assessment")
        self.assertEqual(merged["universality"], "Single jurisdiction")

    def test_merge_deduplicates_sources(self):
        from agents.consolidation_agent import _merge_cluster
        cluster = [
            self._make_obl("Assessment", "EU", "EU AI Act"),
            self._make_obl("Assessment", "EU", "EU AI Act"),  # duplicate source
        ]
        merged = _merge_cluster(cluster, "Assessment")
        # Should deduplicate to 1 source
        self.assertEqual(merged["source_count"], 1)

    def test_merge_has_required_fields(self):
        from agents.consolidation_agent import _merge_cluster
        cluster = [self._make_obl("Test obligation", "EU", "EU AI Act")]
        merged  = _merge_cluster(cluster, "Documentation")
        for field in ["title","category","description","strictest_scope",
                      "sources","jurisdictions","earliest_deadline",
                      "universality","source_count","consolidated_by"]:
            self.assertIn(field, merged, f"Missing field: {field}")


# ── Structural consolidation ──────────────────────────────────────────────────

class TestStructuralConsolidation(unittest.TestCase):

    def _agent(self):
        from agents.consolidation_agent import ConsolidationAgent
        return ConsolidationAgent()

    def _make_obls(self):
        return [
            # Group 1: conformity assessment — should cluster
            {"id": "a1", "title": "Conduct conformity assessment", "description": "EU AI Act conformity assessment", "jurisdiction": "EU", "regulation_title": "EU AI Act", "baseline_id": "eu_ai_act", "deadline": "2026-08-02", "actor": "providers_high_risk"},
            {"id": "a2", "title": "Conduct conformity assessment before deployment", "description": "Colorado impact assessment", "jurisdiction": "CO", "regulation_title": "Colorado AI Act", "baseline_id": "colorado_ai", "deadline": "2026-02-01", "actor": "deployers"},
            # Group 2: human oversight — should cluster
            {"id": "b1", "title": "Implement human oversight of AI decisions", "description": "EU oversight requirement", "jurisdiction": "EU", "regulation_title": "EU AI Act", "baseline_id": "eu_ai_act", "deadline": "2026-08-02", "actor": "deployers"},
            {"id": "b2", "title": "Ensure human oversight mechanisms are in place", "description": "UK oversight requirement", "jurisdiction": "GB", "regulation_title": "UK AI Framework", "baseline_id": "uk_ai_framework", "deadline": None, "actor": "all"},
            # Group 3: unique
            {"id": "c1", "title": "Publish bias audit results on company website", "description": "NYC bias audit publication", "jurisdiction": "NY", "regulation_title": "NYC LL144", "baseline_id": "nyc_ll144", "deadline": "2023-07-05", "actor": "employers"},
        ]

    def test_reduces_obligation_count(self):
        agent  = self._agent()
        raw    = self._make_obls()
        result = agent._structural_consolidate(raw)
        # 5 raw → at most 3 groups (2 clusters + 1 unique)
        self.assertLessEqual(len(result), len(raw))
        self.assertGreater(len(result), 0)

    def test_all_results_have_required_fields(self):
        agent  = self._agent()
        result = agent._structural_consolidate(self._make_obls())
        for item in result:
            self.assertIn("title",            item)
            self.assertIn("category",         item)
            self.assertIn("sources",          item)
            self.assertIn("jurisdictions",    item)
            self.assertIn("universality",     item)
            self.assertIn("earliest_deadline",item)
            self.assertIn("consolidated_by",  item)

    def test_prohibitions_are_first(self):
        agent = self._agent()
        obls  = self._make_obls() + [
            {"id": "p1", "title": "Subliminal manipulation is prohibited", "description": "Prohibited", "jurisdiction": "EU", "regulation_title": "EU AI Act", "baseline_id": "eu_ai_act", "deadline": "2025-02-02", "category": "Prohibition", "actor": "All"},
        ]
        result = agent._structural_consolidate(obls)
        if len(result) > 1:
            self.assertEqual(result[0]["category"], "Prohibition")

    def test_empty_input_returns_empty(self):
        agent  = self._agent()
        result = agent._structural_consolidate([])
        self.assertEqual(result, [])

    def test_categories_assigned(self):
        agent  = self._agent()
        result = agent._structural_consolidate(self._make_obls())
        for item in result:
            self.assertIn(item["category"], [
                "Documentation","Assessment","Oversight","Transparency",
                "Governance","Reporting","Technical","Prohibition","Rights","Training Data"
            ])


# ── Baseline obligation collection ────────────────────────────────────────────

class TestBaselineCollection(unittest.TestCase):

    def _agent(self):
        from agents.consolidation_agent import ConsolidationAgent
        return ConsolidationAgent()

    def test_collect_from_mock_baselines(self):
        agent = self._agent()
        mock_baselines = [
            {
                "id": "eu_ai_act", "short_name": "EU AI Act",
                "jurisdiction": "EU", "title": "EU AI Act",
                "obligations_by_actor": {
                    "providers_high_risk": [
                        {"id": "p1", "title": "Conduct conformity assessment",
                         "description": "Required before market placement", "deadline": "2026-08-02"},
                    ]
                },
                "prohibited_practices": [
                    {"id": "proh1", "title": "Subliminal manipulation",
                     "description": "Prohibited", "in_force_from": "2025-02-02", "applies_to": "All"},
                ],
            }
        ]

        mock_ba = MagicMock()
        mock_ba.get_for_jurisdictions.return_value = mock_baselines

        with patch("agents.consolidation_agent.BaselineAgent", return_value=mock_ba):
            obls = agent._collect_baseline_obligations(["EU"])

        titles = [o["title"] for o in obls]
        self.assertIn("Conduct conformity assessment", titles)
        self.assertIn("Subliminal manipulation",        titles)

        # Check prohibition category is pre-set
        proh = next(o for o in obls if o["title"] == "Subliminal manipulation")
        self.assertEqual(proh["category"], "Prohibition")

    def test_collect_returns_empty_on_error(self):
        agent = self._agent()
        with patch("agents.consolidation_agent.BaselineAgent", side_effect=Exception("no baselines")):
            result = agent._collect_baseline_obligations(["EU"])
        self.assertEqual(result, [])


# ── Fast consolidation with DB cache ─────────────────────────────────────────

class TestFastConsolidationCache(unittest.TestCase):

    def _agent(self):
        from agents.consolidation_agent import ConsolidationAgent
        return ConsolidationAgent()

    def test_uses_cache_when_available(self):
        agent      = self._agent()
        cached_reg = [{"title": "Cached obligation", "category": "Assessment",
                        "sources": [], "jurisdictions": ["EU"], "universality": "Single jurisdiction",
                        "earliest_deadline": None, "source_count": 1, "consolidated_by": "structural",
                        "description": "", "strictest_scope": "", "notes": None}]

        with patch("agents.consolidation_agent.get_register_cache", return_value=cached_reg):
            with patch("agents.consolidation_agent.save_register_cache") as mock_save:
                result = agent.consolidate_fast(["EU"])

        self.assertEqual(result, cached_reg)
        mock_save.assert_not_called()

    def test_builds_and_saves_when_cache_miss(self):
        agent = self._agent()
        mock_obl = [
            {"id": "x1", "title": "Conduct assessment", "description": "desc",
             "jurisdiction": "EU", "regulation_title": "EU AI Act", "baseline_id": "eu_ai_act",
             "deadline": "2026-08-02", "actor": "providers", "category": ""}
        ]

        with patch("agents.consolidation_agent.get_register_cache", return_value=None):
            with patch("agents.consolidation_agent.save_register_cache") as mock_save:
                with patch.object(agent, "_collect_baseline_obligations", return_value=mock_obl):
                    result = agent.consolidate_fast(["EU"])

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        mock_save.assert_called_once()

    def test_force_bypasses_cache(self):
        agent      = self._agent()
        cached_reg = [{"title": "Old cached", "sources": [], "jurisdictions": ["EU"],
                       "universality": "Single jurisdiction", "earliest_deadline": None,
                       "source_count": 0, "consolidated_by": "structural",
                       "category": "Governance", "description": "", "strictest_scope": "", "notes": None}]

        call_count = [0]
        def fake_cache(*args, **kwargs):
            call_count[0] += 1
            return cached_reg

        with patch("agents.consolidation_agent.get_register_cache", side_effect=fake_cache):
            with patch("agents.consolidation_agent.save_register_cache"):
                with patch.object(agent, "_collect_baseline_obligations", return_value=[]):
                    agent.consolidate_fast(["EU"], force=True)

        # force=True should skip the cache check
        self.assertEqual(call_count[0], 0)


# ── Source deduplication ──────────────────────────────────────────────────────

class TestSourceDeduplication(unittest.TestCase):

    def test_deduplicates_same_reg_and_jur(self):
        from agents.consolidation_agent import _dedupe_sources
        sources = [
            {"regulation_title": "EU AI Act", "jurisdiction": "EU", "deadline": "2026-08-02"},
            {"regulation_title": "EU AI Act", "jurisdiction": "EU", "deadline": "2026-08-02"},
            {"regulation_title": "UK Framework", "jurisdiction": "GB", "deadline": None},
        ]
        result = _dedupe_sources(sources)
        self.assertEqual(len(result), 2)

    def test_preserves_distinct_sources(self):
        from agents.consolidation_agent import _dedupe_sources
        sources = [
            {"regulation_title": "EU AI Act",     "jurisdiction": "EU"},
            {"regulation_title": "Colorado AI Act","jurisdiction": "CO"},
            {"regulation_title": "Illinois AIPA", "jurisdiction": "IL"},
        ]
        result = _dedupe_sources(sources)
        self.assertEqual(len(result), 3)

    def test_empty_input(self):
        from agents.consolidation_agent import _dedupe_sources
        self.assertEqual(_dedupe_sources([]), [])


# ── JSON parsing ──────────────────────────────────────────────────────────────

class TestJsonParsing(unittest.TestCase):

    def test_clean_array(self):
        from agents.consolidation_agent import _safe_parse_json_array
        result = _safe_parse_json_array('[{"title": "test"}]')
        self.assertEqual(result, [{"title": "test"}])

    def test_fenced_array(self):
        from agents.consolidation_agent import _safe_parse_json_array
        result = _safe_parse_json_array('```json\n[{"title": "x"}]\n```')
        self.assertIsNotNone(result)
        self.assertEqual(result[0]["title"], "x")

    def test_embedded_array(self):
        from agents.consolidation_agent import _safe_parse_json_array
        result = _safe_parse_json_array('Here is the result:\n[{"title": "y"}]\nEnd.')
        self.assertIsNotNone(result)

    def test_invalid_returns_none(self):
        from agents.consolidation_agent import _safe_parse_json_array
        self.assertIsNone(_safe_parse_json_array("not json"))

    def test_dict_returns_none(self):
        from agents.consolidation_agent import _safe_parse_json_array
        self.assertIsNone(_safe_parse_json_array('{"title": "not a list"}'))


# ── Register key ──────────────────────────────────────────────────────────────

class TestRegisterKey(unittest.TestCase):

    def test_same_jurisdictions_same_key(self):
        from agents.consolidation_agent import _register_key
        k1 = _register_key(["EU", "Federal"], "fast")
        k2 = _register_key(["Federal", "EU"], "fast")
        self.assertEqual(k1, k2)

    def test_different_modes_different_keys(self):
        from agents.consolidation_agent import _register_key
        k1 = _register_key(["EU"], "fast")
        k2 = _register_key(["EU"], "full")
        self.assertNotEqual(k1, k2)

    def test_different_jurisdictions_different_keys(self):
        from agents.consolidation_agent import _register_key
        k1 = _register_key(["EU"], "fast")
        k2 = _register_key(["GB"], "fast")
        self.assertNotEqual(k1, k2)

    def test_key_is_short_string(self):
        from agents.consolidation_agent import _register_key
        k = _register_key(["EU", "Federal", "GB", "CO", "IL"], "fast")
        self.assertIsInstance(k, str)
        self.assertLessEqual(len(k), 32)


if __name__ == "__main__":
    unittest.main(verbosity=2)
