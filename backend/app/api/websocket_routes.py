"""WebSocket and real-time API endpoints."""
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from app.security import decode_token
from app.websocket import get_ws_manager

router = APIRouter(tags=["websocket"])


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
