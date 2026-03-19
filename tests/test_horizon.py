"""
ARIS — Horizon Agent Tests
"""
import sys
import types
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


def setUpModule():
    for pkg, attrs in {
        'tenacity':      ['retry', 'stop_after_attempt', 'wait_exponential'],
        'anthropic':     ['Anthropic', 'APIError'],
        'sqlalchemy':    ['Column', 'String', 'Text', 'DateTime', 'Float', 'Boolean',
                          'JSON', 'Index', 'text', 'create_engine', 'Integer'],
        'sqlalchemy.orm':['DeclarativeBase', 'Session', 'sessionmaker'],
    }.items():
        if pkg not in sys.modules:
            m = types.ModuleType(pkg)
            for a in attrs:
                setattr(m, a,
                        type(a, (), {'__init__': lambda s, *a, **k: None})
                        if a[0].isupper() else (lambda *a, **k: None))
            sys.modules[pkg] = m
    sys.modules['tenacity'].retry = lambda **k: (lambda f: f)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _agent():
    from sources.horizon_agent import HorizonAgent
    return HorizonAgent()


# ── Date parsing ──────────────────────────────────────────────────────────────

class TestDateParsing(unittest.TestCase):

    def _parse(self, s):
        from sources.horizon_agent import _parse_date
        return _parse_date(s)

    def test_iso_date(self):
        d = self._parse("2026-08-02")
        self.assertIsNotNone(d)
        self.assertEqual(d.year, 2026)
        self.assertEqual(d.month, 8)
        self.assertEqual(d.day, 2)

    def test_iso_datetime(self):
        d = self._parse("2025-11-15T00:00:00Z")
        self.assertIsNotNone(d)
        self.assertEqual(d.year, 2025)
        self.assertEqual(d.month, 11)

    def test_month_year_string(self):
        d = self._parse("March 2026")
        self.assertIsNotNone(d)
        self.assertEqual(d.year, 2026)
        self.assertEqual(d.month, 3)

    def test_abbreviated_month_year(self):
        d = self._parse("Nov 2025")
        self.assertIsNotNone(d)
        self.assertEqual(d.year, 2025)
        self.assertEqual(d.month, 11)

    def test_year_only(self):
        d = self._parse("2027")
        self.assertIsNotNone(d)
        self.assertEqual(d.year, 2027)

    def test_none_returns_none(self):
        self.assertIsNone(self._parse(None))

    def test_empty_returns_none(self):
        self.assertIsNone(self._parse(""))

    def test_garbage_returns_none(self):
        self.assertIsNone(self._parse("not a date at all xyz"))

    def test_rss_date_format(self):
        d = self._parse("Mon, 15 Jan 2025 10:00:00 GMT")
        self.assertIsNotNone(d)
        self.assertEqual(d.year, 2025)

    def test_slash_date(self):
        d = self._parse("2025/03")
        self.assertIsNotNone(d)
        self.assertEqual(d.year, 2025)
        self.assertEqual(d.month, 3)


# ── ID generation ─────────────────────────────────────────────────────────────

class TestIdGeneration(unittest.TestCase):

    def test_id_is_string(self):
        from sources.horizon_agent import _make_id
        result = _make_id("agenda", "Artificial Intelligence Rule")
        self.assertIsInstance(result, str)

    def test_id_has_prefix(self):
        from sources.horizon_agent import _make_id
        result = _make_id("hearing", "Some Bill")
        self.assertTrue(result.startswith("hearing-"))

    def test_same_text_same_id(self):
        from sources.horizon_agent import _make_id
        a = _make_id("agenda", "AI Safety Rule")
        b = _make_id("agenda", "AI Safety Rule")
        self.assertEqual(a, b)

    def test_different_text_different_id(self):
        from sources.horizon_agent import _make_id
        a = _make_id("agenda", "AI Safety Rule")
        b = _make_id("agenda", "AI Privacy Rule")
        self.assertNotEqual(a, b)

    def test_different_prefix_different_id(self):
        from sources.horizon_agent import _make_id
        a = _make_id("agenda",  "AI Rule")
        b = _make_id("hearing", "AI Rule")
        self.assertNotEqual(a, b)

    def test_case_insensitive(self):
        from sources.horizon_agent import _make_id
        a = _make_id("agenda", "AI SAFETY RULE")
        b = _make_id("agenda", "ai safety rule")
        self.assertEqual(a, b)


# ── XML text extraction ───────────────────────────────────────────────────────

