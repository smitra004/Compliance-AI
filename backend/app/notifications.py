"""Real-time notifications over WebSocket. Broadcasts scan-completed,
remediation-applied, and injection-blocked events to every connected
dashboard client so the UI's notification bell updates live instead of
polling. Backed by an in-process fan-out; for multi-replica Kubernetes
deployments, back this with a Redis pub/sub channel (the `cache.py` Redis
connection can be reused for that — see UPGRADE_NOTES.md)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    def __init__(self) -> None:
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        payload = {**payload, "timestamp": datetime.now(timezone.utc).isoformat()}
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


async def notifications_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    await websocket.send_text(json.dumps({"type": "connected", "message": "Live notifications online"}))
    try:
        while True:
            # Client doesn't need to send anything; keep the socket open and
            # drain any pings so proxies (e.g. an ingress) don't close it.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
