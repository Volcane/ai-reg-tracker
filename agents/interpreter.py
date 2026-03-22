# SPDX-License-Identifier: Elastic-2.0
# Copyright (c) 2026 Mitch Kwiatkowski
# ARIS � Automated Regulatory Intelligence System
# Licensed under the Elastic License 2.0. See LICENSE in the project root.
"""
ARIS — Interpretation Agent

Uses Claude (via Anthropic API) to:
  1. Score relevance of a document to AI regulation
  2. Classify document type and extract structured metadata
  3. Generate a plain-English summary with business action items
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import anthropic  # kept for backward compat; actual calls go through utils.llm

from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_TOKENS
from utils.llm import call_llm, is_configured, LLMError
from utils.cache import get_logger, keyword_score
from utils.search import is_privacy_relevant

log = get_logger("aris.interpreter")

# Lazy import to avoid circular dependency
def _get_learning_agent():
    try:
        from agents.learning_agent import LearningAgent
        return LearningAgent()
    except Exception:
        return None

# ── Prompts ───────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a regulatory intelligence analyst specializing in AI law and policy.
Your job is to read raw legislative and regulatory text and produce structured, actionable 
business intelligence summaries for companies that use or develop AI systems.

You must be precise, neutral, and prioritize information that helps a legal or compliance team 
determine what actions a company must or should take.

Always respond with valid JSON only — no markdown, no extra commentary."""

ANALYSIS_PROMPT_TEMPLATE = """Analyze the following {doc_type} from {jurisdiction} ({source}).

TITLE: {title}
AGENCY / SPONSOR: {agency}
STATUS: {status}
PUBLISHED: {published_date}
URL: {url}

DOCUMENT TEXT:
{text}

---

Return a JSON object with exactly these keys:

{{
  "relevance_score": <float 0.0–1.0, how directly this applies to AI regulation>,
  "plain_english": "<2–3 sentence plain English summary of what this document does>",
  "requirements": [
    "<specific mandatory obligation for companies — use action verbs like 'Must', 'Shall', 'Required to'>",
    ...
  ],
  "recommendations": [
    "<non-mandatory guidance or best practice suggestion>",
    ...
  ],
  "action_items": [
    "<concrete, specific step a company should take in response to this document>",
    ...
  ],
  "deadline": "<ISO date or human-readable deadline if one exists, else null>",
  "impact_areas": [
    "<business area affected — e.g. 'Healthcare AI', 'Hiring Algorithms', 'Data Privacy', 'Marketing', 'Product Development'>",
    ...
  ],
  "urgency": "<one of: Low | Medium | High | Critical>",
  "doc_classification": "<one of: Final Rule | Proposed Rule | Executive Order | Presidential Memorandum | Guidance | Bill (Introduced) | Bill (Passed) | Enacted Law | Notice | Other>"
}}

Rules:
- requirements should only contain things that are LEGALLY MANDATORY
- recommendations should only contain VOLUNTARY or advisory items
- action_items should be specific and actionable (what should the legal/compliance team actually do?)
- relevance_score should be 0.0 if this has nothing to do with AI; 1.0 if it's directly and comprehensively AI-focused
- if the document is only tangentially AI-related (e.g., general tech regulation that mentions AI briefly), score accordingly
- urgency should reflect both the regulatory force (final rule > proposed rule) and timeline
"""


PRIVACY_SYSTEM_PROMPT = """You are a regulatory intelligence analyst specializing in data privacy law and compliance.
Your job is to read privacy legislation, regulations, and guidance and produce structured, actionable
business intelligence summaries for companies that collect or process personal data.

You must be precise, neutral, and prioritize information that helps a legal or privacy team
determine what obligations a company has, what rights data subjects have, and what actions are required.

Always respond with valid JSON only — no markdown, no extra commentary."""

