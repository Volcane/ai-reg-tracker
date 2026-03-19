"""
ARIS — Knowledge Graph Agent

Builds the regulatory knowledge graph by detecting typed relationships
between the 19 baseline regulations and the live document corpus.

Four relationship types are detected automatically (no LLM calls):

1. CROSS-REFERENCE  — explicit "see also" links declared in baseline JSON files
2. GENEALOGICAL     — one regulation was modelled on another, detected from
                      cross-reference text patterns ("modelled on", "mirrors",
                      "aligned with", "inspired by")
3. SEMANTIC         — two regulations share a major regulatory concept
                      (bias/fairness, human oversight, risk assessment, etc.)
                      detected by scanning for concept keywords
4. DOCUMENT LINK    — live documents that implement or amend a baseline,
                      detected by jurisdiction + keyword matching against
                      document titles and summaries

One optional LLM-based type (requires calling build_conflict_edges):

5. CONFLICT         — two regulations impose materially conflicting obligations,
                      detected via an LLM comparison of their obligation texts.
                      Only run on-demand because it burns API calls.

The graph is stored in the `knowledge_graph_edges` table. The Graph view
reads this table directly. Build is incremental — edges already present are
skipped via the unique (source, target, edge_type, concept) constraint.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.cache import get_logger

log = get_logger("aris.graph")

BASELINES_DIR = Path(__file__).parent.parent / "data" / "baselines"

# ── Concept taxonomy for semantic edges ──────────────────────────────────────

CONCEPTS: Dict[str, List[str]] = {
    "risk_assessment":     ["risk assessment", "impact assessment", "conformity assessment",
                            "risk evaluation", "risk-based approach"],
    "human_oversight":     ["human oversight", "human review", "human in the loop",
                            "meaningful human control", "human supervision"],
    "transparency":        ["transparency", "explainab", "interpretab", "disclosure",
                            "right to explanation", "right to contest"],
    "bias_fairness":       ["bias", "fairness", "discrimination", "disparate impact",
                            "disparate treatment", "equitable", "protected characteristic"],
    "data_governance":     ["training data", "data minimisation", "data quality",
                            "data governance", "dataset", "data provenance"],
    "foundation_models":   ["foundation model", "general purpose ai", "gpai",
                            "large language model", "llm", "generative ai"],
    "prohibited_practices":["prohibited", "forbidden", "social scoring", "subliminal",
                            "unacceptable risk", "banned practice"],
    "automated_decisions": ["automated decision", "automated decision-making",
                            "algorithmic decision", "automated profiling"],
    "penalties":           ["penalty", "fine", "sanction", "enforcement",
                            "administrative fine", "infringement"],
    "incident_reporting":  ["incident report", "notify", "notification", "serious incident",
                            "breach notification", "post-market monitoring"],
}

# Patterns that indicate a genealogical (modelled-on) relationship
GENEALOGICAL_PATTERNS = [
    r"modell?ed on",
    r"mirrors?\b",
    r"substantially aligned",
    r"inspired by",
    r"based on\b",
    r"adopts?\b.{0,30}framework",
    r"follows?\b.{0,20}approach",
    r"aligned with",
]

# Canonical baseline ID lookup — maps short names to full IDs
BASELINE_NAME_MAP: Dict[str, str] = {
    "eu ai act":                 "eu_ai_act",
    "eu aia":                    "eu_ai_act",
    "gdpr":                      "eu_gdpr_ai",
    "eu gdpr":                   "eu_gdpr_ai",
    "dsa":                       "eu_dsa_dma",
    "dma":                       "eu_dsa_dma",
    "eu dsa":                    "eu_dsa_dma",
    "eu ai liability":           "eu_ai_liability",
    "nist ai rmf":               "us_nist_ai_rmf",
    "nist rmf":                  "us_nist_ai_rmf",
    "eo 14110":                  "us_eo_14110",
    "executive order 14110":     "us_eo_14110",
    "ftc":                       "us_ftc_ai",
    "nyc local law 144":         "nyc_ll144",
    "ll144":                     "nyc_ll144",
    "illinois aipa":             "illinois_aipa",
    "illinois ai policy act":    "illinois_aipa",
    "colorado ai act":           "colorado_ai",
    "california ai":             "california_ai",
    "uk ai":                     "uk_ai_framework",
    "uk ai framework":           "uk_ai_framework",
    "canada aida":               "canada_aida",
    "aida":                      "canada_aida",
    "singapore":                 "singapore_ai",
    "australia":                 "australia_ai",
    "japan":                     "japan_ai",
    "brazil":                    "brazil_ai",
    "oecd":                      "oecd_ai_principles",
    "oecd ai principles":        "oecd_ai_principles",
    "g7":                        "oecd_ai_principles",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_baselines() -> List[Dict]:
    baselines = []
    if not BASELINES_DIR.exists():
        log.warning("Baselines dir not found: %s", BASELINES_DIR)
        return baselines
    for path in sorted(BASELINES_DIR.glob("*.json")):
        if path.name == "index.json":
            continue
        try:
            d = json.loads(path.read_text())
            baselines.append(d)
        except Exception as e:
            log.warning("Could not load baseline %s: %s", path.name, e)
    return baselines


def _resolve_baseline_id(name: str, known_ids: set) -> Optional[str]:
    """Map a free-text regulation name to a known baseline ID."""
    lower = name.lower().strip()
    # Direct ID match
    if lower in known_ids:
        return lower
    # Name map lookup
    for key, bid in BASELINE_NAME_MAP.items():
        if key in lower and bid in known_ids:
            return bid
    # Partial match against known IDs (only for non-trivial inputs)
    if len(lower) >= 3:
        for bid in known_ids:
            if bid.replace("_", " ") in lower or lower in bid.replace("_", " "):
                return bid
    return None


def _concept_present(text: str, concept: str) -> bool:
    patterns = CONCEPTS.get(concept, [])
    lower    = text.lower()
    return any(p in lower for p in patterns)


# ── Edge detection ────────────────────────────────────────────────────────────

def detect_cross_reference_edges(baselines: List[Dict]) -> List[Dict]:
    """
    Extract explicit cross-reference edges from baseline JSON files.
    Each baseline has a cross_references list: [{regulation, relevance}].
    """
    known_ids = {b["id"] for b in baselines}
    edges: List[Dict] = []

    for baseline in baselines:
        bid   = baseline["id"]
        xrefs = baseline.get("cross_references", [])
        for xref in xrefs:
            reg_name   = xref.get("regulation", "")
            relevance  = xref.get("relevance", "")
            target_id  = _resolve_baseline_id(reg_name, known_ids)
            if not target_id or target_id == bid:
                continue

            edges.append({
                "source_id":   bid,
                "source_type": "baseline",
                "target_id":   target_id,
                "target_type": "baseline",
                "edge_type":   "cross_ref",
                "concept":     None,
                "evidence":    relevance[:400] if relevance else f"Cross-reference to {reg_name}",
                "strength":    0.9,
            })

    return edges


def detect_genealogical_edges(baselines: List[Dict]) -> List[Dict]:
    """
    Detect genealogical relationships: A was modelled on / inspired by B.
    Scans cross-reference relevance text for pattern words.
    """
    known_ids = {b["id"] for b in baselines}
    edges: List[Dict] = []
    patterns  = [re.compile(p, re.IGNORECASE) for p in GENEALOGICAL_PATTERNS]

    for baseline in baselines:
        bid   = baseline["id"]
        xrefs = baseline.get("cross_references", [])
        for xref in xrefs:
            relevance = xref.get("relevance", "")
            if not any(p.search(relevance) for p in patterns):
                continue
            target_id = _resolve_baseline_id(xref.get("regulation", ""), known_ids)
            if not target_id or target_id == bid:
                continue
            edges.append({
                "source_id":   bid,
                "source_type": "baseline",
                "target_id":   target_id,
                "target_type": "baseline",
                "edge_type":   "genealogical",
                "concept":     None,
                "evidence":    relevance[:400],
                "strength":    0.85,
            })

    return edges


def detect_semantic_edges(baselines: List[Dict]) -> List[Dict]:
    """
    Connect baselines that share regulatory concepts.
    Only creates edges where both baselines genuinely address the concept.
    Avoids trivially connecting everything via the most common terms.
    """
    edges: List[Dict] = []

    # Pre-compute which baselines cover which concepts
    coverage: Dict[str, List[str]] = {c: [] for c in CONCEPTS}
    for b in baselines:
        text = json.dumps(b).lower()
        for concept in CONCEPTS:
            if _concept_present(text, concept):
                coverage[concept].append(b["id"])

    # Create edges between baselines sharing a concept
    # Skip very common concepts (>12 baselines) — they don't add signal
    for concept, bid_list in coverage.items():
        if len(bid_list) < 2 or len(bid_list) > 12:
            continue

        for i, src in enumerate(bid_list):
            for tgt in bid_list[i+1:]:
                # Avoid duplicating genealogical/cross-ref edges
                edges.append({
                    "source_id":   src,
                    "source_type": "baseline",
                    "target_id":   tgt,
                    "target_type": "baseline",
                    "edge_type":   "semantic",
                    "concept":     concept,
                    "evidence":    f"Both regulations address {concept.replace('_', ' ')}",
                    "strength":    0.6,
                })

    return edges


def detect_document_edges(baselines: List[Dict],
                           documents: List[Dict]) -> List[Dict]:
    """
    Link live documents to the baselines they implement or relate to.
    Uses jurisdiction matching + keyword overlap between document title/summary
    and baseline short_name/title.
    """
    edges: List[Dict] = []

    # Build a jurisdiction → baseline mapping
    jur_baselines: Dict[str, List[Dict]] = {}
    for b in baselines:
        jur = b.get("jurisdiction", "")
        if jur not in jur_baselines:
            jur_baselines[jur] = []
        jur_baselines[jur].append(b)

    for doc in documents:
        doc_id  = doc.get("id", "")
        jur     = doc.get("jurisdiction", "")
        title   = (doc.get("title", "") or "").lower()
        summary = (doc.get("plain_english", "") or "").lower()
        text    = f"{title} {summary}"

        # Find candidate baselines for this jurisdiction
        candidates = jur_baselines.get(jur, []) + jur_baselines.get("", [])

        for b in candidates:
            bid        = b["id"]
            bshort     = (b.get("short_name", "") or "").lower()
            btitle     = (b.get("title", "") or "").lower()
            boverview  = (b.get("overview", "") or "").lower()
            # Also try slug words (e.g. "eu_ai_act" → ["eu", "ai", "act"])
            bslug_words = set(w for w in bid.split("_") if len(w) >= 2)

            # Strong signal: baseline short name or significant title words in document
            short_match = bshort and bshort in text
            # Title word match: any word ≥3 chars from the title
            title_words = [w for w in btitle.split() if len(w) >= 3]
            title_match = sum(1 for w in title_words if w in text) >= 2
            # Slug match: majority of slug components appear in doc text
            slug_match  = len(bslug_words) >= 2 and \
                          sum(1 for w in bslug_words if w in text) >= len(bslug_words) - 1

            strong_match = short_match or title_match or slug_match

            # Concept overlap: both doc and baseline overview share regulatory concepts
            concept_overlap = sum(
                1 for c in CONCEPTS
                if _concept_present(text, c) and (
                    _concept_present(boverview, c) or
                    _concept_present(json.dumps(b).lower(), c)
                )
            )

            if strong_match and concept_overlap >= 1:
                edge_type = "implements" if jur == b.get("jurisdiction") else "cross_ref"
                edges.append({
                    "source_id":   doc_id,
                    "source_type": "document",
                    "target_id":   bid,
                    "target_type": "baseline",
                    "edge_type":   edge_type,
                    "concept":     None,
                    "evidence":    (f"Document '{doc.get('title','')[:60]}' "
                                    f"references {b.get('short_name',bid)}"),
                    "strength":    0.7 + (0.05 * min(concept_overlap, 4)),
                })

    return edges


# ── LLM-based conflict detection (optional, on-demand) ───────────────────────

def detect_conflict_edges(baseline_a: Dict, baseline_b: Dict) -> List[Dict]:
    """
    Use the LLM to identify genuinely conflicting obligations between two baselines.
    Only call this for specific pairs — it costs one LLM call per pair.
    """
    from utils.llm import call_llm, LLMError

    oblig_a = _extract_obligations_text(baseline_a)
    oblig_b = _extract_obligations_text(baseline_b)

    if not oblig_a or not oblig_b:
        return []

    prompt = f"""Compare these two AI regulation frameworks and identify genuine conflicts.
