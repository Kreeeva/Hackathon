from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from .db import SurrealClient, get_db
from .graph import workflow
from .models import FeedbackRequest, InvestigateRequest, InvestigateResponse, InvestigationState
from .persist import persist_feedback
from .queries import fetch_transaction_graph


router = APIRouter()


def _to_serializable(obj: Any) -> Any:
    """Ensure graph payload is JSON-serializable (e.g. SurrealDB record IDs -> str)."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if hasattr(obj, "get") and hasattr(obj, "items"):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if hasattr(obj, "__iter__") and not isinstance(obj, str):
        return [_to_serializable(x) for x in obj]
    return str(obj)


@router.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@router.post("/investigate", response_model=InvestigateResponse)
async def investigate(
    payload: InvestigateRequest,
    db: SurrealClient = Depends(get_db),
) -> InvestigateResponse:
    tx_id = payload.transaction_id

    # Run the LangGraph workflow end-to-end
    initial_state: Dict[str, Any] = {
        "transaction_id": tx_id,
        "detections": [],
        "risk_score": 0,
        "severity": "low",
        "evidence": [],
        "explanation_short": None,
        "explanation_long": None,
        "alert_id": None,
        "case_id": None,
        "analyst_decision": None,
    }

    try:
        result_state_dict = await workflow.ainvoke(initial_state)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Investigation failed: {exc}",
        ) from exc

    state = InvestigationState(**result_state_dict)

    # Build graph JSON for frontend visualization
    try:
        raw_graph = await fetch_transaction_graph(db, tx_id)
        graph = _to_serializable(raw_graph)
    except Exception as exc:
        # Graph is helpful but not critical for the investigation result
        graph = {"error": f"Failed to build graph: {exc}"}

    return InvestigateResponse(state=state, graph=graph)


@router.post("/feedback")
async def feedback(
    payload: FeedbackRequest,
    db: SurrealClient = Depends(get_db),
) -> Dict[str, Any]:
    try:
        fb = await persist_feedback(
            db,
            case_id=payload.case_id,
            decision=payload.decision,
            note=payload.note,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist feedback: {exc}",
        ) from exc

    return {"status": "ok", "feedback": fb}

