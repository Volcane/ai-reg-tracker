"""
ARIS — Synthesis Agent Tests
"""
import sys
import types
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
import json


def setUpModule():
    """Apply all necessary mocks before any synthesis_agent imports fire."""
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
    # tenacity.retry must be a passthrough decorator, not a callable that returns None
    sys.modules['tenacity'].retry = lambda **k: (lambda f: f)


class TestSynthesisHelpers(unittest.TestCase):

    def test_topic_key_stable(self):
        from agents.synthesis_agent import _topic_key
        k1 = _topic_key("AI in healthcare", ["EU", "Federal"])
        k2 = _topic_key("AI in healthcare", ["Federal", "EU"])  # order shouldn't matter
        self.assertEqual(k1, k2)

    def test_topic_key_different_topics(self):
        from agents.synthesis_agent import _topic_key
        k1 = _topic_key("AI in healthcare", None)
        k2 = _topic_key("AI in hiring",     None)
        self.assertNotEqual(k1, k2)

    def test_topic_key_different_jurisdictions(self):
        from agents.synthesis_agent import _topic_key
        k1 = _topic_key("AI regulation", ["EU"])
        k2 = _topic_key("AI regulation", ["GB"])
        self.assertNotEqual(k1, k2)

    def test_topic_key_16_chars(self):
        from agents.synthesis_agent import _topic_key
        key = _topic_key("some topic", None)
        self.assertEqual(len(key), 16)

    def test_relevance_to_topic_exact_match(self):
        from agents.synthesis_agent import _relevance_to_topic
        doc = {
            "title":         "Artificial Intelligence in Healthcare Regulation",
            "plain_english": "This rule governs AI systems used in clinical settings.",
            "impact_areas":  ["Healthcare AI"],
            "requirements":  ["Must register AI systems used for diagnosis"],
        }
        score = _relevance_to_topic(doc, "ai in healthcare", {"ai", "in", "healthcare"})
        # Score should be meaningfully above zero — topic words appear in title and impact areas
        self.assertGreater(score, 0.10)

    def test_relevance_to_topic_no_match(self):
        from agents.synthesis_agent import _relevance_to_topic
        doc = {
            "title":         "Farm Subsidy Allocation Act 2024",
            "plain_english": "This act allocates funds to grain farmers.",
            "impact_areas":  ["Agriculture"],
            "requirements":  [],
        }
        score = _relevance_to_topic(doc, "ai hiring algorithms", {"ai", "hiring", "algorithms"})
        self.assertLess(score, 0.05)

    def test_relevance_title_boost(self):
        from agents.synthesis_agent import _relevance_to_topic
        doc_title_match = {
            "title":         "AI Hiring Algorithm Regulations",
            "plain_english": "Covers employment systems.",
            "impact_areas":  [],
        }
        doc_body_only = {
            "title":         "Employment Regulations 2024",
            "plain_english": "AI hiring algorithm systems must be disclosed to applicants.",
            "impact_areas":  [],
        }
        topic_words = {"ai", "hiring", "algorithm"}
        score_title = _relevance_to_topic(doc_title_match, "ai hiring algorithm", topic_words)
        score_body  = _relevance_to_topic(doc_body_only,   "ai hiring algorithm", topic_words)
        self.assertGreater(score_title, score_body)

    def test_format_doc_for_synthesis(self):
        from agents.synthesis_agent import _format_doc_for_synthesis
        doc = {
            "title":          "EU AI Act",
            "jurisdiction":   "EU",
            "doc_type":       "Regulation",
            "status":         "In Force",
            "published_date": "2024-07-12",
            "plain_english":  "Establishes risk-based AI framework.",
            "requirements":   ["Must register high-risk AI systems"],
            "action_items":   ["Conduct conformity assessment"],
            "deadline":       "2026-08-02",
            "impact_areas":   ["Product Development"],
        }
        result = _format_doc_for_synthesis(1, doc)
        self.assertIn("[1]",           result)
        self.assertIn("EU AI Act",     result)
        self.assertIn("EU",            result)
        self.assertIn("Regulation",    result)
        self.assertIn("risk-based",    result)
        self.assertIn("Must register", result)
        self.assertIn("2026-08-02",    result)

    def test_format_jurisdiction_block(self):
        from agents.synthesis_agent import _format_jurisdiction_block
        docs = [
            {
                "title":         "GDPR Enforcement on AI",
                "doc_type":      "Regulation",
                "status":        "In Force",
                "plain_english": "GDPR applies to AI systems processing personal data.",
                "requirements":  ["Must obtain valid consent for AI training data"],
            }
        ]
        synthesis = {
            "cumulative_obligations": [
                {
                    "obligation": "Must register high-risk AI",
                    "source_jurisdictions": ["EU"],
                }
            ]
        }
        result = _format_jurisdiction_block("EU", docs, synthesis)
        self.assertIn("=== EU ===",      result)
        self.assertIn("[OBLIGATION]",    result)
        self.assertIn("Must register",   result)
        self.assertIn("GDPR Enforcement",result)

    def test_safe_parse_json_clean(self):
        from agents.synthesis_agent import _safe_parse_json
        data = _safe_parse_json('{"topic": "healthcare", "landscape_summary": "test"}')
        self.assertEqual(data["topic"], "healthcare")

    def test_safe_parse_json_fenced(self):
        from agents.synthesis_agent import _safe_parse_json
        raw  = '```json\n{"conflict_summary": "minor"}\n```'
        data = _safe_parse_json(raw)
        self.assertEqual(data["conflict_summary"], "minor")

    def test_safe_parse_json_invalid(self):
        from agents.synthesis_agent import _safe_parse_json
        self.assertIsNone(_safe_parse_json("not json at all"))


