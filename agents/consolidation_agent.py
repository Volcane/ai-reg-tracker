"""
ARIS — Consolidation Agent

Produces a single de-duplicated obligation register from all sources:
  - Static baseline JSON files (19 regulations)
  - Summarised documents in the database

The register answers: "For my jurisdictions, what is the complete set of
distinct things I must do — deduplicated across all overlapping regulations?"

When three regulations all require human oversight of AI decisions, the
register produces ONE item — "Implement human oversight for AI decisions" —
with three sources, the union of their deadlines, and the strictest scope.

TWO MODES:

1. FAST MODE (no API call, runs at startup)
   Pure structural consolidation from baseline JSON. Groups obligations by
   category and uses fuzzy title matching to merge near-duplicates. Covers
   ~80% of consolidation quality with zero cost. Always available.

2. FULL MODE (one Claude call per run)
   Assembles all obligations (baseline + database documents), sends them
   in a single structured prompt, and asks Claude to deduplicate, merge,
   and categorise. One call covers 50-150 obligations typically. Result
   is cached for 24 hours. Triggered explicitly by user or after gap analysis.

The register is stored in obligation_register table. Each entry has:
  - A clear obligation title and full description
  - All source regulations with specific provision references
  - The earliest deadline across all sources
  - The strictest scope (most demanding version)
  - Universality (how many jurisdictions impose it)
  - Category (Documentation | Assessment | Oversight | Transparency | etc.)

Integration with gap analysis:
  - GapAnalysisAgent._run_scope_mapping() now pulls the register for the
    relevant jurisdictions and includes it in the scope prompt — giving
    Claude a structured obligation list rather than deriving it fresh
  - The register tab in GapAnalysis.jsx shows the consolidated obligations
    for the current profile's jurisdictions
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

import anthropic  # kept for backward compat; actual calls go through utils.llm

from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL
from utils.llm import call_llm, is_configured, LLMError
from utils.cache import get_logger

log = get_logger("aris.consolidation")

# Module-level re-exports so tests can patch them without namespace issues
def get_register_cache(cache_key: str, max_age_hours: int = 24):
    from utils.db import get_register_cache as _fn
    return _fn(cache_key, max_age_hours)

def save_register_cache(cache_key: str, register):
    from utils.db import save_register_cache as _fn
    return _fn(cache_key, register)

def delete_register_cache(jurisdictions=None):
    from utils.db import delete_register_cache as _fn
    return _fn(jurisdictions)


# Re-export for patching in tests
def BaselineAgent():
    from agents.baseline_agent import BaselineAgent as _BA
    return _BA()

# ── Categories ────────────────────────────────────────────────────────────────

CATEGORIES = [
    "Documentation",     # technical docs, model cards, records
    "Assessment",        # risk assessments, DPIAs, conformity assessments, bias audits
    "Oversight",         # human review, monitoring, oversight mechanisms
    "Transparency",      # disclosures to users, public posting, explainability
    "Governance",        # policies, governance programs, accountability structures
    "Reporting",         # incident reporting, regulatory notification, audit reporting
    "Technical",         # logging, security, robustness, testing measures
    "Prohibition",       # things that are forbidden
    "Rights",            # individual rights: access, correction, contestability
    "Training Data",     # data provenance, consent, purpose limitation for AI training
]

# Keyword patterns ordered by specificity (checked in order; first match wins)
_CATEGORY_PATTERNS_ORDERED = [
    ("Prohibition",   r"prohibit|forbid|must\s+not|shall\s+not|cannot|banned|restricted"),
    ("Training Data", r"training[_ ]data|data[_ ]provenance|synthetic[_ ]data|data[_ ]used.*train|train.*data"),
    ("Rights",        r"right\s+to|opt.out|request.*review|contest|correct.*data|erasure|data.*access"),
    ("Transparency",  r"disclose|notify.*individual|inform.*person|publish.*result|public.*post|notice\s+to"),
    ("Assessment",    r"conformity\s+assess|bias\s+audit|dpia|impact\s+assess|risk\s+assess|evaluat.*ai"),
    ("Oversight",     r"human\s+oversight|human\s+review|oversight\s+mechanism|override.*decision"),
    ("Reporting",     r"report.*authority|incident.*report|register.*system|submit.*regulat|notify.*minister"),
    ("Technical",     r"security|robust|reliable|logging|watermark|safeguard|encrypt"),
    ("Documentation", r"document|record|technical.*doc|model.*card|log|retain|maintain.*record"),
    ("Governance",    r"governance|policy|procedure|program|accountability|responsible.*person"),
]

# Minimum similarity ratio for two obligation titles to be considered duplicates
_MERGE_THRESHOLD = 0.72

# Max obligations to send Claude in full-mode (context budget)
_MAX_OBLIGATIONS_FOR_CLAUDE = 120

# Cache duration for full-mode results
_CACHE_HOURS = 24

# ── Consolidation Agent ───────────────────────────────────────────────────────

class ConsolidationAgent:
    """
    Builds and maintains the de-duplicated obligation register.
    """

    def __init__(self):
        pass   # no client needed — calls go through utils.llm

    def _ensure_configured(self):
        if not is_configured():
            from utils.llm import _provider
            raise ValueError(
                f"LLM provider '{_provider()}' is not configured. "
                "Set the appropriate API key in config/keys.env."
            )

    # ── Public API ────────────────────────────────────────────────────────────

    def consolidate_fast(self,
                          jurisdictions: List[str],
                          force: bool = False) -> List[Dict[str, Any]]:
        """
        Fast structural consolidation from baselines only — no API call.
        Results are cached. Returns the consolidated obligation list.
        """
        cache_key = _register_key(jurisdictions, mode="fast")
        if not force:
            cached = get_register_cache(cache_key, max_age_hours=_CACHE_HOURS * 7)
            if cached:
                log.debug("Returning cached fast register for %s", jurisdictions)
                return cached

        log.info("Building fast register for %s", jurisdictions)
        raw = self._collect_baseline_obligations(jurisdictions)
        consolidated = self._structural_consolidate(raw)

        save_register_cache(cache_key, consolidated)
        log.info("Fast register: %d raw → %d consolidated for %s",
                 len(raw), len(consolidated), jurisdictions)
        return consolidated

    def consolidate_full(self,
                          jurisdictions: List[str],
                          days: int = 365,
                          force: bool = False) -> List[Dict[str, Any]]:
        """
        Full consolidation with Claude — one API call, semantically deduplicated.
        Combines baselines + database documents. Result cached for 24 hours.
        """
        cache_key = _register_key(jurisdictions, mode="full")
        if not force:
            cached = get_register_cache(cache_key, max_age_hours=_CACHE_HOURS)
            if cached:
                log.debug("Returning cached full register for %s", jurisdictions)
                return cached

        log.info("Building full register for %s (with Claude)", jurisdictions)

        # Collect from all sources
        baseline_obls = self._collect_baseline_obligations(jurisdictions)
        document_obls = self._collect_document_obligations(jurisdictions, days)
        all_obls      = baseline_obls + document_obls

        if not all_obls:
            return []

        # Structural pass first to reduce volume for Claude
        pre_consolidated = self._structural_consolidate(all_obls)

        if len(pre_consolidated) <= 10:
            # Too few to need Claude — return structural result
            save_register_cache(cache_key, pre_consolidated)
            return pre_consolidated

        # Send to Claude for semantic deduplication and enrichment
        result = self._claude_consolidate(pre_consolidated, jurisdictions)
        if not result:
            log.warning("Claude consolidation failed — falling back to structural result")
            result = pre_consolidated

        save_register_cache(cache_key, result)
        log.info("Full register: %d obligations for %s", len(result), jurisdictions)
        return result

    def get_register(self,
                     jurisdictions: List[str],
                     mode: str = "fast") -> List[Dict[str, Any]]:
        """
        Get the register for a set of jurisdictions.
        mode: 'fast' (no API, structural only) | 'full' (one Claude call)
        """
        if mode == "full":
            return self.consolidate_full(jurisdictions)
        return self.consolidate_fast(jurisdictions)

    def invalidate(self, jurisdictions: Optional[List[str]] = None) -> None:
        """Invalidate cached register (e.g. after new baselines loaded)."""
        delete_register_cache(jurisdictions)

    # ── Obligation collection ─────────────────────────────────────────────────

    def _collect_baseline_obligations(self,
                                        jurisdictions: List[str]) -> List[Dict]:
        """Extract all obligations from baseline JSON files for given jurisdictions."""
        try:
            agent    = BaselineAgent()
            baselines = agent.get_for_jurisdictions(jurisdictions)
        except Exception as e:
            log.warning("Could not load baselines: %s", e)
            return []

        obligations = []
        for b in baselines:
            bid   = b["id"]
            bname = b.get("short_name", b["title"])
            bjur  = b["jurisdiction"]

            # Structured obligations by actor (EU AI Act style)
            for actor, obls in (b.get("obligations_by_actor") or {}).items():
                for obl in obls:
                    obligations.append(_normalise_obligation(
                        obl, bid, bname, bjur,
                        source_type="baseline",
                        actor=actor,
                    ))

            # Flat obligation lists (state laws, sector rules style)
            for key in ("key_obligations", "proposed_obligations",
                        "developer_obligations", "deployer_obligations",
                        "ico_ai_obligations"):
                for obl in (b.get(key) or []):
                    obligations.append(_normalise_obligation(
                        obl, bid, bname, bjur, source_type="baseline",
                    ))

            # Sector sub-frameworks (us_sector_ai style)
            for sector in (b.get("sector_frameworks") or []):
                for rule in (sector.get("key_rules") or []):
                    for obl_text in (rule.get("obligations") or []):
                        obligations.append({
                            "id":               f"{bid}-{rule.get('id','')}",
                            "title":            rule.get("title", obl_text[:60]),
                            "description":      obl_text,
                            "deadline":         None,
                            "baseline_id":      bid,
                            "regulation_title": bname,
                            "jurisdiction":     bjur,
                            "source_type":      "baseline",
                            "actor":            sector.get("sector", ""),
                        })

            # Prohibited practices (stored separately, category = Prohibition)
            for p in (b.get("prohibited_practices") or []):
                obligations.append({
                    "id":               p.get("id", f"{bid}-prohibited"),
                    "title":            p.get("title", ""),
                    "description":      p.get("description", ""),
                    "deadline":         p.get("in_force_from"),
                    "baseline_id":      bid,
                    "regulation_title": bname,
                    "jurisdiction":     bjur,
                    "source_type":      "baseline",
                    "category":         "Prohibition",
                    "actor":            p.get("applies_to", "All"),
                })

        return [o for o in obligations if o.get("title") or o.get("description")]

    def _collect_document_obligations(self,
                                        jurisdictions: List[str],
                                        days: int) -> List[Dict]:
        """Extract obligations from summarised documents in the database."""
        try:
            from utils.db import get_recent_summaries
        except Exception:
            return []

        obligations = []
        for jur in jurisdictions:
            for doc in get_recent_summaries(days=days, jurisdiction=jur):
                reqs     = doc.get("requirements") or []
                doc_id   = doc.get("id", "")
                doc_name = doc.get("title", "")
                deadline = doc.get("deadline")

                for i, req in enumerate(reqs):
                    if not req or not str(req).strip():
                        continue
                    obligations.append({
                        "id":               f"{doc_id}-req-{i}",
                        "title":            str(req)[:120],
                        "description":      str(req),
                        "deadline":         deadline,
                        "baseline_id":      None,
                        "regulation_title": doc_name,
                        "jurisdiction":     jur,
                        "source_type":      "document",
                        "document_id":      doc_id,
                        "urgency":          doc.get("urgency"),
                    })

        return obligations

    # ── Structural consolidation (no API) ─────────────────────────────────────

    def _structural_consolidate(self,
                                  obligations: List[Dict]) -> List[Dict[str, Any]]:
        """
        Group and deduplicate obligations using fuzzy title matching.
        Returns consolidated obligation entries, each with a sources list.
        """
        if not obligations:
            return []

        # Assign categories where missing
        for obl in obligations:
            if not obl.get("category"):
                obl["category"] = _infer_category(
                    obl.get("title", "") + " " + obl.get("description", "")
                )

        # Group by category then cluster by title similarity
        by_category: Dict[str, List] = {}
        for obl in obligations:
            cat = obl.get("category", "Documentation")
            by_category.setdefault(cat, []).append(obl)

        consolidated = []
        for category, obls in by_category.items():
            clusters = _cluster_by_similarity(obls, threshold=_MERGE_THRESHOLD)
            for cluster in clusters:
                merged = _merge_cluster(cluster, category)
                consolidated.append(merged)

        # Sort: Prohibition first, then by number of sources (most universal first)
        consolidated.sort(key=lambda x: (
            0 if x["category"] == "Prohibition" else 1,
            -len(x.get("sources", [])),
        ))

        return consolidated

    # ── Claude consolidation (one API call) ───────────────────────────────────

    def _claude_consolidate(self,
                              obligations: List[Dict],
                              jurisdictions: List[str]) -> Optional[List[Dict]]:
        """Send pre-consolidated obligations to Claude for semantic deduplication."""
        # Cap to avoid context overflow
        sample = obligations[:_MAX_OBLIGATIONS_FOR_CLAUDE]

        obl_block = "\n".join(
            f"[{i+1}] ({o['category']}) {o['title']} | "
            f"Jurs: {','.join(o.get('jurisdictions',[]))} | "
            f"Sources: {len(o.get('sources',[]))} | "
            f"Deadline: {o.get('earliest_deadline','none')}"
            for i, o in enumerate(sample)
        )

        prompt = f"""You are building a consolidated compliance obligation register for
