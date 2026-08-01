"""LangGraph orchestration of the scan pipeline.

`orchestrator.py` runs the pipeline as a straight-line async function. This
module expresses the same stages — parse → multi-agent council → hash/seal —
as an explicit `langgraph.graph.StateGraph`, which is what you want once the
pipeline grows conditional branches (e.g. skip the LLM tier when the rule
engine already found a P1, or fan out per-regulation agents as separate
graph nodes that can retry independently).

Selected via `ORCHESTRATOR_ENGINE=langgraph` (default remains `native`,
i.e. `orchestrator.run_pipeline`) so the existing hand-rolled path keeps
working unchanged. Both engines return an identical `ScanRecord`.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, TypedDict

from app import config
from app.models import ScanRecord
from app.pipeline.parser import parse_document
from app.pipeline.agents import run_multi_agent_council


class PipelineState(TypedDict, total=False):
    filename: str
    data: bytes
    uploaded_by: str
    department: str
    tenant_id: str
    text: str
    record: ScanRecord


def _node_parse(state: PipelineState) -> Dict[str, Any]:
    text = parse_document(state["filename"], state["data"])
    if not text.strip():
        text = "(empty or unreadable document)"
    return {"text": text}


async def _node_council(state: PipelineState) -> Dict[str, Any]:
    record = await run_multi_agent_council(
        state["filename"],
        state["text"],
        state["uploaded_by"],
        state["department"],
        state["tenant_id"]
    )
    return {"record": record}


def _node_seal(state: PipelineState) -> Dict[str, Any]:
    record = state["record"]
    record.sha256_hash = hashlib.sha256(state["data"]).hexdigest()
    return {"record": record}


def _build_graph():
    from langgraph.graph import StateGraph, END
    graph = StateGraph(PipelineState)
    graph.add_node("parse", _node_parse)
    graph.add_node("council", _node_council)
    graph.add_node("seal", _node_seal)
    graph.set_entry_point("parse")
    graph.add_edge("parse", "council")
    graph.add_edge("council", "seal")
    graph.add_edge("seal", END)
    return graph.compile()


_compiled_graph = None


def _get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = _build_graph()
    return _compiled_graph


async def run_pipeline_langgraph(
        filename,
        data,
        uploaded_by,
        department,
        tenant_id=config.DEFAULT_TENANT,
    ) -> ScanRecord:
    graph = _get_graph()
    result = await graph.ainvoke({
        "filename": filename,
        "data": data,
        "uploaded_by": uploaded_by,
        "department": department,
        "tenant_id": tenant_id,
    })
    return result["record"]
