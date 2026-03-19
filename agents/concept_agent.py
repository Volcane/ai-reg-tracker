"""
ARIS — Concept Mapping Agent

Produces structured cross-jurisdiction comparisons of how different
regulatory frameworks address the same underlying concept.

For a concept like "transparency" the agent generates a table showing:
  - Every jurisdiction that addresses this concept
  - The specific obligation or requirement
  - Who it applies to (scope: providers, deployers, all entities, etc.)
  - What triggers the obligation
  - Whether it is mandatory / recommended / guidance
  - The specific regulatory section or article
  - How similar or different it is to the other jurisdictions' approaches

This is achieved by sending each baseline's relevant content to the LLM
with a structured extraction prompt. Results are cached in the
`concept_map_cache` table for 7 days to avoid repeated API calls.

Architecture
------------
  1. For each concept, identify which baselines address it (using the
     CONCEPTS keyword map from graph_agent.py — no LLM call)
  2. For each relevant baseline, extract concept-relevant sections
     (targeted section lookup — no LLM call)
  3. Call the LLM once per concept with ALL relevant baseline sections
     assembled into a single prompt, asking for structured extraction
     of all jurisdictions in one shot (minimises API calls)
  4. Parse the structured response into ConceptEntry objects
  5. Cache and return

Public API
----------
  agent = ConceptAgent()
  result = agent.get_concept_map("transparency")
  # result = {
  #   concept_key:   "transparency",
  #   concept_label: "Transparency & Explainability",
  #   entries: [
  #     {
  #       jurisdiction:   "EU",
  #       baseline_id:    "eu_ai_act",
  #       baseline_title: "EU AI Act",
  #       obligation:     "Providers must supply clear instructions for use...",
  #       scope:          "High-risk AI system providers and deployers",
  #       trigger:        "Placing a high-risk AI system on the market",
  #       strength:       "mandatory",   # mandatory | recommended | guidance
  #       section:        "Article 13",
  #       similarity_notes: "Stricter than NIST RMF; similar scope to UK Framework",
  #     },
  #     ...
  #   ],
  #   entry_count: 9,
  #   built_at: "2026-01-15T...",
  # }
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.cache import get_logger
from utils.llm   import call_llm, LLMError

log = get_logger("aris.concepts")

BASELINES_DIR = Path(__file__).parent.parent / "data" / "baselines"

# ── Concept catalogue ─────────────────────────────────────────────────────────
# Each concept has a label (display name), description, and the keyword patterns
# used to identify relevant baselines (imported from graph_agent).

CONCEPT_CATALOGUE: Dict[str, Dict] = {
    "transparency": {
        "label":       "Transparency & Explainability",
        "description": "Requirements to disclose how AI systems work, provide explanations "
                       "of automated decisions, and make system capabilities and limitations known.",
        "keywords":    ["transparency", "explainab", "interpretab", "disclosure",
                        "right to explanation", "right to contest"],
    },
    "risk_assessment": {
        "label":       "Risk Assessment",
        "description": "Obligations to assess, evaluate, and document the risks posed by AI "
                       "systems before deployment and on an ongoing basis.",
        "keywords":    ["risk assessment", "impact assessment", "conformity assessment",
                        "risk evaluation", "risk-based approach"],
    },
    "human_oversight": {
        "label":       "Human Oversight & Control",
        "description": "Requirements for human review, override capability, or meaningful human "
                       "control over AI-generated decisions.",
        "keywords":    ["human oversight", "human review", "human in the loop",
                        "meaningful human control", "human supervision"],
    },
    "bias_fairness": {
        "label":       "Bias, Fairness & Non-Discrimination",
        "description": "Requirements to test for, mitigate, and prevent discriminatory outcomes "
                       "from AI systems, including bias auditing obligations.",
        "keywords":    ["bias", "fairness", "discrimination", "disparate impact",
                        "disparate treatment", "equitable", "protected characteristic"],
    },
    "data_governance": {
        "label":       "Training Data Governance",
        "description": "Obligations around the quality, provenance, documentation, and "
                       "governance of data used to train AI systems.",
        "keywords":    ["training data", "data minimisation", "data quality",
                        "data governance", "dataset", "data provenance"],
    },
    "automated_decisions": {
        "label":       "Automated Decision-Making",
        "description": "Specific rules governing AI-generated decisions that affect individuals, "
                       "including rights to contest, explanation, and human review.",
        "keywords":    ["automated decision", "automated decision-making",
                        "algorithmic decision", "automated profiling"],
    },
    "prohibited_practices": {
        "label":       "Prohibited AI Practices",
        "description": "AI applications and uses that are explicitly banned or severely "
                       "restricted across jurisdictions.",
        "keywords":    ["prohibited", "forbidden", "social scoring", "subliminal",
                        "unacceptable risk", "banned practice"],
    },
    "foundation_models": {
        "label":       "Foundation Model & GPAI Obligations",
        "description": "Specific obligations for developers and deployers of foundation models, "
                       "large language models, and general-purpose AI systems.",
        "keywords":    ["foundation model", "general purpose ai", "gpai",
                        "large language model", "llm", "generative ai"],
    },
    "incident_reporting": {
        "label":       "Incident Reporting & Post-Market Monitoring",
        "description": "Requirements to monitor AI systems after deployment, report serious "
                       "incidents or malfunctions, and notify regulators or affected parties.",
        "keywords":    ["incident report", "notify", "notification", "serious incident",
                        "breach notification", "post-market monitoring"],
    },
    "penalties": {
        "label":       "Penalties & Enforcement",
        "description": "Sanctions, fines, and enforcement mechanisms for non-compliance with "
                       "AI regulation across different jurisdictions.",
        "keywords":    ["penalty", "fine", "sanction", "enforcement",
                        "administrative fine", "infringement"],
    },
}

# ── Extraction prompt ─────────────────────────────────────────────────────────

EXTRACTION_SYSTEM = """You are a regulatory analysis expert extracting structured information
from AI regulation texts. Extract precise, accurate information only from the provided content.
Do not infer or add information not present in the source material."""

EXTRACTION_PROMPT_TEMPLATE = """Extract how each jurisdiction below addresses the concept of:
CONCEPT: {concept_label}
DESCRIPTION: {concept_description}

