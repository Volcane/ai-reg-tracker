"""
ARIS — Concept Mapping Agent Tests
"""
import json
import sys
import types
import unittest
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


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _eu_ai_act():
    return {
        'id': 'eu_ai_act', 'jurisdiction': 'EU',
        'title': 'EU AI Act', 'short_name': 'EU AIA',
        'status': 'In Force', 'last_reviewed': '2024-08-01',
        'overview': 'The EU AI Act establishes a risk-based framework for AI.',
        'obligations_by_actor': {
            'providers_high_risk': [
                {
                    'id': 'eu-aia-prov-transparency',
                    'title': 'Transparency and instructions',
                    'description': 'Providers must supply clear instructions for use, '
                                   'including capabilities, limitations, and human oversight requirements.',
                    'article': 'Article 13',
                }
            ],
            'deployers_high_risk': [
                {
                    'id': 'eu-aia-dep-transparency',
                    'title': 'Inform affected persons',
                    'description': 'Deployers must inform persons subject to decisions '
                                   'from high-risk AI systems that they are interacting with AI.',
                    'article': 'Article 50',
                }
            ],
        },
        'cross_references': [],
    }


def _nist_rmf():
    return {
        'id': 'us_nist_ai_rmf', 'jurisdiction': 'Federal',
        'title': 'NIST AI Risk Management Framework', 'short_name': 'NIST AI RMF',
        'status': 'Published',
        'overview': 'NIST AI RMF provides a voluntary framework for managing AI risks '
                    'through risk-based approaches.',
        'trustworthy_ai_characteristics': [
            'Accountable and transparent',
            'Explainable and interpretable',
            'Privacy-enhanced',
            'Fair with harmful bias managed',
        ],
        'core_functions': [
            {
                'function': 'GOVERN',
                'description': 'Cultivate transparency and explainability policies across the organisation.',
            },
        ],
        'cross_references': [],
    }


def _colorado():
    return {
        'id': 'colorado_ai', 'jurisdiction': 'Federal',
        'title': 'Colorado AI Act', 'short_name': 'Colorado AI',
        'status': 'In Force',
        'overview': 'Colorado AI Act requires deployers to provide transparency disclosures '
                    'about high-risk AI systems used in consequential decisions.',
        'deployer_obligations': [
            {
                'title': 'Transparency disclosure',
                'description': 'Deployers must disclose use of AI in consequential decisions '
                               'and provide explanation upon request.',
            }
        ],
        'cross_references': [],
    }


def _sample_llm_response():
    return json.dumps([
        {
            'jurisdiction':     'EU',
            'baseline_id':      'eu_ai_act',
            'baseline_title':   'EU AI Act',
            'obligation':       'Providers must supply instructions for use; deployers must inform affected persons.',
            'scope':            'High-risk AI system providers and deployers',
            'trigger':          'Before placing high-risk AI system on the market',
            'strength':         'mandatory',
            'section':          'Articles 13 and 50',
            'similarity_notes': 'Most detailed transparency requirements; stricter than NIST and Colorado.',
        },
        {
            'jurisdiction':     'Federal',
            'baseline_id':      'us_nist_ai_rmf',
            'baseline_title':   'NIST AI Risk Management Framework',
            'obligation':       'Organisations should implement transparency and explainability practices.',
            'scope':            'All AI developers and deployers',
            'trigger':          'Throughout the AI lifecycle',
            'strength':         'guidance',
            'section':          'GOVERN function',
            'similarity_notes': 'Voluntary framework; broader than EU mandatory requirements.',
        },
    ])


# ── CONCEPT_CATALOGUE ─────────────────────────────────────────────────────────

