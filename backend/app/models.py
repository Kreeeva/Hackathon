from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DetectionType(str, Enum):
    STAR_PATTERN = "star_pattern"
    CIRCULAR_FLOW = "circular_flow"
    FLAGGED_ASSOCIATION = "flagged_association"


class StarPatternDetection(BaseModel):
    detection_type: DetectionType = DetectionType.STAR_PATTERN
    source_account: str
    tx_count: int
    unique_recipients: int
    total_amount: float


class CircularFlowDetection(BaseModel):
    detection_type: DetectionType = DetectionType.CIRCULAR_FLOW
    cycle_exists: bool
    accounts: List[str] = Field(default_factory=list)


class FlaggedAssociationDetection(BaseModel):
    detection_type: DetectionType = DetectionType.FLAGGED_ASSOCIATION
    account: str
    linked_confirmed_fraud_accounts: List[str]


class EvidenceItem(BaseModel):
    type: DetectionType
    data: Dict[str, Any]


class AnalystDecision(str, Enum):
    CONFIRMED_SUSPICIOUS = "confirmed_suspicious"
    FALSE_POSITIVE = "false_positive"
    ESCALATE = "escalate"


class InvestigationState(BaseModel):
    transaction_id: str
    detections: List[EvidenceItem] = Field(default_factory=list)
    risk_score: int = 0
    severity: str = "low"
    evidence: List[EvidenceItem] = Field(default_factory=list)
    explanation_short: Optional[str] = None
    explanation_long: Optional[str] = None
    alert_id: Optional[str] = None
    case_id: Optional[str] = None
    analyst_decision: Optional[AnalystDecision] = None


class InvestigateRequest(BaseModel):
    transaction_id: str


class InvestigateResponse(BaseModel):
    state: InvestigationState
    graph: Dict[str, Any]


class FeedbackRequest(BaseModel):
    case_id: str
    decision: AnalystDecision
    note: Optional[str] = None

