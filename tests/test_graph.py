# SPDX-License-Identifier: Elastic-2.0
# Copyright (c) 2026 Mitch Kwiatkowski
# ARIS � Automated Regulatory Intelligence System
# Licensed under the Elastic License 2.0. See LICENSE in the project root.
"""
ARIS — Knowledge Graph Agent Tests
"""
import json
import sys
import types
import unittest
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


def _eu_ai_act():
    return {
        'id': 'eu_ai_act', 'jurisdiction': 'EU',
        'title': 'EU Artificial Intelligence Act',
        'short_name': 'EU AIA', 'status': 'In Force',
        'overview': 'The EU AI Act establishes a risk-based framework for artificial intelligence.',
        'prohibited_practices': [
            {'title': 'Social scoring', 'description': 'AI systems for social scoring are prohibited.'},
        ],
        'obligations_by_actor': {
            'providers_high_risk': 'Conduct conformity assessments. Ensure transparency.',
        },
        'cross_references': [
            {'regulation': 'EU GDPR', 'relevance': 'Data protection requirements apply to AI systems.'},
            {'regulation': 'NIST AI RMF', 'relevance': 'EU AI Act aligns with NIST risk management concepts.'},
        ],
    }


def _nist_rmf():
    return {
        'id': 'us_nist_ai_rmf', 'jurisdiction': 'Federal',
        'title': 'NIST AI Risk Management Framework',
        'short_name': 'NIST AI RMF', 'status': 'Published',
        'overview': 'NIST AI RMF provides a framework for managing AI risk assessment '
                    'and risk-based approach to trustworthy AI systems.',
        'cross_references': [
            {'regulation': 'EO 14110', 'relevance': 'EO 14110 elevates NIST AI RMF to de facto federal standard.'},
        ],
    }


def _eu_gdpr():
    return {
        'id': 'eu_gdpr_ai', 'jurisdiction': 'EU',
        'title': 'EU GDPR — AI Provisions',
        'short_name': 'EU GDPR', 'status': 'In Force',
        'overview': 'GDPR Article 22 governs automated individual decisions.',
        'cross_references': [
            {'regulation': 'EU AI Act', 'relevance': 'The AI Act applies in addition to GDPR.'},
        ],
    }


def _colorado():
    return {
        'id': 'colorado_ai', 'jurisdiction': 'Federal',
        'title': 'Colorado AI Act',
        'short_name': 'Colorado AI', 'status': 'In Force',
        'overview': 'Colorado AI Act requires risk assessments for high-risk AI deployers.',
        'cross_references': [
            {'regulation': 'Illinois AIPA',
             'relevance': 'Both laws cover employment AI; Colorado was substantially modelled on Illinois approach.'},
            {'regulation': 'NYC Local Law 144',
             'relevance': 'NYC LL144 preceded Colorado; Colorado mirrors several bias audit requirements.'},
        ],
    }


def _brazil():
    return {
        'id': 'brazil_ai', 'jurisdiction': 'BR',
        'title': 'Brazil AI (LGPD + AI Bill)',
        'short_name': 'Brazil AI', 'status': 'Mixed',
        'overview': 'Brazil AI Bill is substantially modeled on EU AI Act with adaptations.',
        'cross_references': [
            {'regulation': 'EU AI Act',
             'relevance': 'Brazil AI Bill is substantially modeled on EU AI Act with additional worker rights.'},
        ],
    }


def _illinois():
    return {
        'id': 'illinois_aipa', 'jurisdiction': 'Federal',
        'title': 'Illinois AI Policy Act',
        'short_name': 'Illinois AIPA', 'status': 'In Force',
        'overview': 'Illinois AIPA requires employers to disclose AI tool use in hiring.',
        'cross_references': [],
    }


# ── Resolve baseline ID ───────────────────────────────────────────────────────

