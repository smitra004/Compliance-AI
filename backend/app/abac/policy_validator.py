"""Policy schema validation module using Pydantic."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from app.abac.exceptions import PolicyValidationError


class PolicyResourceModel(BaseModel):
    department: Optional[List[str]] = None
    classification: Optional[List[str]] = None
    regulation: Optional[List[str]] = None
    contains_pii: Optional[bool] = None
    contains_financial_data: Optional[bool] = None
    contains_hipaa_data: Optional[bool] = None
    contains_pci_data: Optional[bool] = None


class PolicyModel(BaseModel):
    policy_id: str
    name: str = Field(default="Unnamed Policy")
    description: Optional[str] = ""
    effect: str = Field(default="Permit")  # Permit or Deny
    priority: int = Field(default=50, ge=0, le=100)
    roles: Optional[List[str]] = None
    departments: Optional[List[str]] = None
    resource: Optional[PolicyResourceModel] = None
    actions: Optional[List[str]] = None
    conditions: Optional[Dict[str, Any]] = Field(default_factory=dict)
    obligations: Optional[List[str]] = Field(default_factory=list)

    @field_validator("effect")
    @classmethod
    def validate_effect(cls, v: str) -> str:
        if v.title() not in ("Permit", "Deny"):
            raise ValueError("Policy effect must be 'Permit' or 'Deny'")
        return v.title()


def validate_policy_dict(policy_dict: Dict[str, Any]) -> PolicyModel:
    """Validates a single policy dictionary against PolicyModel schema."""
    try:
        return PolicyModel(**policy_dict)
    except Exception as e:
        raise PolicyValidationError(f"Invalid policy schema for policy '{policy_dict.get('policy_id', 'UNKNOWN')}': {e}") from e
