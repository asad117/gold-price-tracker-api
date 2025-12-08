from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.websocket_manager import manager

router = APIRouter()

@router.websocket("/ws/gold_price")
async def websocket_endpoint(websocket: WebSocket):
    """Handles incoming WebSocket connections."""
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket Error: {e}")
        manager.disconnect(websocket)