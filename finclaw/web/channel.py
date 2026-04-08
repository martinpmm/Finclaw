"""Web channel: bridges WebSocket connections to the Finclaw message bus."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket
from loguru import logger

from finclaw.bus.events import InboundMessage, OutboundMessage
from finclaw.bus.queue import MessageBus


class WebChannel:
    """
    Manages WebSocket connections for the web UI.

    Unlike other channels (Telegram, Slack, etc.) that poll or listen to
    external services, WebChannel is driven by incoming WebSocket connections
    from the browser. It registers/unregisters connections and routes
    outbound messages from the bus to the correct WebSocket client.
    """

    name = "web"

    def __init__(self, bus: MessageBus):
        self.bus = bus
        self._connections: dict[str, WebSocket] = {}
        self._running = False

    def register(self, client_id: str, ws: WebSocket) -> None:
        """Register a WebSocket connection."""
        self._connections[client_id] = ws
        logger.info("Web client connected: {}", client_id)

    def unregister(self, client_id: str) -> None:
        """Unregister a WebSocket connection."""
        self._connections.pop(client_id, None)
        logger.info("Web client disconnected: {}", client_id)

    async def send_to_client(self, client_id: str, data: dict[str, Any]) -> None:
        """Send a JSON message to a specific client."""
        ws = self._connections.get(client_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.unregister(client_id)

    async def publish_inbound(self, client_id: str, content: str, media: list[str] | None = None) -> None:
        """Publish a user message from the web UI to the agent."""
        msg = InboundMessage(
            channel="web",
            sender_id=client_id,
            chat_id=client_id,
            content=content,
            media=media or [],
        )
        await self.bus.publish_inbound(msg)

    async def dispatch_outbound(self) -> None:
        """
        Background task: consume outbound messages from the bus and
        route those addressed to web clients to their WebSocket.
        """
        self._running = True
        while self._running:
            try:
                msg: OutboundMessage = await asyncio.wait_for(
                    self.bus.consume_outbound(), timeout=1.0,
                )

                if msg.channel != "web":
                    # Re-publish for other channels to pick up
                    await self.bus.publish_outbound(msg)
                    continue

                is_progress = msg.metadata.get("_progress", False)
                is_tool_hint = msg.metadata.get("_tool_hint", False)

                await self.send_to_client(msg.chat_id, {
                    "type": "progress" if is_progress else "message",
                    "content": msg.content,
                    "is_tool_hint": is_tool_hint,
                })

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Web dispatch error: {}", e)

    def stop(self) -> None:
        self._running = False
