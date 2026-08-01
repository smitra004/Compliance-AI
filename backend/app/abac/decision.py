"""Decision definitions and Pydantic schemas for explainable ABAC decisions."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Decision(str, Enum):
    PERMIT = "PERMIT"
    DENY = "DENY"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INDETERMINATE = "INDETERMINATE"


class ObligationType(str, Enum):
    REQUIRE_MFA = "Require MFA"
    READ_ONLY = "Read Only"
    DISABLE_DOWNLOAD = "Disable Download"
    DISABLE_EXPORT = "Disable Export"
    DISABLE_PRINTING = "Disable Printing"
    WATERMARK_PDF = "Watermark PDF"
    MASK_SENSITIVE_FIELDS = "Mask Sensitive Fields"
    LOG_HIGH_SEVERITY_EVENT = "Log High Severity Event"
    FORCE_REAUTHENTICATION = "Force Re-authentication"
    EXPIRE_SESSION_EARLY = "Expire Session Early"


class Obligation(BaseModel):
    name: str
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ABACDecisionResult(BaseModel):
    decision: Decision
    matched_policy: Optional[str] = "NONE"
    failed_conditions: List[str] = Field(default_factory=list)
    risk_score: int = 0
    reason: str = "Evaluation complete."
    obligations: List[str] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    evaluated_policies: List[str] = Field(default_factory=list)
    effective_attributes: Optional[Dict[str, Any]] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "matched_policy": self.matched_policy,
            "failed_conditions": self.failed_conditions,
            "risk_score": self.risk_score,
            "reason": self.reason,
            "obligations": self.obligations,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "evaluated_policies": self.evaluated_policies,
        }
