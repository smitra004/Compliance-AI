"""Deterministic policy conflict resolution. When two violations target
the same excerpt, the higher-precedence regulation wins. No LLM decides
precedence — every decision is auditable."""
from __future__ import annotations

from typing import List

from app.config import REGULATION_PRECEDENCE
from app.models import Violation


def resolve_conflicts(violations: List[Violation]) -> List[Violation]:
    by_excerpt: dict[str, Violation] = {}
    for v in violations:
        key = v.excerpt[:60].lower()
        existing = by_excerpt.get(key)
        if existing is None:
            by_excerpt[key] = v
            continue
        # keep the higher-precedence (lower number) regulation
        if REGULATION_PRECEDENCE[v.source_regulation.value] < \
                REGULATION_PRECEDENCE[existing.source_regulation.value]:
            by_excerpt[key] = v
    # stable sort by severity weight (P1 first)
    return sorted(by_excerpt.values(), key=lambda x: -x.severity.weight)
