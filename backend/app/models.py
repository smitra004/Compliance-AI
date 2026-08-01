"""
Data contracts for the Policy Compliance Checker.
These schemas are the single source of truth shared across the
parser, rule engine, LLM analyzer, aggregator, and the frontend.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    P1 = "P1"  # Critical  - regulatory violation w/ financial penalty risk
    P2 = "P2"  # High      - policy violation w/ audit risk
    P3 = "P3"  # Medium    - best-practice deviation
    P4 = "P4"  # Low       - style / process suggestion

    @property
    def label(self) -> str:
        return {
            "P1": "Critical",
            "P2": "High",
            "P3": "Medium",
            "P4": "Low",
        }[self.value]

    @property
    def weight(self) -> int:
        return {"P1": 4, "P2": 3, "P3": 2, "P4": 1}[self.value]


class Regulation(str, Enum):
    GDPR = "gdpr"
    ISO27001 = "iso27001"
    SOX = "sox"
    INTERNAL_SECURITY = "internal_security"
    INTERNAL_HR = "internal_hr"
    CUSTOM = "custom"



class PolicyCitation(BaseModel):
    """The exact policy chunk a violation is grounded in (RAG evidence)."""
    regulation: Regulation
    clause: str
    text: str
    similarity: float = Field(ge=0.0, le=1.0)


class Violation(BaseModel):
    id: str
    title: str
    severity: Severity
    source_regulation: Regulation
    detected_by: str  # "rule_engine" | "llm" | "rule_engine+llm"
    excerpt: str       # the offending text from the document
    explanation: str   # plain-language summary of the breach
    recommendation: str
    citation: Optional[PolicyCitation] = None
    regulation_articles: List[str] = []   # mapped statutory clauses, e.g. ["GDPR Art. 32"]
    
    # Autonomous Remediation fields
    remediation_reasoning: Optional[str] = None
    remediated_text: Optional[str] = None
    remediation_score_improvement: Optional[int] = 0
    
    # Executive Risk fields
    risk_multiplier: Optional[float] = 1.0
    estimated_fine_min: Optional[float] = 0.0
    estimated_fine_max: Optional[float] = 0.0
    affected_users_estimate: Optional[int] = 0
    operational_impact: Optional[str] = None
    reputation_risk_level: Optional[str] = "Low"


class ComplianceAnalysisResult(BaseModel):
    """Strict schema the LLM must return. Injected instructions cannot
    add fields or change the structure."""
    is_compliant: bool
    confidence: float = Field(ge=0.0, le=1.0)
    violations: List[Violation] = []
    summary: str


class ResolvedViolation(BaseModel):
    """
    Durable record of a violation that has gone through the Resolve action.
    Persisted on the ScanRecord itself (not just returned to the UI) so a
    page refresh, server restart, or re-fetch of the scan never loses which
    violations were remediated or what was changed.
    """
    violation_id: str
    original_text: str
    remediated_text: str
    violated_rule: str
    recommendation: str
    resolution_status: str = "resolved"
    document_position: int = -1
    resolved_at: datetime


class ScanRecord(BaseModel):
    scan_id: str
    document_name: str
    uploaded_by: str
    department: str
    tenant_id: str
    created_at: datetime

    compliance_score: int
    total_violations: int

    # Derived solely from compliance_score via
    # app.pipeline.scoring.compliance_status_and_risk — never set
    # independently, so these can never disagree with the score.
    compliance_status: str = "Non-Compliant"
    risk_level: str = "High"

    severity_breakdown: dict
    violations: List[Violation]

    summary: str
    demo_mode: bool

    confidence: float = 1.0
    sha256_hash: Optional[str] = None
    predicted_compliance_score: Optional[int] = None

    # Explainability
    score_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    analysis_mode: str = "deterministic"
    agent_reports: List[dict] = Field(default_factory=list)

    # Aggregate Risk
    total_exposure_min: Optional[float] = 0.0
    total_exposure_max: Optional[float] = 0.0
    total_affected_users: Optional[int] = 0
    raw_text: Optional[str] = None

    original_file_path: Optional[str] = None
    original_file_ext: Optional[str] = None

    remediated_documents: List[dict] = Field(default_factory=list)

    resolved_violations: List[ResolvedViolation] = Field(default_factory=list)
    last_remediation: List[dict] = Field(default_factory=list)


class AuditEntry(BaseModel):
    id: int
    timestamp: datetime
    actor: str
    role: str
    department: str
    action: str
    target: str
    detail: str


class DashboardStats(BaseModel):
    overall_compliance_score: int
    policies_scanned: int
    risks_detected: int
    documents_analyzed: int
    compliance_trend: List[dict]      # [{"label": "May 1", "value": 62}, ...]
    risk_by_category: List[dict]      # [{"name": "Access Control", "value": 30}, ...]
    top_risky_areas: List[dict]       # [{"name": "Access Control", "risks": 8}, ...]
    recent_alerts: List[dict]
    
    # Executive Risk Simulator Stats
    total_exposure_min: float = 0.0
    total_exposure_max: float = 0.0
    total_affected_users: int = 0

    # Derived solely from overall_compliance_score, same bands as a single
    # scan's status/risk (see app.pipeline.scoring.compliance_status_and_risk)
    overall_status: str = "Non-Compliant"
    overall_risk_level: str = "High"

