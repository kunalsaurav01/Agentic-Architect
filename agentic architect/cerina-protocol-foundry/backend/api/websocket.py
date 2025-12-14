"""
Cerina Protocol Foundry - WebSocket Manager
Handles real-time streaming of agent states and updates.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState


logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.
    Supports per-thread subscriptions for protocol-specific updates.
    """

    def __init__(self):
        # All active connections
        self.active_connections: list[WebSocket] = []
        # Thread-specific subscriptions: thread_id -> list of websockets
        self.thread_subscriptions: dict[str, list[WebSocket]] = {}
        # Connection metadata
        self.connection_info: dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket, thread_id: Optional[str] = None):
        """
        Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            thread_id: Optional thread ID to subscribe to
        """
        await websocket.accept()
        self.active_connections.append(websocket)

        # Store connection metadata
        self.connection_info[websocket] = {
            "connected_at": datetime.utcnow().isoformat(),
            "thread_id": thread_id,
        }

        # Subscribe to thread if specified
        if thread_id:
            await self.subscribe_to_thread(websocket, thread_id)

        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

        # Send welcome message
        await self.send_personal_message({
            "type": "connected",
            "data": {
                "message": "Connected to Cerina Protocol Foundry",
                "thread_id": thread_id,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }, websocket)

    def disconnect(self, websocket: WebSocket):
        """
        Handle WebSocket disconnection.

        Args:
            websocket: The disconnecting WebSocket
        """
        # Remove from active connections
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # Remove from thread subscriptions
        for thread_id, sockets in list(self.thread_subscriptions.items()):
            if websocket in sockets:
                sockets.remove(websocket)
                if not sockets:
                    del self.thread_subscriptions[thread_id]

        # Remove connection info
        if websocket in self.connection_info:
            del self.connection_info[websocket]

        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def subscribe_to_thread(self, websocket: WebSocket, thread_id: str):
        """
        Subscribe a WebSocket to a specific thread's updates.

        Args:
            websocket: The WebSocket connection
            thread_id: Thread ID to subscribe to
        """
        if thread_id not in self.thread_subscriptions:
            self.thread_subscriptions[thread_id] = []

        if websocket not in self.thread_subscriptions[thread_id]:
            self.thread_subscriptions[thread_id].append(websocket)
            logger.debug(f"WebSocket subscribed to thread: {thread_id}")

        # Update connection info
        if websocket in self.connection_info:
            self.connection_info[websocket]["thread_id"] = thread_id

    async def unsubscribe_from_thread(self, websocket: WebSocket, thread_id: str):
        """
        Unsubscribe a WebSocket from a thread.

        Args:
            websocket: The WebSocket connection
            thread_id: Thread ID to unsubscribe from
        """
        if thread_id in self.thread_subscriptions:
            if websocket in self.thread_subscriptions[thread_id]:
                self.thread_subscriptions[thread_id].remove(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send a message to a specific WebSocket connection.

        Args:
            message: Message dict to send
            websocket: Target WebSocket
        """
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """
        Broadcast a message to all connected clients.

        Args:
            message: Message dict to broadcast
        """
        disconnected = []
        for connection in self.active_connections:
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_to_thread(self, thread_id: str, message: dict):
        """
        Broadcast a message to all clients subscribed to a thread.

        Args:
            thread_id: Thread ID to broadcast to
            message: Message dict to broadcast
        """
        if thread_id not in self.thread_subscriptions:
            return

        disconnected = []
        for connection in self.thread_subscriptions[thread_id]:
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to thread {thread_id}: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def send_agent_update(
        self,
        thread_id: str,
        agent: str,
        status: str,
        message: Optional[str] = None,
        iteration: int = 0,
    ):
        """
        Send an agent status update to thread subscribers.

        Args:
            thread_id: Thread ID
            agent: Agent name
            status: Agent status (starting, processing, complete, error)
            message: Optional message
            iteration: Current iteration
        """
        await self.broadcast_to_thread(thread_id, {
            "type": "agent_update",
            "data": {
                "agent": agent,
                "status": status,
                "message": message,
                "iteration": iteration,
            },
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def send_state_update(
        self,
        thread_id: str,
        active_agent: str,
        approval_status: str,
        iteration_count: int,
        safety_score: float,
        clinical_score: float,
        empathy_overall: float,
        current_draft_preview: Optional[str] = None,
    ):
        """
        Send a state update to thread subscribers.

        Args:
            thread_id: Thread ID
            active_agent: Currently active agent
            approval_status: Current approval status
            iteration_count: Current iteration
            safety_score: Current safety score
            clinical_score: Current clinical score
            empathy_overall: Current empathy score
            current_draft_preview: Preview of current draft
        """
        await self.broadcast_to_thread(thread_id, {
            "type": "state_update",
            "data": {
                "thread_id": thread_id,
                "active_agent": active_agent,
                "approval_status": approval_status,
                "iteration_count": iteration_count,
                "safety_score": safety_score,
                "clinical_score": clinical_score,
                "empathy_overall": empathy_overall,
                "current_draft_preview": current_draft_preview[:500] if current_draft_preview else None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def send_human_review_required(self, thread_id: str, state: dict):
        """
        Notify subscribers that human review is required.

        Args:
            thread_id: Thread ID
            state: Current state for context
        """
        await self.broadcast_to_thread(thread_id, {
            "type": "human_review_required",
            "data": {
                "thread_id": thread_id,
                "current_draft": state.get("current_draft", ""),
                "safety_score": state.get("safety_score", 0),
                "clinical_score": state.get("clinical_score", 0),
                "empathy_scores": state.get("empathy_scores", {}),
                "safety_flags": state.get("safety_flags", []),
                "iteration_count": state.get("iteration_count", 0),
            },
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def send_protocol_complete(self, thread_id: str, protocol_id: str, final_content: str):
        """
        Notify subscribers that protocol is complete.

        Args:
            thread_id: Thread ID
            protocol_id: Protocol ID
            final_content: Final protocol content
        """
        await self.broadcast_to_thread(thread_id, {
            "type": "protocol_complete",
            "data": {
                "thread_id": thread_id,
                "protocol_id": protocol_id,
                "final_content": final_content,
            },
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def send_error(self, thread_id: str, error: str, details: Optional[str] = None):
        """
        Send an error notification to thread subscribers.

        Args:
            thread_id: Thread ID
            error: Error message
            details: Optional error details
        """
        await self.broadcast_to_thread(thread_id, {
            "type": "error",
            "data": {
                "error": error,
                "details": details,
            },
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_connection_count(self) -> int:
        """Get the total number of active connections."""
        return len(self.active_connections)

    def get_thread_subscriber_count(self, thread_id: str) -> int:
        """Get the number of subscribers for a thread."""
        return len(self.thread_subscriptions.get(thread_id, []))


# Global connection manager instance
manager = ConnectionManager()


async def handle_websocket_connection(websocket: WebSocket, thread_id: Optional[str] = None):
    """
    Handle a WebSocket connection lifecycle.

    Args:
        websocket: The WebSocket connection
        thread_id: Optional thread ID to subscribe to
    """
    await manager.connect(websocket, thread_id)

    try:
        while True:
            # Receive and process messages
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=60.0  # 1 minute timeout
                )

                # Handle different message types
                msg_type = data.get("type", "")

                if msg_type == "ping":
                    await manager.send_personal_message({
                        "type": "pong",
                        "data": {},
                        "timestamp": datetime.utcnow().isoformat(),
                    }, websocket)

                elif msg_type == "subscribe":
                    new_thread_id = data.get("thread_id")
                    if new_thread_id:
                        await manager.subscribe_to_thread(websocket, new_thread_id)
                        await manager.send_personal_message({
                            "type": "subscribed",
                            "data": {"thread_id": new_thread_id},
                            "timestamp": datetime.utcnow().isoformat(),
                        }, websocket)

                elif msg_type == "unsubscribe":
                    old_thread_id = data.get("thread_id")
                    if old_thread_id:
                        await manager.unsubscribe_from_thread(websocket, old_thread_id)

            except asyncio.TimeoutError:
                # Send keepalive ping
                await manager.send_personal_message({
                    "type": "ping",
                    "data": {},
                    "timestamp": datetime.utcnow().isoformat(),
                }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
