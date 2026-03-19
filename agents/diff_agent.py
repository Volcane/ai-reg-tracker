"""
ARIS — Diff Agent

Compares two versions of a regulation, rule, or bill and uses Claude
to produce a structured analysis of what changed, what it means for
compliance, and what action a company needs to take as a result.

Two distinct comparison modes:

1. VERSION DIFF — same document, new draft/version published
   Example: NPRM → Final Rule, Draft v1 → Draft v2, EU AI Act → Corrigendum
   Triggered automatically when upsert_document() detects a content_hash change
   on an existing document ID, or manually via CLI.

2. ADDENDUM / AMENDMENT TRACKING — a separate document modifies or
   reinterprets a referenced base regulation
   Example: Commission Guidelines clarifying EU AI Act Article 5,
            FDA guidance updating an existing AI rule,
            Congressional amendment to a previously passed AI bill
   Stored with a link back to the base document it modifies.

Both produce a DocumentDiff record in the database and optionally
update the parent summary's action_items and urgency.
"""

from __future__ import annotations

import difflib
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import anthropic

from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_TOKENS
from utils.cache import get_logger
from agents.interpreter import _safe_parse_json, _truncate

log = get_logger("aris.diff_agent")


# ── System prompt for diff analysis ──────────────────────────────────────────

DIFF_SYSTEM_PROMPT = """You are a regulatory change analyst specializing in AI law and policy.
Your job is to compare two versions of a regulatory document and identify what changed,
what the changes mean for companies that develop or deploy AI systems, and what
compliance actions are newly required, removed, or modified as a result.

Be precise. Focus only on substantive changes that affect compliance obligations,
deadlines, definitions, penalties, or scope. Ignore purely cosmetic or formatting changes.

Always respond with valid JSON only — no markdown, no extra commentary."""


DIFF_PROMPT_TEMPLATE = """Compare these two versions of an AI regulation document.{baseline_context}

DOCUMENT: {title}
JURISDICTION: {jurisdiction}
AGENCY: {agency}

--- VERSION A (OLDER) ---
Status: {status_old}
Date: {date_old}
URL: {url_old}

{text_old}

--- VERSION B (NEWER) ---
Status: {status_new}
Date: {date_new}
URL: {url_new}

{text_new}

---

Identify all substantive regulatory changes between Version A and Version B.
Return a JSON object with exactly these keys:

{{
  "change_summary": "<1–2 sentence plain English description of what changed overall>",
  "change_type": "<one of: Minor Revision | Significant Amendment | Major Overhaul | Final Rule from Proposed | Corrigendum | No Substantive Change>",
  "severity": "<one of: Low | Medium | High | Critical — reflects impact on compliance obligations>",
  "added_requirements": [
    {{
      "description": "<new mandatory obligation added in Version B>",
      "section": "<section or article reference if identifiable, else null>",
      "effective_date": "<date this takes effect, or null>"
    }}
  ],
  "removed_requirements": [
    {{
      "description": "<mandatory obligation that existed in Version A but was removed or relaxed in Version B>",
      "section": "<section or article reference if identifiable, else null>"
    }}
  ],
  "modified_requirements": [
    {{
      "description": "<how an existing obligation changed — describe both old and new wording>",
      "section": "<section or article reference if identifiable, else null>",
      "direction": "<one of: Stricter | More Lenient | Clarified | Scope Changed>"
    }}
  ],
  "definition_changes": [
    {{
      "term": "<defined term that changed>",
      "old_definition": "<brief description of old meaning>",
      "new_definition": "<brief description of new meaning>",
      "impact": "<why this matters for compliance>"
    }}
  ],
  "deadline_changes": [
    {{
      "description": "<deadline or timeline that changed>",
      "old_deadline": "<previous date or description>",
      "new_deadline": "<updated date or description>"
    }}
  ],
  "penalty_changes": [
    {{
      "description": "<penalty or enforcement provision that changed>"
    }}
  ],
  "scope_changes": "<description of any change in who or what the regulation covers, or null>",
  "new_action_items": [
    "<specific action a company must now take that was not required before>"
  ],
  "obsolete_action_items": [
    "<action that was previously required but is no longer needed>"
  ],
  "overall_assessment": "<2–3 sentences: should companies treat this as a material compliance event requiring immediate attention?>"
}}

Rules:
- If there is no substantive difference, set change_type to 'No Substantive Change' and leave all lists empty
- added_requirements must only contain NEW obligations not present in Version A
- removed_requirements must only contain obligations that genuinely no longer apply
- Be specific: quote or paraphrase the actual regulatory language where possible
- severity Critical = new prohibitions, major new penalties, or fundamental scope expansion
- severity High = new mandatory requirements with near-term deadlines
- severity Medium = clarifications that change how existing rules must be implemented
- severity Low = minor wording changes, extended deadlines, or reduced burdens
"""


