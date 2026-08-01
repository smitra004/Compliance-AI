"""Action normalization and validation module."""
from __future__ import annotations

from typing import List, Optional

VALID_ACTIONS: List[str] = [
    "Read",
    "Upload",
    "Download",
    "Delete",
    "Edit",
    "Approve",
    "Reject",
    "Archive",
    "Restore",
    "Share",
    "Export",
    "Print",
    "Run AI Analysis",
    "Generate Report",
    "View Dashboard",
    "Manage Users",
    "Manage Policies",
    "View Audit Logs",
    "Assign Roles",
    "Modify Classification",
]

_ACTION_MAP = {act.lower().replace(" ", "_"): act for act in VALID_ACTIONS}


def normalize_action(action: Optional[str]) -> str:
    if not action:
        return "Read"
    key = str(action).strip().lower().replace(" ", "_")
    return _ACTION_MAP.get(key, action.strip().title())
