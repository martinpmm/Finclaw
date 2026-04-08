"""Chat routes: WebSocket for real-time chat + session history."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["chat"])


@router.websocket("/ws/chat")
async def chat_websocket(ws: WebSocket, request: Request):
    """
    WebSocket endpoint for real-time chat with the AI agent.

    Protocol (JSON messages):
      Client → Server: {"content": "user message text"}
      Server → Client: {"type": "message", "content": "agent response"}
      Server → Client: {"type": "progress", "content": "partial text", "is_tool_hint": false}
    """
    await ws.accept()
    client_id = str(uuid.uuid4())[:12]
    web_channel = request.app.state.web_channel

    web_channel.register(client_id, ws)

    # Send the client their ID so they can reference their session
    await ws.send_json({"type": "connected", "client_id": client_id})

    try:
        while True:
            data = await ws.receive_json()
            content = data.get("content", "").strip()
            if not content:
                continue
            await web_channel.publish_inbound(client_id, content)
    except WebSocketDisconnect:
        pass
    finally:
        web_channel.unregister(client_id)


@router.get("/chat/sessions")
async def list_sessions(request: Request):
    """List all chat sessions."""
    session_manager = request.app.state.session_manager
    sessions = session_manager.list_sessions()
    # Filter to show only web sessions, or all if needed
    return {"sessions": sessions}


@router.get("/chat/sessions/{session_key:path}/messages")
async def get_session_messages(session_key: str, request: Request):
    """Get messages for a specific session."""
    session_manager = request.app.state.session_manager
    session = session_manager.get_or_create(session_key)
    messages = []
    for msg in session.messages:
        if msg.get("role") in ("user", "assistant"):
            messages.append({
                "role": msg["role"],
                "content": msg.get("content", ""),
                "timestamp": msg.get("timestamp"),
            })
    return {"messages": messages, "key": session_key}
