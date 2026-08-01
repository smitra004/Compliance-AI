"""Core Policy Evaluation Engine for ABAC."""
from __future__ import annotations

import time
from typing import List, Optional, Tuple

from app.abac.decision import ABACDecisionResult, Decision
from app.abac.attributes.subject import SubjectAttributes
from app.abac.attributes.resource import ResourceAttributes
from app.abac.attributes.environment import EnvironmentAttributes
from app.abac.attributes.action import normalize_action
from app.abac.policy_loader import load_policies
from app.abac.policy_validator import PolicyModel
from app.abac.conflict_resolver import resolve_conflicts
from app.abac.conditions.time import evaluate_time_condition
from app.abac.conditions.location import evaluate_location_condition
from app.abac.conditions.device import evaluate_device_condition
from app.abac.conditions.ownership import evaluate_ownership_condition
from app.abac.conditions.classification import evaluate_classification_condition
from app.abac.conditions.department import evaluate_department_condition
from app.abac.conditions.clearance import evaluate_clearance_condition
from app.abac.conditions.risk import calculate_risk_score, evaluate_risk_condition
from app.abac.conditions.mfa import evaluate_mfa_condition


def evaluate_policy_target(policy: PolicyModel, subject: SubjectAttributes, resource: ResourceAttributes, action: str) -> bool:
    """Checks if a policy applies to the given subject, resource, and action target."""
    # Action check
    if policy.actions:
        norm_actions = [a.lower().replace(" ", "_") for a in policy.actions]
        if action.lower().replace(" ", "_") not in norm_actions and "*" not in norm_actions:
            return False

    # Role check
    if policy.roles:
        if subject.role not in policy.roles and "*" not in policy.roles:
            return False

    # Department check
    if policy.departments:
        if subject.department not in policy.departments and "Global" not in policy.departments and "*" not in policy.departments:
            return False

    # Resource constraints check
    if policy.resource:
        r = policy.resource
        if r.department and resource.department not in r.department and "General" not in r.department and "*" not in r.department:
            return False
        if r.classification and resource.classification not in r.classification and "*" not in r.classification:
            return False
        if r.regulation and resource.regulation not in r.regulation and "*" not in r.regulation:
            return False
        if r.contains_pii is True and not resource.contains_pii:
            return False
        if r.contains_financial_data is True and not resource.contains_financial_data:
            return False

    return True


def evaluate_policy_conditions(policy: PolicyModel, subject: SubjectAttributes, resource: ResourceAttributes, env: EnvironmentAttributes, risk_score: int) -> Tuple[bool, List[str]]:
    """Evaluates all conditions configured on a policy."""
    failed: List[str] = []
    conds = policy.conditions or {}

    # Time condition
    if "business_hours" in conds or "time" in conds:
        val = conds.get("business_hours") or conds.get("time")
        ok, msg = evaluate_time_condition(val, env)
        if not ok:
            failed.append(msg)

    # Location condition
    if "vpn_required" in conds or "location" in conds or "allowed_countries" in conds:
        val = conds if ("vpn_required" in conds or "allowed_countries" in conds) else conds.get("location")
        ok, msg = evaluate_location_condition(val, env)
        if not ok:
            failed.append(msg)

    # Device condition
    if "min_device_trust" in conds or "device_managed_required" in conds:
        ok, msg = evaluate_device_condition(conds, env)
        if not ok:
            failed.append(msg)

    # Ownership condition
    if "owner_only" in conds:
        ok, msg = evaluate_ownership_condition(conds.get("owner_only"), subject, resource)
        if not ok:
            failed.append(msg)

    # Classification vs clearance rank check
    ok, msg = evaluate_classification_condition(None, subject, resource)
    if not ok:
        failed.append(msg)

    # Department restriction check
    if "department_restricted" in conds:
        ok, msg = evaluate_department_condition(conds.get("department_restricted"), subject, resource)
        if not ok:
            failed.append(msg)

    # Clearance level condition
    if "min_clearance" in conds:
        ok, msg = evaluate_clearance_condition(conds.get("min_clearance"), subject)
        if not ok:
            failed.append(msg)

    # Risk score condition
    if "max_risk_score" in conds:
        ok, msg = evaluate_risk_condition(conds.get("max_risk_score"), risk_score, is_min=False)
        if not ok:
            failed.append(msg)
    if "min_risk_score" in conds:
        ok, msg = evaluate_risk_condition(conds.get("min_risk_score"), risk_score, is_min=True)
        if not ok:
            failed.append(msg)


    # MFA condition
    if "mfa_required" in conds:
        ok, msg = evaluate_mfa_condition(conds.get("mfa_required"), subject)
        if not ok:
            failed.append(msg)

    return len(failed) == 0, failed


