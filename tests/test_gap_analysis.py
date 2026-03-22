# SPDX-License-Identifier: Elastic-2.0
# Copyright (c) 2026 Mitch Kwiatkowski
# ARIS � Automated Regulatory Intelligence System
# Licensed under the Elastic License 2.0. See LICENSE in the project root.
"""
ARIS — Gap Analysis Agent Tests
"""
import sys
import types
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock


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


# ── Profile formatting tests ──────────────────────────────────────────────────

class TestProfileFormatting(unittest.TestCase):

    def _make_profile(self, **overrides):
        base = {
            "id":   1,
            "name": "Acme Corp — Healthcare Division",
            "industry_sector":         "Healthcare",
            "company_size":            "Enterprise (1000-10000)",
            "operating_jurisdictions": ["EU", "Federal"],
            "ai_systems": [
                {
                    "name":               "Patient Risk Scorer",
                    "description":        "ML model predicting patient readmission risk",
                    "purpose":            "Triages patients for follow-up care",
                    "data_inputs":        ["Health/medical data", "Personal data (PII)"],
                    "affected_population": "Patients",
                    "deployment_status":  "production",
                    "autonomy_level":     "human-in-loop",
                }
            ],
            "current_practices": {
                "has_ai_governance_policy":     True,
                "has_risk_assessments":         False,
                "has_human_oversight":          True,
                "has_incident_response":        None,
                "has_documentation":            True,
                "has_bias_testing":             False,
                "has_transparency_disclosures": None,
                "notes": "Risk assessments are informal only",
            },
            "existing_certifications": ["ISO 27001"],
            "primary_concerns": "EU AI Act obligations for high-risk medical AI",
        }
        base.update(overrides)
        return base

    def test_profile_block_contains_name(self):
        from agents.gap_analysis_agent import _format_profile
        profile = self._make_profile()
        block   = _format_profile(profile)
        self.assertIn("Acme Corp", block)
        self.assertIn("Healthcare", block)

    def test_profile_block_contains_jurisdictions(self):
        from agents.gap_analysis_agent import _format_profile
        profile = self._make_profile()
        block   = _format_profile(profile)
        self.assertIn("EU", block)
        self.assertIn("Federal", block)

    def test_profile_block_contains_ai_systems(self):
        from agents.gap_analysis_agent import _format_profile
        profile = self._make_profile()
        block   = _format_profile(profile)
        self.assertIn("Patient Risk Scorer", block)
        self.assertIn("production", block)
        self.assertIn("human-in-loop", block)
        self.assertIn("Health/medical data", block)

    def test_profile_block_shows_practices(self):
        from agents.gap_analysis_agent import _format_profile
        profile = self._make_profile()
        block   = _format_profile(profile)
        self.assertIn("AI governance policy", block)
        self.assertIn("✓", block)   # has_ai_governance_policy = True
        self.assertIn("✗", block)   # has_risk_assessments = False

    def test_profile_block_excludes_none_practices(self):
        """Practices set to None (unsure) are intentionally omitted — no Yes/No to show."""
        from agents.gap_analysis_agent import _format_profile
        profile = self._make_profile()
        block   = _format_profile(profile)
        # has_incident_response = None — should NOT appear with Yes/No symbol
        # (Claude infers "unknown/unsure" from absence rather than noise)
        self.assertNotIn("incident response plan\n  ✓", block)
        self.assertNotIn("incident response plan\n  ✗", block)
        # But the block should still contain things that ARE set
        self.assertIn("AI governance policy", block)
        self.assertIn("✓", block)
        self.assertIn("✗", block)

    def test_system_filter_limits_systems(self):
        from agents.gap_analysis_agent import _format_profile
        profile = self._make_profile()
        profile["ai_systems"].append({
            "name": "HR Resume Screener", "description": "Filters resumes",
            "purpose": "Hiring", "data_inputs": ["Employment data"],
            "affected_population": "Job applicants", "deployment_status": "production",
            "autonomy_level": "fully automated",
        })
        # Filter to HR system only
        block = _format_profile(profile, system_filter=["HR Resume Screener"])
        self.assertIn("HR Resume Screener", block)
        self.assertNotIn("Patient Risk Scorer", block)

    def test_certifications_included(self):
        from agents.gap_analysis_agent import _format_profile
        profile = self._make_profile()
        block   = _format_profile(profile)
        self.assertIn("ISO 27001", block)


