# SPDX-License-Identifier: Elastic-2.0
# Copyright (c) 2026 Mitch Kwiatkowski
# ARIS — Automated Regulatory Intelligence System
# Licensed under the Elastic License 2.0. See LICENSE in the project root.
"""
ARIS â€” Jurisdiction Registry

Single config file controlling which US states and international
jurisdictions are monitored. Edit this file to turn regions on or off.

Jurisdictions are grouped into three independent tracks:
  1. US Federal   â€” always active (FederalAgent handles this)
  2. US States    â€” controlled by ENABLED_US_STATES
  3. International â€” controlled by ENABLED_INTERNATIONAL
"""

# â”€â”€ US States â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Each entry must have a corresponding class in sources/states/<code>.py

ENABLED_US_STATES = [
    # Tier 1 â€” fully implemented with native feeds
    "PA",    # Pennsylvania  â€” LegiScan + palegis.us ZIP feed (hourly)
    "CA",    # California    â€” LegiScan + CA Legislature API
    "CO",    # Colorado      â€” LegiScan + leg.colorado.gov API; CO AI Act effective Jun 2026
    "IL",    # Illinois      â€” LegiScan + ILGA RSS feeds; AIPA enacted
    "TX",    # Texas         â€” LegiScan + TLO RSS; TRAIGA enacted 2025
    "WA",    # Washington    â€” LegiScan + WSL web services; MHMD Act, active AI pipeline
    "NY",    # New York      â€” LegiScan + NY Senate API; RAISE Act pending

    # Tier 2 â€” LegiScan + supplemental native feeds
    "FL",    # Florida       â€” LegiScan + FL Senate API; SB 262, govt AI, deepfakes
    "MN",    # Minnesota     â€” LegiScan + MN Senate RSS; SF 2995 (comprehensive AI) reintroducing
    "CT",    # Connecticut   â€” LegiScan; SB 2 (comprehensive AI) reintroducing 2026

    # Tier 3 â€” LegiScan only (comprehensive coverage)
    "VA",    # Virginia      â€” HB 2094 vetoed 2025, reintroducing 2026
    "NJ",    # New Jersey    â€” NJ Data Privacy Law, AI employment bills
    "MA",    # Massachusetts â€” AI employment bills, Data Privacy Act advancing
    "OR",    # Oregon        â€” Consumer Privacy Act in force, AI deepfake bill
    "MD",    # Maryland      â€” Online Data Privacy Act, AI employment bills
    "GA",    # Georgia       â€” AI employment disclosure, government AI
    "AZ",    # Arizona       â€” Chatbot regulation, deepfake disclosure
    "NC",    # North Carolina â€” AI Employment Act, state government AI
]

# â”€â”€ International Jurisdictions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Each entry must have a corresponding class in sources/international/<code>.py

ENABLED_INTERNATIONAL = [
    # Fully implemented with live feeds
    "EU",    # European Union â€” EUR-Lex SPARQL + EU AI Office RSS
    "GB",    # United Kingdom â€” Parliament Bills + legislation.gov.uk + GOV.UK
    "CA",    # Canada         â€” OpenParliament + Canada Gazette + ISED feed
    "SG",    # Singapore      â€” PDPC RSS + IMDA RSS + pinned framework docs
    "IN",    # India          â€” PIB RSS (MEITY) + DPDP Act + IndiaAI Mission
    "BR",    # Brazil         â€” ANPD RSS + Senate RSS + LGPD + AI Bill PL2338

    # Pinned docs + available feeds (translation via Claude)
    "JP",    # Japan          â€” METI English RSS + pinned AI governance docs
    "KR",    # South Korea    â€” MSIT press releases + PIPA/AI Act pinned docs
    "AU",    # Australia      â€” Voluntary AI Safety Standard + Federal Register
    # "CN",  # China          â€” Pinned docs only (no public CAC API)
]

# â”€â”€ Module path maps â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Maps jurisdiction code â†’ importable Python module path.
# Used by the orchestrator for dynamic class loading.

