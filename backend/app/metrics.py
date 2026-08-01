"""Prometheus metrics. Exposes `/metrics` on the FastAPI app for Prometheus
to scrape; `monitoring/grafana/` ships a dashboard that reads from it."""
from __future__ import annotations

from prometheus_client import Counter, Histogram

from app import config

SCAN_COUNTER = Counter(
    "complianceai_scans_total", "Total documents scanned", ["tenant", "outcome"]
)
VIOLATION_COUNTER = Counter(
    "complianceai_violations_total", "Total violations detected", ["severity", "regulation"]
)
SCAN_DURATION = Histogram(
    "complianceai_scan_duration_seconds", "Time to run the full scan pipeline"
)
REMEDIATION_COUNTER = Counter(
    "complianceai_remediations_total", "Total AI remediations applied"
)
AUTH_FAILURE_COUNTER = Counter(
    "complianceai_auth_failures_total", "Rejected auth attempts (bad role/token)"
)


def instrument(app) -> None:
    if not config.PROMETHEUS_ENABLED:
        return
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    except Exception as e:  # noqa: BLE001
        print(f"[metrics] Prometheus instrumentation unavailable ({e}); /metrics disabled")
