"""Immutable Audit Trail Logger for ABAC evaluation decisions."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from app.abac.decision import ABACDecisionResult
from app.abac.attributes.subject import SubjectAttributes
from app.abac.attributes.resource import ResourceAttributes
from app.abac.attributes.environment import EnvironmentAttributes


def record_abac_audit_entry(
    subject: SubjectAttributes,
    resource: ResourceAttributes,
    environment: EnvironmentAttributes,
    action: str,
    result: ABACDecisionResult,
):
    """Records an immutable audit entry into SQLite database."""
    try:
        from app.db import log_abac_audit

        log_abac_audit(
            user=subject.username,
            role=subject.role,
            department=subject.department,
            resource=resource.resource_id,
            action=action,
            policies_evaluated=result.evaluated_policies,
            matched_policy=result.matched_policy,
            decision=result.decision.value,
            reason=result.reason,
            failed_conditions=result.failed_conditions,
            risk_score=result.risk_score,
            environment_attributes=environment.model_dump(),
            execution_time_ms=result.execution_time_ms,
            ip_address=environment.ip_address,
            device=environment.device_type,
            location=environment.location,
            session_id="",
            obligations=result.obligations,
        )
    except Exception as e:
        print(f"[ABAC Audit Error] Failed to log audit entry: {e}")