def evaluate_abac_request(
    subject: SubjectAttributes,
    resource: ResourceAttributes,
    environment: EnvironmentAttributes,
    action: str,
) -> ABACDecisionResult:
    """Main evaluation loop for ABAC authorization requests."""
    t0 = time.time()
    action = normalize_action(action)

    # 1. Compute dynamic risk score
    risk_score = calculate_risk_score(subject, environment)

    # 2. Central Admin default bypass unless explicit Deny policy matches
    # 3. Risk Threshold Enforcement: Risk > 80 results in automatic Deny
    if risk_score >= 80 and subject.role != "central_admin":
        exec_ms = (time.time() - t0) * 1000.0
        return ABACDecisionResult(
            decision=Decision.DENY,
            matched_policy="RISK-ENGINE-DENY",
            failed_conditions=[f"Risk score {risk_score} exceeds maximum safe threshold (80)."],
            risk_score=risk_score,
            reason="High-risk request detected by Risk Adaptive Access Control.",
            obligations=["Require MFA", "Log High Severity Event"],
            execution_time_ms=exec_ms,
            evaluated_policies=["RISK-ENGINE"],
        )

    # 4. Load all configured policies
    policies = load_policies()
    evaluated_policy_ids: List[str] = []
    matched_candidates: List[Tuple[PolicyModel, List[str], List[str]]] = []

    for pol in policies:
        evaluated_policy_ids.append(pol.policy_id)

        # Check target applicability
        if not evaluate_policy_target(pol, subject, resource, action):
            continue

        # Check conditions
        cond_ok, failed_conds = evaluate_policy_conditions(pol, subject, resource, environment, risk_score)

        if cond_ok:
            # Policy matched cleanly with all conditions satisfied
            matched_candidates.append((pol, [], pol.obligations or []))


    exec_ms = (time.time() - t0) * 1000.0

    # 5. Resolve conflicts
    if not matched_candidates:
        # Fallback default: If Central Admin, Permit; otherwise Deny
        if subject.role == "central_admin":
            return ABACDecisionResult(
                decision=Decision.PERMIT,
                matched_policy="DEFAULT-ADMIN-BYPASS",
                failed_conditions=[],
                risk_score=risk_score,
                reason="Central Admin default permit.",
                obligations=[],
                execution_time_ms=exec_ms,
                evaluated_policies=evaluated_policy_ids,
            )

        # Baseline clearance rank check fallback
        if subject.clearance_rank < resource.classification_rank:
            return ABACDecisionResult(
                decision=Decision.DENY,
                matched_policy="BASELINE-CLEARANCE-DENY",
                failed_conditions=[f"Required clearance rank ≥ {resource.classification_rank}, held rank {subject.clearance_rank}."],
                risk_score=risk_score,
                reason="Security clearance level is lower than resource classification.",
                obligations=["Require MFA"],
                execution_time_ms=exec_ms,
                evaluated_policies=evaluated_policy_ids,
            )

        return ABACDecisionResult(
            decision=Decision.PERMIT,
            matched_policy="DEFAULT-BASELINE-PERMIT",
            failed_conditions=[],
            risk_score=risk_score,
            reason="Access permitted under default baseline zero-trust rule.",
            obligations=["Mask Sensitive Fields"] if resource.contains_pii else [],
            execution_time_ms=exec_ms,
            evaluated_policies=evaluated_policy_ids,
        )

    final_decision, winner, failed_conds, obligations = resolve_conflicts(matched_candidates)

    # Risk-based obligation escalation (31 - 60: Require MFA; 61 - 80: Read Only / Restrictions)
    if 31 <= risk_score <= 60 and "Require MFA" not in obligations:
        obligations.append("Require MFA")
    if 61 <= risk_score <= 80:
        if "Read Only" not in obligations:
            obligations.append("Read Only")
        if "Disable Download" not in obligations:
            obligations.append("Disable Download")

    reason_str = (
        f"Access DENIED by policy {winner.policy_id} ({winner.name})."
        if final_decision == Decision.DENY
        else f"Access PERMITTED by policy {winner.policy_id} ({winner.name})."
    )

    return ABACDecisionResult(
        decision=final_decision,
        matched_policy=winner.policy_id if winner else "NONE",
        failed_conditions=failed_conds,
        risk_score=risk_score,
        reason=reason_str,
        obligations=obligations,
        execution_time_ms=exec_ms,
        evaluated_policies=evaluated_policy_ids,
    )