class TestConceptCatalogue(unittest.TestCase):

    def test_catalogue_has_entries(self):
        from agents.concept_agent import CONCEPT_CATALOGUE
        self.assertGreater(len(CONCEPT_CATALOGUE), 5)

    def test_all_entries_have_required_fields(self):
        from agents.concept_agent import CONCEPT_CATALOGUE
        for key, spec in CONCEPT_CATALOGUE.items():
            self.assertIn('label',       spec, f"{key} missing label")
            self.assertIn('description', spec, f"{key} missing description")
            self.assertIn('keywords',    spec, f"{key} missing keywords")

    def test_keywords_are_lists(self):
        from agents.concept_agent import CONCEPT_CATALOGUE
        for key, spec in CONCEPT_CATALOGUE.items():
            self.assertIsInstance(spec['keywords'], list)
            self.assertGreater(len(spec['keywords']), 0)

    def test_known_concepts_present(self):
        from agents.concept_agent import CONCEPT_CATALOGUE
        for expected in ['transparency', 'risk_assessment', 'bias_fairness',
                         'human_oversight', 'automated_decisions', 'prohibited_practices']:
            self.assertIn(expected, CONCEPT_CATALOGUE)

    def test_labels_are_strings(self):
        from agents.concept_agent import CONCEPT_CATALOGUE
        for key, spec in CONCEPT_CATALOGUE.items():
            self.assertIsInstance(spec['label'], str)
            self.assertGreater(len(spec['label']), 0)


# ── Section extraction ────────────────────────────────────────────────────────

class TestSectionExtraction(unittest.TestCase):

    def _extract(self, baseline, keywords):
        from agents.concept_agent import _extract_concept_sections
        return _extract_concept_sections(baseline, keywords)

    def test_extracts_relevant_section(self):
        result = self._extract(_eu_ai_act(), ['transparency', 'explainab'])
        self.assertIn('eu_ai_act', result)
        self.assertIn('transparency', result.lower())

    def test_returns_empty_for_irrelevant(self):
        baseline = {
            'id': 'test', 'jurisdiction': 'XX',
            'title': 'Bridge Standards',
            'overview': 'Requirements for bridge maintenance and inspection.',
        }
        result = self._extract(baseline, ['transparency', 'explainab'])
        # Should return empty or just the header
        self.assertEqual(result, "")

    def test_includes_regulation_header(self):
        result = self._extract(_eu_ai_act(), ['transparency'])
        self.assertIn('EU AI Act', result)

    def test_captures_nested_content(self):
        result = self._extract(_eu_ai_act(), ['transparency'])
        self.assertIn('Article 13', result)

    def test_caps_content_length(self):
        # Very large baseline should not exceed reasonable length
        big_baseline = {
            'id': 'big', 'jurisdiction': 'XX',
            'title': 'Big Regulation',
            'section_1': {'transparency': 'x' * 5000},
            'section_2': {'transparency': 'y' * 5000},
        }
        result = self._extract(big_baseline, ['transparency'])
        self.assertLess(len(result), 10000)


# ── Response parsing ──────────────────────────────────────────────────────────

class TestResponseParsing(unittest.TestCase):

    def _parse(self, raw):
        from agents.concept_agent import _parse_concept_entries
        return _parse_concept_entries(raw)

    def test_parses_valid_json(self):
        entries = self._parse(_sample_llm_response())
        self.assertEqual(len(entries), 2)

    def test_entries_have_required_fields(self):
        entries = self._parse(_sample_llm_response())
        for e in entries:
            self.assertIn('jurisdiction', e)
            self.assertIn('baseline_id',  e)
            self.assertIn('obligation',   e)
            self.assertIn('strength',     e)

    def test_strength_normalised(self):
        entries = self._parse(_sample_llm_response())
        for e in entries:
            self.assertIn(e['strength'], ('mandatory', 'recommended', 'guidance'))

    def test_sorted_mandatory_first(self):
        entries = self._parse(_sample_llm_response())
        if len(entries) >= 2:
            first_strength = entries[0]['strength']
            # mandatory before guidance
            self.assertEqual(first_strength, 'mandatory')

    def test_invalid_strength_becomes_guidance(self):
        raw = json.dumps([{
            'jurisdiction': 'EU', 'baseline_id': 'test',
            'obligation': 'Test', 'strength': 'totally_invalid',
        }])
        entries = self._parse(raw)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['strength'], 'guidance')

    def test_empty_array_returns_empty(self):
        entries = self._parse('[]')
        self.assertEqual(entries, [])

    def test_invalid_json_returns_empty(self):
        entries = self._parse('not json at all')
        self.assertEqual(entries, [])

    def test_missing_required_fields_skipped(self):
        raw = json.dumps([
            {'jurisdiction': 'EU'},   # missing obligation, baseline_id, strength
            {
                'jurisdiction': 'Federal', 'baseline_id': 'test',
                'obligation': 'Valid', 'strength': 'mandatory',
            }
        ])
        entries = self._parse(raw)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['jurisdiction'], 'Federal')

    def test_handles_json_in_code_block(self):
        raw = '```json\n' + _sample_llm_response() + '\n```'
        entries = self._parse(raw)
        self.assertEqual(len(entries), 2)

    def test_similarity_notes_preserved(self):
        entries = self._parse(_sample_llm_response())
        eu = next((e for e in entries if e['jurisdiction'] == 'EU'), None)
        self.assertIsNotNone(eu)
        self.assertGreater(len(eu.get('similarity_notes', '')), 0)