class TestSynthesisAgentDocGathering(unittest.TestCase):

    def _make_agent(self):
        from agents.synthesis_agent import SynthesisAgent
        agent = SynthesisAgent.__new__(SynthesisAgent)
        agent._client = MagicMock()
        return agent

    def test_gather_filters_by_jurisdiction(self):
        agent = self._make_agent()
        mock_summaries = [
            {"id": "EU-1", "jurisdiction": "EU",      "title": "AI Act Obligations",
             "plain_english": "AI regulation in EU", "impact_areas": ["AI Governance"],
             "requirements": [], "published_date": "2024-07-12"},
            {"id": "US-1", "jurisdiction": "Federal", "title": "Federal AI Policy",
             "plain_english": "US federal AI rules",  "impact_areas": ["AI Policy"],
             "requirements": [], "published_date": "2024-01-15"},
            {"id": "PA-1", "jurisdiction": "PA",      "title": "PA AI Disclosure Bill",
             "plain_english": "Pennsylvania AI",       "impact_areas": ["AI Disclosure"],
             "requirements": [], "published_date": "2024-03-10"},
        ]
        with patch("agents.synthesis_agent.get_recent_summaries", return_value=mock_summaries):
            # Filter to EU only
            docs = agent._gather_documents("AI regulation", ["EU"], days=365)
            jurs = {d["jurisdiction"] for d in docs}
            self.assertEqual(jurs, {"EU"})

    def test_gather_returns_most_relevant_first(self):
        agent = self._make_agent()
        mock_summaries = [
            {"id": "A", "jurisdiction": "EU", "title": "AI Governance Framework",
             "plain_english": "AI governance requirements for EU companies",
             "impact_areas": ["AI Governance"], "requirements": ["Must comply with AI governance rules"],
             "published_date": "2024-07-12"},
            {"id": "B", "jurisdiction": "EU", "title": "Environmental Policy 2024",
             "plain_english": "Carbon emissions reporting requirements",
             "impact_areas": ["Environment"], "requirements": [],
             "published_date": "2024-01-01"},
        ]
        with patch("agents.synthesis_agent.get_recent_summaries", return_value=mock_summaries):
            docs = agent._gather_documents("AI governance", None, days=365)
        # "AI Governance Framework" should rank above "Environmental Policy"
        if len(docs) >= 2:
            self.assertEqual(docs[0]["id"], "A")

    def test_list_suggested_topics(self):
        agent = self._make_agent()
        mock_summaries = [
            {"jurisdiction": "EU",      "urgency": "High",   "impact_areas": ["Healthcare AI", "AI Governance"]},
            {"jurisdiction": "Federal", "urgency": "Medium", "impact_areas": ["Healthcare AI"]},
            {"jurisdiction": "GB",      "urgency": "Low",    "impact_areas": ["Healthcare AI"]},
            {"jurisdiction": "EU",      "urgency": "Critical","impact_areas": ["Hiring Algorithms"]},
            {"jurisdiction": "Federal", "urgency": "High",   "impact_areas": ["Hiring Algorithms"]},
        ]
        with patch("agents.synthesis_agent.get_recent_summaries", return_value=mock_summaries):
            suggestions = agent.list_suggested_topics()

        self.assertIsInstance(suggestions, list)
        # Healthcare AI should appear with 3 jurisdictions
        healthcare = next((s for s in suggestions if s["topic"] == "Healthcare AI"), None)
        self.assertIsNotNone(healthcare)
        self.assertEqual(healthcare["jurisdiction_count"], 3)
        # Single-jurisdiction or single-doc topics should be filtered
        for s in suggestions:
            self.assertGreaterEqual(s["jurisdiction_count"], 2)
            self.assertGreaterEqual(s["doc_count"], 2)


