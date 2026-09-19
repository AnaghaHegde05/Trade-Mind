import json
import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
from backend.utils.logging import register_log_callback, unregister_log_callback, log_history

logger = logging.getLogger("trade_intel.routes.websocket")

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("New WebSocket client connected.")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket client disconnected.")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Connection might be broken
                pass

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    # 1. Send historical logs immediately on connection so the UI has context
    try:
        for entry in log_history:
            await manager.send_personal_message(entry, websocket)
    except Exception as e:
        logger.error(f"Error sending log history to new client: {e}")
        manager.disconnect(websocket)
        return
        
    # 2. Register callback to stream new logs in real-time
    async def log_streamer_callback(log_entry: dict):
        try:
            await manager.send_personal_message(log_entry, websocket)
        except Exception:
            # If sending fails, connection is probably closed
            pass
            
    register_log_callback(log_streamer_callback)
    
    # 3. Hold connection open
    try:
        while True:
            # We listen for messages (like ping) to detect client close
            data = await websocket.receive_text()
            # If client sends ping, we respond pong
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        unregister_log_callback(log_streamer_callback)