# ── Concept Agent ─────────────────────────────────────────────────────────────

class TestConceptAgent(unittest.TestCase):

    def _agent(self):
        from agents.concept_agent import ConceptAgent
        return ConceptAgent()

    def test_unknown_concept_returns_none(self):
        agent = self._agent()
        result = agent.get_concept_map('totally_unknown_concept_xyz')
        self.assertIsNone(result)

    def test_returns_cached_when_available(self):
        agent  = self._agent()
        cached = {
            'concept_key':   'transparency',
            'concept_label': 'Transparency & Explainability',
            'entries':       [{'jurisdiction': 'EU', 'baseline_id': 'eu_ai_act',
                               'obligation': 'test', 'strength': 'mandatory'}],
            'entry_count':   1,
            'model_used':    'test-model',
            'built_at':      '2026-01-01T00:00:00',
        }
        with patch('utils.db.get_concept_map', return_value=cached):
            result = agent.get_concept_map('transparency', force=False)
        self.assertEqual(result['concept_key'], 'transparency')
        self.assertEqual(result['entry_count'], 1)

    def test_bypasses_cache_when_force(self):
        agent = self._agent()
        with patch('utils.db.get_concept_map') as mock_cache:
            with patch('agents.concept_agent._load_baselines',
                       return_value=[_eu_ai_act(), _nist_rmf()]):
                with patch('agents.concept_agent.call_llm',
                           return_value=_sample_llm_response()):
                    with patch('utils.llm.active_model', return_value='test'):
                        with patch('utils.db.save_concept_map'):
                            result = agent.get_concept_map('transparency', force=True)
        # Should NOT have called get_concept_map (cache bypassed)
        mock_cache.assert_not_called()

    def test_builds_from_baselines(self):
        agent = self._agent()
        with patch('utils.db.get_concept_map', return_value=None):
            with patch('agents.concept_agent._load_baselines',
                       return_value=[_eu_ai_act(), _nist_rmf(), _colorado()]):
                with patch('agents.concept_agent.call_llm',
                           return_value=_sample_llm_response()):
                    with patch('utils.llm.active_model', return_value='test-model'):
                        with patch('utils.db.save_concept_map') as mock_save:
                            result = agent.get_concept_map('transparency')

        self.assertIsNotNone(result)
        self.assertEqual(result['concept_key'], 'transparency')
        self.assertGreater(result['entry_count'], 0)
        mock_save.assert_called_once()

    def test_result_structure(self):
        agent = self._agent()
        with patch('utils.db.get_concept_map', return_value=None):
            with patch('agents.concept_agent._load_baselines',
                       return_value=[_eu_ai_act(), _nist_rmf()]):
                with patch('agents.concept_agent.call_llm',
                           return_value=_sample_llm_response()):
                    with patch('utils.llm.active_model', return_value='test'):
                        with patch('utils.db.save_concept_map'):
                            result = agent.get_concept_map('transparency')

        required = ['concept_key', 'concept_label', 'description', 'entries', 'entry_count']
        for field in required:
            self.assertIn(field, result, f"Missing field: {field}")
        self.assertIsInstance(result['entries'], list)

    def test_entries_are_sorted_mandatory_first(self):
        agent = self._agent()
        with patch('utils.db.get_concept_map', return_value=None):
            with patch('agents.concept_agent._load_baselines',
                       return_value=[_eu_ai_act(), _nist_rmf()]):
                with patch('agents.concept_agent.call_llm',
                           return_value=_sample_llm_response()):
                    with patch('utils.llm.active_model', return_value='test'):
                        with patch('utils.db.save_concept_map'):
                            result = agent.get_concept_map('transparency')

        entries = result.get('entries', [])
        if len(entries) >= 2:
            self.assertEqual(entries[0]['strength'], 'mandatory')

    def test_llm_error_returns_none(self):
        from utils.llm import LLMError
        agent = self._agent()
        with patch('utils.db.get_concept_map', return_value=None):
            with patch('agents.concept_agent._load_baselines',
                       return_value=[_eu_ai_act()]):
                with patch('agents.concept_agent.call_llm',
                           side_effect=LLMError("API down")):
                    result = agent.get_concept_map('transparency')
        self.assertIsNone(result)

    def test_no_relevant_baselines_returns_empty(self):
        agent = self._agent()
        # Baseline with no transparency content
        bare_baseline = {
            'id': 'bare', 'jurisdiction': 'XX',
            'title': 'Bridge Standards',
            'overview': 'Bridge maintenance requirements.',
        }
        with patch('utils.db.get_concept_map', return_value=None):
            with patch('agents.concept_agent._load_baselines', return_value=[bare_baseline]):
                result = agent.get_concept_map('transparency')

        self.assertIsNotNone(result)
        self.assertEqual(result['entry_count'], 0)
        self.assertEqual(result['entries'], [])

    def test_list_concepts_returns_all(self):
        from agents.concept_agent import CONCEPT_CATALOGUE
        with patch('utils.db.list_concept_maps', return_value=[]):
            concepts = self._agent().list_concepts()
        self.assertEqual(len(concepts), len(CONCEPT_CATALOGUE))

    def test_list_concepts_shows_cache_status(self):
        cached_entry = {
            'concept_key': 'transparency', 'concept_label': 'Transparency',
            'entry_count': 9, 'built_at': '2026-01-01T00:00:00',
        }
        with patch('utils.db.list_concept_maps', return_value=[cached_entry]):
            concepts = self._agent().list_concepts()

        transparency = next((c for c in concepts if c['key'] == 'transparency'), None)
        self.assertIsNotNone(transparency)
        self.assertTrue(transparency['cached'])
        self.assertEqual(transparency['entry_count'], 9)

    def test_uncached_concept_shows_not_cached(self):
        with patch('utils.db.list_concept_maps', return_value=[]):
            concepts = self._agent().list_concepts()
        for c in concepts:
            self.assertFalse(c['cached'])
            self.assertEqual(c['entry_count'], 0)


