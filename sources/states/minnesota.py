# SPDX-License-Identifier: Elastic-2.0
# Copyright (c) 2026 Mitch Kwiatkowski
# ARIS � Automated Regulatory Intelligence System
# Licensed under the Elastic License 2.0. See LICENSE in the project root.
"""
ARIS — Minnesota State Agent

Minnesota is one of the most active states pursuing comprehensive AI regulation:
  - SF 2995 / HF 4397 (2024) — Minnesota AI Act, narrowly failed; reintroduced 2025
  - Follows Colorado-style risk-based framework with impact assessments
  - SF 3244 (2024) — deepfakes in elections
  - Active 2025-2026 pipeline: algorithmic accountability, employment AI, chatbots

Sources:
  1. LegiScan API (primary — MN has biennial sessions, 2025 session active)
  2. Minnesota Legislature RSS
     https://www.revisor.mn.gov/bills/status_search.php — no public API
     LegiScan covers MN comprehensively.
"""

from sources.state_agent_base import StateAgentBase


class MinnesotaAgent(StateAgentBase):
    """Minnesota AI regulation and privacy legislation monitor."""

    state_code     = "MN"
    state_name     = "Minnesota"
    legiscan_state = "MN"
