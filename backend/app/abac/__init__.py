"""
Enterprise ABAC — Attribute-Based Access Control Service
Provides centralized authorization evaluation via `AuthorizationService.evaluate()` based on real employee attributes fetched from the database.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple, Union
from app.employee_db import get_employee_access_profile, ensure_abac_profile
from app.user_db import get_user_by_identifier

# Clearance rank mappings
CLEARANCE_RANKS = {
    "public": 1,
    "internal": 2,
    "confidential": 3,
    "restricted": 4,
    "top secret": 5,
}

REGULATION_CANONICAL = {
    "gdpr": "GDPR",
    "sox": "SOX",
    "iso27001": "ISO 27001",
    "iso 27001": "ISO 27001",
    "hipaa": "HIPAA",
    "internal_security": "Internal Security",
    "internal security": "Internal Security",
    "internal_hr": "Internal HR",
    "internal hr": "Internal HR",
    "internalpolicy": "Internal Security",
    "custom": "Internal Security",
}


class AuthorizationService:
    @staticmethod
    def evaluate(
        user_identifier: Union[int, str, dict],
        resource: Dict[str, Any],
        action: str = "view",
    ) -> Dict[str, Any]:
        """
        Centralized Authorization Engine evaluating 6 sequential checks:
          1. Clearance Level Rank vs Document Classification
          2. Document Regulation vs Allowed Regulations
          3. Single-Department comparison (User department vs Document department)
          4. Action Permission check (view, download, export, delete)
          5. PII Data Masking check
          6. Financial Data Masking check

        Returns:
          {
            "decision": "PERMIT" | "DENY",
            "reason": "Detailed explainability reason",
            "mask_pii": bool,
            "mask_financial": bool,
            "user_attributes": dict
          }
        """
        # Resolve user profile
        user_profile = None
        if isinstance(user_identifier, dict):
            user_id = user_identifier.get("id") or user_identifier.get("user_id")
            if not user_id and user_identifier.get("username"):
                db_user = get_user_by_identifier(user_identifier["username"])
                if db_user:
                    user_id = db_user["id"]
            if user_id:
                user_profile = get_employee_access_profile(int(user_id))
        elif isinstance(user_identifier, (int, str)):
            if str(user_identifier).isdigit():
                user_profile = get_employee_access_profile(int(user_identifier))
            else:
                db_user = get_user_by_identifier(str(user_identifier))
                if db_user:
                    user_profile = get_employee_access_profile(db_user["id"])

        if not user_profile:
            return {
                "decision": "DENY",
                "reason": "DENY: Employee profile not found in database",
                "mask_pii": False,
                "mask_financial": False,
            }

        # Central Admin bypass for administrative access, but permissions still apply
        is_central_admin = user_profile.get("role") == "central_admin"

        # ─── Check 1: Employee Clearance Rank vs Document Classification ─────
        doc_classification = str(
            resource.get("classification") or resource.get("clearance_level") or "Internal"
        ).lower()
        doc_rank = CLEARANCE_RANKS.get(doc_classification, 2)
        user_rank = user_profile.get("clearance_rank", 2)

        if user_rank < doc_rank and not is_central_admin:
            return {
                "decision": "DENY",
                "reason": f"DENY: Insufficient clearance level (Employee: '{user_profile.get('clearance_level')}' < Document: '{doc_classification.title()}')",
                "mask_pii": False,
                "mask_financial": False,
                "user_attributes": user_profile,
            }

        # ─── Check 2: Document Regulation Check ──────────────────────────────
        raw_doc_reg = str(resource.get("regulation") or resource.get("source_regulation") or "").lower()
        if raw_doc_reg and raw_doc_reg != "none" and not is_central_admin:
            doc_reg = REGULATION_CANONICAL.get(raw_doc_reg, raw_doc_reg.upper())
            allowed_regs = user_profile.get("allowed_regulations", [])
            allowed_regs_normalized = [r.upper().replace(" ", "").replace("_", "") for r in allowed_regs]
            target_reg_normalized = doc_reg.upper().replace(" ", "").replace("_", "")

            if target_reg_normalized not in allowed_regs_normalized:
                return {
                    "decision": "DENY",
                    "reason": f"DENY: Regulation '{doc_reg}' not assigned to employee",
                    "mask_pii": False,
                    "mask_financial": False,
                    "user_attributes": user_profile,
                }

        # ─── Check 3: Single Department Comparison ────────────────────────────
        doc_dept = resource.get("department")
        if doc_dept and doc_dept != "General" and not is_central_admin:
            user_dept = user_profile.get("department", "General")
            if user_dept != doc_dept:
                return {
                    "decision": "DENY",
                    "reason": f"DENY: Employee department '{user_dept}' access not granted for document department '{doc_dept}'",
                    "mask_pii": False,
                    "mask_financial": False,
                    "user_attributes": user_profile,
                }

        # ─── Check 4: Action Permissions Check ───────────────────────────────
        action_clean = action.lower().strip()
        perms = user_profile.get("permissions", {})

        action_perm_map = {
            "view": perms.get("can_view_reports", True),
            "view_reports": perms.get("can_view_reports", True),
            "download": perms.get("can_download", False),
            "export": perms.get("can_export", False),
            "delete": perms.get("can_delete", False),
        }

        has_perm = action_perm_map.get(action_clean, True)
        if not has_perm:
            return {
                "decision": "DENY",
                "reason": f"DENY: Permission '{action_clean}' disabled for employee",
                "mask_pii": False,
                "mask_financial": False,
                "user_attributes": user_profile,
            }

        # ─── Check 5 & 6: Data Masking Checks ───────────────────────────────
        contains_pii = bool(resource.get("contains_pii")) or bool(resource.get("has_pii"))
        contains_financial = bool(resource.get("contains_financial")) or bool(resource.get("has_financial"))

        raw_text = str(resource.get("raw_text") or resource.get("content") or resource.get("summary") or "")
        if not contains_pii and any(kw in raw_text.lower() for kw in ["email", "phone", "candidate", "ssn", "address", "pii"]):
            contains_pii = True

        if not contains_financial and any(kw in raw_text.lower() for kw in ["salary", "compensation", "revenue", "$", "budget", "financial"]):
            contains_financial = True

        mask_pii = contains_pii and not perms.get("can_view_pii", False)
        mask_financial = contains_financial and not perms.get("can_view_financial", False)

        return {
            "decision": "PERMIT",
            "reason": "PERMIT: Access granted based on employee database attributes",
            "mask_pii": mask_pii,
            "mask_financial": mask_financial,
            "user_attributes": user_profile,
        }


def normalize_attributes(attrs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    attrs = attrs or {}
    return {
        "department": str(attrs.get("department", "")).strip().lower(),
        "region": str(attrs.get("region", "")).strip().lower(),
        "clearance_level": str(attrs.get("clearance_level", "")).strip().lower(),
        "role": str(attrs.get("role", "")).strip().lower(),
    }


def evaluate(user_attrs: Dict[str, Any], regulation: str) -> Tuple[bool, str]:
    res = AuthorizationService.evaluate(user_attrs, {"regulation": regulation}, action="view")
    return res["decision"] == "PERMIT", res["reason"]


def evaluate_resource(user_attrs: Dict[str, Any], resource: Dict[str, Any]) -> Tuple[bool, str]:
    res = AuthorizationService.evaluate(user_attrs, resource, action="view")
    return res["decision"] == "PERMIT", res["reason"]


__all__ = [
    "AuthorizationService",
    "normalize_attributes",
    "evaluate",
    "evaluate_resource",
]