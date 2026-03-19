"""
ARIS — Horizon Agent

Monitors forward-looking regulatory calendars to surface regulations that are
PLANNED or ADVANCING but not yet published — giving weeks or months of
preparation time rather than reaction time.

Four source tracks, all free and public:

1. UNIFIED REGULATORY AGENDA (reginfo.gov)
   Published twice per year by OMB, lists every planned US federal rulemaking
   with the responsible agency, rule title, anticipated publication stage
   (pre-rule / proposed / final rule), and anticipated date.
   No API key required.

2. CONGRESS.GOV HEARING SCHEDULES
   Uses the existing Congress.gov API key to fetch committee hearing schedules.
   Bills with upcoming markup hearings are significantly more likely to advance.
   Filters for AI-relevant bills already in the document DB or matching keywords.

3. EU COMMISSION WORK PROGRAMME
   Annual document listing all planned EU legislative initiatives. Fetched once
   per quarter from the Commission website. Parsed for AI-relevant entries.
   No API key required.

4. UK PARLIAMENT UPCOMING BUSINESS
   The whatson.parliament.uk API provides upcoming bill stage dates.
   Uses the existing Parliament Bills API (no key required).

All horizon items are:
  - Scored with the existing keyword_score() filter before storage
  - Stored in the regulatory_horizon table (not documents table)
  - Assigned a stage: planned | pre-rule | proposed | hearing | final | enacted
  - Given an anticipated_date for the timeline view
  - Never sent to Claude — keyword scoring is sufficient

Design:
  - Fails gracefully per source — one source error never blocks others
  - Deduplicates by (source, external_id) — safe to run repeatedly
  - Respects HTTP cache to avoid hammering government APIs
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from utils.cache import http_get, http_get_text, keyword_score, is_ai_relevant, get_logger
from config.settings import CONGRESS_GOV_KEY, CONGRESS_BASE, AI_KEYWORDS

log = get_logger("aris.horizon")


# Module-level re-exports so tests can patch them cleanly
def upsert_horizon_item(item: dict) -> bool:
    from utils.db import upsert_horizon_item as _fn
    return _fn(item)


def get_horizon_items(**kwargs):
    from utils.db import get_horizon_items as _fn
    return _fn(**kwargs)

# ── Stage vocabulary ──────────────────────────────────────────────────────────

STAGES = {
    "planned":  "Planned",
    "pre-rule": "Pre-Rule",
    "proposed": "Proposed Rule",
    "hearing":  "Hearing Scheduled",
    "final":    "Final Rule Pending",
    "enacted":  "Enacted",
}

# Minimum keyword score to store a horizon item
MIN_SCORE = 0.15


# ── Horizon Agent ─────────────────────────────────────────────────────────────

class HorizonAgent:
    """
    Fetches and stores forward-looking regulatory horizon items.
    """

    def run(self, days_ahead: int = 365) -> Dict[str, int]:
        """
        Fetch horizon items from all sources.
        Returns {source: new_items_count} for each source attempted.
        """
        counts: Dict[str, int] = {}

        for name, method in [
            ("unified_agenda",      self._fetch_unified_agenda),
            ("congress_hearings",   self._fetch_congress_hearings),
            ("eu_work_programme",   self._fetch_eu_work_programme),
            ("uk_upcoming",         self._fetch_uk_upcoming),
        ]:
            try:
                items = method(days_ahead=days_ahead)
                saved = self._save_items(items)
                counts[name] = saved
                if items:
                    log.info("Horizon %s: %d fetched, %d new", name, len(items), saved)
            except Exception as e:
                log.warning("Horizon source %s failed: %s", name, e)
                counts[name] = 0

        return counts

    # ── Source 1: Unified Regulatory Agenda ──────────────────────────────────

    def _fetch_unified_agenda(self, days_ahead: int = 365) -> List[Dict]:
        """
        Fetch from the Unified Regulatory Agenda XML feed at reginfo.gov.
        The agenda is published twice per year. We parse the XML for AI-relevant
        rulemakings and extract their anticipated action dates.
        """
        items = []

        # The agenda XML is large; use the search endpoint instead
        # reginfo.gov provides a JSON search API for agenda entries
        url = "https://www.reginfo.gov/public/do/XMLViewPublishedDocsPublic"
        params = {
            "operation": "MAIN",
            "type":      "UNIFIED",
            "publish_date": "current",
        }

        try:
            # Try the lighter-weight search endpoint first
            search_url = "https://www.reginfo.gov/public/do/eAgendaMain"
            # Fetch the agency-filtered search for AI-related terms
            for keyword in ["artificial intelligence", "machine learning", "automated decision"]:
                search_params = {
                    "operation":       "MAIN",
                    "agenda_term":     keyword,
                    "agenda_status":   "active",
                }
                try:
                    data = http_get(search_url, params=search_params, timeout=15)
                    if isinstance(data, dict):
                        entries = data.get("entries") or data.get("results") or []
                        for entry in entries:
                            item = self._parse_agenda_entry(entry)
                            if item:
                                items.append(item)
                except Exception:
                    pass

        except Exception as e:
            log.debug("Unified Agenda search failed: %s — trying RSS fallback", e)

        # RSS fallback — the agenda publishes an RSS with recent additions
        if not items:
            try:
                rss = http_get_text(
                    "https://www.reginfo.gov/public/do/eAgendaXml?operation=MAIN",
                    timeout=20
                )
                items = self._parse_agenda_rss(rss or "")
            except Exception as e:
                log.debug("Unified Agenda RSS fallback failed: %s", e)

        # Deduplicate by external_id
        seen = set()
        unique = []
        for item in items:
            if item["external_id"] not in seen:
                seen.add(item["external_id"])
                unique.append(item)

        return unique

    def _parse_agenda_entry(self, entry: Dict) -> Optional[Dict]:
        title = (entry.get("title") or entry.get("rule_title") or "").strip()
        if not title:
            return None
        score = keyword_score(title + " " + (entry.get("abstract") or ""))
        if score < MIN_SCORE:
            return None

        eid = entry.get("rin") or entry.get("id") or _make_id("agenda", title)

        # Parse anticipated date
        date_str = (entry.get("anticipated_nprmdate") or
                    entry.get("anticipated_finaldate") or
                    entry.get("next_action_date") or "")
        anticipated = _parse_date(date_str)

        stage_raw = (entry.get("stage") or entry.get("priority") or "").lower()
        stage = "proposed" if "proposed" in stage_raw or "nprm" in stage_raw else \
                "pre-rule"  if "pre" in stage_raw else \
                "final"     if "final" in stage_raw else \
                "planned"

        return {
            "source":         "unified_agenda",
            "external_id":    str(eid),
            "jurisdiction":   "Federal",
            "title":          title,
            "description":    entry.get("abstract") or "",
            "agency":         entry.get("agency_name") or entry.get("agency") or "",
            "stage":          stage,
            "anticipated_date": anticipated,
            "url":            entry.get("url") or "",
            "ai_score":       round(score, 3),
        }

    def _parse_agenda_rss(self, rss_text: str) -> List[Dict]:
        """Parse the Unified Regulatory Agenda RSS feed."""
        items = []
        if not rss_text:
            return items

        # Extract <item> blocks
        item_blocks = re.findall(r"<item>(.*?)</item>", rss_text, re.DOTALL)
        for block in item_blocks:
            title = _xml_text(block, "title")
            desc  = _xml_text(block, "description")
            link  = _xml_text(block, "link")
            if not title:
                continue
            score = keyword_score(title + " " + desc)
            if score < MIN_SCORE:
                continue

            # Try to extract a date from description
            date_match = re.search(r"\b(20\d{2}[-/]\d{1,2}[-/]\d{1,2})\b", desc)
            anticipated = _parse_date(date_match.group(1)) if date_match else None

            items.append({
                "source":         "unified_agenda",
                "external_id":    _make_id("agenda-rss", title),
                "jurisdiction":   "Federal",
                "title":          title,
                "description":    desc,
                "agency":         "",
                "stage":          "planned",
                "anticipated_date": anticipated,
                "url":            link,
                "ai_score":       round(score, 3),
            })

        return items

    # ── Source 2: Congress.gov Hearing Schedules ──────────────────────────────

    def _fetch_congress_hearings(self, days_ahead: int = 90) -> List[Dict]:
        """
        Fetch upcoming committee hearings from Congress.gov API.
        Focus on hearings in the next days_ahead days that involve AI bills.
        """
        if not CONGRESS_GOV_KEY:
            log.debug("Congress.gov key not set — skipping hearing schedules")
            return []

        items  = []
        cutoff = datetime.utcnow() + timedelta(days=days_ahead)
        today  = datetime.utcnow().strftime("%Y-%m-%d")
        future = cutoff.strftime("%Y-%m-%d")

        # Fetch recent committee hearings
        try:
            url    = f"{CONGRESS_BASE}/committee-meeting"
            params = {
                "api_key":   CONGRESS_GOV_KEY,
                "format":    "json",
                "fromDateTime": f"{today}T00:00:00Z",
                "toDateTime":   f"{future}T23:59:59Z",
                "limit":     50,
            }
            data     = http_get(url, params=params, timeout=15)
            meetings = (data or {}).get("committeeMeetings") or []

            for m in meetings:
                title = m.get("title") or ""
                desc  = " ".join([
                    title,
                    m.get("chamber") or "",
                    " ".join(str(b.get("title", "")) for b in (m.get("bills") or [])),
                ])
                score = keyword_score(desc)
                if score < MIN_SCORE:
                    continue

                date_str = m.get("date") or m.get("meetingDateTime") or ""
                anticipated = _parse_date(date_str)
                committee   = (m.get("committee") or {}).get("name") or ""
                chamber     = m.get("chamber") or ""

                # Build bill list for title
                bills = m.get("bills") or []
                bill_titles = [b.get("number", "") for b in bills[:3] if b.get("number")]
                full_title  = title or (
                    f"Committee Hearing: {', '.join(bill_titles)}" if bill_titles
                    else "AI-related Committee Hearing"
                )

                items.append({
                    "source":         "congress_hearings",
                    "external_id":    _make_id("hearing", str(m.get("eventId") or full_title)),
                    "jurisdiction":   "Federal",
                    "title":          full_title,
                    "description":    f"{chamber} — {committee}",
                    "agency":         committee,
                    "stage":          "hearing",
                    "anticipated_date": anticipated,
                    "url":            m.get("url") or "",
                    "ai_score":       round(score, 3),
                })

        except Exception as e:
            log.debug("Congress hearings fetch failed: %s", e)

        return items

    # ── Source 3: EU Commission Work Programme ────────────────────────────────

    def _fetch_eu_work_programme(self, days_ahead: int = 365) -> List[Dict]:
        """
        Fetch the EU Commission Work Programme — annual list of planned
        legislative initiatives. Parsed for AI-relevant entries.
        """
        items = []

        # The Commission publishes the Work Programme as a structured page
        # Try the EUR-Lex 'in preparation' feed for AI-related items
        try:
            url    = "https://eur-lex.europa.eu/eurlex-content/EN/search/searchResult.do"
            params = {
                "type":    "quick",
                "qid":     "1",
                "query":   "artificial intelligence",
                "SUBDOM_INIT": "LEGISLATION_IN_FORCE",
                "DTS_DOM":     "LEGISLATION",
                "DTS_SUBDOM":  "LEGISLATION_IN_PREPARATION",
                "format":      "json",
            }
            # Use the EUR-Lex SPARQL endpoint for 'in preparation' documents
            sparql_url = "https://publications.europa.eu/webapi/rdf/sparql"
            sparql = """
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?work ?title ?date WHERE {
  ?work cdm:work_is_about_concept_eurovoc <http://eurovoc.europa.eu/2068> .
  ?expr cdm:expression_belongs_to_work ?work .
  ?expr cdm:expression_title ?title .
  OPTIONAL { ?work cdm:work_date_document ?date }
  FILTER(LANG(?title) = 'en')
  FILTER(?date >= "2024-01-01"^^xsd:date)
}
LIMIT 30
"""
            data = http_get(sparql_url, params={
                "query":  sparql,
                "format": "application/json",
            }, timeout=20)

            bindings = ((data or {}).get("results") or {}).get("bindings") or []
            for b in bindings:
                title = (b.get("title") or {}).get("value") or ""
                date  = (b.get("date")  or {}).get("value") or ""
                score = keyword_score(title)
                if score < MIN_SCORE:
                    continue
                items.append({
                    "source":         "eu_work_programme",
                    "external_id":    _make_id("eu-prep", title),
                    "jurisdiction":   "EU",
                    "title":          title,
                    "description":    "EU legislative initiative in preparation",
                    "agency":         "European Commission",
                    "stage":          "planned",
                    "anticipated_date": _parse_date(date),
                    "url":            (b.get("work") or {}).get("value") or "",
                    "ai_score":       round(score, 3),
                })

        except Exception as e:
            log.debug("EU Work Programme SPARQL failed: %s", e)

        # Fallback: EU AI Office news RSS
        if not items:
            try:
                rss = http_get_text(
                    "https://digital-strategy.ec.europa.eu/en/rss.xml",
                    timeout=15
                )
                items = self._parse_eu_rss(rss or "")
            except Exception as e:
                log.debug("EU RSS fallback failed: %s", e)

        return items

    def _parse_eu_rss(self, rss_text: str) -> List[Dict]:
        items = []
        if not rss_text:
            return items
        for block in re.findall(r"<item>(.*?)</item>", rss_text, re.DOTALL):
            title = _xml_text(block, "title")
            desc  = _xml_text(block, "description")
            link  = _xml_text(block, "link")
            pubdate = _xml_text(block, "pubDate")
            if not title:
                continue
            score = keyword_score(title + " " + desc)
            if score < MIN_SCORE:
                continue
            items.append({
                "source":         "eu_work_programme",
                "external_id":    _make_id("eu-rss", title),
                "jurisdiction":   "EU",
                "title":          title,
                "description":    desc[:400],
                "agency":         "European Commission",
                "stage":          "planned",
                "anticipated_date": _parse_date(pubdate),
                "url":            link,
                "ai_score":       round(score, 3),
            })
        return items

    # ── Source 4: UK Parliament Upcoming Business ─────────────────────────────

    def _fetch_uk_upcoming(self, days_ahead: int = 90) -> List[Dict]:
        """
        Fetch upcoming UK Parliament bill stage dates.
        Uses the whatson.parliament.uk API — no key required.
        """
        items   = []
        today   = datetime.utcnow().strftime("%Y-%m-%d")
        future  = (datetime.utcnow() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

        # Try whatson API for upcoming bill events
        try:
            url    = "https://whatson.parliament.uk/api/v1/Events.json"
            params = {
                "StartDate":  today,
                "EndDate":    future,
                "EventType":  "Bill",
                "take":       50,
            }
            data   = http_get(url, params=params, timeout=15)
            events = (data or []) if isinstance(data, list) else (data or {}).get("Results") or []

            for ev in events:
                title = ev.get("Description") or ev.get("Title") or ""
                date  = ev.get("StartDateTime") or ev.get("Date") or ""
                desc  = " ".join(filter(None, [
                    ev.get("SubCategory") or "",
                    ev.get("House") or "",
                    ev.get("Note") or "",
                ]))
                score = keyword_score(title + " " + desc)
                if score < MIN_SCORE:
                    continue

                items.append({
                    "source":         "uk_upcoming",
                    "external_id":    _make_id("uk-event", str(ev.get("Id") or title)),
                    "jurisdiction":   "GB",
                    "title":          title,
                    "description":    desc,
                    "agency":         ev.get("House") or "UK Parliament",
                    "stage":          "hearing",
                    "anticipated_date": _parse_date(date),
                    "url":            ev.get("Url") or "",
                    "ai_score":       round(score, 3),
                })

        except Exception as e:
            log.debug("UK whatson API failed: %s", e)

        # Fallback: UK Parliament Bills RSS
        if not items:
            try:
                rss = http_get_text(
                    "https://bills.parliament.uk/rss/allbills.rss",
                    timeout=15
                )
                for block in re.findall(r"<item>(.*?)</item>", rss or "", re.DOTALL):
                    title   = _xml_text(block, "title")
                    desc    = _xml_text(block, "description")
                    link    = _xml_text(block, "link")
                    pubdate = _xml_text(block, "pubDate")
                    if not title:
                        continue
                    score = keyword_score(title + " " + desc)
                    if score < MIN_SCORE:
                        continue
                    items.append({
                        "source":         "uk_upcoming",
                        "external_id":    _make_id("uk-bills-rss", title),
                        "jurisdiction":   "GB",
                        "title":          title,
                        "description":    desc[:400],
                        "agency":         "UK Parliament",
                        "stage":          "planned",
                        "anticipated_date": _parse_date(pubdate),
                        "url":            link,
                        "ai_score":       round(score, 3),
                    })
            except Exception as e:
                log.debug("UK Parliament RSS fallback failed: %s", e)

        return items

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save_items(self, items: List[Dict]) -> int:
        """Save horizon items, skipping duplicates. Returns count of new items."""
        if not items:
            return 0
        try:
            new_count = 0
            for item in items:
                if upsert_horizon_item(item):
                    new_count += 1
            return new_count
        except Exception as e:
            log.error("Error saving horizon items: %s", e)
            return 0

    # ── Public query helpers ──────────────────────────────────────────────────

    def get_upcoming(self,
                     days_ahead: int = 365,
                     jurisdiction: Optional[str] = None,
                     stage: Optional[str] = None,
                     limit: int = 100) -> List[Dict]:
        """Return upcoming horizon items from the database."""
        try:
            return get_horizon_items(
                days_ahead   = days_ahead,
                jurisdiction = jurisdiction,
                stage        = stage,
                limit        = limit,
            )
        except Exception as e:
            log.error("Error fetching horizon items: %s", e)
            return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _xml_text(block: str, tag: str) -> str:
    """Extract text content of first XML element with given tag."""
    m = re.search(rf"<{tag}(?:\s[^>]*)?>(<!\[CDATA\[)?(.*?)(\]\]>)?</{tag}>",
                  block, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(2).strip()
    return ""


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    s = str(s).strip()
    for fmt in (
        "%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT",
        "%B %Y", "%b %Y",
        "%Y/%m",
    ):
        try:
            dt = datetime.strptime(s[:len(fmt) + 5].strip(), fmt)
            return dt.replace(tzinfo=None)
        except ValueError:
            continue
    # Try year-only
    m = re.search(r"\b(20\d{2})\b", s)
    if m:
        try:
            return datetime(int(m.group(1)), 6, 1)   # mid-year estimate
        except Exception:
            pass
    return None


def _make_id(prefix: str, text: str) -> str:
    """Generate a stable short ID from prefix + text."""
    h = hashlib.md5(text.lower().encode()).hexdigest()[:10]
    return f"{prefix}-{h}"