PRIVACY_ANALYSIS_PROMPT_TEMPLATE = """Analyze the following {doc_type} from {jurisdiction} ({source}).

TITLE: {title}
AGENCY / REGULATOR: {agency}
STATUS: {status}
PUBLISHED: {published_date}
URL: {url}

DOCUMENT TEXT:
{text}

---

Return a JSON object with exactly these keys:

{{
  "relevance_score": <float 0.0–1.0, how directly this applies to data privacy regulation>,
  "plain_english": "<2–3 sentence plain English summary of what this document requires or establishes>",
  "requirements": [
    "<specific mandatory obligation — use action verbs like 'Must', 'Shall', 'Required to'>",
    ...
  ],
  "recommendations": [
    "<non-mandatory guidance or best practice suggestion>",
    ...
  ],
  "action_items": [
    "<concrete, specific step a privacy/legal team should take in response to this document>",
    ...
  ],
  "data_subject_rights": [
    "<right granted to individuals under this regulation, e.g. right to erasure, right to access>",
    ...
  ],
  "legal_bases": [
    "<lawful basis for processing personal data mentioned, e.g. consent, legitimate interest, contract>",
    ...
  ],
  "breach_notification_timeline": "<timeline for breach notification if specified, else null>",
  "penalty_summary": "<brief description of maximum penalties, else null>",
  "deadline": "<ISO date or human-readable deadline if one exists, else null>",
  "impact_areas": [
    "<business area affected — e.g. 'Marketing', 'HR/Employment', 'Healthcare', 'Finance', 'Product Development', 'IT/Security'>",
    ...
  ],
  "urgency": "<one of: Low | Medium | High | Critical>",
  "doc_classification": "<one of: Final Rule | Proposed Rule | Enacted Law | Guidance | Notice | Bill (Introduced) | Bill (Passed) | Executive Order | Other>"
}}

Rules:
- requirements should only contain things that are LEGALLY MANDATORY
- recommendations should only contain VOLUNTARY or advisory items
- data_subject_rights: list each distinct right granted (leave empty array if no rights are established)
- legal_bases: list each processing basis mentioned or implied (leave empty array if not specified)
- breach_notification_timeline: e.g. "72 hours to supervisory authority, without undue delay to individuals"
- relevance_score: 0.0 if unrelated to data privacy; 1.0 if directly and comprehensively about data privacy
- urgency should reflect regulatory force and timeline urgency
"""

# ── Skipped stub helper ───────────────────────────────────────────────────────

def _write_skipped_stub(doc: dict, reason: str,
                        claude_score: float = 0.0) -> Optional[Dict]:
    """
    Write a minimal summary row with urgency='Skipped' so the document
    leaves the pending queue and the reason is visible in the Documents view.

    Returns the stub dict so callers can return it from analyse() and the
    orchestrator can feed it into the autonomous learning loop.
    claude_score: the relevance score that triggered the skip (0.0 if pre-filter).
    """
    stub = {
        "document_id":    doc.get("id", ""),
        "plain_english":  reason,
        "urgency":        "Skipped",
        "relevance_score": claude_score,
        "requirements":   [],
        "action_items":   [],
        "impact_areas":   [],
        "domain":         doc.get("domain", "ai"),
        # Carry source fields so the orchestrator learning loop has context
        "_source":        doc.get("source", ""),
        "_agency":        doc.get("agency", ""),
        "_jurisdiction":  doc.get("jurisdiction", ""),
        "_doc_type":      doc.get("doc_type", ""),
    }
    try:
        from utils.db import upsert_summary
        upsert_summary({k: v for k, v in stub.items() if not k.startswith("_")})
    except Exception as e:
        log.debug("Could not write skipped stub for %s: %s", doc.get("id", ""), e)
    return stub


# ── Interpreter class ─────────────────────────────────────────────────────────

