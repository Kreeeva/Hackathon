from __future__ import annotations

from typing import Any, Dict, List, Optional

from .db import SurrealClient
from .models import AnalystDecision, EvidenceItem, InvestigationState


def _evidence_to_dict(e: EvidenceItem) -> dict:
    return e.model_dump() if hasattr(e, "model_dump") else e.dict()


def _first_result(res: Any) -> Optional[dict]:
    """Get first record from SurrealDB query result (handles list or single object)."""
    if not res or len(res) == 0:
        return None
    raw = res[0].get("result")
    if raw is None:
        return None
    if isinstance(raw, list):
        return raw[0] if raw else None
    return raw


async def persist_alert_and_case(
    db: SurrealClient,
    state: InvestigationState,
    graph: Dict[str, Any],
) -> InvestigationState:
    """
    Persist an alert and a case_record, and link them to the transaction.
    """
    tx_id = state.transaction_id

    alert_sql = """
    CREATE alert CONTENT {
      transaction: $tx_id,
      risk_score: $risk_score,
      severity: $severity,
      evidence: $evidence,
      explanation_short: $explanation_short,
      explanation_long: $explanation_long
    };
    """

    case_sql = """
    CREATE case_record CONTENT {
      primary_alert: $alert_id,
      status: "open",
      analyst_decision: $analyst_decision,
      metadata: {}
    };
    """

    relate_sql = """
    RELATE $alert_id->for_transaction->$tx_id;
    RELATE $alert_id->in_case->$case_id;
    """

    # Create alert
    alert_res = await db.query(
        alert_sql,
        {
            "tx_id": tx_id,
            "risk_score": state.risk_score,
            "severity": state.severity,
            "evidence": [_evidence_to_dict(e) for e in state.evidence],
            "explanation_short": state.explanation_short,
            "explanation_long": state.explanation_long,
        },
    )
    alert_rec = _first_result(alert_res)
    alert_id: Optional[str] = alert_rec.get("id") if alert_rec else None

    # Create case record
    case_res = await db.query(
        case_sql,
        {
            "alert_id": alert_id,
            "analyst_decision": state.analyst_decision.value if state.analyst_decision else None,
        },
    )
    case_rec = _first_result(case_res)
    case_id: Optional[str] = case_rec.get("id") if case_rec else None

    if alert_id and case_id:
        await db.query(
            relate_sql,
            {
                "alert_id": alert_id,
                "case_id": case_id,
                "tx_id": tx_id,
            },
        )

    state.alert_id = alert_id
    state.case_id = case_id
    return state


async def persist_feedback(
    db: SurrealClient,
    *,
    case_id: str,
    decision: AnalystDecision,
    note: Optional[str],
) -> Dict[str, Any]:
    """
    Persist analyst feedback linked to a case_record.
    """
    sql = """
    LET $fb = (CREATE analyst_feedback CONTENT {
      case: $case_id,
      decision: $decision,
      note: $note
    })[0];

    RELATE $case_id->has_feedback->$fb.id;

    RETURN $fb;
    """
    res = await db.query(
        sql,
        {
            "case_id": case_id,
            "decision": decision.value,
            "note": note,
        },
    )
    return res[0].get("result", [{}])[0] if res else {}