# ── Addendum / Amendment prompt ───────────────────────────────────────────────

ADDENDUM_SYSTEM_PROMPT = """You are a regulatory change analyst specializing in AI law and policy.
Your job is to analyse a new document (an addendum, amendment, guidance, or corrigendum)
that modifies or reinterprets an existing base regulation, and explain what the change
means for companies that must comply with that base regulation.

Always respond with valid JSON only — no markdown, no extra commentary."""


ADDENDUM_PROMPT_TEMPLATE = """A new document has been published that modifies or reinterprets
an existing AI regulation. Analyse the impact.

=== BASE REGULATION ===
Title: {base_title}
Jurisdiction: {base_jurisdiction}
Status: {base_status}
URL: {base_url}

Summary of base regulation:
{base_summary}

=== NEW ADDENDUM / AMENDMENT ===
Title: {addendum_title}
Type: {addendum_type}
Agency: {addendum_agency}
Published: {addendum_date}
URL: {addendum_url}

Full text of addendum:
{addendum_text}

---

Analyse how this addendum changes the interpretation or requirements of the base regulation.
Return a JSON object with exactly these keys:

{{
  "relationship_type": "<one of: Amendment | Corrigendum | Implementing Regulation | Guidance | Clarification | Court Decision | Enforcement Action | Repeal | Extension>",
  "change_summary": "<2–3 sentence plain English summary of what this addendum does to the base regulation>",
  "severity": "<one of: Low | Medium | High | Critical>",
  "affected_provisions": [
    {{
      "provision": "<article, section, or rule reference in the base regulation>",
      "change": "<how this provision is now interpreted or modified>",
      "direction": "<one of: Stricter | More Lenient | Clarified | Extended | Repealed>"
    }}
  ],
  "new_obligations": [
    "<new mandatory obligation that now applies as a result of this addendum>"
  ],
  "removed_obligations": [
    "<obligation from the base regulation that this addendum removes or suspends>"
  ],
  "clarified_definitions": [
    {{
      "term": "<term being clarified>",
      "clarification": "<what the addendum says this term means>",
      "practical_impact": "<how this changes what companies must do>"
    }}
  ],
  "enforcement_implications": "<how this addendum affects enforcement, penalties, or safe harbors, or null>",
  "effective_date": "<when these changes take effect, or null>",
  "new_action_items": [
    "<specific action a company should take in response to this addendum>"
  ],
  "overall_assessment": "<2–3 sentences assessing urgency and whether existing compliance programmes need updating>"
}}
"""


# ── Diff Agent class ──────────────────────────────────────────────────────────

