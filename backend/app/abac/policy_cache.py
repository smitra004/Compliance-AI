"""High-performance policy caching layer."""
from __future__ import annotations

import time
from typing import Dict, List, Optional
from app.abac.policy_validator import PolicyModel


class PolicyCache:
    """Thread-safe in-memory policy cache with TTL and hot-reloading support."""

    def __init__(self, ttl_seconds: float = 300.0):
        self.ttl_seconds = ttl_seconds
        self._policies: List[PolicyModel] = []
        self._last_loaded: float = 0.0
        self._file_mtimes: Dict[str, float] = {}

    def get_policies(self) -> List[PolicyModel]:
        return self._policies

    def set_policies(self, policies: List[PolicyModel], file_mtimes: Dict[str, float]):
        self._policies = policies
        self._file_mtimes = file_mtimes
        self._last_loaded = time.time()

    def is_expired(self) -> bool:
        if not self._policies:
            return True
        return (time.time() - self._last_loaded) > self.ttl_seconds

    def clear(self):
        self._policies = []
        self._last_loaded = 0.0
        self._file_mtimes = {}