US_STATE_MODULE_MAP = {
    "PA": "sources.states.pennsylvania",
    "CA": "sources.states.california",
    "CO": "sources.states.colorado",
    "IL": "sources.states.illinois",
    "TX": "sources.states.texas",
    "WA": "sources.states.washington",
    "NY": "sources.states.new_york",
    "FL": "sources.states.florida",
    "MN": "sources.states.minnesota",
    "CT": "sources.states.connecticut",
    "VA": "sources.states.virginia",
    "NJ": "sources.states.new_jersey",
    "MA": "sources.states.massachusetts",
    "OR": "sources.states.oregon",
    "MD": "sources.states.maryland",
    "GA": "sources.states.georgia",
    "AZ": "sources.states.arizona",
    "NC": "sources.states.north_carolina",
}

INTERNATIONAL_MODULE_MAP = {
    "EU": "sources.international.eu",
    "GB": "sources.international.uk",
    "CA": "sources.international.canada",
    "SG": "sources.international.singapore",
    "IN": "sources.international.india",
    "BR": "sources.international.brazil",
    "JP": "sources.international.stubs",
    "KR": "sources.international.south_korea",
    "AU": "sources.international.stubs",
    "CN": "sources.international.stubs",
}

# â”€â”€ Class name map â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# When a module contains multiple classes (e.g. stubs.py), specify which
# class to instantiate. If omitted, orchestrator picks the first
# InternationalAgentBase or StateAgentBase subclass it finds.

INTERNATIONAL_CLASS_MAP = {
    "JP": "JapanAgent",
    "CN": "ChinaAgent",
    "AU": "AustraliaAgent",
}

# â”€â”€ Region display labels â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Used by the reporter to group jurisdictions into sections.

REGION_LABELS = {
    "Federal":       "ðŸ›  US Federal",
    "PA":            "ðŸ¢  Pennsylvania (US)",
    "VA":            "ðŸ¢  Virginia (US)",
    "NY":            "ðŸ¢  New York (US)",
    "CA":            "ðŸ¢  California (US)",   # note: state code, not Canada
    "TX":            "ðŸ¢  Texas (US)",
    "WA":            "ðŸ¢  Washington (US)",
    "FL":            "ðŸ¢  Florida (US)",
    "MN":            "ðŸ¢  Minnesota (US)",
    "CT":            "ðŸ¢  Connecticut (US)",
    "NJ":            "ðŸ¢  New Jersey (US)",
    "MA":            "ðŸ¢  Massachusetts (US)",
    "OR":            "ðŸ¢  Oregon (US)",
    "MD":            "ðŸ¢  Maryland (US)",
    "GA":            "ðŸ¢  Georgia (US)",
    "AZ":            "ðŸ¢  Arizona (US)",
    "NC":            "ðŸ¢  North Carolina (US)",
    "EU":            "ðŸ‡ªðŸ‡º  European Union",
    "GB":            "ðŸ‡¬ðŸ‡§  United Kingdom",
    "CA_INTL":       "ðŸ‡¨ðŸ‡¦  Canada",            # disambiguated in reporter
    "JP":            "ðŸ‡¯ðŸ‡µ  Japan",
    "CN":            "ðŸ‡¨ðŸ‡³  China",
    "AU":            "ðŸ‡¦ðŸ‡º  Australia",
    "SG":            "ðŸ‡¸ðŸ‡¬  Singapore",
    "KR":            "ðŸ‡°ðŸ‡·  South Korea",
    "IN":            "ðŸ‡®ðŸ‡³  India",
    "BR":            "ðŸ‡§ðŸ‡·  Brazil",
    "SG":            "ðŸ‡¸ðŸ‡¬  Singapore",
    "KR":            "ðŸ‡°ðŸ‡·  South Korea",
}

# â”€â”€ LegiScan state code mapping (US states only) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
LEGISCAN_STATE_MAP = {
    "PA": "PA", "CA": "CA", "CO": "CO", "IL": "IL",
    "TX": "TX", "WA": "WA", "NY": "NY", "FL": "FL", "MN": "MN",
    "CT": "CT", "VA": "VA", "NJ": "NJ", "MA": "MA", "OR": "OR",
    "MD": "MD", "GA": "GA", "AZ": "AZ", "NC": "NC",
    # Note: "CA" here means California state; Canada international uses separate map
}

# â”€â”€ Legacy alias (keeps old imports from states.py working) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
ENABLED_STATES  = ENABLED_US_STATES
STATE_MODULE_MAP = US_STATE_MODULE_MAP
