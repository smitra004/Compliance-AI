"""Identity and Attribute Management Layer for Production & Simulation Modes."""
from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.abac.attributes.subject import SubjectAttributes
from app.abac.services.clearance_service import clearance_registry


class EnterpriseIdentity(BaseModel):
    id: int = 1
    username: str = "guest"
    email: str = "guest@company.com"
    role: str = "viewer"
    department: str = "General"
    clearance_level: str = "Internal"
    clearance_rank: int = 2
    designation: str = "Compliance Analyst"
    employment_type: str = "Full-Time"
    region: str = "Global"
    business_unit: str = "Corporate"
    mfa_status: bool = True
    device_trust_level: str = "trusted"
    failed_login_attempts: int = 0
    risk_score: int = 0


class IdentityService:
    """Enterprise Identity Layer managing automatic claim extraction and mode controls."""

    @staticmethod
    def extract_from_claims(claims: Optional[Dict[str, Any]]) -> EnterpriseIdentity:
        """Production Mode: Automatically extracts subject attributes from verified enterprise IdP JWT claims."""
        if not claims:
            return EnterpriseIdentity()

        username = claims.get("username") or claims.get("sub") or "authenticated_user"
        role = claims.get("role") or "viewer"
        department = claims.get("department") or "General"
        clearance_level = claims.get("clearance_level") or claims.get("clearance") or "Internal"
        clearance_rank = clearance_registry.get_rank(clearance_level)

        designation = claims.get("designation") or claims.get("title") or "Corporate Employee"
        employment_type = claims.get("employment_type") or claims.get("emp_type") or "Full-Time"
        region = claims.get("region") or claims.get("locale") or "Global"
        business_unit = claims.get("business_unit") or claims.get("bu") or "Corporate"

        return EnterpriseIdentity(
            id=claims.get("id") or 1,
            username=username,
            email=claims.get("email") or f"{username}@company.com",
            role=role,
            department=department,
            clearance_level=clearance_level,
            clearance_rank=clearance_rank,
            designation=designation,
            employment_type=employment_type,
            region=region,
            business_unit=business_unit,
            mfa_status=claims.get("mfa_status", True),
            device_trust_level=claims.get("device_trust_level", "trusted"),
            failed_login_attempts=claims.get("failed_login_attempts", 0),
            risk_score=claims.get("risk_score", 0),
        )

    @staticmethod
    def create_subject_attributes(
        claims: Optional[Dict[str, Any]],
        overrides: Optional[Dict[str, Any]] = None,
        is_simulation: bool = False,
    ) -> SubjectAttributes:
        """
        Creates SubjectAttributes for the authorization engine.
        If is_simulation is False, strictly extracts attributes from IdP JWT claims.
        If is_simulation is True (Admin only), applies contextual testing overrides.
        """
        identity = IdentityService.extract_from_claims(claims)

        if is_simulation and overrides:
            # Simulation Mode: Apply overrides for testing
            user_val = overrides.get("user") or overrides.get("username") or identity.username
            role_val = overrides.get("role") or identity.role
            dept_val = overrides.get("department") or identity.department
            clearance_val = overrides.get("clearance_level") or overrides.get("clearance") or identity.clearance_level
            rank_val = clearance_registry.get_rank(clearance_val)

            mfa_val = overrides.get("mfa_status") if "mfa_status" in overrides else identity.mfa_status
            if isinstance(overrides.get("subject"), dict):
                subj_dict = overrides["subject"]
                if "clearance_level" in subj_dict:
                    clearance_val = subj_dict["clearance_level"]
                    rank_val = clearance_registry.get_rank(clearance_val)
                if "mfa_status" in subj_dict:
                    mfa_val = subj_dict["mfa_status"]

            return SubjectAttributes(
                user_id=identity.id,
                username=user_val,
                role=role_val,
                department=dept_val,
                clearance_level=clearance_val,
                clearance_rank=rank_val,
                designation=overrides.get("designation", identity.designation),
                employment_type=overrides.get("employment_type", identity.employment_type),
                region=overrides.get("region", identity.region),
                business_unit=overrides.get("business_unit", identity.business_unit),
                mfa_status=bool(mfa_val),
                device_trust_level=overrides.get("device_trust_level", identity.device_trust_level),
                failed_login_attempts=overrides.get("failed_login_attempts", identity.failed_login_attempts),
                risk_score=overrides.get("risk_score", identity.risk_score),
            )

        # Production Mode: Strictly use claims extracted from IdP JWT
        return SubjectAttributes(
            user_id=identity.id,
            username=identity.username,
            role=identity.role,
            department=identity.department,
            clearance_level=identity.clearance_level,
            clearance_rank=identity.clearance_rank,
            designation=identity.designation,
            employment_type=identity.employment_type,
            region=identity.region,
            business_unit=identity.business_unit,
            mfa_status=identity.mfa_status,
            device_trust_level=identity.device_trust_level,
            failed_login_attempts=identity.failed_login_attempts,
            risk_score=identity.risk_score,
        )


identity_service = IdentityService()
