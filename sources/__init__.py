# SPDX-License-Identifier: Elastic-2.0
# Copyright (c) 2026 Mitch Kwiatkowski
# ARIS � Automated Regulatory Intelligence System
# Licensed under the Elastic License 2.0. See LICENSE in the project root.
"""
ARIS — International sources package.

Active agents:
  EU  — European Union (EUR-Lex SPARQL + EU AI Office RSS)
  GB  — United Kingdom (Parliament Bills API + legislation.gov.uk + GOV.UK)
  CA  — Canada (OpenParliament + Canada Gazette RSS + ISED feed)

Stub agents (activate by adding code to ENABLED_INTERNATIONAL in jurisdictions.py):
  JP  — Japan (METI RSS + pinned docs)
  CN  — China (pinned docs only — no public API)
  AU  — Australia (pinned docs only)
"""

from sources.international.eu     import EUAgent
from sources.international.uk     import UKAgent
from sources.international.canada import CanadaAgent
from sources.international.stubs  import JapanAgent, ChinaAgent, AustraliaAgent

__all__ = [
    "EUAgent",
    "CanadaAgent",
    "UKAgent",
    "JapanAgent",
    "ChinaAgent",
    "AustraliaAgent",
]
