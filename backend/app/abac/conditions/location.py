"""Location and Network condition evaluator."""
from __future__ import annotations

from typing import Any, List, Tuple
from app.abac.attributes.environment import EnvironmentAttributes


def evaluate_location_condition(condition_val: Any, env: EnvironmentAttributes) -> Tuple[bool, str]:
    if isinstance(condition_val, dict):
        if condition_val.get("vpn_required") and not env.vpn_connected:
            return False, "Corporate VPN Connection is required for this action."
        if condition_val.get("office_network_required") and not env.office_network:
            return False, "Request must originate from an authorized Office Network."
        allowed_countries: List[str] = condition_val.get("allowed_countries", [])
        if allowed_countries and env.country not in allowed_countries:
            return False, f"Location '{env.country}' is not in allowed list {allowed_countries}."
    elif isinstance(condition_val, bool) and condition_val:
        if not env.vpn_connected and not env.office_network:
            return False, "Secure network connection (VPN or Office Network) is required."
    return True, ""
