"""Dynamic Policy Loader supporting hot reloading from JSON policy files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from app.abac.policy_validator import PolicyModel, validate_policy_dict
from app.abac.policy_cache import PolicyCache


POLICIES_DIR = Path(__file__).parent / "policies"
_cache = PolicyCache(ttl_seconds=300.0)


def load_policies(force_reload: bool = False) -> List[PolicyModel]:
    """Loads all JSON policies from app/abac/policies/ directory with hot-reloading capability."""
    global _cache

    if not force_reload and not _cache.is_expired():
        # Check if any file modified since last load
        modified = False
        for path in POLICIES_DIR.glob("*.json"):
            mtime = path.stat().st_mtime
            if mtime > _cache._file_mtimes.get(str(path), 0.0):
                modified = True
                break
        if not modified:
            return _cache.get_policies()

    policies: List[PolicyModel] = []
    new_mtimes: Dict[str, float] = {}

    if POLICIES_DIR.exists():
        for json_file in POLICIES_DIR.glob("*.json"):
            mtime = json_file.stat().st_mtime
            new_mtimes[str(json_file)] = mtime
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            policies.append(validate_policy_dict(item))
                    elif isinstance(data, dict):
                        policies.append(validate_policy_dict(data))
            except Exception as e:
                print(f"[ABAC] Error loading policy file {json_file.name}: {e}")

    _cache.set_policies(policies, new_mtimes)
    return policies


def reload_policies() -> List[PolicyModel]:
    """Forces an immediate hot-reload of all JSON policies without app restart."""
    return load_policies(force_reload=True)
