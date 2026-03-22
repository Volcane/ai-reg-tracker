# SPDX-License-Identifier: Elastic-2.0
# Copyright (c) 2026 Mitch Kwiatkowski
# ARIS � Automated Regulatory Intelligence System
# Licensed under the Elastic License 2.0. See LICENSE in the project root.
"""
ARIS — Gap Analysis Agent

Compares a company profile against the regulatory documents in the database
to identify specific compliance gaps — obligations the company does not yet
have evidence of satisfying.

Two Claude passes:

PASS 1 — REGULATORY SCOPE MAPPING
  Given the company profile (industry, jurisdictions, AI systems, data types),
  identify which specific regulations in the database apply and exactly which
  provisions within each regulation are triggered by this company's profile.
  Output is a structured list of applicable obligations, each anchored to a
  specific document ID so the result is auditable.

PASS 2 — GAP IDENTIFICATION
  Given the applicable obligations from Pass 1 and the company's current
  practices, identify specific gaps. Each gap is:
    - Anchored to a specific regulation and document ID
    - Rated by severity (Critical / High / Medium / Low)
    - Compared: what the regulation requires vs what the company has
    - Given the earliest applicable deadline
    - Given a concrete, specific first action (not generic advice)

Results are stored in gap_analyses table. Running again with the same profile
produces a new analysis — history is preserved for comparison over time.

Design principles:
  - Every gap links back to a document ID — auditable, not generic
  - Two focused passes beat one unfocused pass
  - The profile is never sent verbatim to Claude — it is formatted into
    a structured prompt block to control what the model focuses on
  - Gaps are scored independently of synthesis — analysis can run even if
    no synthesis exists for a topic
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import anthropic  # kept for backward compat; actual calls go through utils.llm

from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL
from utils.llm import call_llm, is_configured, LLMError
from utils.cache import get_logger

log = get_logger("aris.gap")


# Module-level re-exports so tests can patch them cleanly
def get_profile(profile_id: int):
    from utils.db import get_profile as _fn
    return _fn(profile_id)


def get_recent_summaries(days: int = 365, jurisdiction=None):
    from utils.db import get_recent_summaries as _fn
    return _fn(days=days, jurisdiction=jurisdiction)


def save_gap_analysis(result: dict) -> int:
    from utils.db import save_gap_analysis as _fn
    return _fn(result)

# ── Token budgets ─────────────────────────────────────────────────────────────

SCOPE_MAX_TOKENS = 3000   # Pass 1: scope mapping
GAP_MAX_TOKENS   = 4096   # Pass 2: gap identification

# ── System prompts ─────────────────────────────────────────────────────────────

SCOPE_SYSTEM = """You are a senior regulatory compliance analyst specialising in AI law.

You are given a company profile and a set of regulatory documents. Your job is to
determine which specific regulations apply to this company and which specific
provisions within each regulation are triggered by their profile.

Be precise. Only include regulations that genuinely apply — do not include every
regulation in the database just because it exists. Consider:
- The company's operating jurisdictions (which regulations have territorial reach)
- The company's industry sector (which sectoral rules apply)
- The company's AI systems and their characteristics (risk classification, data types, 
  affected population, autonomy level determine scope)

Always respond with valid JSON only — no markdown, no extra commentary."""


SCOPE_PROMPT = """Company Profile:
{profile_block}

Available regulatory documents ({doc_count} documents across {jurisdictions}):
{doc_block}

---

Identify which regulations apply to this company. Return JSON:

{{
  "applicable_regulations": [
    {{
      "document_id": "<exact document ID from the list above>",
      "title": "<regulation title>",
      "jurisdiction": "<jurisdiction code>",
      "why_applicable": "<1-2 sentences: which aspect of the company profile triggers this regulation>",
      "triggered_provisions": [
        {{
          "provision": "<specific obligation, requirement, or prohibition>",
          "triggered_by": "<which part of the company profile triggers this — e.g. 'HR hiring algorithm processing employee data'>",
          "deadline": "<compliance deadline if known, else null>",
          "severity_if_missed": "<Critical | High | Medium | Low>"
        }}
      ]
    }}
  ],
  "out_of_scope": [
    {{
      "document_id": "<document ID>",
      "reason": "<why this regulation does not apply>"
    }}
  ],
  "coverage_note": "<1 sentence on any significant regulatory areas not covered by the available documents>"
}}"""


GAP_SYSTEM = """You are a senior AI compliance officer conducting a gap analysis.

