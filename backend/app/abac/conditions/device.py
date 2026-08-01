"""Device trust condition evaluator."""
from __future__ import annotations

from typing import Any, Tuple
from app.abac.attributes.environment import EnvironmentAttributes


def evaluate_device_condition(condition_val: Any, env: EnvironmentAttributes) -> Tuple[bool, str]:
    if isinstance(condition_val, dict):
        if condition_val.get("device_managed_required") and not env.device_managed:
            return False, "Access requires a Corporate Managed Device (MDM)."
        min_trust = condition_val.get("min_trust_level")
        if min_trust and env.device_trust_level.lower() != min_trust.lower():
            if env.device_trust_level.lower() == "untrusted":
                return False, f"Device trust level '{env.device_trust_level}' does not meet minimum '{min_trust}'."
    return True, ""
