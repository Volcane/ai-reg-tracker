# SPDX-License-Identifier: Elastic-2.0
# Copyright (c) 2026 Mitch Kwiatkowski
# ARIS � Automated Regulatory Intelligence System
# Licensed under the Elastic License 2.0. See LICENSE in the project root.
"""
ARIS — Oregon Agent

Oregon has enacted data privacy and is active on AI:
  - Oregon Consumer Privacy Act (OCPA, SB 619, 2023) — in force July 2024
  - HB 4107 (2024) — AI-generated deepfakes in elections
  - HB 2985 (2025) — automated decision-making disclosures
  - Foreign AI systems prohibition (DeepSeek) — 2025
  - Active pipeline: employment AI, healthcare AI, chatbot regulation

Sources:
  1. LegiScan API (primary — OR has biennial sessions)
"""

from sources.state_agent_base import StateAgentBase


class OregonAgent(StateAgentBase):
    """Oregon AI regulation and privacy legislation monitor."""

    state_code     = "OR"
    state_name     = "Oregon"
    legiscan_state = "OR"
