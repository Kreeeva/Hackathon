from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.tools import tool

from .db import surreal_client
from .queries import (
    detect_circular_flow as q_detect_circular_flow,
    detect_flagged_association as q_detect_flagged_association,
    detect_star_pattern as q_detect_star_pattern,
)


@tool(name="detect_star_pattern", description="Detect star pattern sources in recent transactions.")
async def detect_star_pattern_tool(
    window_minutes: int = 60,
    min_recipients: int = 10,
) -> List[Dict[str, Any]]:
    """
    Find source accounts that sent to many distinct destination accounts
    within the given time window.
    """
    return await q_detect_star_pattern(
        surreal_client,
        window_minutes=window_minutes,
        min_recipients=min_recipients,
    )


@tool(name="detect_circular_flow", description="Detect circular flow / ring layering patterns.")
async def detect_circular_flow_tool() -> List[Dict[str, Any]]:
    """
    Detect circular flow rings among suspicious accounts.
    """
    return await q_detect_circular_flow(surreal_client)


@tool(
    name="detect_flagged_association",
    description="Detect accounts directly linked to confirmed fraud via linked_to_flag edges.",
)
async def detect_flagged_association_tool() -> List[Dict[str, Any]]:
    """
    Find accounts that are directly associated with confirmed fraudulent accounts.
    """
    return await q_detect_flagged_association(surreal_client)


ALL_TOOLS = [
    detect_star_pattern_tool,
    detect_circular_flow_tool,
    detect_flagged_association_tool,
]