class DiffAgent:
    """
    Compares document versions and tracks addenda/amendments.

    Two entry points:
      compare_versions(old_doc, new_doc)  — side-by-side version comparison
      analyse_addendum(base_doc, addendum_doc)  — addendum impact analysis
    """

    def __init__(self):
        if not ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. "
                "Get your key at https://console.anthropic.com/settings/keys"
            )
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # ── Version comparison ────────────────────────────────────────────────────

    def compare_versions(self,
                         old_doc: Dict[str, Any],
                         new_doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Compare two versions of the same document.

        old_doc and new_doc are document dicts as stored in the DB.
        Returns a diff result dict ready to be stored in DocumentDiff table,
        or None if Claude determines there is no substantive change.
        """
        log.info("Comparing versions: %s → %s", old_doc["id"], new_doc["id"])

        old_text = _truncate(old_doc.get("full_text") or old_doc.get("title") or "", 3500)
        new_text = _truncate(new_doc.get("full_text") or new_doc.get("title") or "", 3500)

        # Quick pre-check: if texts are identical, skip Claude
        if old_text.strip() == new_text.strip():
            log.debug("Texts identical — skipping Claude diff for %s", new_doc["id"])
            return None

        # Generate a line-level diff as additional context for Claude
        line_diff = _make_line_diff(old_text, new_text, max_lines=60)

        # Load baseline context if available for this document
        baseline_context = ""
        try:
            from agents.baseline_agent import BaselineAgent
            ba = BaselineAgent()
            ctx = ba.format_for_diff_context(new_doc)
            if ctx:
                baseline_context = f"\n\n{ctx}\n\nUse the baseline above to identify which specific baseline obligations this version change affects, adds to, or contradicts.\n"
        except Exception as e:
            log.debug("Baseline context unavailable: %s", e)

        prompt = DIFF_PROMPT_TEMPLATE.format(
            baseline_context = baseline_context,
            title        = new_doc.get("title", ""),
            jurisdiction = new_doc.get("jurisdiction", ""),
            agency       = new_doc.get("agency", ""),
            status_old   = old_doc.get("status", ""),
            date_old     = str(old_doc.get("published_date", "Unknown")),
            url_old      = old_doc.get("url", ""),
            text_old     = old_text,
            status_new   = new_doc.get("status", ""),
            date_new     = str(new_doc.get("published_date", "Unknown")),
            url_new      = new_doc.get("url", ""),
            text_new     = new_text,
        )

        # Append the line diff as extra context
        if line_diff:
            prompt += f"\n\n--- LINE-LEVEL DIFF PREVIEW ---\n{line_diff}"

        data = self._call_claude(prompt, DIFF_SYSTEM_PROMPT)
        if not data:
            return None

        if data.get("change_type") == "No Substantive Change":
            log.info("No substantive change detected for %s", new_doc["id"])
            return None

        return {
            "base_document_id":     old_doc["id"],
            "new_document_id":      new_doc["id"],
            "diff_type":            "version_update",
            "relationship_type":    data.get("change_type", ""),
            "change_summary":       data.get("change_summary", ""),
            "severity":             data.get("severity", "Medium"),
            "added_requirements":   data.get("added_requirements", []),
            "removed_requirements": data.get("removed_requirements", []),
            "modified_requirements":data.get("modified_requirements", []),
            "definition_changes":   data.get("definition_changes", []),
            "deadline_changes":     data.get("deadline_changes", []),
            "penalty_changes":      data.get("penalty_changes", []),
            "scope_changes":        data.get("scope_changes"),
            "new_action_items":     data.get("new_action_items", []),
            "obsolete_action_items":data.get("obsolete_action_items", []),
            "overall_assessment":   data.get("overall_assessment", ""),
            "model_used":           CLAUDE_MODEL,
            "detected_at":          datetime.utcnow(),
        }

    # ── Addendum / Amendment analysis ─────────────────────────────────────────

    def analyse_addendum(self,
                         base_doc: Dict[str, Any],
                         addendum_doc: Dict[str, Any],
                         base_summary: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Analyse a new document that modifies or reinterprets base_doc.

        base_doc     — the existing regulation being modified
        addendum_doc — the new document (amendment, guidance, corrigendum, etc.)
        base_summary — existing AI summary of base_doc (optional, adds context)

        Returns a diff result dict ready for DocumentDiff table.
        """
        log.info("Analysing addendum: '%s' → base '%s'",
                 addendum_doc.get("title", ""), base_doc.get("title", ""))

        base_text = _truncate(
            (base_summary.get("plain_english", "") if base_summary else "")
            + "\n\n"
            + (base_doc.get("full_text") or base_doc.get("title") or ""),
            max_chars=2500,
        )

        addendum_text = _truncate(
            addendum_doc.get("full_text") or addendum_doc.get("title") or "",
            max_chars=3500,
        )

        prompt = ADDENDUM_PROMPT_TEMPLATE.format(
            base_title        = base_doc.get("title", ""),
            base_jurisdiction = base_doc.get("jurisdiction", ""),
            base_status       = base_doc.get("status", ""),
            base_url          = base_doc.get("url", ""),
            base_summary      = base_text,
            addendum_title    = addendum_doc.get("title", ""),
            addendum_type     = addendum_doc.get("doc_type", ""),
            addendum_agency   = addendum_doc.get("agency", ""),
            addendum_date     = str(addendum_doc.get("published_date", "Unknown")),
            addendum_url      = addendum_doc.get("url", ""),
            addendum_text     = addendum_text,
        )

        data = self._call_claude(prompt, ADDENDUM_SYSTEM_PROMPT)
        if not data:
            return None

        return {
            "base_document_id":      base_doc["id"],
            "new_document_id":       addendum_doc["id"],
            "diff_type":             "addendum",
            "relationship_type":     data.get("relationship_type", ""),
            "change_summary":        data.get("change_summary", ""),
            "severity":              data.get("severity", "Medium"),
            "added_requirements":    data.get("new_obligations", []),
            "removed_requirements":  data.get("removed_obligations", []),
            "modified_requirements": [
                {"description": p["change"], "section": p["provision"],
                 "direction": p["direction"]}
                for p in data.get("affected_provisions", [])
            ],
            "definition_changes":    data.get("clarified_definitions", []),
            "deadline_changes":      (
                [{"description": data["effective_date"],
                  "old_deadline": None, "new_deadline": data["effective_date"]}]
                if data.get("effective_date") else []
            ),
            "penalty_changes":       (
                [{"description": data["enforcement_implications"]}]
                if data.get("enforcement_implications") else []
            ),
            "scope_changes":         None,
            "new_action_items":      data.get("new_action_items", []),
            "obsolete_action_items": [],
            "overall_assessment":    data.get("overall_assessment", ""),
            "model_used":            CLAUDE_MODEL,
            "detected_at":           datetime.utcnow(),
        }

    # ── Batch: scan for addenda in a list of new documents ────────────────────

    def scan_for_addenda(self,
                         new_docs: List[Dict[str, Any]],
                         existing_docs: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
        """
        Lightweight scan: given a list of new documents, identify which ones
        appear to be addenda, amendments, or implementing acts for existing
        documents in the database.

        Returns a list of (addendum_id, base_doc_id) tuples for confirmed links.
        Uses Claude for ambiguous cases; uses heuristics for clear-cut ones.
        """
        links = []
        existing_index = {d["id"]: d for d in existing_docs}

        for new_doc in new_docs:
            base_id = self._find_base_document(new_doc, existing_docs)
            if base_id:
                links.append((new_doc["id"], base_id))
                log.info("Linked addendum '%s' → base '%s'",
                         new_doc.get("title", "")[:60], base_id)

        return links

    def _find_base_document(self,
                             new_doc: Dict[str, Any],
                             existing_docs: List[Dict[str, Any]]) -> Optional[str]:
        """
        Heuristic + Claude: determine whether new_doc is an addendum to
        any of existing_docs. Returns the base document ID if found.
        """
        title      = (new_doc.get("title") or "").lower()
        full_text  = (new_doc.get("full_text") or "").lower()
        combined   = f"{title} {full_text}"

        # Heuristic signals that this is an addendum-type document
        addendum_signals = [
            "amend", "amendment", "corrigendum", "erratum", "implementing",
            "delegated", "supplementing", "guidance on", "guidelines on",
            "clarif", "pursuant to", "in accordance with", "as required by",
            "modif", "replac", "repeal", "extension of", "revision of",
        ]
        is_addendum_like = any(sig in combined for sig in addendum_signals)
        if not is_addendum_like:
            return None

        # Look for explicit document references in the text (CELEX, CFR, etc.)
        celex_refs = re.findall(r"\b3\d{4}[A-Z]\d{4}\b", combined.upper())
        cfr_refs   = re.findall(r"\b\d+\s*cfr\s*part\s*\d+", combined)
        bill_refs  = re.findall(r"\b(?:regulation|directive|act|rule)\s+[\(\[]?(?:eu|us)?\s*[\d/]+", combined)

        # Match against existing documents by CELEX / title similarity
        for existing in existing_docs:
            ex_id    = existing["id"]
            ex_title = (existing.get("title") or "").lower()

            # Direct CELEX reference match
            for ref in celex_refs:
                if ref.lower() in ex_id.lower() or ref.lower() in ex_title:
                    return ex_id

            # Title keyword overlap (simple but effective for same-jurisdiction docs)
            if (new_doc.get("jurisdiction") == existing.get("jurisdiction")
                    and _title_overlap_score(title, ex_title) > 0.4):
                return ex_id

        return None

    # ── Internal Claude caller ────────────────────────────────────────────────

    def _call_claude(self, prompt: str, system: str) -> Optional[Dict]:
        try:
            message = self._client.messages.create(
                model      = CLAUDE_MODEL,
                max_tokens = MAX_TOKENS,
                system     = system,
                messages   = [{"role": "user", "content": prompt}],
            )
            raw  = message.content[0].text.strip()
            return _safe_parse_json(raw)
        except anthropic.APIError as e:
            log.error("Anthropic API error in DiffAgent: %s", e)
            return None
        except Exception as e:
            log.error("Unexpected DiffAgent error: %s", e)
            return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_line_diff(old_text: str, new_text: str, max_lines: int = 60) -> str:
    """
    Generate a unified-diff-style preview for Claude to use as context.
    Truncated to max_lines to stay within token budget.
    """
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff      = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile="Version A", tofile="Version B",
        lineterm="", n=2,
    ))
    if not diff:
        return ""
    truncated = diff[:max_lines]
    if len(diff) > max_lines:
        truncated.append(f"\n... [{len(diff) - max_lines} more diff lines truncated]")
    return "".join(truncated)


def _title_overlap_score(title_a: str, title_b: str) -> float:
    """
    Simple word-overlap score between two titles.
    Returns 0.0–1.0 where 1.0 = identical word sets.
    """
    words_a = set(re.findall(r"\b[a-z]{4,}\b", title_a))
    words_b = set(re.findall(r"\b[a-z]{4,}\b", title_b))
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union        = words_a | words_b
    return len(intersection) / len(union)