class TestDocumentFormatting(unittest.TestCase):

    def test_format_docs_for_scope(self):
        from agents.gap_analysis_agent import _format_docs_for_scope
        docs = [
            {
                "id":           "EU-CELEX-32024R1689",
                "title":        "EU AI Act",
                "jurisdiction": "EU",
                "doc_type":     "Regulation",
                "status":       "In Force",
                "urgency":      "Critical",
                "plain_english":"Risk-based framework for AI systems.",
                "requirements": ["Must register high-risk AI systems"],
                "impact_areas": ["Healthcare AI"],
                "deadline":     "2026-08-02",
            }
        ]
        result = _format_docs_for_scope(docs)
        self.assertIn("EU-CELEX-32024R1689", result)
        self.assertIn("EU AI Act",            result)
        self.assertIn("Must register",        result)
        self.assertIn("Healthcare AI",        result)
        self.assertIn("2026-08-02",           result)

    def test_format_obligations(self):
        from agents.gap_analysis_agent import _format_obligations
        applicable = [
            {
                "document_id":  "EU-CELEX-32024R1689",
                "title":        "EU AI Act",
                "jurisdiction": "EU",
                "why_applicable": "Company's patient risk scorer qualifies as high-risk AI under Annex III.",
                "triggered_provisions": [
                    {
                        "provision":        "Must conduct conformity assessment before market placement",
                        "triggered_by":     "Patient Risk Scorer in production for healthcare",
                        "deadline":         "2026-08-02",
                        "severity_if_missed": "Critical",
                    }
                ],
            }
        ]
        result = _format_obligations(applicable)
        self.assertIn("EU-CELEX-32024R1689",        result)
        self.assertIn("conformity assessment",       result)
        self.assertIn("Critical",                    result)
        self.assertIn("2026-08-02",                  result)
        self.assertIn("Patient Risk Scorer",         result)


class TestSafeParseJson(unittest.TestCase):

    def test_clean_json(self):
        from agents.gap_analysis_agent import _safe_parse_json
        data = _safe_parse_json('{"posture_score": 42, "gaps": []}')
        self.assertEqual(data["posture_score"], 42)

    def test_fenced_json(self):
        from agents.gap_analysis_agent import _safe_parse_json
        raw  = '```json\n{"posture_score": 55}\n```'
        data = _safe_parse_json(raw)
        self.assertEqual(data["posture_score"], 55)

    def test_invalid_json(self):
        from agents.gap_analysis_agent import _safe_parse_json
        self.assertIsNone(_safe_parse_json("not json"))

    def test_embedded_json(self):
        from agents.gap_analysis_agent import _safe_parse_json
        raw  = 'Here is the analysis:\n{"gaps": [], "posture_score": 80}\nEnd.'
        data = _safe_parse_json(raw)
        self.assertIsNotNone(data)
        self.assertEqual(data["posture_score"], 80)


