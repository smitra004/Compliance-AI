"""Orchestrator: chains parse -> Multi-Agent Council into a single ScanRecord."""
from __future__ import annotations

from app import config
from app.models import ScanRecord
from app.pipeline.parser import parse_document
from app.pipeline.agents import run_multi_agent_council


async def run_pipeline(
    filename,
    data,
    uploaded_by,
    department,
    tenant_id=config.DEFAULT_TENANT
) -> ScanRecord:
    if config.ORCHESTRATOR_ENGINE == "langgraph":
        try:
            from app.pipeline.langgraph_orchestrator import run_pipeline_langgraph
            return await run_pipeline_langgraph(
                filename,
                data,
                uploaded_by,
                department,
                tenant_id
            )
        except Exception as e:  # noqa: BLE001 — never let an engine swap break a scan
            print(f"[orchestrator] LangGraph engine failed ({e}); falling back to native pipeline")

    text = parse_document(filename, data)
    if not text.strip():
        text = "(empty or unreadable document)"

    record = await run_multi_agent_council(
        filename,
        text,
        uploaded_by,
        department,
        tenant_id
    )
    import hashlib
    record.sha256_hash = hashlib.sha256(data).hexdigest()
    return record

