"""Centralized Clearance Management Service for Enterprise ABAC."""
from __future__ import annotations

import json
import threading
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ClearanceLevelMapping(BaseModel):
    name: str
    rank: int
    description: str = ""


DEFAULT_CLEARANCE_REGISTRY: Dict[str, int] = {
    "Public": 1,
    "Internal": 2,
    "Confidential": 3,
    "Restricted": 4,
    "Top Secret": 5,
}

# Alias map for normalized case-insensitive lookups
ALIAS_MAP: Dict[str, str] = {
    "public": "Public",
    "internal": "Internal",
    "confidential": "Confidential",
    "highly_confidential": "Restricted",
    "highly confidential": "Restricted",
    "restricted": "Restricted",
    "top_secret": "Top Secret",
    "top secret": "Top Secret",
    "secret": "Restricted",
}


class CentralizedClearanceRegistry:
    """Thread-safe enterprise clearance registry for dynamic clearance rank management."""

    def __init__(self, initial_mappings: Optional[Dict[str, int]] = None):
        self._lock = threading.RLock()
        self._mappings: Dict[str, int] = dict(initial_mappings or DEFAULT_CLEARANCE_REGISTRY)

    def get_mappings(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._mappings)

    def get_rank(self, clearance_name: str) -> int:
        """Resolve numerical rank for a given clearance level name."""
        if not clearance_name:
            return 1

        raw_str = str(clearance_name).strip()
        with self._lock:
            # 1. Exact match
            if raw_str in self._mappings:
                return self._mappings[raw_str]

            # 2. Case-insensitive match
            for k, v in self._mappings.items():
                if k.lower() == raw_str.lower():
                    return v

            # 3. Alias match
            norm_key = raw_str.lower()
            if norm_key in ALIAS_MAP:
                canonical = ALIAS_MAP[norm_key]
                if canonical in self._mappings:
                    return self._mappings[canonical]

            # Fallback default rank
            return 1

    def update_mappings(self, new_mappings: Dict[str, int]) -> Dict[str, int]:
        """Update clearance mappings dynamically without code changes or server restart."""
        with self._lock:
            validated = {}
            for name, rank in new_mappings.items():
                if not name or not isinstance(rank, int):
                    continue
                validated[str(name).strip()] = max(0, rank)
            
            if validated:
                self._mappings = validated
            return dict(self._mappings)

    def list_levels(self) -> List[ClearanceLevelMapping]:
        with self._lock:
            sorted_items = sorted(self._mappings.items(), key=lambda x: x[1])
            return [
                ClearanceLevelMapping(
                    name=name,
                    rank=rank,
                    description=f"Level {rank} clearance boundary",
                )
                for name, rank in sorted_items
            ]


# Singleton instance
clearance_registry = CentralizedClearanceRegistry()
