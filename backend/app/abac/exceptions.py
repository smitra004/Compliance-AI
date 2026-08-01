"""ABAC Exception hierarchy for Enterprise Authorization."""
from __future__ import annotations


class ABACException(Exception):
    """Base exception for all ABAC errors."""
    pass


class PolicyEvaluationError(ABACException):
    """Raised when policy evaluation fails due to invalid parameters or runtime exceptions."""
    pass


class PolicyValidationError(ABACException):
    """Raised when a policy JSON document fails schema validation."""
    pass


class InvalidAttributeError(ABACException):
    """Raised when subject, resource, or environment attributes are missing or malformed."""
    pass


class ABACDeniedException(ABACException):
    """Raised when access is explicitly denied by ABAC evaluation."""

    def __init__(self, message: str, decision_result: dict = None):
        super().__init__(message)
        self.decision_result = decision_result or {}