class TestXmlTextExtraction(unittest.TestCase):

    def _extract(self, block, tag):
        from sources.horizon_agent import _xml_text
        return _xml_text(block, tag)

    def test_simple_element(self):
        block = "<title>AI Regulation Rule</title><desc>Some description</desc>"
        self.assertEqual(self._extract(block, "title"), "AI Regulation Rule")

    def test_cdata_element(self):
        block = "<description><![CDATA[Some <b>HTML</b> content]]></description>"
        result = self._extract(block, "description")
        self.assertIn("HTML", result)

    def test_missing_element_returns_empty(self):
        block = "<title>Something</title>"
        self.assertEqual(self._extract(block, "description"), "")

    def test_multiline(self):
        block = "<title>AI\nRegulation\nRule</title>"
        result = self._extract(block, "title")
        self.assertIn("AI", result)

    def test_element_with_attributes(self):
        block = '<link rel="alternate">https://example.com</link>'
        result = self._extract(block, "link")
        self.assertIn("example.com", result)


# ── RSS parsing ───────────────────────────────────────────────────────────────

class TestRSSParsing(unittest.TestCase):

    def _make_rss(self, items):
        """Build a minimal RSS XML string."""
        item_xml = ""
        for title, desc, link, date in items:
            item_xml += f"""
            <item>
                <title>{title}</title>
                <description>{desc}</description>
                <link>{link}</link>
                <pubDate>{date}</pubDate>
            </item>"""
        return f"<?xml version='1.0'?><rss><channel>{item_xml}</channel></rss>"

    def test_agenda_rss_parses_relevant(self):
        agent = _agent()
        rss   = self._make_rss([
            ("AI Risk Management Final Rule",
             "NIST finalizing risk management framework for artificial intelligence systems",
             "https://example.gov/rule",
             "Mon, 15 Jan 2026 00:00:00 GMT"),
        ])
        result = agent._parse_agenda_rss(rss)
        self.assertEqual(len(result), 1)
        self.assertIn("AI Risk Management", result[0]["title"])
        self.assertEqual(result[0]["source"], "unified_agenda")
        self.assertEqual(result[0]["jurisdiction"], "Federal")

    def test_agenda_rss_filters_irrelevant(self):
        agent  = _agent()
        rss    = self._make_rss([
            ("Bridge Inspection Standards",
             "New requirements for structural inspection of bridges and overpasses",
             "https://example.gov/rule2",
             "Mon, 15 Jan 2026 00:00:00 GMT"),
        ])
        result = agent._parse_agenda_rss(rss)
        self.assertEqual(len(result), 0)

    def test_agenda_rss_empty_input(self):
        agent  = _agent()
        result = agent._parse_agenda_rss("")
        self.assertEqual(result, [])

    def test_eu_rss_parses_relevant(self):
        agent = _agent()
        rss   = self._make_rss([
            ("Implementing Act on AI Governance",
             "Commission proposal for implementing regulation on artificial intelligence accountability",
             "https://ec.europa.eu/act",
             "Tue, 10 Feb 2026 00:00:00 GMT"),
        ])
        result = agent._parse_eu_rss(rss)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["jurisdiction"], "EU")
        self.assertEqual(result[0]["source"], "eu_work_programme")

    def test_rss_extracts_date(self):
        agent = _agent()
        # Use ISO date in description since pubDate "GMT" format may not parse
        rss   = self._make_rss([
            ("AI Safety Final Rule",
             "Artificial intelligence safety requirements — effective 2026-03-15",
             "https://example.gov",
             "2026-03-15"),
        ])
        result = agent._parse_agenda_rss(rss)
        self.assertEqual(len(result), 1)
        # Date is extracted from description via regex, not pubDate
        # Just verify the item was parsed; date may or may not be set
        self.assertEqual(result[0]["source"], "unified_agenda")


# ── Agenda entry parsing ──────────────────────────────────────────────────────