class TestResolveBaselineId(unittest.TestCase):

    def setUp(self):
        self.known_ids = {
            'eu_ai_act', 'eu_gdpr_ai', 'us_nist_ai_rmf',
            'us_eo_14110', 'colorado_ai', 'illinois_aipa', 'nyc_ll144',
        }

    def _resolve(self, name):
        from agents.graph_agent import _resolve_baseline_id
        return _resolve_baseline_id(name, self.known_ids)

    def test_exact_id_match(self):
        self.assertEqual(self._resolve('eu_ai_act'), 'eu_ai_act')

    def test_name_map_match(self):
        self.assertEqual(self._resolve('EU AI Act'),   'eu_ai_act')
        self.assertEqual(self._resolve('EU GDPR'),     'eu_gdpr_ai')
        self.assertEqual(self._resolve('NIST AI RMF'), 'us_nist_ai_rmf')
        self.assertEqual(self._resolve('EO 14110'),    'us_eo_14110')

    def test_case_insensitive(self):
        self.assertEqual(self._resolve('eu ai act'),   'eu_ai_act')
        self.assertEqual(self._resolve('NIST AI RMF'), 'us_nist_ai_rmf')

    def test_partial_match(self):
        self.assertEqual(self._resolve('Colorado'), 'colorado_ai')
        self.assertEqual(self._resolve('Illinois'), 'illinois_aipa')

    def test_unknown_returns_none(self):
        self.assertIsNone(self._resolve('Outer Space Treaty on Lunar Mining'))
        self.assertIsNone(self._resolve('bridge maintenance standards'))

    def test_empty_string_returns_none(self):
        self.assertIsNone(self._resolve(''))

    def test_self_reference_not_matched(self):
        # "eu_ai_act" is in known_ids so resolves to itself — callers filter same-id
        result = self._resolve('eu_ai_act')
        self.assertEqual(result, 'eu_ai_act')


# ── Cross-reference edges ─────────────────────────────────────────────────────

class TestCrossReferenceEdges(unittest.TestCase):

    def _detect(self, baselines):
        from agents.graph_agent import detect_cross_reference_edges
        return detect_cross_reference_edges(baselines)

    def test_detects_cross_refs(self):
        baselines = [_eu_ai_act(), _eu_gdpr(), _nist_rmf()]
        edges = self._detect(baselines)
        self.assertGreater(len(edges), 0)

    def test_all_edges_are_cross_ref_type(self):
        baselines = [_eu_ai_act(), _eu_gdpr(), _nist_rmf()]
        edges = self._detect(baselines)
        for e in edges:
            self.assertEqual(e['edge_type'], 'cross_ref')

    def test_source_and_target_populated(self):
        baselines = [_eu_ai_act(), _eu_gdpr()]
        edges = self._detect(baselines)
        for e in edges:
            self.assertIn('source_id', e)
            self.assertIn('target_id', e)
            self.assertNotEqual(e['source_id'], e['target_id'])

    def test_source_type_baseline(self):
        baselines = [_eu_ai_act(), _eu_gdpr()]
        edges = self._detect(baselines)
        for e in edges:
            self.assertEqual(e['source_type'], 'baseline')
            self.assertEqual(e['target_type'], 'baseline')

    def test_evidence_populated(self):
        baselines = [_eu_ai_act(), _eu_gdpr()]
        edges = self._detect(baselines)
        for e in edges:
            self.assertIsNotNone(e['evidence'])
            self.assertGreater(len(e['evidence']), 0)

    def test_no_self_links(self):
        baselines = [_eu_ai_act(), _eu_gdpr()]
        edges = self._detect(baselines)
        for e in edges:
            self.assertNotEqual(e['source_id'], e['target_id'])

    def test_unresolvable_ref_skipped(self):
        baseline = {
            'id': 'test_baseline', 'jurisdiction': 'XX',
            'cross_references': [
                {'regulation': 'Unknown Outer Space Treaty', 'relevance': 'test'},
            ]
        }
        edges = self._detect([baseline])
        self.assertEqual(len(edges), 0)

    def test_known_pair_detected(self):
        baselines = [_eu_ai_act(), _eu_gdpr(), _nist_rmf()]
        edges = self._detect(baselines)
        pairs = {(e['source_id'], e['target_id']) for e in edges}
        # eu_ai_act references eu_gdpr_ai
        self.assertIn(('eu_ai_act', 'eu_gdpr_ai'), pairs)


# ── Genealogical edges ────────────────────────────────────────────────────────

