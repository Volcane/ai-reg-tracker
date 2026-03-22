# SPDX-License-Identifier: Elastic-2.0
# Copyright (c) 2026 Mitch Kwiatkowski
# ARIS — Automated Regulatory Intelligence System
# Licensed under the Elastic License 2.0. See LICENSE in the project root.
"""
ARIS â€” Timeline, Brief, and Compare Agent Tests
"""
import json
import sys
import types
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock


def setUpModule():
    for pkg, attrs in {
        'tenacity':      ['retry', 'stop_after_attempt', 'wait_exponential'],
        'anthropic':     ['Anthropic', 'APIError'],
        'sqlalchemy':    ['Column', 'String', 'Text', 'DateTime', 'Float', 'Boolean',
                          'JSON', 'Index', 'text', 'create_engine', 'Integer'],
        'sqlalchemy.orm': ['DeclarativeBase', 'Session', 'sessionmaker'],
    }.items():
        if pkg not in sys.modules:
            m = types.ModuleType(pkg)
            for a in attrs:
                setattr(m, a,
                        type(a, (), {'__init__': lambda s, *a, **k: None})
                        if a[0].isupper() else (lambda *a, **k: None))
            sys.modules[pkg] = m
    sys.modules['tenacity'].retry = lambda **k: (lambda f: f)


TODAY = date.today().isoformat()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# TIMELINE AGENT TESTS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestDateParsing(unittest.TestCase):

    def _p(self, s):
        from agents.timeline_agent import _parse_date
        return _parse_date(s)

    def test_iso_date(self):
        self.assertEqual(self._p("2024-08-01"), "2024-08-01")

    def test_year_month(self):
        self.assertEqual(self._p("2024-08"), "2024-08-01")

    def test_year_only(self):
        self.assertEqual(self._p("2026"), "2026-01-01")

    def test_month_year_string(self):
        result = self._p("March 2026")
        self.assertIsNotNone(result)
        self.assertIn("2026", result)
        self.assertIn("03", result)

    def test_abbreviated_month(self):
        result = self._p("Feb 2025")
        self.assertIsNotNone(result)
        self.assertIn("2025", result)
        self.assertIn("02", result)

    def test_none_returns_none(self):
        self.assertIsNone(self._p(None))

    def test_empty_returns_none(self):
        self.assertIsNone(self._p(""))

    def test_garbage_returns_none(self):
        self.assertIsNone(self._p("not a date"))


class TestBaselineEventExtraction(unittest.TestCase):

    def _eu_ai_act(self):
        return {
            'id': 'eu_ai_act', 'jurisdiction': 'EU',
            'title': 'EU AI Act', 'short_name': 'EU AIA',
            'timeline': [
                {'date': '2024-08-01', 'milestone': 'Regulation enters into force'},
                {'date': '2025-02-02', 'milestone': 'Prohibited practices apply'},
                {'date': '2026-08-02', 'milestone': 'Full high-risk obligations apply'},
            ],
            'implementing_acts_status': [
                {'title': 'Guidelines on prohibited practices', 'status': 'Published Feb 2025'},
                {'title': 'GPAI Code of Practice', 'status': 'Expected 2025'},
            ],
        }

    def _colorado(self):
        return {
            'id': 'colorado_ai', 'jurisdiction': 'CO',
            'title': 'Colorado AI Act', 'short_name': 'Colorado AI',
            'effective_date': '2026-02-01',
        }

    def _canada(self):
        return {
            'id': 'canada_aida', 'jurisdiction': 'CA',
            'title': 'Canada AIDA', 'short_name': 'AIDA',
            'legislative_status': {'bill': 'Bill C-27', 'introduced': '2022-06-16'},
        }

    def test_extracts_timeline_milestones(self):
        from agents.timeline_agent import extract_baseline_events
        events = extract_baseline_events(self._eu_ai_act())
        milestone_events = [e for e in events if e['event_type'] == 'milestone']
        self.assertGreaterEqual(len(milestone_events), 3)

    def test_extracts_effective_date(self):
        from agents.timeline_agent import extract_baseline_events
        events = extract_baseline_events(self._colorado())
        eff = [e for e in events if e['event_type'] == 'effective']
        self.assertEqual(len(eff), 1)
        self.assertEqual(eff[0]['date'], '2026-02-01')

    def test_extracts_legislative_intro_date(self):
        from agents.timeline_agent import extract_baseline_events
        events = extract_baseline_events(self._canada())
        intro = [e for e in events if e['event_type'] == 'introduced']
        self.assertEqual(len(intro), 1)
        self.assertIn('2022', intro[0]['date'])

    def test_extracts_implementing_acts(self):
        from agents.timeline_agent import extract_baseline_events
        events = extract_baseline_events(self._eu_ai_act())
        ia = [e for e in events if e['event_type'] == 'implementing_act']
        self.assertGreaterEqual(len(ia), 1)

    def test_event_metadata_populated(self):
        from agents.timeline_agent import extract_baseline_events
        events = extract_baseline_events(self._eu_ai_act())
        for e in events:
            self.assertIn('date',            e)
            self.assertIn('event',           e)
            self.assertIn('event_type',      e)
            self.assertIn('regulation_id',   e)
            self.assertIn('regulation_name', e)
            self.assertIn('jurisdiction',    e)
            self.assertIn('status',          e)

    def test_past_events_marked_confirmed(self):
        from agents.timeline_agent import extract_baseline_events
        events = extract_baseline_events(self._eu_ai_act())
        past = [e for e in events if e['date'] < TODAY]
        for e in past:
            self.assertEqual(e['status'], 'confirmed')

    def test_future_events_marked_anticipated(self):
        from agents.timeline_agent import extract_baseline_events
        # Force a future date
        baseline = {
            'id': 'test', 'jurisdiction': 'XX',
            'effective_date': '2099-01-01',
            'title': 'Future Law', 'short_name': 'FL',
        }
        events = extract_baseline_events(baseline)
        self.assertEqual(events[0]['status'], 'anticipated')

    def test_baseline_without_timeline_returns_empty(self):
        from agents.timeline_agent import extract_baseline_events
        events = extract_baseline_events({'id': 'x', 'jurisdiction': 'XX', 'title': 'X'})
        self.assertEqual(events, [])


