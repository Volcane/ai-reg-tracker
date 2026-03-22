# SPDX-License-Identifier: Elastic-2.0
# Copyright (c) 2026 Mitch Kwiatkowski
# ARIS � Automated Regulatory Intelligence System
# Licensed under the Elastic License 2.0. See LICENSE in the project root.
"""
ARIS — North Carolina Agent

North Carolina is advancing AI governance legislation:
  - AI use disclosure for government agencies
  - Employment AI bills
  - Data privacy legislation (NC Privacy Act advancing)
  - Active 2025-2026 pipeline

Sources:
  1. LegiScan API (primary — NC has biennial sessions)
"""

from sources.state_agent_base import StateAgentBase


class NorthCarolinaAgent(StateAgentBase):
    """North Carolina AI regulation and privacy legislation monitor."""

    state_code     = "NC"
    state_name     = "North Carolina"
    legiscan_state = "NC"
