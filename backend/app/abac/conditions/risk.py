"""Risk-Adaptive Access Control scoring and condition evaluation."""
from __future__ import annotations

from typing import Any, Tuple
from app.abac.attributes.subject import SubjectAttributes
from app.abac.attributes.environment import EnvironmentAttributes


def calculate_risk_score(subject: SubjectAttributes, env: EnvironmentAttributes) -> int:
    """Calculates threat risk score based on contextual environment and subject attributes."""
    score = subject.risk_score

    # Trusted device check (+0 if trusted, +15 if untrusted/public)
    if subject.device_trust_level.lower() != "trusted" or not env.device_managed:
        score += 15

    # Corporate VPN missing (+20)
    if not env.vpn_connected and not env.office_network:
        score += 20

    # Outside business hours (+15)
    if not env.business_hours:
        score += 15

    # Weekend (+5)
    if env.weekend:
        score += 5

    # Unknown / non-US country (+30)
    if env.country.upper() not in ("US", "GLOBAL", "EU"):
        score += 30

    # MFA missing (+25)
    if not subject.mfa_status:
        score += 25

    # Multiple login failures (+40)
    if subject.failed_login_attempts >= 3:
        score += 40

    # High request frequency (+20)
    if env.request_frequency > 30:
        score += 20

    return min(score, 100)


def evaluate_risk_condition(condition_val: Any, calculated_risk: int, is_min: bool = False) -> Tuple[bool, str]:
    if isinstance(condition_val, (int, float)):
        threshold = int(condition_val)
        if is_min:
            if calculated_risk < threshold:
                return False, f"Calculated Risk Score ({calculated_risk}) is below minimum threshold ({threshold})."
        else:
            if calculated_risk > threshold:
                return False, f"Calculated Risk Score ({calculated_risk}) exceeds maximum threshold ({threshold})."
    return True, ""