class TestDocumentEventExtraction(unittest.TestCase):

    def _doc(self, **kwargs):
        base = {
            'id':            'DOC-001',
            'title':         'AI Risk Management Final Rule',
            'jurisdiction':  'Federal',
            'status':        'Final Rule',
            'published_date': '2025-06-15T00:00:00',
            'plain_english': 'This rule requires risk assessments.',
            'url':           'https://example.gov',
        }
        base.update(kwargs)
        return base

    def test_extracts_document_event(self):
        from agents.timeline_agent import extract_document_events
        events = extract_document_events([self._doc()])
        self.assertEqual(len(events), 1)

    def test_maps_status_to_event_type(self):
        from agents.timeline_agent import extract_document_events
        events = extract_document_events([self._doc(status='Final Rule')])
        self.assertEqual(events[0]['event_type'], 'final')

    def test_proposed_rule_type(self):
        from agents.timeline_agent import extract_document_events
        events = extract_document_events([self._doc(status='Proposed Rule')])
        self.assertEqual(events[0]['event_type'], 'proposed')

    def test_skips_docs_without_summary(self):
        from agents.timeline_agent import extract_document_events
        doc = self._doc()
        doc['plain_english'] = ''
        events = extract_document_events([doc])
        self.assertEqual(len(events), 0)

    def test_skips_docs_without_date(self):
        from agents.timeline_agent import extract_document_events
        doc = self._doc()
        doc['published_date'] = None
        doc['fetched_at']     = None
        events = extract_document_events([doc])
        self.assertEqual(len(events), 0)

    def test_date_extracted_correctly(self):
        from agents.timeline_agent import extract_document_events
        events = extract_document_events([self._doc(published_date='2025-06-15T00:00:00')])
        self.assertEqual(events[0]['date'], '2025-06-15')


