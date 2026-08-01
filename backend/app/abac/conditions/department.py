"""Department condition evaluator."""
from __future__ import annotations

from typing import Any, List, Tuple
from app.abac.attributes.subject import SubjectAttributes
from app.abac.attributes.resource import ResourceAttributes


def evaluate_department_condition(condition_val: Any, subject: SubjectAttributes, resource: ResourceAttributes) -> Tuple[bool, str]:
    if subject.role == "central_admin":
        return True, ""

    if isinstance(condition_val, list):
        if subject.department not in condition_val and "Global" not in condition_val:
            return False, f"User department '{subject.department}' is not in policy permitted departments {condition_val}."

    if isinstance(condition_val, bool) and condition_val:
        if subject.department != resource.department and subject.department != "Global" and resource.department != "General":
            return False, f"Cross-department restriction: User in '{subject.department}' cannot access resource in '{resource.department}'."

    return True, ""