class TestSynthesisAgentClaudeIntegration(unittest.TestCase):

    def _make_agent_with_response(self, synth_response, conflict_response=None):
        from agents.synthesis_agent import SynthesisAgent
        agent = SynthesisAgent.__new__(SynthesisAgent)

        responses = [synth_response]
        if conflict_response:
            responses.append(conflict_response)

        call_count = [0]
        def mock_call(prompt, system, max_tokens):
            result = responses[min(call_count[0], len(responses)-1)]
            call_count[0] += 1
            return result

        agent._call_claude = mock_call
        return agent

    def test_run_synthesis_returns_structured_result(self):
        synth = {
            "topic":            "AI in healthcare",
            "landscape_summary":"Multiple jurisdictions are converging on risk-based AI frameworks for healthcare.",
            "regulatory_maturity": "Developing",
            "evolution_narrative": "Rules are tightening across all jurisdictions.",
            "cumulative_obligations": [
                {
                    "obligation": "Must conduct clinical validation before deployment",
                    "source_jurisdictions": ["EU", "Federal"],
                    "applies_to": "AI medical device providers",
                    "earliest_deadline": "2026-08-02",
                    "universality": "Majority",
                }
            ],
            "cumulative_prohibitions":  [],
            "enforcement_landscape":    {"strictest_jurisdiction": "EU", "max_penalty_summary": "Up to 7% global revenue", "enforcement_gaps": "None identified"},
            "regulatory_gaps":          ["No rules on AI explainability in emergency medicine"],
            "emerging_trends":          ["Increasing focus on human oversight requirements"],
            "key_definitions_compared": [],
            "recommended_compliance_posture": "Adopt the EU AI Act's conformity assessment as your baseline.",
        }
        conflict = {
            "conflict_summary": "Two material conflicts identified.",
            "conflicts": [
                {
                    "conflict_id":         "eu-us-consent",
                    "title":               "AI Training Data Consent Requirements",
                    "type":                "Direct Conflict",
                    "severity":            "High",
                    "jurisdiction_a":      "EU",
                    "jurisdiction_b":      "Federal",
                    "jurisdiction_a_position": "Requires explicit opt-in consent for all training data",
                    "jurisdiction_b_position": "No explicit consent requirement for de-identified data",
                    "conflict_description":"EU requires opt-in; US permits de-identified data without consent",
                    "practical_impact":    "Company must implement opt-in consent even for US-only training data if EU users are included",
                    "affected_companies":  "All companies training AI on healthcare data with any EU users",
                    "resolution_options":  ["Implement EU-standard opt-in consent globally"],
                    "safest_approach":     "Treat all healthcare training data as requiring explicit opt-in consent",
                }
            ],
            "harmonised_areas":              [{"area": "Risk documentation", "jurisdictions": ["EU", "Federal"], "description": "Both require risk assessment documentation"}],
            "highest_common_denominator":    "Implement EU-level compliance everywhere.",
            "jurisdiction_risk_ranking":     [{"jurisdiction": "EU", "compliance_complexity": "High", "rationale": "Most prescriptive requirements"}],
        }

        agent = self._make_agent_with_response(synth, conflict)
        docs  = [
            {"id": "EU-1",  "jurisdiction": "EU",      "title": "EU AI Act",      "plain_english": "Risk-based AI framework.", "requirements": ["Must register high-risk AI"], "impact_areas": ["Healthcare AI"], "action_items": [], "published_date": "2024-07-12", "doc_type": "Regulation", "status": "In Force"},
            {"id": "US-1",  "jurisdiction": "Federal", "title": "FDA AI Guidance", "plain_english": "FDA AI medical device rules.", "requirements": ["Must submit premarket notification"], "impact_areas": ["Healthcare AI"], "action_items": [], "published_date": "2024-01-15", "doc_type": "Guidance", "status": "Published"},
        ]

        with patch("agents.synthesis_agent.get_existing_synthesis", return_value=None):
            with patch("agents.synthesis_agent.save_synthesis", return_value=42):
                with patch("agents.synthesis_agent.get_recent_summaries", return_value=docs):
                    result = agent.run(
                        topic="AI in healthcare",
                        jurisdictions=None,
                        days=365,
                        detect_conflicts=True,
                        force_refresh=True,
                    )

        self.assertIsNone(result.get("error"))
        self.assertEqual(result["topic"], "AI in healthcare")
        self.assertIn("synthesis",  result)
        self.assertIn("conflicts",  result)
        self.assertIsNotNone(result["synthesis"])
        self.assertIsNotNone(result["conflicts"])
        self.assertEqual(result["synthesis"]["regulatory_maturity"], "Developing")
        self.assertEqual(len(result["conflicts"]["conflicts"]), 1)
        self.assertEqual(result["conflicts"]["conflicts"][0]["severity"], "High")

    def test_run_returns_error_when_no_docs(self):
        agent = self._make_agent_with_response({})

        with patch("agents.synthesis_agent.get_recent_summaries", return_value=[]):
            with patch("agents.synthesis_agent.get_existing_synthesis", return_value=None):
                result = agent.run(
                    topic="obscure topic nobody has written about",
                    jurisdictions=None, days=365,
                    detect_conflicts=False, force_refresh=True,
                )
        self.assertIn("error", result)

    def test_uses_cached_synthesis_when_fresh(self):
        agent = self._make_agent_with_response({})
        cached = {
            "id": 99, "topic": "AI governance", "synthesis": {"landscape_summary": "cached result"},
            "conflicts": None, "docs_used": 5, "jurisdictions": ["EU"],
            "generated_at": datetime.utcnow().isoformat(),
        }
        with patch("agents.synthesis_agent.get_existing_synthesis", return_value=cached):
            result = agent.run("AI governance", days=365, force_refresh=False)
        self.assertEqual(result["id"], 99)
        self.assertEqual(result["synthesis"]["landscape_summary"], "cached result")