You have been given:
1. A company profile describing their AI systems and current governance practices
2. A structured list of applicable regulatory obligations, each anchored to a specific document

Your job is to identify specific compliance gaps — places where the regulatory
obligation is not yet clearly satisfied by the company's stated practices.

Rules:
- Every gap must reference a specific document_id and specific provision
- Be precise about what is missing — not "implement AI governance" but
  "no documented conformity assessment process for the HR screening AI system"
- Distinguish between gaps that are clearly absent vs gaps where evidence is unclear
- Do not invent obligations that are not in the applicable regulations
- Do not mark something as a gap if the company profile clearly satisfies it

Always respond with valid JSON only — no markdown, no extra commentary."""


GAP_PROMPT = """Company Profile:
{profile_block}

Applicable Regulatory Obligations:
{obligations_block}

---

Identify compliance gaps. Return JSON:

{{
  "posture_summary": "<2-3 sentences: overall compliance posture, most significant risks, general assessment>",
  "posture_score": <integer 0-100 where 100 = fully compliant, 0 = no compliance practices>,
  "gaps": [
    {{
      "gap_id": "<short slug e.g. eu-ai-act-conformity-hr-system>",
      "title": "<short descriptive title>",
      "severity": "<Critical | High | Medium | Low>",
      "document_id": "<exact document ID>",
      "regulation_title": "<regulation name>",
      "jurisdiction": "<jurisdiction>",
      "obligation": "<the specific regulatory requirement>",
      "current_state": "<what the company currently has, based on their profile>",
      "gap_description": "<precise description of what is missing or unclear>",
      "deadline": "<earliest compliance deadline, or null>",
      "affected_systems": ["<which of the company's AI systems are affected>"],
      "first_action": "<the single most important concrete action to start closing this gap>",
      "effort_estimate": "<Low | Medium | High — rough effort to close the gap>"
    }}
  ],
  "compliant_areas": [
    {{
      "area": "<what the company is already doing well>",
      "document_ids": ["<documents whose requirements are satisfied>"],
      "evidence": "<what in the company profile satisfies this>"
    }}
  ],
  "priority_roadmap": [
    {{
      "phase": "<Phase 1: Immediate (0-30 days) | Phase 2: Near-term (1-3 months) | Phase 3: Medium-term (3-6 months)>",
      "actions": ["<specific action>"]
    }}
  ]
}}"""


# ── Gap Analysis Agent ────────────────────────────────────────────────────────

class GapAnalysisAgent:
    """
    Compares a company profile against the regulatory corpus to identify
    specific, document-anchored compliance gaps.
    """

    def __init__(self):
        if not is_configured():
            from utils.llm import _provider
            raise ValueError(
                f"LLM provider '{_provider()}' is not configured. "
                "Set the appropriate API key in config/keys.env."
            )

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self,
            profile_id: int,
            jurisdictions: Optional[List[str]] = None,
            days: int = 365,
            system_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run a full gap analysis for the given company profile.

        profile_id     — ID of a CompanyProfile record in the database
        jurisdictions  — limit analysis to specific jurisdictions (default: all
                         jurisdictions listed in the profile)
        days           — how far back to look for relevant documents
        system_filter  — limit analysis to specific AI system names from profile

        Returns a dict suitable for storage and display, with gaps anchored to
        specific document IDs.
        """
        profile = get_profile(profile_id)
        if not profile:
            raise ValueError(f"Company profile {profile_id} not found")

        # Use profile's operating jurisdictions if not overridden
        jurs = jurisdictions or profile.get("operating_jurisdictions") or []

        log.info("Gap analysis: profile='%s' jurisdictions=%s", profile.get("name"), jurs)

        # 1. Gather relevant documents
        docs = self._gather_documents(jurs, days)
        if not docs:
            return {
                "id":            None,
                "profile_id":    profile_id,
                "profile_name":  profile.get("name"),
                "error":         f"No summarized documents found for jurisdictions: {jurs}",
                "docs_examined": 0,
            }

        log.info("Gap analysis examining %d documents", len(docs))

        # 2. Load baseline obligations and inject into the scope prompt.
        # Use fast consolidation (no API) to provide a structured obligation
        # list — this replaces the raw baseline text with a cleaner prompt.
        baseline_block = ""
        try:
            from agents.consolidation_agent import ConsolidationAgent
            register = ConsolidationAgent().consolidate_fast(jurs)
            if register:
                baseline_block = _format_register_for_prompt(register, jurs)
                log.info("Consolidated register: %d obligations for %s",
                         len(register), jurs)
        except Exception as e:
            # Fall back to raw baseline text if consolidation unavailable
            log.debug("Consolidation unavailable, falling back to raw baselines: %s", e)
            try:
                from agents.baseline_agent import BaselineAgent
                baseline_block = BaselineAgent().format_for_gap_analysis(jurs)
            except Exception:
                pass

        log.info("Gap analysis examining %d documents", len(docs))

        # 3. Pass 1 — regulatory scope mapping (database docs + baseline)
        profile_block     = _format_profile(profile, system_filter)
        scope             = self._run_scope_mapping(profile_block, docs, baseline_block)
        if not scope or not scope.get("applicable_regulations"):
            return {
                "id":            None,
                "profile_id":    profile_id,
                "profile_name":  profile.get("name"),
                "error":         "Scope mapping found no applicable regulations",
                "docs_examined": len(docs),
            }

        applicable_count = len(scope["applicable_regulations"])
        log.info("Scope mapping: %d applicable regulations", applicable_count)

        # 3. Pass 2 — gap identification
        # 4. Pass 2 — gap identification
        obligations_block = _format_obligations(scope["applicable_regulations"])
        gaps_result       = self._run_gap_identification(profile_block, obligations_block)
        if not gaps_result:
            return {
                "id":            None,
                "profile_id":    profile_id,
                "profile_name":  profile.get("name"),
                "error":         "Gap identification failed",
                "docs_examined": len(docs),
            }

        gap_count = len(gaps_result.get("gaps", []))
        log.info("Gap analysis complete: %d gaps, posture score %s",
                 gap_count, gaps_result.get("posture_score"))

        # 5. Build result
        result = {
            "profile_id":         profile_id,
            "profile_name":       profile.get("name"),
            "jurisdictions":      jurs,
            "docs_examined":      len(docs),
            "applicable_count":   applicable_count,
            "scope":              scope,
            "gaps_result":        gaps_result,
            "gap_count":          gap_count,
            "critical_count":     sum(1 for g in gaps_result.get("gaps", [])
                                      if g.get("severity") == "Critical"),
            "posture_score":      gaps_result.get("posture_score", 0),
            "generated_at":       datetime.utcnow().isoformat(),
            "model_used":         CLAUDE_MODEL,
        }

        analysis_id   = save_gap_analysis(result)
        result["id"]  = analysis_id
        return result

    # ── Document gathering ────────────────────────────────────────────────────

    def _gather_documents(self,
                           jurisdictions: List[str],
                           days: int) -> List[Dict[str, Any]]:
        """Get all summarized documents for the relevant jurisdictions."""
        if jurisdictions:
            docs = []
            seen = set()
            for jur in jurisdictions:
                for doc in get_recent_summaries(days=days, jurisdiction=jur):
                    if doc["id"] not in seen:
                        docs.append(doc)
                        seen.add(doc["id"])
        else:
            docs = get_recent_summaries(days=days, jurisdiction=None)

        # Cap at 40 documents — use most urgent/recent
        docs.sort(
            key=lambda d: (
                {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}.get(
                    d.get("urgency", "Low"), 3),
                -(d.get("relevance_score") or 0),
            )
        )
        return docs[:40]

    # ── Claude calls ──────────────────────────────────────────────────────────

    def _run_scope_mapping(self,
                            profile_block: str,
                            docs: List[Dict],
                            baseline_block: str = "") -> Optional[Dict]:
        doc_block     = _format_docs_for_scope(docs)
        jurisdictions = sorted({d.get("jurisdiction", "?") for d in docs})

        # Prepend baseline context before the documents block so Claude
        # reasons about settled law first, then new/recent documents
        full_doc_block = (
            (baseline_block + "\n\n--- RECENT DOCUMENTS FROM DATABASE ---\n\n"
             if baseline_block else "")
            + doc_block
        )

        prompt = SCOPE_PROMPT.format(
            profile_block = profile_block,
            doc_count     = len(docs),
            jurisdictions = ", ".join(jurisdictions),
            doc_block     = full_doc_block,
        )
        return self._call_claude(prompt, SCOPE_SYSTEM, SCOPE_MAX_TOKENS)

    def _run_gap_identification(self,
                                 profile_block: str,
                                 obligations_block: str) -> Optional[Dict]:
        prompt = GAP_PROMPT.format(
            profile_block     = profile_block,
            obligations_block = obligations_block,
        )
        return self._call_claude(prompt, GAP_SYSTEM, GAP_MAX_TOKENS)

    def _call_claude(self, prompt: str, system: str, max_tokens: int) -> Optional[Dict]:
        try:
            raw  = call_llm(prompt=prompt, system=system, max_tokens=max_tokens)
            data = _safe_parse_json(raw)
            if not data:
                log.error("GapAnalysisAgent: LLM returned unparseable JSON")
            return data
        except LLMError as e:
            log.error("GapAnalysisAgent LLM error: %s", e)
            return None
        except Exception as e:
            log.error("GapAnalysisAgent unexpected error: %s", e)
            return None


