# SPDX-License-Identifier: Elastic-2.0
# Copyright (c) 2026 Mitch Kwiatkowski
# ARIS � Automated Regulatory Intelligence System
# Licensed under the Elastic License 2.0. See LICENSE in the project root.
"""
ARIS — Timeline Agent

Builds a unified regulatory timeline from three data sources:

1. BASELINE MILESTONES — structured timeline arrays from baseline JSON files
   (EU AI Act has 6 dated milestones; US state laws have effective dates)

2. LIVE DOCUMENT EVENTS — documents in the database with published_date,
   categorised as proposed_rule, final_rule, guidance, enforcement_action, etc.
   Their status fields map to timeline event types.

3. HORIZON ITEMS — planned/anticipated regulations from the horizon table,
   shown as future events on the timeline.

Each event has:
  date            ISO date string (YYYY-MM-DD or YYYY-MM)
  event           Human-readable description
  event_type      milestone | proposed | final | guidance | enforcement
                  | implementing_act | effective | introduced | anticipated
  regulation_id   baseline ID or document ID
  regulation_name Short name
  jurisdiction    Jurisdiction code
  status          In Force | Proposed | Anticipated | etc.
  url             Link to source (optional)

The timeline is sorted chronologically. Future events (> today) are marked
anticipated. Past events with documents in the DB are marked confirmed.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.cache import get_logger

log = get_logger("aris.timeline")

BASELINES_DIR = Path(__file__).parent.parent / "data" / "baselines"

TODAY = date.today().isoformat()

# ── Event type definitions ────────────────────────────────────────────────────

EVENT_TYPES = {
    "milestone":        {"label": "Milestone",         "color": "#4f8fe0"},
    "effective":        {"label": "Effective Date",    "color": "#52a878"},
    "proposed":         {"label": "Proposed Rule",     "color": "#d4a843"},
    "final":            {"label": "Final Rule",        "color": "#52a878"},
    "guidance":         {"label": "Guidance",          "color": "#5299d4"},
    "enforcement":      {"label": "Enforcement",       "color": "#e05252"},
    "implementing_act": {"label": "Implementing Act",  "color": "#a06bd4"},
    "introduced":       {"label": "Introduced",        "color": "#d4a843"},
    "anticipated":      {"label": "Anticipated",       "color": "#607070"},
    "amendment":        {"label": "Amendment",         "color": "#e0834a"},
}

# Status → event_type mapping for live documents
STATUS_TO_EVENT_TYPE = {
    "proposed rule":      "proposed",
    "notice of proposed": "proposed",
    "nprm":               "proposed",
    "final rule":         "final",
    "final":              "final",
    "in force":           "effective",
    "enacted":            "effective",
    "guidance":           "guidance",
    "advisory":           "guidance",
    "enforcement action": "enforcement",
    "consent order":      "enforcement",
    "amendment":          "amendment",
}


def _parse_date(s: Any) -> Optional[str]:
    """Normalise various date formats to YYYY-MM-DD or YYYY-MM."""
    if not s:
        return None
    s = str(s).strip()
    # Already ISO
    if re.match(r'^\d{4}-\d{2}-\d{2}$', s):
        return s
    if re.match(r'^\d{4}-\d{2}$', s):
        return s + "-01"
    if re.match(r'^\d{4}$', s):
        return s + "-01-01"
    # "Month YYYY"
    months = {'january':'01','february':'02','march':'03','april':'04','may':'05',
              'june':'06','july':'07','august':'08','september':'09','october':'10',
              'november':'11','december':'12',
              'jan':'01','feb':'02','mar':'03','apr':'04','jun':'06','jul':'07',
              'aug':'08','sep':'09','oct':'10','nov':'11','dec':'12'}
    m = re.match(r'(\w+)\s+(\d{4})', s, re.IGNORECASE)
    if m:
        mon = m.group(1).lower()
        yr  = m.group(2)
        if mon in months:
            return f"{yr}-{months[mon]}-01"
    return None


# ── Baseline timeline extraction ──────────────────────────────────────────────

def extract_baseline_events(baseline: Dict) -> List[Dict]:
    """Extract all timeline events from a single baseline JSON."""
    bid   = baseline.get("id", "")
    name  = baseline.get("short_name") or baseline.get("title", bid)
    jur   = baseline.get("jurisdiction", "")
    url   = baseline.get("url", "")
    events = []

    # Explicit timeline array (EU AI Act style)
    for t in baseline.get("timeline", []):
        d = _parse_date(t.get("date"))
        if d:
            events.append({
                "date":            d,
                "event":           t.get("milestone", ""),
                "event_type":      "milestone",
                "regulation_id":   bid,
                "regulation_name": name,
                "jurisdiction":    jur,
                "status":          "confirmed" if d <= TODAY else "anticipated",
                "url":             url,
            })

    # Effective date
    eff = _parse_date(baseline.get("effective_date"))
    if eff:
        events.append({
            "date":            eff,
            "event":           f"{name} takes effect",
            "event_type":      "effective",
            "regulation_id":   bid,
            "regulation_name": name,
            "jurisdiction":    jur,
            "status":          "confirmed" if eff <= TODAY else "anticipated",
            "url":             url,
        })

    # Legislative status (Canada AIDA style)
    ls = baseline.get("legislative_status", {})
    if isinstance(ls, dict):
        intro = _parse_date(ls.get("introduced"))
        if intro:
            events.append({
                "date":            intro,
                "event":           f"{ls.get('bill', name)} introduced",
                "event_type":      "introduced",
                "regulation_id":   bid,
                "regulation_name": name,
                "jurisdiction":    jur,
                "status":          "confirmed" if intro <= TODAY else "anticipated",
                "url":             url,
            })

    # Implementing acts (EU AI Act style)
    for ia in baseline.get("implementing_acts_status", []):
        if not isinstance(ia, dict):
            continue
        ia_title  = ia.get("title", "")
        ia_status = ia.get("status", "")
        # Try to extract a date from status text
        d = None
        m = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s+(\d{4})', ia_status, re.I)
        if m:
            d = _parse_date(f"{m.group(1)} {m.group(2)}")
        m2 = re.search(r'(\d{4})', ia_status)
        if not d and m2:
            d = _parse_date(m2.group(1))
        if d:
            events.append({
                "date":            d,
                "event":           ia_title,
                "event_type":      "implementing_act",
                "regulation_id":   bid,
                "regulation_name": name,
                "jurisdiction":    jur,
                "status":          "confirmed" if d <= TODAY else "anticipated",
                "url":             url,
            })

    return events


# ── Live document event extraction ────────────────────────────────────────────

def extract_document_events(documents: List[Dict]) -> List[Dict]:
    """Convert summarised documents to timeline events."""
    events = []
    for doc in documents:
        doc_id = doc.get("id", "")
        title  = doc.get("title", "")
        jur    = doc.get("jurisdiction", "")
        status = (doc.get("status", "") or "").lower()
        url    = doc.get("url", "")
        date_s = doc.get("published_date") or doc.get("fetched_at")
        d      = _parse_date(date_s[:10] if date_s else None) if date_s else None
        if not d:
            continue

        # Map status to event type
        etype = "final"
        for pattern, etype_val in STATUS_TO_EVENT_TYPE.items():
            if pattern in status:
                etype = etype_val
                break

        # Only include docs with summaries (they've been AI-analysed)
        if doc.get("plain_english"):
            events.append({
                "date":            d,
                "event":           title[:80],
                "event_type":      etype,
                "regulation_id":   doc_id,
                "regulation_name": title[:40],
                "jurisdiction":    jur,
                "status":          "confirmed",
                "url":             url,
                "urgency":         doc.get("urgency"),
                "plain_english":   (doc.get("plain_english") or "")[:200],
            })
    return events


# ── Horizon event extraction ──────────────────────────────────────────────────

def extract_horizon_events() -> List[Dict]:
    """Pull anticipated future events from the regulatory_horizon table."""
    try:
        from utils.db import get_horizon_items
        items = get_horizon_items(days_ahead=730, limit=200)
    except Exception as e:
        log.debug("Could not load horizon items: %s", e)
        return []

    events = []
    for item in items:
        if item.get("dismissed"):
            continue
        ant = item.get("anticipated_date")
        d   = _parse_date(str(ant)[:10] if ant else None)
        if not d or d < TODAY:
            continue

        stage = item.get("stage", "planned")
        etype = {
            "proposed": "proposed",
            "final":    "final",
            "hearing":  "guidance",
            "enacted":  "effective",
        }.get(stage, "anticipated")

        events.append({
            "date":            d,
            "event":           item.get("title", "")[:80],
            "event_type":      etype,
            "regulation_id":   item.get("id", ""),
            "regulation_name": item.get("title", "")[:40],
            "jurisdiction":    item.get("jurisdiction", ""),
            "status":          "anticipated",
            "url":             item.get("url", ""),
            "stage":           stage,
            "source":          item.get("source", ""),
        })
    return events


# ── Timeline Agent ────────────────────────────────────────────────────────────

class TimelineAgent:

    def get_timeline(self,
                     jurisdiction:  Optional[str]   = None,
                     include_docs:  bool             = True,
                     include_horizon: bool           = True,
                     years_back:    int              = 10,
                     years_ahead:   int              = 3,
                     ) -> Dict[str, Any]:
        """
        Build and return the unified regulatory timeline.

        Returns:
          {
            events:       List[event dicts], sorted chronologically
            jurisdictions: unique jurisdictions present
            event_types:   unique event types present
            date_range:    {min, max}
            total:         int
          }
        """
        all_events: List[Dict] = []
        cutoff_past   = f"{date.today().year - years_back}-01-01"
        cutoff_future = f"{date.today().year + years_ahead}-12-31"

        # 1. Baseline milestones
        if BASELINES_DIR.exists():
            for path in sorted(BASELINES_DIR.glob("*.json")):
                if path.name == "index.json":
                    continue
                try:
                    b = json.loads(path.read_text())
                    all_events.extend(extract_baseline_events(b))
                except Exception as e:
                    log.debug("Baseline event error %s: %s", path.name, e)

        # 2. Live documents
        if include_docs:
            try:
                from utils.db import get_recent_summaries
                docs = get_recent_summaries(days=years_back * 365)
                all_events.extend(extract_document_events(docs))
            except Exception as e:
                log.debug("Document event error: %s", e)

        # 3. Horizon items
        if include_horizon:
            all_events.extend(extract_horizon_events())

        # Filter by jurisdiction
        if jurisdiction:
            all_events = [e for e in all_events
                          if e.get("jurisdiction", "").upper() == jurisdiction.upper()]

        # Filter by date range
        all_events = [
            e for e in all_events
            if cutoff_past <= (e.get("date") or "") <= cutoff_future
        ]

        # Deduplicate by (regulation_id, event_type, date)
        seen = set()
        unique = []
        for e in all_events:
            key = (e.get("regulation_id"), e.get("event_type"), e.get("date"))
            if key not in seen:
                seen.add(key)
                unique.append(e)

        # Sort chronologically
        unique.sort(key=lambda e: e.get("date", "9999"))

        # Summarise
        jurisdictions = sorted(set(e.get("jurisdiction", "") for e in unique if e.get("jurisdiction")))
        event_types   = sorted(set(e.get("event_type", "") for e in unique if e.get("event_type")))
        dates = [e["date"] for e in unique if e.get("date")]

        return {
            "events":        unique,
            "jurisdictions": jurisdictions,
            "event_types":   event_types,
            "event_type_config": EVENT_TYPES,
            "date_range":    {"min": min(dates, default=""), "max": max(dates, default="")},
            "total":         len(unique),
        }