For each jurisdiction, extract:
1. The specific obligation or requirement (what must be done)
2. Scope (who it applies to: e.g. "high-risk AI providers", "all deployers", "employers")
3. Trigger (what activates the requirement: e.g. "before market placement", "for automated hiring")
4. Strength (one of: mandatory | recommended | guidance)
5. Section (the specific article, provision, or section reference)
6. Similarity notes (1 sentence: how this compares to the other jurisdictions — convergences or divergences)

SOURCE MATERIAL BY JURISDICTION:
{source_material}

Respond with a JSON array. Each element represents one jurisdiction's approach.
Include ONLY jurisdictions with meaningful content about this concept.
Use EXACTLY this structure:
[
  {{
    "jurisdiction":      "EU",
    "baseline_id":       "eu_ai_act",
    "baseline_title":    "EU AI Act",
    "obligation":        "Clear, specific description of what is required",
    "scope":             "Who it applies to",
    "trigger":           "What activates the requirement",
    "strength":          "mandatory",
    "section":           "Article 13",
    "similarity_notes":  "One sentence comparing to other jurisdictions"
  }}
]

Rules:
- Use "mandatory" only if the regulation imposes a legal obligation with potential sanctions
- Use "recommended" if the regulation strongly encourages but does not legally require
- Use "guidance" for voluntary frameworks, best-practice guidance, or principles
- If a jurisdiction has multiple distinct requirements for this concept, create one entry per requirement
- Be concise in "obligation" — 1-2 sentences maximum
- If the source material is insufficient for a jurisdiction, omit it entirely
- Respond with only the JSON array, no preamble or explanation"""


# ── Baseline section extractor ────────────────────────────────────────────────

def _extract_concept_sections(baseline: Dict, keywords: List[str]) -> str:
    """
    Extract concept-relevant sections from a baseline dict.
    Returns a formatted text block for that jurisdiction.
    """
    title = baseline.get("title", baseline.get("id", ""))
    jur   = baseline.get("jurisdiction", "")
    parts = [f"=== {title} ({jur}) — {baseline.get('id', '')} ==="]

    # Skip metadata keys
    skip = {"id", "jurisdiction", "title", "official_title", "short_name",
            "celex", "oj_reference", "status", "last_reviewed"}

    for key, value in baseline.items():
        if key in skip or not value:
            continue
        text = json.dumps(value).lower()
        if any(kw in text for kw in keywords):
            section_name = key.replace("_", " ").title()
            parts.append(f"\n[{section_name}]")
            # Format the value
            if isinstance(value, list):
                for item in value[:8]:   # cap items per section
                    if isinstance(item, dict):
                        parts.append(json.dumps(item, indent=2)[:600])
                    else:
                        parts.append(str(item)[:300])
            elif isinstance(value, dict):
                parts.append(json.dumps(value, indent=2)[:800])
            else:
                parts.append(str(value)[:600])

    return "\n".join(parts) if len(parts) > 1 else ""


def _load_baselines() -> List[Dict]:
    baselines = []
    if not BASELINES_DIR.exists():
        return baselines
    for path in sorted(BASELINES_DIR.glob("*.json")):
        if path.name == "index.json":
            continue
        try:
            baselines.append(json.loads(path.read_text()))
        except Exception as e:
            log.warning("Could not load baseline %s: %s", path.name, e)
    return baselines


def _parse_concept_entries(raw: str) -> List[Dict]:
    """Parse LLM response JSON into validated entry list."""
    clean = re.sub(r'```json|```', '', raw).strip()
    try:
        entries = json.loads(clean)
        if not isinstance(entries, list):
            return []
    except json.JSONDecodeError:
        # Try to salvage partial JSON
        match = re.search(r'\[.*\]', clean, re.DOTALL)
        if match:
            try:
                entries = json.loads(match.group(0))
            except Exception:
                return []
        else:
            return []

    # Validate and normalise each entry
    valid = []
    required = {"jurisdiction", "baseline_id", "obligation", "strength"}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if not all(k in entry for k in required):
            continue
        # Normalise strength
        strength = entry.get("strength", "guidance").lower()
        if strength not in ("mandatory", "recommended", "guidance"):
            strength = "guidance"
        valid.append({
            "jurisdiction":     entry.get("jurisdiction", ""),
            "baseline_id":      entry.get("baseline_id", ""),
            "baseline_title":   entry.get("baseline_title", ""),
            "obligation":       entry.get("obligation", ""),
            "scope":            entry.get("scope", ""),
            "trigger":          entry.get("trigger", ""),
            "strength":         strength,
            "section":          entry.get("section", ""),
            "similarity_notes": entry.get("similarity_notes", ""),
        })

    # Sort: mandatory first, then recommended, then guidance
    order = {"mandatory": 0, "recommended": 1, "guidance": 2}
    valid.sort(key=lambda e: (order.get(e["strength"], 3), e["jurisdiction"]))
    return valid


# ── Concept Agent ─────────────────────────────────────────────────────────────

class ConceptAgent:
    """
    Generates cross-jurisdiction concept maps.
    """

    def get_concept_map(self,
                         concept_key: str,
                         force: bool = False,
                         max_age_days: int = 7) -> Optional[Dict]:
        """
        Return a concept map for the given concept key.

        Uses cached result if available and fresh (< max_age_days old).
        If not cached or force=True, builds the map using the LLM.

        Args:
            concept_key:  One of the keys in CONCEPT_CATALOGUE.
            force:        Rebuild even if cached.
            max_age_days: Maximum age of cached result to accept.

        Returns:
            Full concept map dict, or None if the concept is unknown.
        """
        if concept_key not in CONCEPT_CATALOGUE:
            log.warning("Unknown concept key: %s", concept_key)
            return None

        # Return cached result if fresh
        if not force:
            from utils.db import get_concept_map
            cached = get_concept_map(concept_key, max_age_days=max_age_days)
            if cached:
                log.debug("Concept map served from cache: %s", concept_key)
                return cached

        # Build fresh
        return self._build(concept_key)

    def _build(self, concept_key: str) -> Optional[Dict]:
        """Build concept map via LLM extraction."""
        spec = CONCEPT_CATALOGUE[concept_key]
        keywords = spec["keywords"]
        baselines = _load_baselines()

        # Filter to baselines that contain this concept
        relevant = [
            b for b in baselines
            if any(kw in json.dumps(b).lower() for kw in keywords)
        ]

        if not relevant:
            log.warning("No baselines found for concept: %s", concept_key)
            return self._empty(concept_key, spec)

        log.info("Building concept map '%s' from %d baselines", concept_key, len(relevant))

        # Extract concept-relevant sections per baseline
        source_blocks = []
        for b in relevant:
            block = _extract_concept_sections(b, keywords)
            if block:
                source_blocks.append(block)

        if not source_blocks:
            return self._empty(concept_key, spec)

        # Assemble prompt — cap total length to stay within context window
        source_material = "\n\n".join(source_blocks)
        if len(source_material) > 24000:
            source_material = source_material[:24000] + "\n\n[content truncated]"

        prompt = EXTRACTION_PROMPT_TEMPLATE.format(
            concept_label       = spec["label"],
            concept_description = spec["description"],
            source_material     = source_material,
        )

        try:
            from utils.llm import active_model
            raw   = call_llm(prompt=prompt, system=EXTRACTION_SYSTEM, max_tokens=3000)
            model = active_model()
        except LLMError as e:
            log.error("Concept map LLM call failed for %s: %s", concept_key, e)
            return None

        entries = _parse_concept_entries(raw)
        if not entries:
            log.warning("Concept map parse returned no entries for %s", concept_key)
            return self._empty(concept_key, spec)

        # Persist to cache
        from utils.db import save_concept_map
        save_concept_map(
            concept_key   = concept_key,
            concept_label = spec["label"],
            entries       = entries,
            model_used    = model,
        )

        return {
            "concept_key":   concept_key,
            "concept_label": spec["label"],
            "description":   spec["description"],
            "entries":       entries,
            "entry_count":   len(entries),
            "model_used":    model,
            "built_at":      None,   # freshly built, no timestamp from cache
        }

    @staticmethod
    def _empty(concept_key: str, spec: Dict) -> Dict:
        return {
            "concept_key":   concept_key,
            "concept_label": spec["label"],
            "description":   spec["description"],
            "entries":       [],
            "entry_count":   0,
            "model_used":    None,
            "built_at":      None,
        }

    @staticmethod
    def list_concepts() -> List[Dict]:
        """Return all available concepts with cache status."""
        from utils.db import list_concept_maps
        cached = {r["concept_key"]: r for r in list_concept_maps()}
        return [
            {
                "key":         k,
                "label":       v["label"],
                "description": v["description"],
                "cached":      k in cached,
                "entry_count": cached[k]["entry_count"] if k in cached else 0,
                "built_at":    cached[k].get("built_at") if k in cached else None,
            }
            for k, v in CONCEPT_CATALOGUE.items()
        ]
