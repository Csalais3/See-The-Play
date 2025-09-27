#backend/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import uvicorn
from typing import List, Dict, Any, Optional
import json
import logging
from datetime import datetime, timedelta
import random

from routes.predictions import router as predictions_router
from routes.live import router as live_router
from routes.health import router as health_router
from services.live_updates import LiveUpdateManager
from services.ml_model import PredictionEngine
from services.cedar_integration import CedarExplainer
from utils.api_clients import PulseAPIClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if self.active_connections:
            message_str = json.dumps(message)
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_text(message_str)
                except Exception as e:
                    logger.error(f"Error sending message to client: {e}")
                    disconnected.append(connection)
            
            # Clean up disconnected clients
            for connection in disconnected:
                self.active_connections.remove(connection)

# Global instances
manager = ConnectionManager()
live_update_manager = None
prediction_engine = None
cedar_explainer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global live_update_manager, prediction_engine, cedar_explainer
    
    logger.info("Starting SeeThePlay backend...")
    
    # Initialize services
    pulse_client = PulseAPIClient()
    prediction_engine = PredictionEngine(pulse_client)
    cedar_explainer = CedarExplainer()
    live_update_manager = LiveUpdateManager(pulse_client, prediction_engine, cedar_explainer, manager)
    
    # Start background tasks
    asyncio.create_task(live_update_manager.start_simulation())
    
    logger.info("SeeThePlay backend started successfully!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down SeeThePlay backend...")
    if live_update_manager:
        await live_update_manager.stop_simulation()

app = FastAPI(
    title="SeeThePlay API",
    description="Transparent sports predictions with live updates & explainable AI",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/api")
app.include_router(predictions_router, prefix="/api")
app.include_router(live_router, prefix="/api")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle client requests (like scenario changes)
            if message.get("type") == "scenario_change":
                await live_update_manager.handle_scenario_change(message.get("data"))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.get("/")
async def root():
    return {
        "message": "SeeThePlay API - You don't just get numbers, you see them!",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/health",
            "predictions": "/api/predictions",
            "live": "/api/live",
            "websocket": "/ws"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
