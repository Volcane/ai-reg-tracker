# SPDX-License-Identifier: Elastic-2.0
# Copyright (c) 2026 Mitch Kwiatkowski
# ARIS � Automated Regulatory Intelligence System
# Licensed under the Elastic License 2.0. See LICENSE in the project root.
"""
ARIS — Jurisdiction Registry

Single config file controlling which US states and international
jurisdictions are monitored. Edit this file to turn regions on or off.

Jurisdictions are grouped into three independent tracks:
  1. US Federal   — always active (FederalAgent handles this)
  2. US States    — controlled by ENABLED_US_STATES
  3. International — controlled by ENABLED_INTERNATIONAL
"""

# ── US States ─────────────────────────────────────────────────────────────────
# Each entry must have a corresponding class in sources/states/<code>.py

ENABLED_US_STATES = [
    "PA",    # Pennsylvania — LegiScan + palegis.us ZIP feed (hourly)
    "CA",    # California   — most active AI regulation state; LegiScan + CA Legislature API
    "CO",    # Colorado     — Colorado AI Act (SB 24-205, effective Jun 2026); LegiScan + leg.colorado.gov API
    "IL",    # Illinois     — AIPA enacted, BIPA AI-relevant; LegiScan + ILGA RSS feeds
    # "VA",  # Virginia     — LegiScan only (no native feed); enable by uncommenting
    # "NY",  # New York     — add sources/states/new_york.py to enable
    # "TX",  # Texas        — add sources/states/texas.py to enable
    # "FL",  # Florida      — add sources/states/florida.py to enable
    # "WA",  # Washington   — add sources/states/washington.py to enable
]

# ── International Jurisdictions ───────────────────────────────────────────────
# Each entry must have a corresponding class in sources/international/<code>.py

ENABLED_INTERNATIONAL = [
    "EU",    # European Union — EUR-Lex SPARQL + EU AI Office RSS
    "GB",    # United Kingdom — Parliament Bills + legislation.gov.uk + GOV.UK
    "CA",    # Canada         — OpenParliament + Canada Gazette + ISED feed
    # "JP",  # Japan          — METI RSS + pinned docs (stub ready)
    # "CN",  # China          — Pinned docs only (no public API; stub ready)
    # "AU",  # Australia      — Pinned docs (stub ready)
    # "SG",  # Singapore      — add sources/international/singapore.py to enable
    # "KR",  # South Korea    — add sources/international/south_korea.py to enable
    # "IN",  # India          — add sources/international/india.py to enable
    # "BR",  # Brazil         — add sources/international/brazil.py to enable
]

# ── Module path maps ──────────────────────────────────────────────────────────
# Maps jurisdiction code → importable Python module path.
# Used by the orchestrator for dynamic class loading.

US_STATE_MODULE_MAP = {
    "PA": "sources.states.pennsylvania",
    "VA": "sources.states.virginia",
    "NY": "sources.states.new_york",
    "CA": "sources.states.california",
    "TX": "sources.states.texas",
    "IL": "sources.states.illinois",
    "CO": "sources.states.colorado",
    "FL": "sources.states.florida",
    "WA": "sources.states.washington",
}

INTERNATIONAL_MODULE_MAP = {
    "EU": "sources.international.eu",
    "GB": "sources.international.uk",
    "CA": "sources.international.canada",
    "JP": "sources.international.stubs",
    "CN": "sources.international.stubs",
    "AU": "sources.international.stubs",
    "SG": "sources.international.singapore",
    "KR": "sources.international.south_korea",
    "IN": "sources.international.india",
    "BR": "sources.international.brazil",
}

# ── Class name map ────────────────────────────────────────────────────────────
# When a module contains multiple classes (e.g. stubs.py), specify which
# class to instantiate. If omitted, orchestrator picks the first
# InternationalAgentBase or StateAgentBase subclass it finds.

INTERNATIONAL_CLASS_MAP = {
    "JP": "JapanAgent",
    "CN": "ChinaAgent",
    "AU": "AustraliaAgent",
}

# ── Region display labels ─────────────────────────────────────────────────────
# Used by the reporter to group jurisdictions into sections.

REGION_LABELS = {
    "Federal":       "�  US Federal",
    "PA":            "�  Pennsylvania (US)",
    "VA":            "�  Virginia (US)",
    "NY":            "�  New York (US)",
    "CA":            "�  California (US)",   # note: state code, not Canada
    "TX":            "�  Texas (US)",
    "EU":            "🇪🇺  European Union",
    "GB":            "🇬🇧  United Kingdom",
    "CA_INTL":       "🇨🇦  Canada",            # disambiguated in reporter
    "JP":            "🇯🇵  Japan",
    "CN":            "🇨🇳  China",
    "AU":            "🇦🇺  Australia",
    "SG":            "🇸🇬  Singapore",
    "KR":            "🇰🇷  South Korea",
    "IN":            "🇮🇳  India",
    "BR":            "🇧🇷  Brazil",
}

# ── LegiScan state code mapping (US states only) ──────────────────────────────
LEGISCAN_STATE_MAP = {
    "PA": "PA", "CA": "CA", "CO": "CO", "IL": "IL",
    "VA": "VA", "NY": "NY", "TX": "TX", "FL": "FL", "WA": "WA",
    # Note: "CA" here means California state; Canada international uses separate map
}

# ── Legacy alias (keeps old imports from states.py working) ──────────────────
ENABLED_STATES  = ENABLED_US_STATES
STATE_MODULE_MAP = US_STATE_MODULE_MAP
