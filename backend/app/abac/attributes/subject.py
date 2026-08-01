"""Subject attribute extraction and dynamic profile loading."""
from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


CLEARANCE_HIERARCHY = {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "highly_confidential": 3,
    "restricted": 4,
    "top_secret": 5,
}


class SubjectAttributes(BaseModel):
    user_id: int = 1
    username: str = "guest"
    role: str = "viewer"
    department: str = "General"
    designation: str = "Analyst"
    clearance_level: str = "internal"
    employment_type: str = "Full-Time"
    region: str = "Global"
    business_unit: str = "Corporate"
    office_location: str = "Headquarters"

    country: str = "US"
    years_of_experience: int = 3
    manager_id: Optional[int] = 1
    project_assignment: str = "Enterprise Compliance"
    risk_score: int = 0
    mfa_status: bool = True
    email_verified: bool = True
    account_status: str = "Active"
    device_trust_level: str = "Trusted"
    last_password_change: Optional[str] = None
    failed_login_attempts: int = 0
    policy_certifications: list[str] = Field(default_factory=lambda: ["GDPR", "ISO27001"])

    @property
    def clearance_rank(self) -> int:
        from app.abac.services.clearance_service import clearance_registry
        return clearance_registry.get_rank(self.clearance_level)



def extract_subject_attributes(claims: Optional[Dict[str, Any]], custom_overrides: Optional[Dict[str, Any]] = None) -> SubjectAttributes:
    """Dynamically loads and normalizes subject attributes from JWT claims, DB profiles, or custom simulation context."""
    from app.user_db import get_user

    claims = claims or {}
    username = claims.get("username") or claims.get("sub") or (custom_overrides.get("username") if custom_overrides else None) or "guest"
    
    # Attempt DB fetch if username available
    db_user = get_user(username) if username != "guest" else None
    user_dict = dict(db_user) if db_user else {}

    # Merge hierarchy: Defaults -> DB values -> JWT claims -> Custom Overrides
    merged = {
        "user_id": user_dict.get("id") or claims.get("id") or 1,
        "username": username,
        "role": claims.get("role") or user_dict.get("role") or "viewer",
        "department": claims.get("department") or user_dict.get("department") or "General",
        "designation": user_dict.get("designation") or claims.get("designation") or "Senior Specialist",
        "clearance_level": claims.get("clearance_level") or user_dict.get("clearance_level") or "internal",
        "employment_type": user_dict.get("employment_type") or "Full-Time",
        "office_location": user_dict.get("office_location") or "Headquarters",
        "country": user_dict.get("country") or "US",
        "years_of_experience": user_dict.get("years_of_experience") or 5,
        "manager_id": user_dict.get("manager_id") or 1,
        "project_assignment": user_dict.get("project_assignment") or "Core Compliance",
        "risk_score": user_dict.get("risk_score") if user_dict.get("risk_score") is not None else 0,
        "mfa_status": bool(user_dict.get("mfa_status", 1)),
        "email_verified": bool(user_dict.get("email_verified", 1)),
        "account_status": user_dict.get("status") or claims.get("status") or "Active",
        "device_trust_level": user_dict.get("device_trust_level") or "Trusted",
        "last_password_change": user_dict.get("last_password_change"),
        "failed_login_attempts": user_dict.get("failed_login_attempts") or 0,
        "policy_certifications": (user_dict.get("policy_certifications") or "GDPR,ISO27001,SOX").split(","),
    }

    if custom_overrides:
        for k, v in custom_overrides.items():
            if v is not None and k in SubjectAttributes.model_fields:
                merged[k] = v

    return SubjectAttributes(**merged)