class TestSynthesisDatabase(unittest.TestCase):

    def setUp(self):
        import utils.db as db_module
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from utils.db import Base
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        db_module._engine  = engine
        db_module._Session = sessionmaker(bind=engine)

    def test_save_and_retrieve_synthesis(self):
        from utils.db import save_synthesis, get_synthesis_by_id
        result = {
            "topic_key":    "abc123",
            "topic":        "AI in healthcare",
            "jurisdictions":["EU", "Federal"],
            "docs_used":    5,
            "doc_ids":      ["EU-1", "US-1"],
            "synthesis":    {"landscape_summary": "Converging landscape"},
            "conflicts":    {"conflicts": [{"conflict_id": "x", "severity": "High"}]},
            "model_used":   "claude-test",
        }
        sid = save_synthesis(result)
        self.assertIsInstance(sid, int)

        retrieved = get_synthesis_by_id(sid)
        self.assertEqual(retrieved["topic"],    "AI in healthcare")
        self.assertEqual(retrieved["docs_used"], 5)
        self.assertEqual(retrieved["conflict_count"], 1)
        self.assertTrue(retrieved["has_conflicts"])

    def test_get_existing_synthesis_fresh(self):
        from utils.db import save_synthesis, get_existing_synthesis
        save_synthesis({
            "topic_key":    "test-key",
            "topic":        "Test",
            "jurisdictions":["EU"],
            "docs_used":    2,
            "doc_ids":      [],
            "synthesis":    {"landscape_summary": "fresh"},
            "conflicts":    None,
            "model_used":   "test",
        })
        result = get_existing_synthesis("test-key", max_age_days=7)
        self.assertIsNotNone(result)
        self.assertEqual(result["synthesis"]["landscape_summary"], "fresh")

    def test_get_existing_synthesis_stale_returns_none(self):
        from utils.db import get_session, ThematicSynthesis, get_existing_synthesis
        from datetime import timedelta
        # Insert a record with old generated_at
        with get_session() as session:
            row = ThematicSynthesis(
                topic_key   = "old-key",
                topic       = "Old Topic",
                docs_used   = 2,
                model_used  = "test",
                synthesis_json = {"landscape_summary": "old"},
                generated_at = datetime.utcnow() - timedelta(days=10),
            )
            session.add(row)
            session.commit()
        result = get_existing_synthesis("old-key", max_age_days=7)
        self.assertIsNone(result)  # too old

    def test_star_and_annotate(self):
        from utils.db import save_synthesis, get_synthesis_by_id, star_synthesis, annotate_synthesis
        sid = save_synthesis({
            "topic_key": "star-test", "topic": "Star Topic",
            "jurisdictions": [], "docs_used": 1, "doc_ids": [],
            "synthesis": {}, "conflicts": None, "model_used": "test",
        })
        self.assertFalse(get_synthesis_by_id(sid)["starred"])
        star_synthesis(sid, True)
        self.assertTrue(get_synthesis_by_id(sid)["starred"])

        annotate_synthesis(sid, "Important for Q3 review")
        self.assertIn("Q3", get_synthesis_by_id(sid)["notes"])

    def test_list_recent_syntheses(self):
        from utils.db import save_synthesis, get_recent_syntheses
        for i in range(3):
            save_synthesis({
                "topic_key": f"key-{i}", "topic": f"Topic {i}",
                "jurisdictions": ["EU"], "docs_used": i+1, "doc_ids": [],
                "synthesis": {}, "conflicts": None, "model_used": "test",
            })
        rows = get_recent_syntheses(limit=10)
        self.assertEqual(len(rows), 3)
        # summary_only mode shouldn't include full synthesis/conflicts JSON
        for r in rows:
            self.assertNotIn("synthesis", r)
            self.assertNotIn("conflicts", r)

    def test_delete_synthesis(self):
        from utils.db import save_synthesis, get_synthesis_by_id, delete_synthesis
        sid = save_synthesis({
            "topic_key": "del-test", "topic": "Delete Me",
            "jurisdictions": [], "docs_used": 0, "doc_ids": [],
            "synthesis": {}, "conflicts": None, "model_used": "test",
        })
        self.assertIsNotNone(get_synthesis_by_id(sid))
        delete_synthesis(sid)
        self.assertIsNone(get_synthesis_by_id(sid))

    def test_stats_include_synthesis_count(self):
        from utils.db import save_synthesis, get_stats
        save_synthesis({
            "topic_key": "stat-test", "topic": "Stats",
            "jurisdictions": [], "docs_used": 0, "doc_ids": [],
            "synthesis": {}, "conflicts": None, "model_used": "test",
        })
        stats = get_stats()
        self.assertIn("total_syntheses", stats)
        self.assertEqual(stats["total_syntheses"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