class TestGenealogicalEdges(unittest.TestCase):

    def _detect(self, baselines):
        from agents.graph_agent import detect_genealogical_edges
        return detect_genealogical_edges(baselines)

    def test_modelled_on_detected(self):
        baselines = [_brazil(), _eu_ai_act()]
        edges = self._detect(baselines)
        self.assertGreater(len(edges), 0)
        types = {e['edge_type'] for e in edges}
        self.assertIn('genealogical', types)

    def test_mirrors_detected(self):
        baselines = [_colorado(), _illinois(), _eu_ai_act()]
        edges = self._detect(baselines)
        types = {e['edge_type'] for e in edges}
        self.assertIn('genealogical', types)

    def test_all_edges_are_genealogical(self):
        baselines = [_brazil(), _eu_ai_act()]
        edges = self._detect(baselines)
        for e in edges:
            self.assertEqual(e['edge_type'], 'genealogical')

    def test_no_genealogical_without_pattern(self):
        # NIST cross-references EO 14110 but with neutral language
        baselines = [_nist_rmf(), {'id': 'us_eo_14110', 'jurisdiction': 'Federal',
                                    'title': 'EO 14110', 'cross_references': []}]
        edges = self._detect(baselines)
        self.assertEqual(len(edges), 0)

    def test_evidence_contains_pattern_text(self):
        baselines = [_brazil(), _eu_ai_act()]
        edges = self._detect(baselines)
        if edges:
            self.assertIsNotNone(edges[0]['evidence'])

    def test_strength_reasonable(self):
        baselines = [_brazil(), _eu_ai_act()]
        edges = self._detect(baselines)
        for e in edges:
            self.assertGreaterEqual(e['strength'], 0.5)
            self.assertLessEqual(e['strength'],    1.0)


# ── Semantic edges ────────────────────────────────────────────────────────────

class TestSemanticEdges(unittest.TestCase):

    def _detect(self, baselines):
        from agents.graph_agent import detect_semantic_edges
        return detect_semantic_edges(baselines)

    def test_produces_edges(self):
        baselines = [_eu_ai_act(), _nist_rmf(), _eu_gdpr(), _colorado()]
        edges = self._detect(baselines)
        self.assertGreater(len(edges), 0)

    def test_all_edges_are_semantic(self):
        baselines = [_eu_ai_act(), _nist_rmf(), _eu_gdpr()]
        edges = self._detect(baselines)
        for e in edges:
            self.assertEqual(e['edge_type'], 'semantic')

    def test_concept_field_populated(self):
        baselines = [_eu_ai_act(), _nist_rmf(), _colorado()]
        edges = self._detect(baselines)
        for e in edges:
            self.assertIsNotNone(e['concept'])
            self.assertGreater(len(e['concept']), 0)

    def test_no_self_links(self):
        baselines = [_eu_ai_act(), _nist_rmf(), _eu_gdpr()]
        edges = self._detect(baselines)
        for e in edges:
            self.assertNotEqual(e['source_id'], e['target_id'])

    def test_source_and_target_in_baselines(self):
        baselines = [_eu_ai_act(), _nist_rmf(), _colorado()]
        ids = {b['id'] for b in baselines}
        edges = self._detect(baselines)
        for e in edges:
            self.assertIn(e['source_id'], ids)
            self.assertIn(e['target_id'], ids)

    def test_known_shared_concept(self):
        """EU AI Act and NIST RMF both address risk_assessment."""
        baselines = [_eu_ai_act(), _nist_rmf()]
        edges = self._detect(baselines)
        concepts = {e['concept'] for e in edges}
        self.assertIn('risk_assessment', concepts)

    def test_strength_in_range(self):
        baselines = [_eu_ai_act(), _nist_rmf(), _colorado()]
        edges = self._detect(baselines)
        for e in edges:
            self.assertGreaterEqual(e['strength'], 0.0)
            self.assertLessEqual(e['strength'],    1.0)


# ── Document edges ────────────────────────────────────────────────────────────