class TestGapAnalysisAgent(unittest.TestCase):

    def _make_agent(self, scope_response, gap_response):
        from agents.gap_analysis_agent import GapAnalysisAgent
        agent = GapAnalysisAgent.__new__(GapAnalysisAgent)
        responses = [scope_response, gap_response]
        call_count = [0]

        def mock_call(prompt, system, max_tokens):
            r = responses[min(call_count[0], len(responses) - 1)]
            call_count[0] += 1
            return r

        agent._call_claude = mock_call
        return agent

    def _sample_scope(self):
        return {
            "applicable_regulations": [
                {
                    "document_id":  "EU-CELEX-32024R1689",
                    "title":        "EU AI Act",
                    "jurisdiction": "EU",
                    "why_applicable": "Healthcare AI system qualifies as high-risk",
                    "triggered_provisions": [
                        {
                            "provision": "Conformity assessment required",
                            "triggered_by": "Patient Risk Scorer in production",
                            "deadline": "2026-08-02",
                            "severity_if_missed": "Critical",
                        }
                    ],
                }
            ],
            "out_of_scope":    [],
            "coverage_note":   "Analysis covers all available documents for EU and Federal.",
        }

    def _sample_gaps(self):
        return {
            "posture_summary":  "Significant gaps in formal documentation and conformity assessment processes.",
            "posture_score":    38,
            "gaps": [
                {
                    "gap_id":           "eu-ai-act-conformity-patient-scorer",
                    "title":            "No conformity assessment for Patient Risk Scorer",
                    "severity":         "Critical",
                    "document_id":      "EU-CELEX-32024R1689",
                    "regulation_title": "EU AI Act",
                    "jurisdiction":     "EU",
                    "obligation":       "High-risk AI systems must undergo conformity assessment",
                    "current_state":    "No formal risk assessment process documented",
                    "gap_description":  "Patient Risk Scorer is in production with no conformity assessment",
                    "deadline":         "2026-08-02",
                    "affected_systems": ["Patient Risk Scorer"],
                    "first_action":     "Engage an accredited conformity assessment body",
                    "effort_estimate":  "High",
                }
            ],
            "compliant_areas": [
                {
                    "area":        "Human oversight of AI decisions",
                    "document_ids":["EU-CELEX-32024R1689"],
                    "evidence":    "Company has human-in-loop for Patient Risk Scorer",
                }
            ],
            "priority_roadmap": [
                {
                    "phase":   "Phase 1: Immediate (0-30 days)",
                    "actions": ["Engage conformity assessment body", "Document current system architecture"],
                }
            ],
        }

    def test_run_returns_structured_result(self):
        agent = self._make_agent(self._sample_scope(), self._sample_gaps())
        mock_profile = {
            "id": 1, "name": "Acme Corp", "industry_sector": "Healthcare",
            "company_size": "Enterprise", "operating_jurisdictions": ["EU"],
            "ai_systems": [{"name": "Patient Risk Scorer", "data_inputs": ["Health/medical data"],
                            "purpose": "Triage", "deployment_status": "production",
                            "autonomy_level": "human-in-loop", "affected_population": "Patients",
                            "description": "ML model"}],
            "current_practices": {"has_risk_assessments": False, "has_ai_governance_policy": True},
            "existing_certifications": [],
        }
        mock_docs = [
            {
                "id": "EU-CELEX-32024R1689", "title": "EU AI Act", "jurisdiction": "EU",
                "doc_type": "Regulation", "status": "In Force", "urgency": "Critical",
                "plain_english": "Risk-based framework", "requirements": ["Must assess high-risk AI"],
                "impact_areas": ["Healthcare AI"], "deadline": "2026-08-02",
                "relevance_score": 1.0,
            }
        ]

        with patch("agents.gap_analysis_agent.get_profile", return_value=mock_profile):
            with patch("agents.gap_analysis_agent.get_recent_summaries", return_value=mock_docs):
                with patch("agents.gap_analysis_agent.save_gap_analysis", return_value=7):
                    result = agent.run(profile_id=1, jurisdictions=["EU"])

        self.assertIsNone(result.get("error"))
        self.assertEqual(result["profile_id"],    1)
        self.assertEqual(result["profile_name"],  "Acme Corp")
        self.assertEqual(result["gap_count"],     1)
        self.assertEqual(result["critical_count"],1)
        self.assertEqual(result["posture_score"], 38)
        self.assertIsNotNone(result["scope"])
        self.assertIsNotNone(result["gaps_result"])

    def test_run_returns_error_no_docs(self):
        agent = self._make_agent({}, {})
        mock_profile = {
            "id": 1, "name": "Test Corp", "operating_jurisdictions": ["EU"],
            "ai_systems": [], "current_practices": {},
        }
        with patch("agents.gap_analysis_agent.get_profile", return_value=mock_profile):
            with patch("agents.gap_analysis_agent.get_recent_summaries", return_value=[]):
                result = agent.run(profile_id=1)
        self.assertIn("error", result)

    def test_run_returns_error_no_profile(self):
        agent = self._make_agent({}, {})
        with patch("agents.gap_analysis_agent.get_profile", return_value=None):
            with self.assertRaises(ValueError):
                agent.run(profile_id=999)

    def test_scope_no_applicable_returns_error(self):
        agent = self._make_agent(
            {"applicable_regulations": [], "out_of_scope": [], "coverage_note": ""},
            {}
        )
        mock_profile = {
            "id": 1, "name": "Test", "operating_jurisdictions": ["EU"],
            "ai_systems": [], "current_practices": {},
        }
        mock_docs = [{"id": "D1", "title": "Some doc", "jurisdiction": "EU",
                      "doc_type": "Rule", "status": "Active", "urgency": "Low",
                      "plain_english": "text", "requirements": [], "impact_areas": [],
                      "relevance_score": 0.5}]
        with patch("agents.gap_analysis_agent.get_profile", return_value=mock_profile):
            with patch("agents.gap_analysis_agent.get_recent_summaries", return_value=mock_docs):
                result = agent.run(profile_id=1)
        self.assertIn("error", result)


