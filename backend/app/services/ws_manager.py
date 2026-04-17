from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import WebSocket


class InterviewWebSocketManager:
    def __init__(self) -> None:
        self._connections: dict[UUID, dict[WebSocket, dict[str, Any]]] = defaultdict(dict)

    async def connect(
        self,
        session_id: UUID,
        websocket: WebSocket,
        *,
        user_id: UUID | None = None,
        role: str = 'unknown',
    ) -> dict[str, Any]:
        await websocket.accept()
        meta = {
            'user_id': user_id or uuid4(),
            'role': role,
            'joined_at': datetime.now(timezone.utc),
        }
        self._connections[session_id][websocket] = meta
        return meta

    def disconnect(self, session_id: UUID, websocket: WebSocket) -> None:
        session_connections = self._connections.get(session_id)
        if not session_connections:
            return
        session_connections.pop(websocket, None)
        if not session_connections:
            self._connections.pop(session_id, None)

    def participants(self, session_id: UUID) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for meta in self._connections.get(session_id, {}).values():
            joined_at = meta['joined_at']
            items.append(
                {
                    'user_id': meta['user_id'],
                    'role': meta['role'],
                    'joined_at': joined_at.isoformat() if hasattr(joined_at, 'isoformat') else joined_at,
                }
            )
        return items

    async def send(self, websocket: WebSocket, message_type: str, payload: dict[str, Any]) -> None:
        await websocket.send_json({'type': message_type, 'payload': payload})

    async def broadcast(
        self,
        session_id: UUID,
        message_type: str,
        payload: dict[str, Any],
        *,
        exclude_user_id: UUID | None = None,
    ) -> None:
        sockets = list(self._connections.get(session_id, {}).items())
        for socket, meta in sockets:
            if exclude_user_id and meta.get('user_id') == exclude_user_id:
                continue
            try:
                await socket.send_json({'type': message_type, 'payload': payload})
            except Exception:
                self.disconnect(session_id, socket)


ws_manager = InterviewWebSocketManager()
