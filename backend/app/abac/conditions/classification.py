"""Resource classification vs Subject clearance rank evaluator."""
from __future__ import annotations

from typing import Any, List, Tuple
from app.abac.attributes.subject import SubjectAttributes
from app.abac.attributes.resource import ResourceAttributes


def evaluate_classification_condition(condition_val: Any, subject: SubjectAttributes, resource: ResourceAttributes) -> Tuple[bool, str]:
    # If policy explicitly restricts classifications
    if isinstance(condition_val, list):
        if resource.classification not in condition_val and resource.classification.title() not in condition_val:
            return False, f"Resource classification '{resource.classification}' is not matched by policy target {condition_val}."

    # Baseline rule: Subject Clearance Rank MUST be >= Resource Classification Rank
    if subject.clearance_rank < resource.classification_rank:
        return False, (
            f"Security Clearance Too Low: Resource classification '{resource.classification}' "
            f"requires rank ≥ {resource.classification_rank}, but user holds '{subject.clearance_level}' (rank {subject.clearance_rank})."
        )

    return True, ""