jurisdictions: {', '.join(jurisdictions)}.

Below are {len(sample)} pre-grouped obligations. Your job is to:
1. Identify any remaining duplicates (same obligation described differently) and merge them
2. Ensure each entry has a clear, action-oriented title (starts with a verb)
3. Identify the strictest version where obligations overlap
4. Return the final consolidated list as JSON

Obligations:
{obl_block}

Return a JSON array where each item has:
{{
  "title": "<verb-first clear obligation title>",
  "category": "<one of: {', '.join(CATEGORIES)}>",
  "description": "<1-2 sentences describing what specifically must be done>",
  "merged_indices": [<list of input indices that were merged into this item>],
  "strictest_scope": "<the most demanding version of this requirement>",
  "notes": "<any important nuance about how requirements differ across sources, or null>"
}}

Return only the JSON array, no other text."""

        try:
            self._ensure_configured()
            raw  = call_llm(prompt=prompt, max_tokens=3000)
            data = _safe_parse_json_array(raw)
            if not data:
                return None

            # Re-attach source metadata from the pre-consolidated list
            result = []
            used_indices: Set[int] = set()
            for item in data:
                merged_idx = item.get("merged_indices") or []
                sources    = []
                jurisds    = set()
                deadlines  = []
                for idx in merged_idx:
                    if 1 <= idx <= len(sample):
                        src = sample[idx - 1]
                        sources.extend(src.get("sources", []))
                        jurisds.update(src.get("jurisdictions", []))
                        if src.get("earliest_deadline"):
                            deadlines.append(src["earliest_deadline"])
                        used_indices.add(idx)

                earliest = min(deadlines) if deadlines else None
                n_jurs   = len(jurisds)
                universality = (
                    "Universal"   if n_jurs >= max(3, len(jurisdictions) * 0.8)
                    else "Majority"  if n_jurs >= 2
                    else "Single jurisdiction"
                )

                result.append({
                    "title":            item.get("title", ""),
                    "category":         item.get("category", "Documentation"),
                    "description":      item.get("description", ""),
                    "strictest_scope":  item.get("strictest_scope", ""),
                    "notes":            item.get("notes"),
                    "sources":          _dedupe_sources(sources),
                    "jurisdictions":    sorted(jurisds),
                    "earliest_deadline": earliest,
                    "universality":     universality,
                    "source_count":     len(_dedupe_sources(sources)),
                    "consolidated_by":  "claude",
                })

            # Include any obligations Claude didn't merge (not in merged_indices)
            for i, obl in enumerate(sample, 1):
                if i not in used_indices:
                    result.append({**obl, "consolidated_by": "passthrough"})

            return result

        except LLMError as e:
            log.error("LLM consolidation error: %s", e)
            return None
        except Exception as e:
            log.error("Consolidation error: %s", e)
            return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise_obligation(obl: Dict, baseline_id: str, reg_name: str,
                           jurisdiction: str, source_type: str,
                           actor: str = "") -> Dict:
    """Normalise an obligation dict from any baseline format."""
    return {
        "id":               obl.get("id", ""),
        "title":            obl.get("title") or obl.get("obligation", "")[:120],
        "description":      obl.get("description") or obl.get("obligation", ""),
        "deadline":         obl.get("deadline"),
        "baseline_id":      baseline_id,
        "regulation_title": reg_name,
        "jurisdiction":     jurisdiction,
        "source_type":      source_type,
        "actor":            actor,
        "category":         obl.get("category", ""),
    }


def _infer_category(text: str) -> str:
    """Infer obligation category from text using ordered keyword patterns (first match wins)."""
    text_lower = text.lower()
    for cat, pattern in _CATEGORY_PATTERNS_ORDERED:
        if re.search(pattern, text_lower):
            return cat
    return "Governance"


def _cluster_by_similarity(obligations: List[Dict],
                             threshold: float) -> List[List[Dict]]:
    """
    Group obligations whose titles are sufficiently similar into clusters.
    Uses SequenceMatcher for fuzzy title comparison.
    """
    clusters: List[List[Dict]] = []
    used = set()

    for i, obl in enumerate(obligations):
        if i in used:
            continue
        cluster  = [obl]
        title_i  = _clean_title(obl.get("title") or obl.get("description", ""))
        used.add(i)

        for j, other in enumerate(obligations):
            if j in used:
                continue
            title_j = _clean_title(other.get("title") or other.get("description", ""))
            ratio   = difflib.SequenceMatcher(None, title_i, title_j).ratio()
            if ratio >= threshold:
                cluster.append(other)
                used.add(j)

        clusters.append(cluster)

    return clusters


def _clean_title(title: str) -> str:
    """Normalise a title for similarity comparison — strip all leading action verbs."""
    t = title.lower().strip()
    # Strip any number of leading action verbs so "must implement X" → "X"
    verb_pattern = r"^(must|shall|should|ensure|implement|conduct|establish|provide|maintain|perform|deploy|create|document|register|notify|disclose|test|assess|monitor|report|obtain)\s+"
    prev = None
    while prev != t:
        prev = t
        t = re.sub(verb_pattern, "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _merge_cluster(cluster: List[Dict], category: str) -> Dict[str, Any]:
    """Merge a cluster of similar obligations into one consolidated entry."""
    # Use the longest title as the canonical one (usually most descriptive)
    canonical = max(cluster, key=lambda o: len(o.get("title") or ""))
    title     = _make_action_title(canonical.get("title") or canonical.get("description", ""))

    # Collect all sources
    sources   = []
    jurisds   = set()
    deadlines = []
    for obl in cluster:
        sources.append({
            "regulation_title": obl.get("regulation_title", ""),
            "jurisdiction":     obl.get("jurisdiction", ""),
            "baseline_id":      obl.get("baseline_id"),
            "document_id":      obl.get("document_id"),
            "deadline":         obl.get("deadline"),
            "actor":            obl.get("actor", ""),
        })
        if obl.get("jurisdiction"):
            jurisds.add(obl["jurisdiction"])
        if obl.get("deadline"):
            deadlines.append(obl["deadline"])

    sources   = _dedupe_sources(sources)
    jurisds   = sorted(jurisds)
    earliest  = min(deadlines) if deadlines else None
    n_jurs    = len(jurisds)
    n_total   = 3   # rough minimum for "universal" in our context

    universality = (
        "Universal"          if n_jurs >= n_total
        else "Majority"      if n_jurs >= 2
        else "Single jurisdiction"
    )

    return {
        "title":             title,
        "category":          category,
        "description":       canonical.get("description") or canonical.get("title", ""),
        "strictest_scope":   _pick_strictest(cluster),
        "notes":             None,
        "sources":           sources,
        "jurisdictions":     jurisds,
        "earliest_deadline": earliest,
        "universality":      universality,
        "source_count":      len(sources),
        "consolidated_by":   "structural",
    }


def _make_action_title(title: str) -> str:
    """Ensure the title starts with an action verb."""
    title = title.strip()
    if not title:
        return title
    first = title.split()[0].lower() if title.split() else ""
    action_verbs = {
        "implement","conduct","establish","maintain","provide","ensure",
        "deploy","create","document","register","notify","disclose",
        "test","assess","monitor","report","obtain","perform",
    }
    if first not in action_verbs:
        # Prefix with most likely verb based on category keywords
        if re.search(r"assessment|audit|evaluation|test", title.lower()):
            title = "Conduct " + title[0].lower() + title[1:]
        elif re.search(r"document|record|log", title.lower()):
            title = "Maintain " + title[0].lower() + title[1:]
        elif re.search(r"oversight|review|human", title.lower()):
            title = "Implement " + title[0].lower() + title[1:]
        elif re.search(r"notif|disclos|inform|transparen", title.lower()):
            title = "Disclose " + title[0].lower() + title[1:]
    return title


def _pick_strictest(cluster: List[Dict]) -> str:
    """Return the description with the most requirements (longest) as strictest."""
    return max(
        (o.get("description") or o.get("title", "") for o in cluster),
        key=len
    )


def _dedupe_sources(sources: List[Dict]) -> List[Dict]:
    """Remove duplicate sources keeping one per regulation_title + jurisdiction."""
    seen    = set()
    result  = []
    for s in sources:
        key = (s.get("regulation_title", ""), s.get("jurisdiction", ""))
        if key not in seen:
            seen.add(key)
            result.append(s)
    return result


def _register_key(jurisdictions: List[str], mode: str) -> str:
    raw = mode + "::" + ",".join(sorted(jurisdictions))
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _safe_parse_json_array(raw: str) -> Optional[List]:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw   = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        result = json.loads(raw)
        return result if isinstance(result, list) else None
    except json.JSONDecodeError:
        start = raw.find("[")
        end   = raw.rfind("]") + 1
        if start != -1 and end > start:
            try:
                result = json.loads(raw[start:end])
                return result if isinstance(result, list) else None
            except json.JSONDecodeError:
                pass
    return None
