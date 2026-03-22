# SPDX-License-Identifier: Elastic-2.0
# Copyright (c) 2026 Mitch Kwiatkowski
# ARIS � Automated Regulatory Intelligence System
# Licensed under the Elastic License 2.0. See LICENSE in the project root.
"""
ARIS — Diff Agent & Change Detection Tests
Run with: python -m unittest tests.test_diff -v
"""

import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock


# ── DiffAgent unit tests ──────────────────────────────────────────────────────

class TestDiffAgentHelpers(unittest.TestCase):

    def test_make_line_diff_detects_changes(self):
        from agents.diff_agent import _make_line_diff
        old = "The system must notify users.\nPenalty: $10,000.\nScope: all providers."
        new = "The system must notify users within 30 days.\nPenalty: $25,000.\nScope: all providers and deployers."
        result = _make_line_diff(old, new)
        self.assertIn("---", result)
        self.assertIn("+++", result)
        self.assertIn("30 days", result)

    def test_make_line_diff_identical_text(self):
        from agents.diff_agent import _make_line_diff
        text   = "The regulation requires disclosure."
        result = _make_line_diff(text, text)
        self.assertEqual(result, "")

    def test_make_line_diff_respects_max_lines(self):
        from agents.diff_agent import _make_line_diff
        old = "\n".join(f"Line {i}: old content here" for i in range(200))
        new = "\n".join(f"Line {i}: new content here" for i in range(200))
        result = _make_line_diff(old, new, max_lines=20)
        self.assertIn("truncated", result)

    def test_title_overlap_score_identical(self):
        from agents.diff_agent import _title_overlap_score
        score = _title_overlap_score(
            "artificial intelligence regulation act",
            "artificial intelligence regulation act"
        )
        self.assertAlmostEqual(score, 1.0)

    def test_title_overlap_score_different(self):
        from agents.diff_agent import _title_overlap_score
        score = _title_overlap_score(
            "artificial intelligence regulation",
            "farm subsidy programme"
        )
        self.assertLess(score, 0.1)

    def test_title_overlap_score_partial(self):
        from agents.diff_agent import _title_overlap_score
        score = _title_overlap_score(
            "guidelines on artificial intelligence systems",
            "artificial intelligence regulation act"
        )
        self.assertGreater(score, 0.3)

    def test_title_overlap_score_empty(self):
        from agents.diff_agent import _title_overlap_score
        self.assertEqual(_title_overlap_score("", "some words here"), 0.0)
        self.assertEqual(_title_overlap_score("some words here", ""), 0.0)

    def test_find_base_document_non_addendum(self):
        """Documents with no addendum signals should return None."""
        import sys, types
        for pkg in ['anthropic']:
            m = types.ModuleType(pkg)
            m.Anthropic  = type('Anthropic',  (), {'__init__': lambda s, **k: None})
            m.APIError   = Exception
            sys.modules[pkg] = m

        from agents.diff_agent import DiffAgent
        agent = DiffAgent.__new__(DiffAgent)   # bypass __init__

        new_doc = {"id": "DOC-NEW", "title": "Farm subsidy programme 2025",
                   "full_text": "This bill funds agricultural support.", "jurisdiction": "Federal"}
        existing = [
            {"id": "DOC-OLD", "title": "AI Regulation Act",
             "full_text": "Governs AI systems.", "jurisdiction": "Federal"}
        ]
        result = agent._find_base_document(new_doc, existing)
        self.assertIsNone(result)

    def test_find_base_document_amendment_signal(self):
        """Documents with 'amend' in title should trigger addendum detection."""
        import sys, types
        for pkg in ['anthropic']:
            m = types.ModuleType(pkg)
            m.Anthropic  = type('Anthropic',  (), {'__init__': lambda s, **k: None})
            m.APIError   = Exception
            sys.modules[pkg] = m

        from agents.diff_agent import DiffAgent
        agent = DiffAgent.__new__(DiffAgent)

        new_doc = {
            "id": "DOC-AMEND",
            "title": "Amendment to Artificial Intelligence Regulation Act",
            "full_text": "This amends the artificial intelligence regulation by adding new requirements.",
            "jurisdiction": "Federal",
        }
        existing = [
            {
                "id": "DOC-BASE",
                "title": "Artificial Intelligence Regulation Act",
                "full_text": "Original regulation text.",
                "jurisdiction": "Federal",
            }
        ]
        result = agent._find_base_document(new_doc, existing)
        self.assertEqual(result, "DOC-BASE")

    def test_compare_versions_skips_identical_text(self):
        """If texts are identical, compare_versions should return None without calling Claude."""
        import sys, types
        for pkg in ['anthropic']:
            m = types.ModuleType(pkg)
            m.Anthropic  = type('Anthropic',  (), {'__init__': lambda s, **k: None})
            m.APIError   = Exception
            sys.modules[pkg] = m

        from agents.diff_agent import DiffAgent
        agent = DiffAgent.__new__(DiffAgent)
        agent._client = MagicMock()

        old = {"id": "DOC-V1", "title": "AI Rule", "full_text": "Same text.", "status": "Draft",
               "published_date": "2024-01-01", "url": "", "jurisdiction": "Federal", "agency": ""}
        new = {"id": "DOC-V2", "title": "AI Rule", "full_text": "Same text.", "status": "Final",
               "published_date": "2025-01-01", "url": "", "jurisdiction": "Federal", "agency": ""}

        result = agent.compare_versions(old, new)
        self.assertIsNone(result)
        agent._client.messages.create.assert_not_called()


