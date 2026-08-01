"""Enterprise Forensic Audit Trail Service with Tamper-Evident Signatures."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.abac.attributes.subject import SubjectAttributes
from app.abac.attributes.resource import ResourceAttributes
from app.abac.attributes.environment import EnvironmentAttributes
from app.abac.decision import ABACDecisionResult
from app.abac.services.risk_engine import RiskAnalysis
from app import db


AUDIT_HMAC_SECRET = "complianceai_forensic_integrity_secret_2026"


class EnterpriseAuditEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
    request_id: str = Field(default_factory=lambda: f"req-{uuid.uuid4().hex[:8]}")
    session_id: str = Field(default_factory=lambda: f"sess-{uuid.uuid4().hex[:12]}")
    evaluation_time_ms: float = 0.0

    # Subject Attributes
    user: str
    role: str
    department: str
    subject_attributes: Dict[str, Any]

    # Resource Attributes
    resource_id: str = "RES-001"
    resource_classification: str = "Internal"
    resource_attributes: Dict[str, Any]

    # Action & Decision
    requested_action: str
    decision: str
    matched_policy: str
    evaluated_policies: List[str]
    failed_conditions: List[str]
    obligations_applied: List[str]

    # Risk Engine Metrics
    risk_score: int
    risk_breakdown: List[Dict[str, Any]]

    # Contextual Environment & Device Attributes
    environment_attributes: Dict[str, Any]
    device: str = "Corporate Workstation"
    ip_address: str = "127.0.0.1"
    country: str = "US"

    # Governance Versioning & Security Signature
    policy_version: str = "v1.0.0"
    integrity_signature: str = ""


class AuditService:
    """Logs tamper-evident, 25+ attribute forensic audit records to database."""

    @staticmethod
    def record(
        subject: SubjectAttributes,
        resource: ResourceAttributes,
        environment: EnvironmentAttributes,
        action: str,
        result: ABACDecisionResult,
        risk_analysis: Optional[RiskAnalysis] = None,
        policy_version: str = "v1.0.0",
    ) -> EnterpriseAuditEntry:
        # Build breakdown dictionary list
        breakdown_list = []
        if risk_analysis and hasattr(risk_analysis, "breakdown"):
            for item in risk_analysis.breakdown:
                breakdown_list.append(item.model_dump() if hasattr(item, "model_dump") else item.dict())
        elif hasattr(result, "risk_breakdown") and result.risk_breakdown:
            breakdown_list = result.risk_breakdown

        entry = EnterpriseAuditEntry(
            evaluation_time_ms=round(result.execution_time_ms, 2),
            user=subject.username,
            role=subject.role,
            department=subject.department,
            subject_attributes={
                "clearance_level": subject.clearance_level,
                "clearance_rank": subject.clearance_rank,
                "designation": subject.designation,
                "employment_type": subject.employment_type,
                "region": subject.region,
                "mfa_status": subject.mfa_status,
                "device_trust_level": subject.device_trust_level,
            },
            resource_id=getattr(resource, "resource_id", "RES-001"),
            resource_classification=resource.classification,
            resource_attributes={
                "department": resource.department,
                "contains_pii": resource.contains_pii,
                "contains_financial_data": resource.contains_financial_data,
                "regulation": resource.regulation,
            },
            requested_action=action,
            decision=result.decision.value if hasattr(result.decision, "value") else str(result.decision),
            matched_policy=result.matched_policy,
            evaluated_policies=result.evaluated_policies or [],
            failed_conditions=result.failed_conditions or [],
            obligations_applied=result.obligations or [],
            risk_score=result.risk_score,
            risk_breakdown=breakdown_list,
            environment_attributes={
                "vpn_connected": environment.vpn_connected,
                "business_hours": environment.business_hours,
                "device_managed": environment.device_managed,
                "office_network": environment.office_network,
                "country": environment.country,
                "request_frequency": environment.request_frequency,
            },
            device="Corporate Workstation",
            ip_address=getattr(environment, "ip_address", "127.0.0.1"),
            country=environment.country,
            policy_version=policy_version,
        )

        # Compute tamper-evident HMAC signature
        raw_payload = f"{entry.timestamp}|{entry.user}|{entry.requested_action}|{entry.decision}|{entry.risk_score}|{entry.matched_policy}"
        signature = hmac.new(
            AUDIT_HMAC_SECRET.encode("utf-8"),
            raw_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        entry.integrity_signature = signature

        # Save to SQLite database
        try:
            db.save_abac_audit_log(entry.model_dump())
        except Exception:
            pass

        return entry


audit_service = AuditService()
