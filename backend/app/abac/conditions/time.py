"""Time condition evaluator."""
from __future__ import annotations

from typing import Any, Dict, Tuple
from app.abac.attributes.environment import EnvironmentAttributes


def evaluate_time_condition(condition_val: Any, env: EnvironmentAttributes) -> Tuple[bool, str]:
    if isinstance(condition_val, bool):
        if condition_val and not env.business_hours:
            return False, "Access permitted only during Business Hours (09:00 - 18:00 Mon-Fri)."
        return True, ""

    if isinstance(condition_val, dict):
        if condition_val.get("business_hours_required") and not env.business_hours:
            return False, "Access requires Business Hours."
        if condition_val.get("allow_weekend") is False and env.weekend:
            return False, "Weekend access is disabled."
    return True, ""