A conflict means: complying fully with one makes it harder or impossible to comply with the other.
Do not list differences — only true conflicts.

REGULATION A: {baseline_a.get('title')} ({baseline_a.get('jurisdiction')})
{oblig_a[:2000]}

REGULATION B: {baseline_b.get('title')} ({baseline_b.get('jurisdiction')})
{oblig_b[:2000]}

Respond with a JSON array (empty if no conflicts):
[
  {{
    "description": "Brief description of the conflict",
    "concept": "The regulatory concept at issue",
    "severity": "high | medium | low"
  }}
]
Only respond with the JSON array, nothing else."""

    try:
        raw  = call_llm(prompt=prompt, max_tokens=800)
        raw  = re.sub(r'```json|```', '', raw).strip()
        conflicts = json.loads(raw)
        if not isinstance(conflicts, list):
            return []
    except (LLMError, json.JSONDecodeError, Exception) as e:
        log.warning("Conflict detection failed for %s / %s: %s",
                    baseline_a["id"], baseline_b["id"], e)
        return []

    edges = []
    for c in conflicts:
        if not isinstance(c, dict) or not c.get("description"):
            continue
        edges.append({
            "source_id":   baseline_a["id"],
            "source_type": "baseline",
            "target_id":   baseline_b["id"],
            "target_type": "baseline",
            "edge_type":   "conflict",
            "concept":     c.get("concept"),
            "evidence":    c.get("description", "")[:400],
            "strength":    {"high": 0.95, "medium": 0.75, "low": 0.55}.get(
                               c.get("severity", "medium"), 0.75),
        })
    return edges


def _extract_obligations_text(baseline: Dict, max_chars: int = 3000) -> str:
    parts = [baseline.get("overview", "")]
    for key in ["obligations_by_actor", "key_obligations", "developer_obligations",
                "deployer_obligations", "proposed_obligations", "prohibited_practices",
                "prohibited_conduct"]:
        val = baseline.get(key)
        if val:
            parts.append(json.dumps(val))
    return "\n".join(parts)[:max_chars]


# ── Graph Agent ───────────────────────────────────────────────────────────────

class GraphAgent:

    def build(self, include_documents: bool = True,
               force: bool = False) -> Dict[str, int]:
        """
        Build (or refresh) the full knowledge graph.

        Detects cross-reference, genealogical, semantic, and document edges.
        Skips conflict edges (require explicit LLM calls via build_conflicts).

        Returns counts per edge type.
        """
        from utils.db import upsert_graph_edge, count_graph_edges

        if not force and count_graph_edges() > 0:
            log.info("Graph already built — use force=True to rebuild")
            return {}

        if force:
            self._clear_auto_edges()

        baselines = _load_baselines()
        if not baselines:
            log.warning("No baselines found — graph will be empty")
            return {}

        counts: Dict[str, int] = {
            "cross_ref":    0,
            "genealogical": 0,
            "semantic":     0,
            "document":     0,
        }

        # Baseline → baseline edges
        for edge in detect_cross_reference_edges(baselines):
            upsert_graph_edge(edge)
            counts["cross_ref"] += 1

        for edge in detect_genealogical_edges(baselines):
            upsert_graph_edge(edge)
            counts["genealogical"] += 1

        for edge in detect_semantic_edges(baselines):
            upsert_graph_edge(edge)
            counts["semantic"] += 1

        # Document → baseline edges
        if include_documents:
            try:
                from utils.db import get_recent_summaries
                docs = get_recent_summaries(days=3650)
                for edge in detect_document_edges(baselines, docs):
                    upsert_graph_edge(edge)
                    counts["document"] += 1
            except Exception as e:
                log.warning("Document edge detection failed: %s", e)

        total = sum(counts.values())
        log.info("Knowledge graph built: %d total edges %s", total, counts)
        return counts

    def build_conflicts(self, jurisdiction_pairs: Optional[List[Tuple[str, str]]] = None
                        ) -> int:
        """
        Detect conflict edges using the LLM.
        If jurisdiction_pairs is None, runs on a curated set of important pairs.
        Returns number of conflict edges found.
        """
        from utils.db import upsert_graph_edge

        baselines  = _load_baselines()
        b_map      = {b["id"]: b for b in baselines}

        default_pairs = [
            ("eu_ai_act",      "us_nist_ai_rmf"),
            ("eu_ai_act",      "us_eo_14110"),
            ("eu_ai_act",      "uk_ai_framework"),
            ("eu_ai_act",      "colorado_ai"),
            ("eu_gdpr_ai",     "us_sector_ai"),
            ("nyc_ll144",      "illinois_aipa"),
            ("colorado_ai",    "illinois_aipa"),
        ]
        pairs = jurisdiction_pairs or default_pairs

        found = 0
        for src_id, tgt_id in pairs:
            if src_id not in b_map or tgt_id not in b_map:
                continue
            log.info("Detecting conflicts: %s ↔ %s", src_id, tgt_id)
            edges = detect_conflict_edges(b_map[src_id], b_map[tgt_id])
            for e in edges:
                upsert_graph_edge(e)
                found += 1

        log.info("Conflict detection complete: %d conflicts found", found)
        return found

    def get_graph_data(self,
                        jurisdiction:  Optional[str]       = None,
                        node_types:    Optional[List[str]] = None,
                        edge_types:    Optional[List[str]] = None,
                        include_isolated: bool             = False,
                        max_nodes:     int                 = 200) -> Dict:
        """
        Return a nodes + edges dict ready for the graph renderer.

        node_types: ["baseline", "document"] — filter node types
        edge_types: filter edge types to render
        include_isolated: include nodes with no edges (False = cleaner graph)
        """
        from utils.db import get_graph_edges, get_session
        from utils.db import Document, Summary, KnowledgeGraphEdge as _KGE

        baselines  = {b["id"]: b for b in _load_baselines()}
        all_edges  = get_graph_edges(edge_types=edge_types)

        # Filter by jurisdiction
        if jurisdiction:
            all_edges = [
                e for e in all_edges
                if self._edge_in_jurisdiction(e, baselines, jurisdiction)
            ]

        # Collect referenced node IDs
        node_ids: Dict[str, str] = {}   # id → type
        for e in all_edges:
            node_ids[e["source_id"]] = e["source_type"]
            node_ids[e["target_id"]] = e["target_type"]

        # Build nodes
        nodes = []
        for nid, ntype in node_ids.items():
            if node_types and ntype not in node_types:
                continue
            if ntype == "baseline":
                b = baselines.get(nid, {})
                nodes.append({
                    "id":           nid,
                    "node_type":    "baseline",
                    "label":        b.get("short_name") or b.get("title", nid)[:30],
                    "title":        b.get("title", nid),
                    "jurisdiction": b.get("jurisdiction", ""),
                    "status":       b.get("status", ""),
                    "urgency":      None,
                    "overview":     (b.get("overview", "") or "")[:300],
                })
            else:
                # Document node — fetch from DB
                nodes.append(self._doc_node(nid))

        # Trim to max_nodes (prefer baselines)
        if len(nodes) > max_nodes:
            bl_nodes  = [n for n in nodes if n["node_type"] == "baseline"]
            doc_nodes = [n for n in nodes if n["node_type"] == "document"]
            nodes = bl_nodes + doc_nodes[:max_nodes - len(bl_nodes)]

        valid_ids   = {n["id"] for n in nodes}
        edges_out   = [
            {
                "id":        e["id"],
                "source":    e["source_id"],
                "target":    e["target_id"],
                "type":      e["edge_type"],
                "concept":   e["concept"],
                "evidence":  (e["evidence"] or "")[:200],
                "strength":  e["strength"],
            }
            for e in all_edges
            if e["source_id"] in valid_ids and e["target_id"] in valid_ids
        ]

        return {
            "nodes": nodes,
            "edges": edges_out,
            "meta": {
                "total_nodes": len(nodes),
                "total_edges": len(edges_out),
                "edge_type_counts": self._count_by_type(edges_out),
            },
        }

    @staticmethod
    def _doc_node(doc_id: str) -> Dict:
        try:
            from utils.db import get_session, Document, Summary
            with get_session() as s:
                doc  = s.get(Document, doc_id)
                summ = s.get(Summary, doc_id)
                if not doc:
                    return {"id": doc_id, "node_type": "document", "label": doc_id[:30],
                            "title": doc_id, "jurisdiction": "", "status": "", "urgency": None}
                return {
                    "id":           doc.id,
                    "node_type":    "document",
                    "label":        (doc.title or "")[:40],
                    "title":        doc.title or "",
                    "jurisdiction": doc.jurisdiction or "",
                    "status":       doc.status or "",
                    "urgency":      summ.urgency if summ else None,
                    "agency":       doc.agency or "",
                    "url":          doc.url or "",
                    "overview":     summ.plain_english[:300] if summ and summ.plain_english else "",
                }
        except Exception:
            return {"id": doc_id, "node_type": "document", "label": doc_id[:30],
                    "title": doc_id, "jurisdiction": "", "status": "", "urgency": None}

    @staticmethod
    def _edge_in_jurisdiction(edge: Dict, baselines: Dict, jur: str) -> bool:
        for nid in (edge["source_id"], edge["target_id"]):
            b = baselines.get(nid)
            if b and b.get("jurisdiction", "").upper() == jur.upper():
                return True
        return False

    @staticmethod
    def _count_by_type(edges: List[Dict]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for e in edges:
            t = e.get("type", "unknown")
            counts[t] = counts.get(t, 0) + 1
        return counts

    @staticmethod
    def _clear_auto_edges() -> None:
        from utils.db import get_session, KnowledgeGraphEdge
        with get_session() as s:
            s.query(KnowledgeGraphEdge).filter(
                KnowledgeGraphEdge.detected_by == "system"
            ).delete()
            s.commit()
