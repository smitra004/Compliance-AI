"""Ownership condition evaluator."""
from __future__ import annotations

from typing import Any, Tuple
from app.abac.attributes.subject import SubjectAttributes
from app.abac.attributes.resource import ResourceAttributes


def evaluate_ownership_condition(condition_val: Any, subject: SubjectAttributes, resource: ResourceAttributes) -> Tuple[bool, str]:
    if isinstance(condition_val, bool) and condition_val:
        # Central Admin bypasses owner restrictions
        if subject.role == "central_admin":
            return True, ""
        if subject.username != resource.owner:
            return False, f"Resource owner match required (Owner is '{resource.owner}', User is '{subject.username}')."
    return True, ""
