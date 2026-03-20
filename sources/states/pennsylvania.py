"""
ARIS — Pennsylvania State Agent

Extends StateAgentBase with:
  1. LegiScan API (inherited)
  2. PA General Assembly native XML feed (hourly updates, no key needed)
     https://www.palegis.us/data — ZIP archive containing combined bill history XML
     Updated as of February 2026: single ZIP per session (House + Senate combined)
"""

from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from typing import List, Dict, Any, Optional

from sources.state_agent_base import StateAgentBase, _parse_date
from config.settings import AI_KEYWORDS
from utils.cache import is_ai_relevant, get_logger

log = get_logger("aris.state.pa")

# PA General Assembly bill history — new unified ZIP format (Feb 2026+)
# Single archive contains both House and Senate bills for the session
def _pa_zip_url(year: int = 2025) -> str:
    return f"https://www.palegis.us/data/bill-history/{year}.zip"


class PennsylvaniaAgent(StateAgentBase):
    """
    Pennsylvania AI regulation and privacy legislation monitor.

    Data sources:
      - LegiScan API  (keyword search, full text)
      - PA Legis XML  (combined bill history ZIP, updated hourly, no key required)
    """

    state_code     = "PA"
    state_name     = "Pennsylvania"
    legiscan_state = "PA"

    # ── Native feed: PA General Assembly ZIP/XML ──────────────────────────────

    def get_native_feed_url(self) -> Optional[str]:
        # We override fetch_native() directly
        return None

    def fetch_native(self) -> List[Dict[str, Any]]:
        """
        Pull the PA General Assembly combined bill history ZIP and filter for
        AI/privacy-relevant legislation.

        As of February 2026, PA migrated from separate House/Senate XML endpoints
        (legis.state.pa.us/cfdocs/...) to a single ZIP archive on palegis.us.
        The ZIP contains one XML file with all bills for the session.
        """
        import requests
        from datetime import datetime as dt

        year = dt.utcnow().year
        zip_url = _pa_zip_url(year)

        try:
            resp = requests.get(zip_url, timeout=30, headers={
                "User-Agent": "Mozilla/5.0 (compatible; ARIS regulatory monitor)"
            })
            resp.raise_for_status()
        except Exception as e:
            log.warning(
                "PA bill history ZIP fetch failed (%s): %s — LegiScan will cover PA",
                zip_url, e,
            )
            return []

        try:
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                xml_names = [n for n in zf.namelist() if n.lower().endswith(".xml")]
                if not xml_names:
                    log.warning("PA ZIP contained no XML files: %s", zf.namelist())
                    return []
                xml_text = zf.read(xml_names[0]).decode("utf-8", errors="replace")
        except Exception as e:
            log.error("PA ZIP extraction failed: %s", e)
            return []

        results = self._parse_pa_xml(xml_text)
        log.info("PA General Assembly ZIP: %d AI/privacy-relevant bills", len(results))
        return results

    def _parse_pa_xml(self, xml_text: str, chamber: str = "") -> List[Dict[str, Any]]:
        """
        Parse the PA General Assembly combined bill history XML.

        The feed uses <BillHistory> -> <Bill> elements. Chamber is determined
        from the BillBody attribute on each Bill, falling back to number prefix.
        The optional `chamber` argument is accepted for backward compatibility
        but ignored — chamber is auto-detected from the XML.
        """
        results = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            log.error("PA XML parse error: %s", e)
            return []

        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        for bill_el in root.iter(f"{ns}Bill"):
            title = (
                bill_el.get("ShortTitle")
                or bill_el.findtext(f"{ns}ShortTitle")
                or ""
            )
            actions_text = " ".join(
                a.get("Description", "") or a.text or ""
                for a in bill_el.iter(f"{ns}Action")
            )
            combined = f"{title} {actions_text}"

            if not is_ai_relevant(combined):
                continue

            bill_num       = bill_el.get("BillNumber") or bill_el.findtext(f"{ns}BillNumber") or ""
            printer_num    = bill_el.get("PrintersNumber") or ""
            sponsor        = bill_el.get("PrimeSponsor") or bill_el.findtext(f"{ns}PrimeSponsor") or ""
            last_action    = bill_el.get("LastAction") or bill_el.findtext(f"{ns}LastAction") or ""
            last_action_dt = bill_el.get("LastActionDate") or bill_el.findtext(f"{ns}LastActionDate") or ""

            # Detect chamber from attribute, fall back to bill number prefix
            bill_body = bill_el.get("BillBody") or bill_el.get("Chamber") or ""
            if not bill_body:
                bill_body = "H" if str(bill_num).upper().startswith("H") else "S"
            detected_chamber = "House" if bill_body.upper().startswith("H") else "Senate"
            prefix = "HB" if detected_chamber == "House" else "SB"

            doc_id = f"PA-LEGIS-{prefix}{bill_num}"

            results.append({
                "id":             doc_id,
                "source":         "pa_general_assembly",
                "jurisdiction":   "PA",
                "doc_type":       "Bill",
                "title":          title or f"PA {detected_chamber} Bill {bill_num}",
                "url":            self._build_pa_url(detected_chamber, bill_num),
                "published_date": _parse_date(last_action_dt),
                "agency":         f"PA General Assembly — {detected_chamber}",
                "status":         last_action or "Introduced",
                "full_text":      f"{title}. Last action: {last_action}",
                "raw_json": {
                    "bill_number":    bill_num,
                    "printer_number": printer_num,
                    "sponsor":        sponsor,
                    "last_action":    last_action,
                    "chamber":        detected_chamber,
                },
            })

        return results

    @staticmethod
    def _build_pa_url(chamber: str, bill_num: str, printer_num: str = "") -> str:
        """Construct a URL to the bill on the PA General Assembly site.

        Args:
            chamber:     'House' or 'Senate'
            bill_num:    Bill number (numeric string or prefixed e.g. 'HB1925')
            printer_num: Ignored — kept for backward compatibility with existing tests
        """
        if not bill_num:
            return "https://www.palegis.us/legislation/bills/"
        b_type = "H" if chamber == "House" else "S"
        num = re.sub(r"[^0-9]", "", str(bill_num))
        if not num:
            return "https://www.palegis.us/legislation/bills/"
        return (
            f"https://www.palegis.us/legislation/bills/bill-info"
            f"?SessYr=2025&SessInd=0&BillBody={b_type}&BillType=B&BillNum={num}"
        )

    # ── Enrichment ────────────────────────────────────────────────────────────

    def enrich_with_full_text(self, docs: List[Dict]) -> List[Dict]:
        """For LegiScan docs lacking full text, attempt to fetch it."""
        for doc in docs:
            if doc["source"] == "legiscan_pa" and len(doc.get("full_text", "")) < 200:
                bill_id = doc["id"].replace("PA-LS-", "")
                text = self.fetch_bill_text(bill_id)
                if text:
                    doc["full_text"] = text
        return docs

    def fetch_all(self, lookback_days: int = 30, domain: str = "both") -> List[Dict[str, Any]]:
        """Override to add enrichment pass."""
        docs = super().fetch_all(lookback_days, domain=domain)
        docs = self.enrich_with_full_text(docs)
        return docs