class TestDocumentEdges(unittest.TestCase):

    def _detect(self, baselines, documents):
        from agents.graph_agent import detect_document_edges
        return detect_document_edges(baselines, documents)

    def _doc(self, **kwargs):
        base = {
            'id': 'DOC-001',
            'jurisdiction': 'EU',
            'title': 'EU AI Act Implementing Regulation on Conformity Assessment',
            'plain_english': 'This implementing regulation specifies conformity assessment procedures '
                             'for high-risk AI systems under the EU AI Act.',
            'urgency': 'High',
        }
        base.update(kwargs)
        return base

    def test_eu_doc_links_to_eu_ai_act(self):
        baselines = [_eu_ai_act(), _eu_gdpr()]
        documents = [self._doc()]
        edges = self._detect(baselines, documents)
        target_ids = [e['target_id'] for e in edges]
        self.assertIn('eu_ai_act', target_ids)

    def test_document_source_type(self):
        baselines = [_eu_ai_act()]
        documents = [self._doc()]
        edges = self._detect(baselines, documents)
        for e in edges:
            self.assertEqual(e['source_type'], 'document')

    def test_baseline_target_type(self):
        baselines = [_eu_ai_act()]
        documents = [self._doc()]
        edges = self._detect(baselines, documents)
        for e in edges:
            self.assertEqual(e['target_type'], 'baseline')

    def test_unrelated_doc_no_links(self):
        baselines = [_eu_ai_act()]
        documents = [{
            'id': 'DOC-002', 'jurisdiction': 'Federal',
            'title': 'Highway Bridge Inspection Annual Report',
            'plain_english': 'New standards for structural inspection of highway bridges.',
        }]
        edges = self._detect(baselines, documents)
        self.assertEqual(len(edges), 0)

    def test_strength_in_range(self):
        baselines = [_eu_ai_act()]
        documents = [self._doc()]
        edges = self._detect(baselines, documents)
        for e in edges:
            self.assertGreaterEqual(e['strength'], 0.0)
            self.assertLessEqual(e['strength'],    1.05)


# ── Graph agent ───────────────────────────────────────────────────────────────