# ── Profile formatting helpers ────────────────────────────────────────────────

def _format_profile(profile: Dict, system_filter: Optional[List[str]] = None) -> str:
    """Format a company profile into a structured prompt block."""
    lines = [
        f"Company: {profile.get('name', 'Unknown')}",
        f"Industry: {profile.get('industry_sector', 'Unknown')}",
        f"Size: {profile.get('company_size', 'Unknown')}",
        f"Operating jurisdictions: {', '.join(profile.get('operating_jurisdictions') or [])}",
    ]

    # AI systems
    systems = profile.get("ai_systems") or []
    if system_filter:
        systems = [s for s in systems if s.get("name") in system_filter]

    if systems:
        lines.append(f"\nAI Systems ({len(systems)}):")
        for sys in systems:
            lines.append(f"  [{sys.get('name', 'Unnamed')}]")
            lines.append(f"    Purpose: {sys.get('purpose', 'Not specified')}")
            lines.append(f"    Description: {sys.get('description', 'Not specified')}")
            data = sys.get("data_inputs") or []
            if data:
                lines.append(f"    Data processed: {', '.join(data)}")
            pop = sys.get("affected_population")
            if pop:
                lines.append(f"    Affected population: {pop}")
            lines.append(f"    Deployment: {sys.get('deployment_status', 'Unknown')}")
            lines.append(f"    Autonomy: {sys.get('autonomy_level', 'Unknown')}")

    # Current practices
    practices = profile.get("current_practices") or {}
    if practices:
        lines.append("\nCurrent governance practices:")
        bool_fields = {
            "has_ai_governance_policy":     "AI governance policy",
            "has_risk_assessments":         "AI risk assessments",
            "has_human_oversight":          "Human oversight mechanisms",
            "has_incident_response":        "AI incident response plan",
            "has_documentation":            "AI system documentation",
            "has_bias_testing":             "Bias/fairness testing",
            "has_transparency_disclosures": "Transparency disclosures to affected parties",
        }
        for key, label in bool_fields.items():
            val = practices.get(key)
            if val is not None:
                status = "✓ Yes" if val else "✗ No"
                lines.append(f"  {status}: {label}")
        if practices.get("notes"):
            lines.append(f"  Notes: {practices['notes']}")

    # Certifications
    certs = profile.get("existing_certifications") or []
    if certs:
        lines.append(f"\nExisting certifications: {', '.join(certs)}")

    # Context
    concerns = profile.get("primary_concerns")
    if concerns:
        lines.append(f"\nPrimary compliance concerns: {concerns}")

    changes = profile.get("recent_changes")
    if changes:
        lines.append(f"Recent changes: {changes}")

    return "\n".join(lines)