class TestGapDatabase(unittest.TestCase):

    def setUp(self):
        import utils.db as db_module
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from utils.db import Base
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        db_module._engine  = engine
        db_module._Session = sessionmaker(bind=engine)

    def _make_profile(self, name="Test Corp"):
        return {
            "name":                    name,
            "industry_sector":         "Technology",
            "company_size":            "SME (50-250)",
            "operating_jurisdictions": ["EU", "Federal"],
            "ai_systems": [
                {
                    "name":               "Content Moderator",
                    "description":        "NLP model for content moderation",
                    "purpose":            "Detect policy-violating content",
                    "data_inputs":        ["Behavioral/inferred data", "Personal data (PII)"],
                    "affected_population": "Platform users",
                    "deployment_status":  "production",
                    "autonomy_level":     "human-in-loop",
                }
            ],
            "current_practices": {
                "has_ai_governance_policy":     True,
                "has_risk_assessments":         False,
                "has_human_oversight":          True,
                "has_bias_testing":             None,
                "notes":                        "Governance policy is 6 months old",
            },
            "existing_certifications": ["SOC 2"],
            "primary_concerns":        "DSA content moderation AI obligations",
        }

    def test_save_and_retrieve_profile(self):
        from utils.db import save_profile, get_profile
        pid = save_profile(self._make_profile())
        self.assertIsInstance(pid, int)

        profile = get_profile(pid)
        self.assertIsNotNone(profile)
        self.assertEqual(profile["name"],           "Test Corp")
        self.assertEqual(profile["industry_sector"],"Technology")
        self.assertIn("EU", profile["operating_jurisdictions"])
        self.assertEqual(len(profile["ai_systems"]), 1)
        self.assertEqual(profile["ai_systems"][0]["name"], "Content Moderator")

    def test_update_profile(self):
        from utils.db import save_profile, get_profile
        pid = save_profile(self._make_profile())
        profile = get_profile(pid)
        profile["name"] = "Test Corp — Updated"
        save_profile(profile)
        updated = get_profile(pid)
        self.assertEqual(updated["name"], "Test Corp — Updated")

    def test_list_profiles(self):
        from utils.db import save_profile, list_profiles
        save_profile(self._make_profile("Alpha Corp"))
        save_profile(self._make_profile("Beta Corp"))
        profiles = list_profiles()
        self.assertEqual(len(profiles), 2)
        names = {p["name"] for p in profiles}
        self.assertIn("Alpha Corp", names)
        self.assertIn("Beta Corp",  names)

    def test_delete_profile(self):
        from utils.db import save_profile, get_profile, delete_profile
        pid = save_profile(self._make_profile())
        self.assertIsNotNone(get_profile(pid))
        delete_profile(pid)
        self.assertIsNone(get_profile(pid))

    def test_save_and_retrieve_gap_analysis(self):
        from utils.db import save_profile, save_gap_analysis, get_gap_analysis
        pid = save_profile(self._make_profile())
        result = {
            "profile_id":    pid,
            "profile_name":  "Test Corp",
            "jurisdictions": ["EU", "Federal"],
            "docs_examined": 12,
            "applicable_count": 4,
            "gap_count":     3,
            "critical_count":1,
            "posture_score": 55,
            "scope":         {"applicable_regulations": []},
            "gaps_result":   {
                "posture_summary": "Some gaps found.",
                "posture_score":   55,
                "gaps": [{"gap_id": "x", "severity": "Critical", "title": "Test gap"}],
                "compliant_areas": [],
                "priority_roadmap": [],
            },
            "model_used":    "claude-test",
        }
        aid = save_gap_analysis(result)
        self.assertIsInstance(aid, int)

        analysis = get_gap_analysis(aid)
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis["profile_id"],    pid)
        self.assertEqual(analysis["gap_count"],     3)
        self.assertEqual(analysis["critical_count"],1)
        self.assertEqual(analysis["posture_score"], 55)
        self.assertIn("gaps",      analysis["gaps_result"])
        self.assertIn("applicable_regulations", analysis["scope"])

    def test_list_gap_analyses(self):
        from utils.db import save_profile, save_gap_analysis, list_gap_analyses
        pid = save_profile(self._make_profile())
        for i in range(3):
            save_gap_analysis({
                "profile_id": pid, "profile_name": "Test Corp",
                "jurisdictions": ["EU"], "docs_examined": 5+i,
                "applicable_count": 2, "gap_count": i, "critical_count": 0,
                "posture_score": 70+i*5, "scope": {}, "gaps_result": {}, "model_used": "test",
            })
        analyses = list_gap_analyses(profile_id=pid)
        self.assertEqual(len(analyses), 3)
        # Summary only — no full scope/gaps_result
        for a in analyses:
            self.assertNotIn("scope",       a)
            self.assertNotIn("gaps_result", a)

    def test_star_and_annotate_analysis(self):
        from utils.db import save_profile, save_gap_analysis, get_gap_analysis, star_gap_analysis, annotate_gap_analysis
        pid = save_profile(self._make_profile())
        aid = save_gap_analysis({
            "profile_id": pid, "profile_name": "Test",
            "jurisdictions": [], "docs_examined": 1, "applicable_count": 1,
            "gap_count": 0, "critical_count": 0, "posture_score": 90,
            "scope": {}, "gaps_result": {}, "model_used": "test",
        })
        self.assertFalse(get_gap_analysis(aid)["starred"])
        star_gap_analysis(aid, True)
        self.assertTrue(get_gap_analysis(aid)["starred"])

        annotate_gap_analysis(aid, "Reviewed by legal team 2025-03-15")
        self.assertIn("legal team", get_gap_analysis(aid)["notes"])

    def test_stats_include_gap_counts(self):
        from utils.db import save_profile, get_stats
        save_profile(self._make_profile("Stats Test Corp"))
        stats = get_stats()
        self.assertIn("company_profiles", stats)
        self.assertIn("gap_analyses",     stats)
        self.assertEqual(stats["company_profiles"], 1)
        self.assertEqual(stats["gap_analyses"],     0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
