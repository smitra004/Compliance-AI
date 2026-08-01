"""Enterprise Policy Repository Service with Lifecycle, Versioning & Hot-Reloading."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import threading
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.abac.policy_validator import PolicyModel
from app.abac.policy_loader import load_policies as load_base_policies


class ExtendedPolicyModel(PolicyModel):
    status: str = Field(default="Published", description="Draft, Review, Approved, Published")
    version: str = Field(default="v1.0.0", description="Semantic version string")
    owner: str = Field(default="security-team@corp.com", description="Policy owner or team")
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
    history: List[Dict[str, str]] = Field(default_factory=list, description="Audit version history")


class PolicyRepository:
    """Thread-safe centralized policy repository service."""

    def __init__(self):
        self._lock = threading.RLock()
        self._policies: Dict[str, ExtendedPolicyModel] = {}
        self._version_history: Dict[str, List[ExtendedPolicyModel]] = {}
        self._load_initial_policies()

    def _load_initial_policies(self):
        """Initializes repository from base policies with enterprise metadata."""
        base_list = load_base_policies()
        with self._lock:
            for p in base_list:
                p_dict = p.model_dump() if hasattr(p, "model_dump") else p.dict()
                ext_p = ExtendedPolicyModel(
                    **p_dict,
                    status="Published",
                    version="v1.0.0",
                    owner=p_dict.get("owner", "security-admin@company.com"),
                    last_updated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    history=[{
                        "version": "v1.0.0",
                        "status": "Published",
                        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "action": "Initial load",
                    }],
                )
                self._policies[ext_p.policy_id] = ext_p
                self._version_history[ext_p.policy_id] = [ext_p.model_copy(deep=True)]

    def get_published_policies(self) -> List[ExtendedPolicyModel]:
        """Returns all currently Published policies for active evaluation."""
        with self._lock:
            return [
                p for p in self._policies.values()
                if p.status == "Published"
            ]

    def get_all_policies(self) -> List[ExtendedPolicyModel]:
        """Returns all policies in repository regardless of status (for registry UI)."""
        with self._lock:
            return list(self._policies.values())

    def get_policy(self, policy_id: str) -> Optional[ExtendedPolicyModel]:
        with self._lock:
            return self._policies.get(policy_id)

    def create_draft(self, policy_data: Dict) -> ExtendedPolicyModel:
        """Creates a new policy draft."""
        with self._lock:
            pid = policy_data.get("policy_id") or f"POL-{len(self._policies) + 101:03d}"
            policy_data["policy_id"] = pid
            policy_data["status"] = "Draft"
            policy_data["version"] = "v1.0.0"
            policy_data["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            ext_p = ExtendedPolicyModel(**policy_data)
            ext_p.history.append({
                "version": "v1.0.0",
                "status": "Draft",
                "timestamp": ext_p.last_updated,
                "action": "Created draft",
            })
            self._policies[pid] = ext_p
            self._version_history[pid] = [ext_p.model_copy(deep=True)]
            return ext_p

    def update_status(self, policy_id: str, target_status: str, updated_by: str = "admin") -> ExtendedPolicyModel:
        """Transitions policy lifecycle: Draft -> Review -> Approved -> Published."""
        valid_transitions = {
            "Draft": ["Review"],
            "Review": ["Approved", "Draft"],
            "Approved": ["Published", "Draft"],
            "Published": ["Review", "Draft"],
        }
        with self._lock:
            policy = self._policies.get(policy_id)
            if not policy:
                raise ValueError(f"Policy {policy_id} not found")

            # Update status
            old_status = policy.status
            policy.status = target_status
            policy.last_updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            # Bump version if publishing
            if target_status == "Published" and old_status != "Published":
                v_parts = policy.version.replace("v", "").split(".")
                major, minor, patch = int(v_parts[0]), int(v_parts[1]), int(v_parts[2])
                policy.version = f"v{major}.{minor + 1}.0"

            policy.history.append({
                "version": policy.version,
                "status": target_status,
                "timestamp": policy.last_updated,
                "action": f"Status changed from {old_status} to {target_status} by {updated_by}",
            })

            # Record version snapshot
            self._version_history[policy_id].append(policy.model_copy(deep=True))
            return policy

    def rollback(self, policy_id: str, target_version: str) -> ExtendedPolicyModel:
        """Rollback policy to a previous version snapshot."""
        with self._lock:
            history_list = self._version_history.get(policy_id, [])
            target = next((p for p in history_list if p.version == target_version), None)
            if not target:
                raise ValueError(f"Version {target_version} not found for policy {policy_id}")

            restored = target.model_copy(deep=True)
            restored.last_updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            restored.history.append({
                "version": restored.version,
                "status": restored.status,
                "timestamp": restored.last_updated,
                "action": f"Rolled back to version {target_version}",
            })
            self._policies[policy_id] = restored
            return restored

    def hot_reload(self) -> List[ExtendedPolicyModel]:
        """Hot-reloads policies instantly without restarting server."""
        self._load_initial_policies()
        return self.get_published_policies()


policy_repository = PolicyRepository()
