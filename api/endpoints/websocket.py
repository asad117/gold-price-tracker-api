# from fastapi import APIRouter, WebSocket, WebSocketDisconnect
# from services.websocket_manager import manager

# router = APIRouter()

# @router.websocket("/ws/gold_price")
# async def websocket_endpoint(websocket: WebSocket):
#     """Handles incoming WebSocket connections."""
#     await manager.connect(websocket)
#     try:
#         while True:
#             await websocket.receive_text()
            
#     except WebSocketDisconnect:
#         manager.disconnect(websocket)
#     except Exception as e:
#         print(f"WebSocket Error: {e}")
#         manager.disconnect(websocket)



# api/endpoints/websocket.py

from fastapi import APIRouter, WebSocket
import asyncio
from services.websocket_manager import manager

router = APIRouter()

@router.websocket("/ws/gold_price")
async def websocket_endpoint(ws: WebSocket):
    # 1. Connect client
    await manager.connect(ws)
    print("New WebSocket client connected")

    try:
        while True:
            # 2. Keep connection alive (idle)
            await asyncio.sleep(10)
    except Exception as e:
        print(f"WebSocket disconnected: {e}")
    finally:
        # 3. Remove client when disconnected
        manager.disconnect(ws)
