"""Deterministic Conflict Resolution Engine."""
from __future__ import annotations

from typing import List, Optional, Tuple
from app.abac.decision import Decision
from app.abac.policy_validator import PolicyModel


def resolve_conflicts(matching_policies: List[Tuple[PolicyModel, List[str], List[str]]]) -> Tuple[Decision, Optional[PolicyModel], List[str], List[str]]:
    """
    Evaluates matched policies and resolves conflict using precedence rules:
      1. Explicit Deny overrides Permit
      2. Higher Priority policy overrides Lower Priority
      3. Department Policy overrides Global Policy
      4. Most Specific Policy overrides Generic Policy

    matching_policies: List of tuples (policy, failed_conditions, obligations)
    Returns: (Final Decision, Winning Policy, Consolidated Failed Conditions, Consolidated Obligations)
    """
    if not matching_policies:
        return Decision.NOT_APPLICABLE, None, [], []

    # Sort matching policies by:
    # 1. Deny first (Deny = 1, Permit = 0)
    # 2. Priority descending (e.g. 100 before 50)
    # 3. Department specific (1 if departments defined, 0 if global/null)
    # 4. Actions/Resource specificity (length of constraints)
    def policy_key(item: Tuple[PolicyModel, List[str], List[str]]):
        pol = item[0]
        is_deny = 1 if pol.effect == "Deny" else 0
        priority = pol.priority
        is_dept = 1 if pol.departments else 0
        specificity = (len(pol.actions or []) + len(pol.roles or []))
        return (is_deny, priority, is_dept, specificity)

    sorted_matches = sorted(matching_policies, key=policy_key, reverse=True)
    winner_policy, failed_conds, obligations = sorted_matches[0]

    # Consolidate obligations across all matching permit policies
    all_obligations: List[str] = []
    for pol, _, ob_list in sorted_matches:
        for ob in ob_list:
            if ob not in all_obligations:
                all_obligations.append(ob)

    final_decision = Decision.DENY if winner_policy.effect == "Deny" else Decision.PERMIT
    return final_decision, winner_policy, failed_conds, all_obligations