def _format_docs_for_scope(docs: List[Dict]) -> str:
    """Format document list for the scope mapping prompt."""
    blocks = []
    for doc in docs:
        reqs = doc.get("requirements") or []
        areas = doc.get("impact_areas") or []
        block = [
            f"ID: {doc['id']}",
            f"Title: {doc.get('title', 'Untitled')}",
            f"Jurisdiction: {doc.get('jurisdiction')} | "
            f"Type: {doc.get('doc_type')} | "
            f"Status: {doc.get('status')} | "
            f"Urgency: {doc.get('urgency')}",
        ]
        if doc.get("plain_english"):
            block.append(f"Summary: {doc['plain_english']}")
        if reqs:
            block.append("Key requirements: " + "; ".join(str(r) for r in reqs[:4]))
        if areas:
            block.append(f"Impact areas: {', '.join(str(a) for a in areas)}")
        if doc.get("deadline"):
            block.append(f"Deadline: {doc['deadline']}")
        blocks.append("\n".join(block))
    return "\n\n---\n\n".join(blocks)


def _format_obligations(applicable: List[Dict]) -> str:
    """Format applicable obligations for the gap identification prompt."""
    blocks = []
    for reg in applicable:
        provisions = reg.get("triggered_provisions") or []
        block = [
            f"Regulation: {reg.get('title')} [{reg.get('document_id')}]",
            f"Jurisdiction: {reg.get('jurisdiction')}",
            f"Applicable because: {reg.get('why_applicable', '')}",
            "Specific obligations:",
        ]
        for prov in provisions:
            sev = prov.get("severity_if_missed", "Medium")
            dl  = f" (deadline: {prov['deadline']})" if prov.get("deadline") else ""
            block.append(
                f"  • [{sev}] {prov.get('provision', '')}"
                f"{dl}"
                f" — triggered by: {prov.get('triggered_by', '')}"
            )
        blocks.append("\n".join(block))
    return "\n\n".join(blocks)