class TestTimelineAgent(unittest.TestCase):

    def _agent(self):
        from agents.timeline_agent import TimelineAgent
        return TimelineAgent()

    def test_returns_dict_with_required_keys(self):
        agent = self._agent()
        with patch('agents.timeline_agent.BASELINES_DIR', Path('/tmp/nonexistent_xyz')):
            with patch('utils.db.get_recent_summaries', return_value=[]):
                with patch('agents.timeline_agent.extract_horizon_events', return_value=[]):
                    result = agent.get_timeline()

        for key in ('events', 'jurisdictions', 'event_types', 'total'):
            self.assertIn(key, result)

    def test_events_sorted_chronologically(self):
        agent = self._agent()
        mock_events = [
            {'date': '2025-03-01', 'event': 'C', 'event_type': 'milestone',
             'regulation_id': 'x', 'regulation_name': 'X',
             'jurisdiction': 'EU', 'status': 'confirmed'},
            {'date': '2024-01-01', 'event': 'A', 'event_type': 'milestone',
             'regulation_id': 'y', 'regulation_name': 'Y',
             'jurisdiction': 'EU', 'status': 'confirmed'},
            {'date': '2024-06-15', 'event': 'B', 'event_type': 'effective',
             'regulation_id': 'z', 'regulation_name': 'Z',
             'jurisdiction': 'EU', 'status': 'confirmed'},
        ]
        with patch('agents.timeline_agent.BASELINES_DIR', Path('/tmp/nonexistent_xyz')):
            with patch('utils.db.get_recent_summaries', return_value=[]):
                with patch('agents.timeline_agent.extract_horizon_events',
                           return_value=mock_events):
                    result = agent.get_timeline(years_back=5, years_ahead=3)

        dates = [e['date'] for e in result['events']]
        self.assertEqual(dates, sorted(dates))

    def test_jurisdiction_filter_applied(self):
        agent = self._agent()
        mock_events = [
            {'date': '2025-01-01', 'event': 'EU Event', 'event_type': 'milestone',
             'regulation_id': 'eu', 'regulation_name': 'EU Law',
             'jurisdiction': 'EU', 'status': 'confirmed'},
            {'date': '2025-02-01', 'event': 'US Event', 'event_type': 'final',
             'regulation_id': 'us', 'regulation_name': 'US Rule',
             'jurisdiction': 'Federal', 'status': 'confirmed'},
        ]
        with patch('agents.timeline_agent.BASELINES_DIR', Path('/tmp/nonexistent_xyz')):
            with patch('utils.db.get_recent_summaries', return_value=[]):
                with patch('agents.timeline_agent.extract_horizon_events',
                           return_value=mock_events):
                    result = agent.get_timeline(jurisdiction='EU')

        jurs = {e['jurisdiction'] for e in result['events']}
        self.assertNotIn('Federal', jurs)

    def test_deduplication_works(self):
        agent = self._agent()
        dup = {'date': '2025-01-01', 'event': 'Same', 'event_type': 'milestone',
               'regulation_id': 'x', 'regulation_name': 'X',
               'jurisdiction': 'EU', 'status': 'confirmed'}
        with patch('agents.timeline_agent.BASELINES_DIR', Path('/tmp/nonexistent_xyz')):
            with patch('utils.db.get_recent_summaries', return_value=[]):
                with patch('agents.timeline_agent.extract_horizon_events',
                           return_value=[dup, dup, dup]):
                    result = agent.get_timeline()

        # Three identical events should be deduplicated to one
        count = sum(1 for e in result['events'] if e['regulation_id'] == 'x')
        self.assertEqual(count, 1)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# BRIEF AGENT TESTS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestBriefAgent(unittest.TestCase):

    def _agent(self):
        from agents.brief_agent import BriefAgent
        return BriefAgent()

    def _mock_passages(self):
        return [
            {'id': 1, 'source_id': 'eu_ai_act', 'source_title': 'EU AI Act',
             'jurisdiction': 'EU', 'section_label': 'Overview', 'source_type': 'baseline',
             'chunk_index': 0, 'chunk_total': 1,
             'text': 'Foundation model providers must comply with transparency obligations.',
             'score': 0.9},
            {'id': 2, 'source_id': 'us_eo_14110', 'source_title': 'EO 14110',
             'jurisdiction': 'Federal', 'section_label': 'Overview', 'source_type': 'baseline',
             'chunk_index': 0, 'chunk_total': 1,
             'text': 'Advanced AI developers must report capabilities to NIST.',
             'score': 0.8},
        ]

    def _mock_llm_response(self):
        return """## Overview
Foundation model governance is addressed differently across jurisdictions. [SOURCE: eu_ai_act][SOURCE: us_eo_14110]

## Key Jurisdictions

**EU (eu_ai_act)**: The EU AI Act Chapter V establishes GPAI obligations. [SOURCE: eu_ai_act]

**Federal (us_eo_14110)**: EO 14110 requires developers to report to NIST. [SOURCE: us_eo_14110]

## Convergences
- Both require transparency about capabilities [SOURCE: eu_ai_act]

## Divergences
- EU mandates binding requirements; US relies on voluntary disclosures

## What Is Settled vs Still Developing
Settled: EU GPAI requirements in force since August 2025. [SOURCE: eu_ai_act]
Developing: US statutory framework pending.

## Practical Implications
- Organisations must prepare GPAI documentation for EU market access [SOURCE: eu_ai_act]

## Open Questions & What to Watch
- US federal AI legislation trajectory"""

    def test_returns_result_structure(self):
        agent = self._agent()
        with patch('utils.db.get_brief_cache', return_value=None):
            with patch('utils.rag.get_retriever') as mock_ret:
                mock_ret.return_value.retrieve.return_value = self._mock_passages()
                mock_ret.return_value._ready = True
                with patch('agents.brief_agent.call_llm',
                           return_value=self._mock_llm_response()):
                    with patch('agents.brief_agent.active_model', return_value='test'):
                        with patch('utils.db.save_brief_cache'):
                            result = agent.generate('foundation model governance')

        for key in ('topic_key', 'topic_label', 'content', 'citations', 'model_used'):
            self.assertIn(key, result)

    def test_content_is_markdown(self):
        agent = self._agent()
        with patch('utils.db.get_brief_cache', return_value=None):
            with patch('utils.rag.get_retriever') as mock_ret:
                mock_ret.return_value.retrieve.return_value = self._mock_passages()
                mock_ret.return_value._ready = True
                with patch('agents.brief_agent.call_llm',
                           return_value=self._mock_llm_response()):
                    with patch('agents.brief_agent.active_model', return_value='test'):
                        with patch('utils.db.save_brief_cache'):
                            result = agent.generate('foundation model governance')

        self.assertIn('##', result['content'])

    def test_citations_extracted(self):
        agent = self._agent()
        with patch('utils.db.get_brief_cache', return_value=None):
            with patch('utils.rag.get_retriever') as mock_ret:
                mock_ret.return_value.retrieve.return_value = self._mock_passages()
                mock_ret.return_value._ready = True
                with patch('agents.brief_agent.call_llm',
                           return_value=self._mock_llm_response()):
                    with patch('agents.brief_agent.active_model', return_value='test'):
                        with patch('utils.db.save_brief_cache'):
                            result = agent.generate('foundation model governance')

        self.assertIsInstance(result['citations'], list)
        self.assertGreater(len(result['citations']), 0)

    def test_returns_cached_when_available(self):
        agent  = self._agent()
        cached = {'topic_key': 'brief_abc', 'topic_label': 'test',
                  'content': 'cached content', 'citations': [],
                  'model_used': 'test', 'built_at': '2026-01-01T00:00:00'}
        with patch('utils.db.get_brief_cache', return_value=cached):
            result = agent.generate('test topic', force=False)
        self.assertEqual(result['content'], 'cached content')

    def test_force_bypasses_cache(self):
        agent = self._agent()
        with patch('utils.db.get_brief_cache') as mock_cache:
            with patch('utils.rag.get_retriever') as mock_ret:
                mock_ret.return_value.retrieve.return_value = self._mock_passages()
                mock_ret.return_value._ready = True
                with patch('agents.brief_agent.call_llm',
                           return_value=self._mock_llm_response()):
                    with patch('agents.brief_agent.active_model', return_value='test'):
                        with patch('utils.db.save_brief_cache'):
                            agent.generate('test', force=True)
        mock_cache.assert_not_called()

    def test_empty_passages_returns_error_result(self):
        agent = self._agent()
        with patch('utils.db.get_brief_cache', return_value=None):
            with patch('utils.rag.get_retriever') as mock_ret:
                mock_ret.return_value.retrieve.return_value = []
                mock_ret.return_value._ready = True
                result = agent.generate('completely unknown topic xyz')

        self.assertTrue(result.get('error'))
        self.assertIn('content', result)

    def test_llm_error_returns_error_result(self):
        from utils.llm import LLMError
        agent = self._agent()
        with patch('utils.db.get_brief_cache', return_value=None):
            with patch('utils.rag.get_retriever') as mock_ret:
                mock_ret.return_value.retrieve.return_value = self._mock_passages()
                mock_ret.return_value._ready = True
                with patch('agents.brief_agent.call_llm',
                           side_effect=LLMError("API down")):
                    result = agent.generate('test topic')

        self.assertTrue(result.get('error'))

    def test_topic_key_deterministic(self):
        from agents.brief_agent import BriefAgent
        k1 = BriefAgent._make_key("foundation model governance", None)
        k2 = BriefAgent._make_key("foundation model governance", None)
        self.assertEqual(k1, k2)

    def test_different_topics_different_keys(self):
        from agents.brief_agent import BriefAgent
        k1 = BriefAgent._make_key("transparency", None)
        k2 = BriefAgent._make_key("risk assessment", None)
        self.assertNotEqual(k1, k2)

    def test_jurisdiction_affects_key(self):
        from agents.brief_agent import BriefAgent
        k1 = BriefAgent._make_key("transparency", "EU")
        k2 = BriefAgent._make_key("transparency", "Federal")
        self.assertNotEqual(k1, k2)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# COMPARE AGENT TESTS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestCompareAgent(unittest.TestCase):

    def _agent(self):
        from agents.compare_agent import CompareAgent
        return CompareAgent()

    def _eu_baseline(self):
        return {
            'id': 'eu_ai_act', 'jurisdiction': 'EU',
            'title': 'EU AI Act', 'short_name': 'EU AIA',
            'overview': 'Risk-based framework for AI with mandatory obligations.',
            'obligations_by_actor': {
                'providers_high_risk': [
                    {'title': 'Conformity assessment',
                     'description': 'Providers must conduct conformity assessments.',
                     'article': 'Article 43'}
                ],
            },
            'penalties': {'max_fine': 'â‚¬35M or 7% global turnover'},
        }

    def _nist_baseline(self):
        return {
            'id': 'us_nist_ai_rmf', 'jurisdiction': 'Federal',
            'title': 'NIST AI RMF', 'short_name': 'NIST AI RMF',
            'overview': 'Voluntary framework for managing AI risks.',
            'core_functions': [
                {'function': 'GOVERN', 'description': 'Policies for AI risk governance.'},
                {'function': 'MAP', 'description': 'Categorise AI risks.'},
            ],
        }

    def _mock_compare_response(self):
        return json.dumps({
            "summary": "EU AI Act is mandatory with penalties; NIST RMF is voluntary guidance. [eu_ai_act][us_nist_ai_rmf]",
            "agreements": [
                {"area": "Risk management", "description": "Both emphasise risk-based approaches. [eu_ai_act]"}
            ],
            "divergences": [
                {
                    "area": "Legal force",
                    "a_approach": "Legally binding with fines up to â‚¬35M [eu_ai_act]",
                    "b_approach": "Voluntary framework [us_nist_ai_rmf]",
                    "significance": "Fundamentally different compliance obligations"
                }
            ],
            "a_stricter_on": ["Conformity assessments", "Prohibited practices"],
            "b_stricter_on": [],
            "practical_notes": ["Organisations should use NIST RMF to prepare for EU requirements"]
        })

    def test_returns_comparison_structure(self):
        agent = self._agent()
        with patch('agents.compare_agent._load_baseline') as mock_load:
            mock_load.side_effect = lambda bid: (
                self._eu_baseline() if bid == 'eu_ai_act' else
                self._nist_baseline()
            )
            with patch('agents.compare_agent.call_llm',
                       return_value=self._mock_compare_response()):
                with patch('agents.compare_agent.active_model', return_value='test'):
                    result = self._agent().compare('eu_ai_act', 'us_nist_ai_rmf',
                                                   type_a='baseline', type_b='baseline')

        for key in ('title', 'summary', 'agreements', 'divergences',
                    'a_stricter_on', 'b_stricter_on', 'practical_notes'):
            self.assertIn(key, result)

    def test_title_contains_both_names(self):
        agent = self._agent()
        with patch('agents.compare_agent._load_baseline') as mock_load:
            mock_load.side_effect = lambda bid: (
                self._eu_baseline() if bid == 'eu_ai_act' else self._nist_baseline()
            )
            with patch('agents.compare_agent.call_llm',
                       return_value=self._mock_compare_response()):
                with patch('agents.compare_agent.active_model', return_value='test'):
                    result = self._agent().compare('eu_ai_act', 'us_nist_ai_rmf',
                                                   type_a='baseline', type_b='baseline')

        self.assertIn('EU AI Act', result['title'])
        self.assertIn('NIST', result['title'])

    def test_returns_error_for_unknown_source(self):
        result = self._agent().compare('totally_nonexistent_id', 'eu_ai_act')
        self.assertIn('error', result)

    def test_agreements_is_list(self):
        agent = self._agent()
        with patch('agents.compare_agent._load_baseline') as mock_load:
            mock_load.side_effect = lambda bid: (
                self._eu_baseline() if bid == 'eu_ai_act' else self._nist_baseline()
            )
            with patch('agents.compare_agent.call_llm',
                       return_value=self._mock_compare_response()):
                with patch('agents.compare_agent.active_model', return_value='test'):
                    result = self._agent().compare('eu_ai_act', 'us_nist_ai_rmf',
                                                   type_a='baseline', type_b='baseline')

        self.assertIsInstance(result['agreements'],  list)
        self.assertIsInstance(result['divergences'], list)
        self.assertIsInstance(result['a_stricter_on'], list)
        self.assertIsInstance(result['b_stricter_on'], list)

    def test_citations_extracted(self):
        agent = self._agent()
        with patch('agents.compare_agent._load_baseline') as mock_load:
            mock_load.side_effect = lambda bid: (
                self._eu_baseline() if bid == 'eu_ai_act' else self._nist_baseline()
            )
            with patch('agents.compare_agent.call_llm',
                       return_value=self._mock_compare_response()):
                with patch('agents.compare_agent.active_model', return_value='test'):
                    result = self._agent().compare('eu_ai_act', 'us_nist_ai_rmf',
                                                   type_a='baseline', type_b='baseline')

        self.assertIsInstance(result['citations'], list)

    def test_llm_error_returns_error_result(self):
        from utils.llm import LLMError
        with patch('agents.compare_agent._load_baseline') as mock_load:
            mock_load.side_effect = lambda bid: (
                self._eu_baseline() if bid == 'eu_ai_act' else self._nist_baseline()
            )
            with patch('agents.compare_agent.call_llm',
                       side_effect=LLMError("API down")):
                result = self._agent().compare('eu_ai_act', 'us_nist_ai_rmf',
                                               type_a='baseline', type_b='baseline')

        self.assertIn('error', result)

    def test_focus_included_in_result(self):
        agent = self._agent()
        with patch('agents.compare_agent._load_baseline') as mock_load:
            mock_load.side_effect = lambda bid: (
                self._eu_baseline() if bid == 'eu_ai_act' else self._nist_baseline()
            )
            with patch('agents.compare_agent.call_llm',
                       return_value=self._mock_compare_response()):
                with patch('agents.compare_agent.active_model', return_value='test'):
                    result = self._agent().compare('eu_ai_act', 'us_nist_ai_rmf',
                                                   type_a='baseline', type_b='baseline',
                                                   focus='transparency')

        self.assertEqual(result.get('focus'), 'transparency')

    def test_malformed_llm_response_handled(self):
        with patch('agents.compare_agent._load_baseline') as mock_load:
            mock_load.side_effect = lambda bid: (
                self._eu_baseline() if bid == 'eu_ai_act' else self._nist_baseline()
            )
            with patch('agents.compare_agent.call_llm',
                       return_value='not json at all just text'):
                with patch('agents.compare_agent.active_model', return_value='test'):
                    result = self._agent().compare('eu_ai_act', 'us_nist_ai_rmf',
                                                   type_a='baseline', type_b='baseline')

        # Should not crash, should return something
        self.assertIn('title', result)
        self.assertIn('summary', result)


