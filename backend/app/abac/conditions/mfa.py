"""MFA enforcement condition evaluator."""
from __future__ import annotations

from typing import Any, Tuple
from app.abac.attributes.subject import SubjectAttributes


def evaluate_mfa_condition(condition_val: Any, subject: SubjectAttributes) -> Tuple[bool, str]:
    if isinstance(condition_val, bool) and condition_val:
        if not subject.mfa_status:
            return False, "Multi-Factor Authentication (MFA) verification is required for this operation."
    return True, ""
