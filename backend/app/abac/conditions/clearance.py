"""Security Clearance condition evaluator."""
from __future__ import annotations

from typing import Any, Tuple
from app.abac.attributes.subject import SubjectAttributes, CLEARANCE_HIERARCHY


def evaluate_clearance_condition(condition_val: Any, subject: SubjectAttributes) -> Tuple[bool, str]:
    if isinstance(condition_val, str):
        req_rank = CLEARANCE_HIERARCHY.get(condition_val.lower(), 1)
        if subject.clearance_rank < req_rank:
            return False, f"Required clearance level ≥ '{condition_val.title()}' (You hold '{subject.clearance_level.title()}')."
    return True, ""