# ── Content filtering ─────────────────────────────────────────────────────────

class TestContentFiltering(unittest.TestCase):
    """Test that relevant baselines are correctly identified per concept."""

    def test_transparency_baselines_identified(self):
        from agents.concept_agent import CONCEPT_CATALOGUE, _extract_concept_sections
        keywords = CONCEPT_CATALOGUE['transparency']['keywords']
        eu_result = _extract_concept_sections(_eu_ai_act(), keywords)
        self.assertGreater(len(eu_result), 0)

    def test_nist_identified_for_transparency(self):
        from agents.concept_agent import CONCEPT_CATALOGUE, _extract_concept_sections
        keywords = CONCEPT_CATALOGUE['transparency']['keywords']
        result = _extract_concept_sections(_nist_rmf(), keywords)
        self.assertGreater(len(result), 0)

    def test_irrelevant_baseline_gives_empty(self):
        from agents.concept_agent import _extract_concept_sections
        bridge = {
            'id': 'bridge', 'jurisdiction': 'XX',
            'title': 'Bridge Standards',
            'overview': 'Annual inspection requirements for bridges.',
            'requirements': ['structural', 'load-bearing', 'corrosion resistance'],
        }
        result = _extract_concept_sections(bridge, ['transparency', 'explainab'])
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
