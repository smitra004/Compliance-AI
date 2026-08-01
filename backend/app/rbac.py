"""RBAC — role/permission checks, plus small department- and
resource-isolation helpers used across the scan/audit/dashboard
endpoints.

Role -> permission grants are kept in lockstep with
frontend/src/utils/permissions.js, which is the single source of truth
for every role and the permissions granted to it.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException

from app import abac
from app.auth import require_bearer


# ─── Role -> permissions mapping (mirrors permissions.js) ──────────────────
ROLE_PERMISSIONS: Dict[str, set] = {

    "central_admin": {
        "dashboard",
        "upload",
        "scan",
        "users",
        "reports",
        "audit",
        "policy_create",
        "policy_delete",
        "policy_edit",
        "remediation",
        "simulator",
        "report_delete",
    },

    "admin": {
        "dashboard",
        "upload",
        "scan",
        "users",
        "reports",
        "audit",
        "policy_create",
        "policy_edit",
        "remediation",
        "simulator",
        "report_delete",
    },

    "manager": {
        "dashboard",
        "reports",
        "audit",
        "policy_create",
        "policy_edit",
        "simulator",
        "upload",
        "scan",
    },

    "auditor": {
        "dashboard",
        "reports",
        "audit",
    },

    "viewer": {
        "dashboard",
    },
}


# ─── Backend-vocabulary aliases ─────────────────────────────────────────────
# A handful of endpoints check permissions under older backend-only names
# ("view", "manage") rather than the permissions.js names directly. Each
# alias resolves to the canonical permissions.js grant(s) that satisfy it.
PERMISSION_ALIASES: Dict[str, set] = {
    "view": {"dashboard"},
    "manage": {"policy_edit", "policy_delete"},
}


def _is_granted(permissions: set, permission: str) -> bool:
    if "*" in permissions:
        return True
    if permission in permissions:
        return True
    aliases = PERMISSION_ALIASES.get(permission)
    return bool(aliases and (aliases & permissions))


def require(permission: str):
    """
    Usage:
        user: dict = Depends(require("view"))

    Verifies the JWT, checks the user's role against ROLE_PERMISSIONS
    (i.e. permissions.js), and — on success — returns the FULL claims
    dict (id, username, role, department, status, permissions), not
    just the role string. Endpoints rely on this to read
    user["username"], user["department"], etc. straight off the
    dependency result.
    """

    def dependency(claims: dict = Depends(require_bearer)) -> dict:
        role = claims.get("role")

        if role is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token",
            )

        permissions = ROLE_PERMISSIONS.get(role)

        if permissions is None:
            raise HTTPException(
                status_code=403,
                detail="Unknown role",
            )

        if not _is_granted(permissions, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission '{permission}' required",
            )

        return claims

    return dependency


def get_user_permissions(user: dict) -> List[str]:
    """The full, resolved permission list for a user's role — the same
    list permissions.js grants that role on the frontend. Useful for
    exposing to the client (e.g. from /api/auth/me) so the UI can render
    purely off `permissions` rather than re-deriving it from `role`."""
    return sorted(ROLE_PERMISSIONS.get(user.get("role"), set()))


# ─── Department- and resource-isolation helpers ─────────────────────────────
# central_admin sees/touches everything; every other role is scoped to
# their own department. These operate on ScanRecord / AuditEntry objects
# as well as plain dicts, so callers can pass `rec.__dict__` or a raw dict
# interchangeably.

def _dept_of(item: Any) -> Optional[str]:
    if isinstance(item, dict):
        return item.get("department")
    return getattr(item, "department", None)


def filter_documents(user: dict, items: List[Any]) -> List[Any]:
    """Scope a list of scans/audit entries to the caller's department.
    central_admin gets the unfiltered list."""
    if user.get("role") == "central_admin":
        return items
    return [item for item in items if _dept_of(item) == user.get("department")]


def has_document_access(user: dict, resource: Dict[str, Any]) -> bool:
    """Department-scoping check only. True if the caller may act on a
    single resource (a scan, a predicted-department upload target, etc).
    central_admin always passes."""
    if user.get("role") == "central_admin":
        return True
    return resource.get("department") == user.get("department")


def can_view_document(user: dict, resource: Dict[str, Any]) -> bool:
    """Full read gate for a single document: department scoping AND
    resource-level ABAC (owner override / classification / visibility)
    must both pass. Use this instead of has_document_access() wherever
    the resource dict may carry owner/classification/visibility fields
    (once ScanRecord grows them — see app/models.py)."""
    if not has_document_access(user, resource):
        return False
    user_attrs = abac.normalize_attributes(user)
    user_attrs["username"] = user.get("username")
    allowed, _reason = abac.evaluate_resource(user_attrs, resource)
    return allowed


def can_delete_document(user: dict, resource: Dict[str, Any]) -> bool:
    """Deletion gate for a single document. The `report_delete`
    permission itself is enforced separately via
    Depends(require("report_delete")) at the route level; this re-checks
    the department/ownership half so a department-scoped admin can't
    delete another department's scan even though their role holds
    report_delete."""
    return has_document_access(user, resource)
