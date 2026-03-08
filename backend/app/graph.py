from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from .db import surreal_client
from .explain import generate_explanations
from .models import (
    AnalystDecision,
    DetectionType,
    EvidenceItem,
    InvestigationState,
)
from .persist import persist_alert_and_case
from .queries import (
    detect_circular_flow,
    detect_flagged_association,
    detect_star_pattern,
    fetch_transaction_graph,
)


class GraphState(TypedDict, total=False):
    transaction_id: str
    detections: List[EvidenceItem]
    risk_score: int
    severity: str
    evidence: List[EvidenceItem]
    explanation_short: Optional[str]
    explanation_long: Optional[str]
    alert_id: Optional[str]
    case_id: Optional[str]
    analyst_decision: Optional[AnalystDecision]


async def run_detections(state: GraphState) -> GraphState:
    tx_id = state["transaction_id"]

    db = surreal_client

    detections: List[EvidenceItem] = []

    # Fetch the base transaction to identify the source account
    graph = await fetch_transaction_graph(db, tx_id)
    source_account = graph.get("source_account")
    source_str = str(source_account) if source_account is not None else None

    # Star pattern detection
    star_rows = await detect_star_pattern(
        db,
        window_minutes=60,
        min_recipients=20,
    )
    for row in star_rows:
        row_src = str(row.get("source_account", "")) if row.get("source_account") is not None else ""
        if source_str and row_src == source_str:
            detections.append(
                EvidenceItem(
                    type=DetectionType.STAR_PATTERN,
                    data={
                        "source_account": row_src,
                        "tx_count": int(row.get("tx_count", 0)),
                        "unique_recipients": int(row.get("unique_recipients", 0)),
                        "total_amount": float(row.get("total_amount", 0.0)),
                    },
                )
            )

    # Circular flow detection
    cycle_rows = await detect_circular_flow(db)
    for row in cycle_rows:
        accounts = [str(a) for a in row.get("accounts", [])]
        if source_str and source_str in accounts and row.get("cycle_exists"):
            detections.append(
                EvidenceItem(
                    type=DetectionType.CIRCULAR_FLOW,
                    data={
                        "cycle_exists": True,
                        "accounts": accounts,
                    },
                )
            )

    # Flagged association detection
    assoc_rows = await detect_flagged_association(db)
    for row in assoc_rows:
        row_account = str(row.get("account", "")) if row.get("account") is not None else ""
        if source_str and row_account == source_str:
            linked = [str(a) for a in row.get("linked_confirmed_fraud_accounts", [])]
            detections.append(
                EvidenceItem(
                    type=DetectionType.FLAGGED_ASSOCIATION,
                    data={
                        "account": row_account,
                        "linked_confirmed_fraud_accounts": linked,
                    },
                )
            )

    state["detections"] = detections
    state["evidence"] = detections.copy()
    return state


def score_risk(state: GraphState) -> GraphState:
    detections: List[EvidenceItem] = state.get("detections", [])
    score = 0
    for item in detections:
        if item.type == DetectionType.STAR_PATTERN:
            score += 30
        elif item.type == DetectionType.CIRCULAR_FLOW:
            score += 20
        elif item.type == DetectionType.FLAGGED_ASSOCIATION:
            score += 25

    if score >= 50:
        severity = "high"
    elif score >= 25:
        severity = "medium"
    else:
        severity = "low"

    state["risk_score"] = score
    state["severity"] = severity
    return state


async def generate_explanation(state: GraphState) -> GraphState:
    evidence: List[EvidenceItem] = state.get("evidence", [])
    risk_score = state.get("risk_score", 0)
    severity = state.get("severity", "low")

    if not evidence:
        state["explanation_short"] = "No strong fraud patterns were detected for this transaction."
        state["explanation_long"] = (
            "The deterministic checks for star patterns, circular flows, and flagged associations "
            "did not return any significant findings for this transaction based on the current dataset."
        )
        return state

    short, long = await generate_explanations(evidence, risk_score, severity)
    state["explanation_short"] = short
    state["explanation_long"] = long
    return state


async def persist_alert_case(state: GraphState) -> GraphState:
    inv_state = InvestigationState(**state)  # type: ignore[arg-type]

    # Persist alert and case; graph is not strictly needed here for MVP
    updated = await persist_alert_and_case(surreal_client, inv_state, graph={})

    state["alert_id"] = updated.alert_id
    state["case_id"] = updated.case_id
    return state


def build_workflow():
    graph = StateGraph(GraphState)

    graph.add_node("run_detections", run_detections)
    graph.add_node("score_risk", score_risk)
    graph.add_node("generate_explanation", generate_explanation)
    graph.add_node("persist_alert_case", persist_alert_case)

    graph.add_edge(START, "run_detections")
    graph.add_edge("run_detections", "score_risk")
    graph.add_edge("score_risk", "generate_explanation")
    graph.add_edge("generate_explanation", "persist_alert_case")
    graph.add_edge("persist_alert_case", END)

    return graph.compile()


workflow = build_workflow()