class TestGraphAgent(unittest.TestCase):

    def _make_agent(self):
        from agents.graph_agent import GraphAgent
        return GraphAgent()

    def test_build_runs_without_crash(self):
        agent = self._make_agent()
        with patch('agents.graph_agent._load_baselines', return_value=[_eu_ai_act(), _nist_rmf(), _eu_gdpr()]):
            with patch('agents.graph_agent.detect_cross_reference_edges', return_value=[]):
                with patch('agents.graph_agent.detect_genealogical_edges', return_value=[]):
                    with patch('agents.graph_agent.detect_semantic_edges', return_value=[]):
                        with patch('utils.db.upsert_graph_edge', return_value=1):
                            with patch('utils.db.count_graph_edges', return_value=0):
                                counts = agent.build(include_documents=False)
        self.assertIsInstance(counts, dict)

    def test_build_returns_edge_type_counts(self):
        agent = self._make_agent()
        xref_edge = {
            'source_id': 'eu_ai_act', 'source_type': 'baseline',
            'target_id': 'eu_gdpr_ai', 'target_type': 'baseline',
            'edge_type': 'cross_ref', 'concept': None,
            'evidence': 'test', 'strength': 0.9,
        }
        with patch('agents.graph_agent._load_baselines', return_value=[_eu_ai_act(), _eu_gdpr()]):
            with patch('agents.graph_agent.detect_cross_reference_edges', return_value=[xref_edge]):
                with patch('agents.graph_agent.detect_genealogical_edges', return_value=[]):
                    with patch('agents.graph_agent.detect_semantic_edges', return_value=[]):
                        with patch('utils.db.upsert_graph_edge', return_value=1):
                            with patch('utils.db.count_graph_edges', return_value=0):
                                counts = agent.build(include_documents=False)
        self.assertEqual(counts.get('cross_ref', 0), 1)

    def test_get_graph_data_structure(self):
        agent = self._make_agent()
        mock_edges = [
            {'id': 1, 'source_id': 'eu_ai_act', 'source_type': 'baseline',
             'target_id': 'eu_gdpr_ai', 'target_type': 'baseline',
             'edge_type': 'cross_ref', 'concept': None,
             'evidence': 'Test', 'strength': 0.9},
        ]
        with patch('utils.db.get_graph_edges', return_value=mock_edges):
            with patch('agents.graph_agent._load_baselines', return_value=[_eu_ai_act(), _eu_gdpr()]):
                result = agent.get_graph_data()

        self.assertIn('nodes', result)
        self.assertIn('edges', result)
        self.assertIn('meta',  result)
        self.assertIsInstance(result['nodes'], list)
        self.assertIsInstance(result['edges'], list)

    def test_get_graph_data_nodes_have_required_fields(self):
        agent = self._make_agent()
        mock_edges = [
            {'id': 1, 'source_id': 'eu_ai_act', 'source_type': 'baseline',
             'target_id': 'eu_gdpr_ai', 'target_type': 'baseline',
             'edge_type': 'cross_ref', 'concept': None,
             'evidence': 'Test', 'strength': 0.9},
        ]
        with patch('utils.db.get_graph_edges', return_value=mock_edges):
            with patch('agents.graph_agent._load_baselines', return_value=[_eu_ai_act(), _eu_gdpr()]):
                result = agent.get_graph_data()

        for node in result['nodes']:
            self.assertIn('id',         node)
            self.assertIn('label',      node)
            self.assertIn('node_type',  node)
            self.assertIn('jurisdiction', node)

    def test_get_graph_data_edges_have_required_fields(self):
        agent = self._make_agent()
        mock_edges = [
            {'id': 1, 'source_id': 'eu_ai_act', 'source_type': 'baseline',
             'target_id': 'eu_gdpr_ai', 'target_type': 'baseline',
             'edge_type': 'cross_ref', 'concept': None,
             'evidence': 'Test', 'strength': 0.9},
        ]
        with patch('utils.db.get_graph_edges', return_value=mock_edges):
            with patch('agents.graph_agent._load_baselines', return_value=[_eu_ai_act(), _eu_gdpr()]):
                result = agent.get_graph_data()

        for edge in result['edges']:
            self.assertIn('source', edge)
            self.assertIn('target', edge)
            self.assertIn('type',   edge)

    def test_skip_build_if_already_built(self):
        agent = self._make_agent()
        with patch('utils.db.count_graph_edges', return_value=50):
            counts = agent.build(force=False)
        self.assertEqual(counts, {})

    def test_force_rebuild_clears_first(self):
        agent = self._make_agent()
        with patch('agents.graph_agent.GraphAgent._clear_auto_edges') as mock_clear:
            with patch('agents.graph_agent._load_baselines', return_value=[]):
                with patch('utils.db.count_graph_edges', return_value=50):
                    agent.build(force=True)
        mock_clear.assert_called_once()

    def test_conflict_detection_calls_llm(self):
        agent = self._make_agent()
        mock_response = json.dumps([
            {'description': 'Test conflict', 'concept': 'transparency', 'severity': 'high'}
        ])
        with patch('utils.llm.call_llm', return_value=mock_response):
            with patch('agents.graph_agent._load_baselines', return_value=[_eu_ai_act(), _nist_rmf()]):
                with patch('utils.db.upsert_graph_edge', return_value=1):
                    n = agent.build_conflicts([('eu_ai_act', 'us_nist_ai_rmf')])
        self.assertGreaterEqual(n, 1)


# ── Concept detection ─────────────────────────────────────────────────────────

class TestConceptDetection(unittest.TestCase):

    def test_risk_assessment_detected(self):
        from agents.graph_agent import _concept_present
        self.assertTrue(_concept_present(
            "Deployers must conduct a risk assessment prior to deployment.", 'risk_assessment'
        ))

    def test_human_oversight_detected(self):
        from agents.graph_agent import _concept_present
        self.assertTrue(_concept_present(
            "The system shall ensure meaningful human control over automated decisions.",
            'human_oversight'
        ))

    def test_bias_fairness_detected(self):
        from agents.graph_agent import _concept_present
        self.assertTrue(_concept_present(
            "Annual bias audits are required for all covered systems.",
            'bias_fairness'
        ))

    def test_unrelated_text_not_detected(self):
        from agents.graph_agent import _concept_present
        self.assertFalse(_concept_present(
            "The highway infrastructure funding allocation is determined annually.",
            'risk_assessment'
        ))

    def test_all_concepts_have_patterns(self):
        from agents.graph_agent import CONCEPTS
        for concept, patterns in CONCEPTS.items():
            self.assertGreater(len(patterns), 0, f"No patterns for concept {concept}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
