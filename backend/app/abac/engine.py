"""Top-level Enterprise ABAC Engine and FastAPI Integration Middleware."""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional, Union
from fastapi import Depends, HTTPException, Request

from app.auth import require_bearer
from app.abac.decision import ABACDecisionResult, Decision
from app.abac.attributes.subject import SubjectAttributes, extract_subject_attributes
from app.abac.attributes.resource import ResourceAttributes, extract_resource_attributes
from app.abac.attributes.environment import EnvironmentAttributes, extract_environment_attributes
from app.abac.evaluator import evaluate_abac_request
from app.abac.services.identity_service import identity_service
from app.abac.services.risk_engine import risk_engine, RiskAnalysis
from app.abac.services.audit_service import audit_service
from app.abac.services.explainability import explainability_service
from app.abac.services.masking_service import masking_service
from app.abac.services.policy_repository import policy_repository


class ABACEngine:
    """Enterprise Zero-Trust ABAC Authorization Engine."""

    @staticmethod
    def evaluate(
        claims: Optional[Dict[str, Any]],
        resource_dict: Optional[Dict[str, Any]],
        action: str,
        request: Optional[Request] = None,
        custom_subject: Optional[Dict[str, Any]] = None,
        custom_environment: Optional[Dict[str, Any]] = None,
        is_simulation: bool = False,
    ) -> Dict[str, Any]:
        """Executes full zero-trust authorization pipeline and returns explainable response."""
        # 1. Identity & Attribute Extraction (Production claims vs Admin Simulation)
        subject = identity_service.create_subject_attributes(
            claims=claims,
            overrides=custom_subject,
            is_simulation=is_simulation,
        )

        resource = extract_resource_attributes(resource_dict)
        environment = extract_environment_attributes(request, custom_environment)

        # 2. Enterprise Risk Analysis
        risk_analysis = risk_engine.calculate(subject, environment)

        # 3. Core Policy Evaluation
        result = evaluate_abac_request(subject, resource, environment, action)
        result.risk_score = risk_analysis.final_score

        # 4. Forensic Audit Trail Recording (25+ attributes with HMAC signature)
        audit_service.record(
            subject=subject,
            resource=resource,
            environment=environment,
            action=action,
            result=result,
            risk_analysis=risk_analysis,
            policy_version="v1.0.0",
        )

        # 5. Build Explainable Response & Pipeline Visualization
        report = explainability_service.build_report(
            subject=subject,
            resource=resource,
            environment=environment,
            action=action,
            result=result,
            risk_analysis=risk_analysis,
        )

        return report.model_dump()

    @staticmethod
    def simulate(
        user: str = "admin",
        role: str = "manager",
        department: str = "Finance",
        action: str = "Read",
        resource_dict: Optional[Dict[str, Any]] = None,
        environment_dict: Optional[Dict[str, Any]] = None,
        custom_subject: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Admin Policy Simulator Endpoint (Simulation Sandbox)."""
        overrides = custom_subject or {}
        overrides.update({"user": user, "role": role, "department": department})
        claims = {"username": user, "role": role, "department": department}

        return ABACEngine.evaluate(
            claims=claims,
            resource_dict=resource_dict,
            action=action,
            request=None,
            custom_subject=overrides,
            custom_environment=environment_dict,
            is_simulation=True,
        )


def require_abac(action: str, resource_extractor: Optional[Callable[[Request], Dict[str, Any]]] = None):
    """FastAPI Dependency Middleware enforcing ABAC evaluation on API endpoints."""
    async def abac_dependency(request: Request, claims: dict = Depends(require_bearer)):
        res_dict = resource_extractor(request) if resource_extractor else {}
        result_dict = ABACEngine.evaluate(
            claims=claims,
            resource_dict=res_dict,
            action=action,
            request=request,
            is_simulation=False,
        )

        if result_dict.get("decision") == "DENY":
            raise HTTPException(
                status_code=403,
                detail=result_dict,
            )
        return result_dict

    return abac_dependency