class TestDiffAgentClaudeOutput(unittest.TestCase):
    """Tests that verify correct handling of LLM JSON response."""

    def _make_agent_with_response(self, llm_response: dict):
        """Return a DiffAgent whose call_llm is patched to return llm_response as JSON."""
        import json
        from agents.diff_agent import DiffAgent
        agent = DiffAgent.__new__(DiffAgent)
        # Patch the module-level call_llm used by _call_claude
        self._patcher = patch(
            'agents.diff_agent.call_llm',
            return_value=json.dumps(llm_response)
        )
        self._patcher.start()
        return agent

    def tearDown(self):
        if hasattr(self, '_patcher'):
            self._patcher.stop()

    def test_compare_versions_no_change_returns_none(self):
        agent = self._make_agent_with_response({"change_type": "No Substantive Change"})
        old = {"id": "A", "title": "Rule", "full_text": "text A",
               "status": "", "published_date": "", "url": "", "jurisdiction": "Federal", "agency": ""}
        new = {"id": "B", "title": "Rule", "full_text": "text B",
               "status": "", "published_date": "", "url": "", "jurisdiction": "Federal", "agency": ""}
        result = agent.compare_versions(old, new)
        self.assertIsNone(result)

    def test_compare_versions_returns_structured_result(self):
        response = {
            "change_type":           "Significant Amendment",
            "change_summary":        "The rule now requires 90-day notice instead of 30.",
            "severity":              "High",
            "added_requirements":    [{"description": "Must file 90-day notice", "section": "§3(a)", "effective_date": "2026-01-01"}],
            "removed_requirements":  [],
            "modified_requirements": [{"description": "Notice period extended", "section": "§3", "direction": "Stricter"}],
            "definition_changes":    [],
            "deadline_changes":      [{"description": "Filing deadline", "old_deadline": "30 days", "new_deadline": "90 days"}],
            "penalty_changes":       [],
            "scope_changes":         None,
            "new_action_items":      ["Update internal compliance calendar to 90-day notice period"],
            "obsolete_action_items": ["Remove 30-day filing reminder from compliance checklist"],
            "overall_assessment":    "This is a material change requiring immediate compliance team action.",
        }
        agent = self._make_agent_with_response(response)
        old = {"id": "A", "title": "AI Rule", "full_text": "thirty day notice",
               "status": "Proposed", "published_date": "", "url": "", "jurisdiction": "Federal", "agency": ""}
        new = {"id": "B", "title": "AI Rule", "full_text": "ninety day notice",
               "status": "Final",    "published_date": "", "url": "", "jurisdiction": "Federal", "agency": ""}

        result = agent.compare_versions(old, new)
        self.assertIsNotNone(result)
        self.assertEqual(result["diff_type"],          "version_update")
        self.assertEqual(result["severity"],           "High")
        self.assertEqual(result["relationship_type"],  "Significant Amendment")
        self.assertEqual(len(result["added_requirements"]),    1)
        self.assertEqual(len(result["deadline_changes"]),      1)
        self.assertEqual(len(result["new_action_items"]),      1)
        self.assertEqual(len(result["obsolete_action_items"]), 1)
        self.assertIn("base_document_id", result)
        self.assertIn("new_document_id",  result)
        self.assertIn("detected_at",      result)
        self.assertEqual(result["base_document_id"], "A")
        self.assertEqual(result["new_document_id"],  "B")

    def test_analyse_addendum_returns_structured_result(self):
        response = {
            "relationship_type":   "Guidance",
            "change_summary":      "Clarifies which AI systems fall under the prohibited category.",
            "severity":            "Critical",
            "affected_provisions": [{"provision": "Article 5", "change": "Social scoring now includes ...", "direction": "Stricter"}],
            "new_obligations":     ["Must immediately audit all social scoring systems"],
            "removed_obligations": [],
            "clarified_definitions": [{"term": "Social scoring", "clarification": "Includes any ranking...", "practical_impact": "Broader scope"}],
            "enforcement_implications": "Enforcement began 2 Feb 2025.",
            "effective_date":      "2025-02-02",
            "new_action_items":    ["Audit all systems for social scoring functionality"],
            "overall_assessment":  "This guidance materially expands the scope of prohibited practices.",
        }
        agent = self._make_agent_with_response(response)

        base_doc = {"id": "EU-CELEX-32024R1689", "title": "EU AI Act",
                    "full_text": "...", "status": "In Force",
                    "url": "", "jurisdiction": "EU", "agency": "EC"}
        addendum = {"id": "EU-GUIDELINES-2025", "title": "Guidelines on Prohibited AI Practices",
                    "full_text": "Article 5 guidance...", "doc_type": "Guidelines",
                    "published_date": "2025-02-04", "url": "", "jurisdiction": "EU", "agency": "EC"}

        result = agent.analyse_addendum(base_doc, addendum)
        self.assertIsNotNone(result)
        self.assertEqual(result["diff_type"],         "addendum")
        self.assertEqual(result["severity"],          "Critical")
        self.assertEqual(result["relationship_type"], "Guidance")
        self.assertGreater(len(result["added_requirements"]),    0)
        self.assertGreater(len(result["modified_requirements"]), 0)
        self.assertGreater(len(result["new_action_items"]),      0)