class TestBaselineTextExtraction(unittest.TestCase):

    def _eu(self):
        return {
            'id': 'eu_ai_act', 'jurisdiction': 'EU',
            'title': 'EU AI Act', 'overview': 'Risk-based framework.',
            'obligations_by_actor': {'providers': 'Must conduct assessments.'},
        }

    def test_extracts_text(self):
        from agents.compare_agent import _baseline_text
        result = _baseline_text(self._eu())
        self.assertGreater(len(result), 0)
        self.assertIn('Risk-based', result)

    def test_caps_length(self):
        from agents.compare_agent import _baseline_text
        big = {**self._eu(), 'section_1': 'x' * 10000, 'section_2': 'y' * 10000}
        result = _baseline_text(big)
        self.assertLessEqual(len(result), 5000)

    def test_focus_filters_sections(self):
        from agents.compare_agent import _baseline_text
        b = {
            'id': 'x', 'jurisdiction': 'EU', 'title': 'X', 'overview': 'Overview.',
            'transparency_section': 'Transparency obligations here.',
            'unrelated_section': 'Bridge maintenance requirements.',
        }
        result_focused    = _baseline_text(b, focus='transparency')
        result_unfocused  = _baseline_text(b)
        # Focused should include transparency section
        self.assertIn('Transparency', result_focused)


if __name__ == "__main__":
    unittest.main(verbosity=2)