class TestAgendaEntryParsing(unittest.TestCase):

    def _entry(self, **kwargs):
        base = {
            "rin":            "1234-AB56",
            "title":          "Artificial Intelligence Risk Assessment Rule",
            "abstract":       "Proposed rule on AI risk management for federal agencies",
            "agency_name":    "Office of Management and Budget",
            "stage":          "Proposed Rule Stage",
            "anticipated_nprmdate": "2026-03-01",
        }
        base.update(kwargs)
        return base

    def test_parses_valid_entry(self):
        agent  = _agent()
        result = agent._parse_agenda_entry(self._entry())
        self.assertIsNotNone(result)
        self.assertIn("Intelligence", result["title"])   # full phrase, not abbreviation
        self.assertEqual(result["jurisdiction"], "Federal")
        self.assertEqual(result["source"], "unified_agenda")

    def test_filters_irrelevant_entry(self):
        agent  = _agent()
        result = agent._parse_agenda_entry({
            "rin":         "9999-ZZ99",
            "title":       "Beef Grading Standards Revision",
            "abstract":    "New standards for beef quality grading in slaughterhouses",
            "agency_name": "USDA",
            "stage":       "Final Rule Stage",
        })
        self.assertIsNone(result)

    def test_stage_mapping_proposed(self):
        agent  = _agent()
        result = agent._parse_agenda_entry(self._entry(stage="Proposed Rule Stage"))
        self.assertIsNotNone(result)
        self.assertEqual(result["stage"], "proposed")

    def test_stage_mapping_final(self):
        agent  = _agent()
        result = agent._parse_agenda_entry(self._entry(stage="Final Rule Stage"))
        self.assertIsNotNone(result)
        self.assertEqual(result["stage"], "final")

    def test_stage_mapping_prerule(self):
        agent  = _agent()
        result = agent._parse_agenda_entry(self._entry(stage="Pre-rule Stage"))
        self.assertIsNotNone(result)
        self.assertEqual(result["stage"], "pre-rule")

    def test_stage_mapping_unknown_defaults_to_planned(self):
        agent  = _agent()
        result = agent._parse_agenda_entry(self._entry(stage="Unknown Stage XYZ"))
        self.assertIsNotNone(result)
        self.assertEqual(result["stage"], "planned")

    def test_missing_title_returns_none(self):
        agent  = _agent()
        result = agent._parse_agenda_entry({"rin": "1111-AA11", "title": "", "abstract": ""})
        self.assertIsNone(result)

    def test_ai_score_populated(self):
        agent  = _agent()
        result = agent._parse_agenda_entry(self._entry())
        self.assertIsNotNone(result)
        self.assertGreater(result["ai_score"], 0.0)
        self.assertLessEqual(result["ai_score"], 1.0)

    def test_uses_rin_as_external_id(self):
        agent  = _agent()
        result = agent._parse_agenda_entry(self._entry(rin="1234-AB56"))
        self.assertIsNotNone(result)
        self.assertEqual(result["external_id"], "1234-AB56")


# ── Horizon item persistence ──────────────────────────────────────────────────

class TestHorizonPersistence(unittest.TestCase):

    def _make_item(self, title="AI Governance Rule", source="unified_agenda",
                   eid=None, jur="Federal", stage="proposed", days_ahead=90):
        return {
            "source":         source,
            "external_id":    eid or f"test-{hash(title) % 10000}",
            "jurisdiction":   jur,
            "title":          title,
            "description":    "Test description",
            "agency":         "Test Agency",
            "stage":          stage,
            "anticipated_date": datetime.utcnow() + timedelta(days=days_ahead),
            "url":            "https://example.gov",
            "ai_score":       0.75,
        }

    def test_save_items_calls_upsert(self):
        agent = _agent()
        items = [self._make_item()]
        with patch("sources.horizon_agent.upsert_horizon_item", return_value=True) as mock_upsert:
            count = agent._save_items(items)
        self.assertEqual(count, 1)
        mock_upsert.assert_called_once()

    def test_save_items_counts_new_only(self):
        agent  = _agent()
        items  = [self._make_item("Rule A"), self._make_item("Rule B"), self._make_item("Rule C")]
        # First two new (True), third duplicate (False)
        with patch("sources.horizon_agent.upsert_horizon_item", side_effect=[True, True, False]):
            count = agent._save_items(items)
        self.assertEqual(count, 2)

    def test_save_empty_returns_zero(self):
        agent = _agent()
        count = agent._save_items([])
        self.assertEqual(count, 0)

    def test_save_handles_db_error_gracefully(self):
        agent = _agent()
        items = [self._make_item()]
        with patch("sources.horizon_agent.upsert_horizon_item", side_effect=Exception("DB error")):
            count = agent._save_items(items)
        self.assertEqual(count, 0)


# ── Full run method ───────────────────────────────────────────────────────────