# ── Database diff/link tests ──────────────────────────────────────────────────

class TestDiffDatabase(unittest.TestCase):

    def setUp(self):
        """Use in-memory SQLite."""
        import utils.db as db_module
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from utils.db import Base
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        db_module._engine  = engine
        db_module._Session = sessionmaker(bind=engine)

    def _make_doc(self, doc_id, title, full_text="some ai text"):
        from utils.db import upsert_document
        upsert_document({
            "id":            doc_id,
            "source":        "test",
            "jurisdiction":  "Federal",
            "doc_type":      "RULE",
            "title":         title,
            "url":           "https://example.com",
            "published_date": datetime(2025, 1, 1),
            "agency":        "Test Agency",
            "status":        "Final Rule",
            "full_text":     full_text,
            "raw_json":      {},
        })

    def test_save_and_retrieve_diff(self):
        from utils.db import save_diff, get_diffs_for_document, get_recent_diffs
        self._make_doc("DOC-A", "AI Rule v1")
        self._make_doc("DOC-B", "AI Rule v2")

        diff_data = {
            "base_document_id":      "DOC-A",
            "new_document_id":       "DOC-B",
            "diff_type":             "version_update",
            "relationship_type":     "Significant Amendment",
            "change_summary":        "Notice period extended.",
            "severity":              "High",
            "added_requirements":    [{"description": "90-day notice required"}],
            "removed_requirements":  [],
            "modified_requirements": [],
            "definition_changes":    [],
            "deadline_changes":      [],
            "penalty_changes":       [],
            "scope_changes":         None,
            "new_action_items":      ["Update compliance calendar"],
            "obsolete_action_items": [],
            "overall_assessment":    "Material change.",
            "model_used":            "claude-test",
            "detected_at":          datetime.utcnow(),
        }
        diff_id = save_diff(diff_data)
        self.assertIsInstance(diff_id, int)
        self.assertGreater(diff_id, 0)

        diffs = get_diffs_for_document("DOC-A")
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0]["severity"], "High")
        self.assertEqual(len(diffs[0]["added_requirements"]), 1)

        recent = get_recent_diffs(days=7)
        self.assertEqual(len(recent), 1)

    def test_diff_exists_check(self):
        from utils.db import save_diff, diff_exists
        self._make_doc("DOC-X", "Rule X")
        self._make_doc("DOC-Y", "Rule Y")

        self.assertFalse(diff_exists("DOC-X", "DOC-Y"))
        save_diff({
            "base_document_id":   "DOC-X",
            "new_document_id":    "DOC-Y",
            "diff_type":          "version_update",
            "severity":           "Low",
            "detected_at":       datetime.utcnow(),
        })
        self.assertTrue(diff_exists("DOC-X", "DOC-Y"))

    def test_save_and_retrieve_link(self):
        from utils.db import save_link, get_links_for_document
        self._make_doc("BASE-DOC",    "EU AI Act")
        self._make_doc("ADDEND-DOC",  "AI Act Guidelines")

        save_link("BASE-DOC", "ADDEND-DOC", link_type="amends",
                  notes="Guidelines clarify Article 5")

        links = get_links_for_document("BASE-DOC")
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["link_type"],      "amends")
        self.assertEqual(links[0]["related_doc_id"], "ADDEND-DOC")
        self.assertIn("Article 5", links[0]["notes"])

    def test_duplicate_link_not_saved(self):
        from utils.db import save_link, get_links_for_document
        self._make_doc("BASE-2", "Rule A")
        self._make_doc("ADDEND-2", "Rule A Guidance")

        save_link("BASE-2", "ADDEND-2", link_type="clarifies")
        save_link("BASE-2", "ADDEND-2", link_type="clarifies")  # duplicate

        links = get_links_for_document("BASE-2")
        self.assertEqual(len(links), 1)

    def test_mark_diff_reviewed(self):
        from utils.db import save_diff, get_unreviewed_diffs, mark_diff_reviewed
        self._make_doc("DOC-R1", "Rule 1")
        self._make_doc("DOC-R2", "Rule 2")

        diff_id = save_diff({
            "base_document_id": "DOC-R1",
            "new_document_id":  "DOC-R2",
            "diff_type":        "version_update",
            "severity":         "Medium",
            "detected_at":      datetime.utcnow(),
        })
        unreviewed = get_unreviewed_diffs()
        self.assertEqual(len(unreviewed), 1)

        mark_diff_reviewed(diff_id)
        unreviewed_after = get_unreviewed_diffs()
        self.assertEqual(len(unreviewed_after), 0)

    def test_stats_include_diff_counts(self):
        from utils.db import save_diff, get_stats
        self._make_doc("DOC-S1", "Stat Rule 1")
        self._make_doc("DOC-S2", "Stat Rule 2")

        save_diff({
            "base_document_id": "DOC-S1",
            "new_document_id":  "DOC-S2",
            "diff_type":        "version_update",
            "severity":         "Critical",
            "detected_at":      datetime.utcnow(),
        })

        stats = get_stats()
        self.assertIn("total_diffs",         stats)
        self.assertIn("unreviewed_diffs",    stats)
        self.assertIn("critical_diffs",      stats)
        self.assertIn("high_severity_diffs", stats)
        self.assertEqual(stats["total_diffs"],    1)
        self.assertEqual(stats["critical_diffs"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
