from fastapi import WebSocket
from typing import List, Dict, Any 

class ConnectionManager:
    def __init__(self):
        # Stores active WebSocket connections
        self.active_connections: List[WebSocket] = []
        self.last_broadcasted_data: Dict[str, Any] = {} 


    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # CRITICAL FIX: Send last data immediately upon connection
        if self.last_broadcasted_data:
            await websocket.send_json(self.last_broadcasted_data)

    async def broadcast(self, data: Dict[str, Any]):
        # CRITICAL: Update the last data before broadcasting
        self.last_broadcasted_data = data 
        for connection in self.active_connections:
            await connection.send_json(data)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"Client disconnected. Total active: {len(self.active_connections)}")


manager = ConnectionManager() 