def _format_register_for_prompt(register: List[Dict], jurisdictions: List[str]) -> str:
    """
    Format a consolidated obligation register as a structured prompt block
    for the gap analysis scope-mapping pass.
    """
    if not register:
        return ""

    lines = [
        "=== CONSOLIDATED OBLIGATION REGISTER (pre-deduplicated across all sources) ===",
        f"Jurisdictions: {', '.join(jurisdictions)}",
        f"Total obligations: {len(register)}",
        "",
    ]

    current_cat = None
    for obl in sorted(register, key=lambda x: (x.get("category",""), x.get("title",""))):
        cat = obl.get("category", "Other")
        if cat != current_cat:
            lines.append(f"\n── {cat.upper()} ──")
            current_cat = cat

        title    = obl.get("title", "")
        jurs     = ", ".join(obl.get("jurisdictions") or [])
        univ     = obl.get("universality", "")
        deadline = obl.get("earliest_deadline", "")
        sources  = len(obl.get("sources") or [])

        line = f"  • {title}"
        if jurs:
            line += f" [{jurs}]"
        if deadline:
            line += f" ⚑ {deadline}"
        if univ and univ != "Single jurisdiction":
            line += f" ({univ})"
        lines.append(line)

        desc = obl.get("description") or obl.get("strictest_scope") or ""
        if desc and desc.lower()[:60] != title.lower()[:60]:
            lines.append(f"    {desc[:200]}")

    return "\n".join(lines)


def _safe_parse_json(raw: str) -> Optional[Dict]:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw   = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                pass
    return None
