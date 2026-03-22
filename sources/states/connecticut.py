# SPDX-License-Identifier: Elastic-2.0
# Copyright (c) 2026 Mitch Kwiatkowski
# ARIS � Automated Regulatory Intelligence System
# Licensed under the Elastic License 2.0. See LICENSE in the project root.
"""
ARIS — Connecticut State Agent

Connecticut is highly active on comprehensive AI regulation:
  - SB 2 (2023, 2024, 2025) — Connecticut AI Act, passed Senate 2025 but did not
    reach House floor; one of the most comprehensive state AI bills attempted
  - CT Data Privacy Act (CTDPA, 2022) — in force, includes automated decisions
  - PA 24-5 (2024) — AI in hiring disclosures
  - Active 2026 pipeline: SB 2 successor expected

Sources:
  1. LegiScan API (primary)
  2. Connecticut General Assembly — no public API; LegiScan covers CT.
"""

from sources.state_agent_base import StateAgentBase


class ConnecticutAgent(StateAgentBase):
    """Connecticut AI regulation and privacy legislation monitor."""

    state_code     = "CT"
    state_name     = "Connecticut"
    legiscan_state = "CT"
