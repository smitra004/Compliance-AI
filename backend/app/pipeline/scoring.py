"""
Single source of truth for the Compliance Score formula.

This module exists so that the score computed for a *fresh* scan (initial
upload, or a later re-upload of a previously remediated document) and the
score computed when violations are resolved via the Remediation endpoint are
always derived from the exact same arithmetic. Nothing here is hardcoded to
a document, a scan, or a cached result — every input (violations, exposure,
affected users, confidence) is derived from the current state of the actual
document content being analyzed.

Because both code paths (initial scan in `agents.py` and the remediation
flow in `main.py`) call this same function, a document that has had
violations fixed and is re-uploaded will be re-scanned from its current
content, find the same (now-clean) state, and land on the identical
compliance score — no drift between "resolve" math and "re-scan" math.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.models import Severity


def compliance_status_and_risk(score: int) -> Dict[str, str]:
    """
    Single source of truth for turning a compliance score into a status and
    risk label. This is the ONLY place that decides Compliant / Needs
    Remediation / Non-Compliant — nothing else (severity counts, LLM
    opinions, UI heuristics) may override it. Every surface (Audit Desk,
    Dashboard, Reports, downloaded document metadata, re-upload validation)
    must call this function on the current score rather than deriving its
    own status independently, so they can never drift out of sync with
    each other or with the underlying score.

    Bands:
        80-100 -> Compliant        / Low risk
        60-79  -> Needs Remediation / Medium risk
        0-59   -> Non-Compliant    / High risk
    """
    if score >= 80:
        return {"status": "Compliant", "risk_level": "Low"}
    if score >= 60:
        return {"status": "Needs Remediation", "risk_level": "Medium"}
    return {"status": "Non-Compliant", "risk_level": "High"}


def calculate_compliance_score(
    violations: List[Any],
    total_exposure_max: float,
    total_affected_users: int,
    confidence: float = 1.0,
) -> Dict[str, Any]:
    """
    Derive the compliance score purely from the current findings.

    Args:
        violations: the violations currently present in the document
                    (i.e. the ones detected in THIS pass over THIS content).
        total_exposure_max: sum of estimated_fine_max across those violations.
        total_affected_users: sum of affected_users_estimate across those violations.
        confidence: analysis confidence for this pass (0-1).

    Returns:
        dict with score, breakdown, risk_points, and per-severity counts.
    """
    critical = sum(1 for v in violations if v.severity == Severity.P1)
    high = sum(1 for v in violations if v.severity == Severity.P2)
    medium = sum(1 for v in violations if v.severity == Severity.P3)
    low = sum(1 for v in violations if v.severity == Severity.P4)

    risk_points = (critical * 15) + (high * 8) + (medium * 4) + (low * 1)

    exposure_penalty = 0
    if total_exposure_max > 10_000_000:
        exposure_penalty = 15
    elif total_exposure_max > 5_000_000:
        exposure_penalty = 10
    elif total_exposure_max > 1_000_000:
        exposure_penalty = 5
    risk_points += exposure_penalty

    affected_users_penalty = 0
    if total_affected_users > 10000:
        affected_users_penalty = 10
    elif total_affected_users > 5000:
        affected_users_penalty = 7
    elif total_affected_users > 1000:
        affected_users_penalty = 3
    risk_points += affected_users_penalty

    confidence_penalty = 5 if confidence < 0.50 else 0
    risk_points += confidence_penalty

    if not violations:
        # Every detected violation has been resolved: the score is
        # deterministically exactly 100, regardless of stale exposure/
        # affected-user carryover or low analysis confidence on this pass.
        score = 100
    else:
        # At least one violation remains: the score must always stay
        # strictly below 100 so a non-zero violation state is never mistaken
        # for "fully clean".  The floor is 1 (not 10) so heavily-violated
        # documents reflect accurate low scores instead of an artificial floor.
        score = max(1, min(99, 100 - risk_points))

    breakdown = {
        "critical_penalty": critical * 15,
        "high_penalty": high * 8,
        "medium_penalty": medium * 4,
        "low_penalty": low * 1,
        "exposure_penalty": exposure_penalty,
        "affected_users_penalty": affected_users_penalty,
        "confidence_penalty": confidence_penalty,
    }

    status_risk = compliance_status_and_risk(score)

    return {
        "score": score,
        "risk_points": risk_points,
        "breakdown": breakdown,
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
        "status": status_risk["status"],
        "risk_level": status_risk["risk_level"],
    }
