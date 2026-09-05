"""WebSocket and real-time API endpoints."""
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from app.security import decode_token
from app.websocket import get_ws_manager

logger = logging.getLogger("quantive.websocket_routes")

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/market")
async def market_ws_endpoint(websocket: WebSocket):
    """Live market price stream.

    Broadcasts `price_update` payloads (batches of quotes) to every connected
    client every 30s. Auth-optional: the market data itself is non-sensitive,
    so anonymous connections are allowed for the dashboard preview.
    """
    await websocket.accept()
    try:
        from app.websocket import get_ws_manager
        manager = get_ws_manager()

        # Join the shared "market" room (anonymous id per connection)
        import uuid
        conn_id = f"market-{uuid.uuid4().hex[:8]}"
        manager.rooms.setdefault("market", set()).add(conn_id)
        # Register connection so broadcast_all also reaches it
        manager.active_connections[conn_id] = websocket

        await manager._send_to(websocket, {
            "type": "stream_connected",
            "interval_seconds": 30,
            "message": "Live market price stream connected",
        })

        while True:
            raw = await websocket.receive_text()
            # Client pings: reply with a lightweight ack so connections stay alive
            if raw in ("ping", "\"ping\""):
                await manager._send_to(websocket, {"type": "pong", "timestamp": None})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug("Market WS closed: %s", e)
    finally:
        try:
            from app.websocket import get_ws_manager
            manager = get_ws_manager()
            manager.rooms.get("market", set()).discard(conn_id)
            manager.active_connections.pop(conn_id, None)
        except Exception:
            pass


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    token: str = Query(default=""),
):
    """Main WebSocket endpoint for real-time updates.

    Connect with: ws://host/ws/{user_id}?token={jwt_token}

    SECURITY: Token is validated against user_id to prevent
    unauthorized access to other users' real-time data.
    """
    # Validate token is provided
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    # Validate JWT and verify user_id matches token subject
    try:
        payload = decode_token(token)
        token_user_id = payload.get("sub")
        if token_user_id != user_id:
            await websocket.close(code=4003, reason="User ID mismatch")
            return
    except Exception:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    manager = get_ws_manager()

    try:
        await manager.connect(websocket, user_id)

        while True:
            data = await websocket.receive_json()
            await manager.handle_message(websocket, user_id, data)

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception:
        manager.disconnect(websocket, user_id)