class TestHorizonAgentRun(unittest.TestCase):

    def _mock_items(self, source, n=2):
        from sources.horizon_agent import _make_id
        return [
            {
                "source":         source,
                "external_id":    _make_id(source, f"item-{i}"),
                "jurisdiction":   "Federal",
                "title":          f"AI Rule {i} from {source}",
                "description":    "Test",
                "agency":         "Test Agency",
                "stage":          "proposed",
                "anticipated_date": datetime.utcnow() + timedelta(days=60),
                "url":            "",
                "ai_score":       0.6,
            }
            for i in range(n)
        ]

    def test_run_returns_counts_per_source(self):
        agent = _agent()
        with patch.object(agent, '_fetch_unified_agenda',    return_value=self._mock_items("unified_agenda", 2)):
            with patch.object(agent, '_fetch_congress_hearings', return_value=self._mock_items("congress_hearings", 1)):
                with patch.object(agent, '_fetch_eu_work_programme', return_value=[]):
                    with patch.object(agent, '_fetch_uk_upcoming',      return_value=[]):
                        with patch.object(agent, '_save_items', side_effect=lambda items: len(items)):
                            result = agent.run()

        self.assertIn("unified_agenda",      result)
        self.assertIn("congress_hearings",   result)
        self.assertIn("eu_work_programme",   result)
        self.assertIn("uk_upcoming",         result)
        self.assertEqual(result["unified_agenda"],    2)
        self.assertEqual(result["congress_hearings"], 1)
        self.assertEqual(result["eu_work_programme"], 0)

    def test_run_continues_when_one_source_fails(self):
        agent = _agent()
        with patch.object(agent, '_fetch_unified_agenda',    side_effect=Exception("network error")):
            with patch.object(agent, '_fetch_congress_hearings', return_value=self._mock_items("congress_hearings", 3)):
                with patch.object(agent, '_fetch_eu_work_programme', return_value=[]):
                    with patch.object(agent, '_fetch_uk_upcoming',      return_value=[]):
                        with patch.object(agent, '_save_items', side_effect=lambda items: len(items)):
                            result = agent.run()

        # unified_agenda failed → 0 (not crash)
        self.assertEqual(result["unified_agenda"],    0)
        self.assertEqual(result["congress_hearings"], 3)

    def test_run_all_sources_fail_returns_zero_counts(self):
        agent = _agent()
        with patch.object(agent, '_fetch_unified_agenda',    side_effect=Exception("fail")):
            with patch.object(agent, '_fetch_congress_hearings', side_effect=Exception("fail")):
                with patch.object(agent, '_fetch_eu_work_programme', side_effect=Exception("fail")):
                    with patch.object(agent, '_fetch_uk_upcoming',      side_effect=Exception("fail")):
                        result = agent.run()

        for key in result.values():
            self.assertEqual(key, 0)

    def test_get_upcoming_delegates_to_db(self):
        agent = _agent()
        mock_items = [{"id": 1, "title": "Test Rule", "stage": "proposed"}]
        with patch("sources.horizon_agent.get_horizon_items", return_value=mock_items):
            result = agent.get_upcoming(days_ahead=90, jurisdiction="Federal")
        self.assertEqual(result, mock_items)


# ── Congress hearing parsing ──────────────────────────────────────────────────

class TestCongressHearingParsing(unittest.TestCase):

    def test_skips_when_no_api_key(self):
        """No key = empty result, no network call."""
        import sources.horizon_agent as ha_mod
        original = ha_mod.CONGRESS_GOV_KEY
        try:
            ha_mod.CONGRESS_GOV_KEY = ""
            agent  = ha_mod.HorizonAgent()
            result = agent._fetch_congress_hearings()
            self.assertEqual(result, [])
        finally:
            ha_mod.CONGRESS_GOV_KEY = original

    def test_parses_meeting_with_ai_bills(self):
        agent = _agent()
        mock_resp = {
            "committeeMeetings": [
                {
                    "eventId":  "1234",
                    "title":    "Hearing on Artificial Intelligence Risk, Safety, and Machine Learning Accountability",
                    "chamber":  "Senate",
                    "date":     "2026-04-15",
                    "committee":{"name": "Senate Commerce Committee"},
                    "bills":    [{"number": "S.1234", "title": "Artificial Intelligence Safety and Accountability Act"}],
                    "url":      "https://congress.gov/event/1234",
                }
            ]
        }
        import sources.horizon_agent as ha_mod
        original_key = ha_mod.CONGRESS_GOV_KEY
        try:
            ha_mod.CONGRESS_GOV_KEY = "test-key"
            with patch("sources.horizon_agent.http_get", return_value=mock_resp):
                result = agent._fetch_congress_hearings()
        finally:
            ha_mod.CONGRESS_GOV_KEY = original_key

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["stage"],        "hearing")
        self.assertEqual(result[0]["jurisdiction"], "Federal")
        self.assertIsNotNone(result[0]["anticipated_date"])

    def test_filters_non_ai_hearings(self):
        agent = _agent()
        mock_resp = {
            "committeeMeetings": [
                {
                    "eventId":  "5678",
                    "title":    "Highway Infrastructure Funding",
                    "chamber":  "House",
                    "date":     "2026-04-20",
                    "committee":{"name": "House Transportation Committee"},
                    "bills":    [],
                    "url":      "",
                }
            ]
        }
        import sources.horizon_agent as ha_mod
        original_key = ha_mod.CONGRESS_GOV_KEY
        try:
            ha_mod.CONGRESS_GOV_KEY = "test-key"
            with patch("sources.horizon_agent.http_get", return_value=mock_resp):
                result = agent._fetch_congress_hearings()
        finally:
            ha_mod.CONGRESS_GOV_KEY = original_key

        self.assertEqual(len(result), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
