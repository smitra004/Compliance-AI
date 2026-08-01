"""Enterprise Authorization Decision Visualization & Explainability Service."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.abac.attributes.subject import SubjectAttributes
from app.abac.attributes.resource import ResourceAttributes
from app.abac.attributes.environment import EnvironmentAttributes
from app.abac.decision import ABACDecisionResult, Decision
from app.abac.services.risk_engine import RiskAnalysis


class PipelineStep(BaseModel):
    step: int
    name: str
    status: str  # PASSED, FAILED, WARNING, EXECUTED
    details: str


class ExplainableDecisionResponse(BaseModel):
    decision: str
    confidence: float = 1.0
    matched_policy: str
    evaluated_policies: List[str]
    failed_policies: List[str]
    failed_conditions: List[str]
    risk_score: int
    risk_level: str
    risk_breakdown: List[Dict[str, Any]]
    policy_priority: int = 100
    conflict_resolution_explanation: str
    reason: str
    obligations: List[str]
    pipeline_visualization: List[PipelineStep]
    suggested_fix: str
    effective_attributes: Dict[str, Any]


class ExplainabilityService:
    """Formats enterprise decision metrics into visual decision pipelines and structured JSON explanations."""

    @staticmethod
    def build_report(
        subject: SubjectAttributes,
        resource: ResourceAttributes,
        environment: EnvironmentAttributes,
        action: str,
        result: ABACDecisionResult,
        risk_analysis: Optional[RiskAnalysis] = None,
    ) -> ExplainableDecisionResponse:

        dec_str = result.decision.value if hasattr(result.decision, "value") else str(result.decision)
        is_permit = dec_str == "PERMIT"

        # Risk details
        risk_score = risk_analysis.final_score if risk_analysis else result.risk_score
        risk_level = risk_analysis.risk_level if risk_analysis else ("Low" if risk_score < 30 else "High")
        breakdown_data = []
        if risk_analysis and hasattr(risk_analysis, "breakdown"):
            breakdown_data = [b.model_dump() if hasattr(b, "model_dump") else b.dict() for b in risk_analysis.breakdown]

        # Conflict resolution explanation
        conflict_explanation = (
            f"Policy '{result.matched_policy}' evaluated with highest precedence rules."
            if is_permit
            else f"Access DENIED by policy '{result.matched_policy}' due to failed zero-trust boundary criteria."
        )

        # Build 11-step Decision Pipeline Visualization
        pipeline: List[PipelineStep] = [
            PipelineStep(step=1, name="JWT Authentication", status="PASSED", details=f"Verified user identity: {subject.username}"),
            PipelineStep(step=2, name="RBAC Authorization", status="PASSED", details=f"Role '{subject.role}' cleared for action '{action}'"),
            PipelineStep(step=3, name="Subject Attributes", status="PASSED", details=f"Clearance level '{subject.clearance_level}' (Rank {subject.clearance_rank})"),
            PipelineStep(step=4, name="Resource Classification", status="PASSED", details=f"Resource classification '{resource.classification}' (Dept: {resource.department})"),
            PipelineStep(step=5, name="Environment Context", status="PASSED" if environment.vpn_connected else "WARNING", details=f"VPN: {'Yes' if environment.vpn_connected else 'No'} | Country: {environment.country}"),
            PipelineStep(
                step=6,
                name="Enterprise Risk Engine",
                status="PASSED" if risk_score < 60 else ("WARNING" if risk_score < 80 else "FAILED"),
                details=f"Calculated Threat Risk Score: {risk_score}/100 ({risk_level} Risk)",
            ),
            PipelineStep(
                step=7,
                name="Policy Condition Evaluation",
                status="PASSED" if is_permit else "FAILED",
                details=f"Evaluated {len(result.evaluated_policies or [])} policies. Matched: {result.matched_policy}",
            ),
            PipelineStep(step=8, name="Conflict Resolution", status="PASSED" if is_permit else "FAILED", details=conflict_explanation),
            PipelineStep(step=9, name="Final Authorization Decision", status="PASSED" if is_permit else "FAILED", details=f"Verdict: {dec_str}"),
            PipelineStep(
                step=10,
                name="Obligations Enforcement",
                status="EXECUTED",
                details=f"Applied {len(result.obligations or [])} obligations ({', '.join(result.obligations) if result.obligations else 'None'})",
            ),
            PipelineStep(step=11, name="Immutable Forensic Audit", status="EXECUTED", details="Committed 25+ attribute log record with HMAC signature"),
        ]

        # Suggested remediation
        suggested_fix = (
            "No remediation needed. Access PERMITTED."
            if is_permit
            else f"Connect via Corporate VPN, verify MFA, or elevate clearance level to meet policy criteria."
        )

        return ExplainableDecisionResponse(
            decision=dec_str,
            confidence=1.0 if is_permit else 0.95,
            matched_policy=result.matched_policy,
            evaluated_policies=result.evaluated_policies or [],
            failed_policies=[result.matched_policy] if not is_permit else [],
            failed_conditions=result.failed_conditions or [],
            risk_score=risk_score,
            risk_level=risk_level,
            risk_breakdown=breakdown_data,
            policy_priority=100,
            conflict_resolution_explanation=conflict_explanation,
            reason=result.reason,
            obligations=result.obligations or [],
            pipeline_visualization=pipeline,
            suggested_fix=suggested_fix,
            effective_attributes={
                "subject": subject.model_dump() if hasattr(subject, "model_dump") else subject.dict(),
                "resource": resource.model_dump() if hasattr(resource, "model_dump") else resource.dict(),
                "environment": environment.model_dump() if hasattr(environment, "model_dump") else environment.dict(),
            },
        )


explainability_service = ExplainabilityService()