class InterpreterAgent:
    """
    Sends document text to the configured LLM and returns a structured summary dict.
    """

    def __init__(self):
        if not is_configured():
            from utils.llm import _provider
            raise ValueError(
                f"LLM provider '{_provider()}' is not configured. "
                "Set the appropriate API key in config/keys.env."
            )

    def analyse(self, doc: Dict[str, Any],
                force: bool = False) -> Optional[Dict[str, Any]]:
        """
        Analyse a single document dict.
        Returns a summary dict ready to be stored in the `summaries` table,
        or None if the document is not AI-relevant.

        force=True bypasses the learning pre-filter entirely.
        """
        # ── Stage 1: Learning-aware pre-filter ───────────────────────────────
        learner = _get_learning_agent()

        if not force:
            if learner:
                skip, pre_score, reason = learner.should_skip(doc)
                if skip:
                    log.warning(
                        "Pre-filter skipped '%s' (%s): %s — run with --force to override",
                        doc.get("title", doc.get("id", ""))[:60],
                        doc.get("source", ""),
                        reason,
                    )
                    # Write a stub summary so this doc leaves the pending queue
                    # and the user can see why it was filtered.
                    return _write_skipped_stub(doc, reason)
            else:
                # Fallback to basic keyword/privacy score
                text_blob  = f"{doc.get('title','')} {doc.get('full_text','')}"
                doc_domain_check = doc.get("domain", "ai")
                if doc_domain_check == "privacy":
                    if not is_privacy_relevant(text_blob):
                        log.debug("Skipping low-relevance privacy document: %s", doc["id"])
                        return _write_skipped_stub(doc, "low privacy relevance score (no learner)")
                elif keyword_score(text_blob) < 0.05:
                    log.debug("Skipping low-relevance document: %s", doc["id"])
                    return _write_skipped_stub(doc, "low keyword relevance score (no learner)")

        # ── Stage 2: Build prompt with any domain-specific adaptations ────────
        text_blob = f"{doc.get('title','')} {doc.get('full_text','')}"
        doc_domain = doc.get("domain", "ai")

        # Select prompt template based on document domain
        if doc_domain == "privacy":
            chosen_system   = PRIVACY_SYSTEM_PROMPT
            chosen_template = PRIVACY_ANALYSIS_PROMPT_TEMPLATE
        else:
            chosen_system   = SYSTEM_PROMPT
            chosen_template = ANALYSIS_PROMPT_TEMPLATE

        # Get learned prompt additions for this source/agency/jurisdiction
        prompt_additions = ""
        if learner:
            prompt_additions = learner.get_adapted_prompt_additions(doc)

        prompt = chosen_template.format(
            doc_type      = doc.get("doc_type", "Document"),
            jurisdiction  = doc.get("jurisdiction", "Unknown"),
            source        = doc.get("source", "Unknown"),
            title         = doc.get("title", ""),
            agency        = doc.get("agency", "N/A"),
            status        = doc.get("status", "Unknown"),
            published_date= str(doc.get("published_date", "Unknown")),
            url           = doc.get("url", ""),
            text          = _truncate(text_blob, max_chars=5000),
        )

        # Inject prompt adaptations before the JSON instruction block
        if prompt_additions:
            prompt = prompt_additions + "\n\n" + prompt

        # ── Stage 3: LLM analysis ─────────────────────────────────────────────
        try:
            raw  = call_llm(prompt=prompt, system=chosen_system, max_tokens=MAX_TOKENS)
            data = _safe_parse_json(raw)
        except LLMError as e:
            log.error("LLM error for doc %s: %s", doc["id"], e)
            return None
        except json.JSONDecodeError as e:
            log.error("JSON parse error for doc %s: %s", doc["id"], e)
            return None

        if not data:
            return None

        # Final gate: if Claude rated relevance low, write a Skipped stub
        # so the document is visible in Documents view with the reason.
        # Threshold 0.35 — below this Claude is saying "this isn't about AI/privacy".
        relevance = data.get("relevance_score", 0)
        if relevance < 0.35:
            log.info("Claude rated doc %s as low relevance (%.2f) — writing Skipped stub",
                     doc["id"], relevance)
            # Return a Skipped stub so the document leaves the pending queue
            # and appears in Documents view with a clear reason
            return _write_skipped_stub(
                doc,
                reason=f"Claude relevance score {relevance:.2f} — document does not appear to "
                       f"be about AI regulation or data privacy (possible false positive from "
                       f"keyword search)",
                claude_score=relevance,
            )

        summary = {
            "document_id":     doc["id"],
            "plain_english":   data.get("plain_english", ""),
            "requirements":    data.get("requirements", []),
            "recommendations": data.get("recommendations", []),
            "action_items":    data.get("action_items", []),
            "deadline":        data.get("deadline"),
            "impact_areas":    data.get("impact_areas", []),
            "urgency":         data.get("urgency", "Medium"),
            "relevance_score": float(data.get("relevance_score", 0.5)),
            "model_used":      CLAUDE_MODEL,
            "domain":          doc_domain,
        }

        # Preserve privacy-specific extracted fields as additional impact_areas entries
        # when the document is privacy-domain
        if doc_domain == "privacy":
            rights = data.get("data_subject_rights", [])
            if rights:
                summary["action_items"] = (
                    summary["action_items"] +
                    [f"Data subject right to implement: {r}" for r in rights[:3]]
                )
            breach_timeline = data.get("breach_notification_timeline")
            if breach_timeline:
                summary["requirements"] = (
                    [f"Breach notification: {breach_timeline}"] +
                    summary["requirements"]
                )

        return summary

    def analyse_batch(self, docs: List[Dict[str, Any]],
                      progress_callback=None,
                      force: bool = False) -> List[Dict[str, Any]]:
        """
        Analyse a list of documents. Returns list of successful summary dicts.
        progress_callback(current, total) is called if provided.

        force=True bypasses the learning pre-filter so every document is sent
        to the LLM regardless of source quality scores.
        """
        summaries  = []
        skipped    = 0
        for i, doc in enumerate(docs):
            if progress_callback:
                progress_callback(i + 1, len(docs))
            try:
                result = self.analyse(doc, force=force)
                if result:
                    summaries.append(result)
                else:
                    skipped += 1
            except Exception as e:
                log.error("Unexpected error analysing doc %s: %s", doc.get("id"), e)
        if skipped:
            log.warning(
                "%d/%d documents skipped by pre-filter (run with --force to override)",
                skipped, len(docs)
            )
        return summaries


# ── Helpers ───────────────────────────────────────────────────────────────────

def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n[... truncated at {max_chars} chars]"


def _safe_parse_json(raw: str) -> Optional[Dict]:
    """Handle Claude potentially wrapping JSON in markdown fences."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw   = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to find the JSON object in the text
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                pass
    return None
