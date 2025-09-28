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
from routes.players import router as players_router
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
    import os
    use_mock = os.getenv("USE_PULSE_MOCK") == "1"
    if use_mock:
        try:
            from pulse_mock import NFLMockClient
            pulse_client = NFLMockClient()
            logger.info("Using NFLMockClient for pulse data (USE_PULSE_MOCK=1)")
        except Exception as e:
            logger.error(f"Failed to initialize NFLMockClient, falling back to PulseAPIClient: {e}")
            pulse_client = PulseAPIClient()
    else:
        pulse_client = PulseAPIClient()
    prediction_engine = PredictionEngine(pulse_client)
    # Use the ChatGPT-based explainer (keeps backward-compatible alias)
    from services.cedar_integration import ChatGPTExplainer
    chatgpt_explainer = ChatGPTExplainer()
    cedar_explainer = chatgpt_explainer  # keep old name for compatibility
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
app.include_router(players_router, prefix="/api/v1")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    # Immediately send current game state and initial predictions to the newly connected client
    try:
        if live_update_manager and live_update_manager.current_game:
            try:
                initial_predictions = []
                for player in live_update_manager.current_game['players'][:5]:
                    try:
                        prediction = prediction_engine.predict_player_performance(
                            player,
                            live_update_manager.current_game['home_team']['id']
                        )
                        explanation = cedar_explainer.generate_explanation(prediction)
                        initial_predictions.append({'prediction': prediction, 'explanation': explanation})
                    except Exception as e:
                        logger.error(f"Error generating initial prediction for player on connect: {e}")

                initial_message = {
                    'type': 'game_initialized',
                    'timestamp': datetime.now().isoformat(),
                    'game_state': live_update_manager._get_current_game_state(),
                    'initial_predictions': initial_predictions,
                    'message': 'Client connected - delivering current game state.'
                }

                await websocket.send_text(json.dumps(initial_message))
                logger.info('Sent initial game state to newly connected client')
            except Exception as e:
                logger.error(f"Error sending initial game state to client: {e}")
    except Exception:
        # Non-fatal - proceed to the main receive loop
        logger.exception('Unexpected error while sending initial state to client')

    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle client requests (like scenario changes)
            if message.get("type") == "scenario_change":
                await live_update_manager.handle_scenario_change(message.get("data"))

            # Handle Cedar AI chat questions from frontend
            elif message.get("type") in ("cedar_question", "chatgpt_question"):
                try:
                    question = message.get("question")
                    player_id = message.get("player_id")
                    reply_type = 'chatgpt_answer' if message.get("type") == 'chatgpt_question' else 'cedar_answer'

                    player_obj = None
                    if live_update_manager and live_update_manager.current_game:
                        for p in live_update_manager.current_game.get('players', []):
                            if p.get('id') == player_id:
                                player_obj = p
                                break

                    if not player_obj:
                        # Try to reply with a helpful error
                        await websocket.send_text(json.dumps({
                            'type': reply_type,
                            'question': question,
                            'answer': f'Player with id {player_id} not found',
                            'player_id': player_id
                        }))
                    else:
                        # Generate a fresh prediction and explanation for the player
                        pred = prediction_engine.predict_player_performance(player_obj, live_update_manager.current_game['home_team']['id'])
                        explanation = cedar_explainer.generate_explanation(pred)

                        answer = cedar_explainer.answer_question(question, {
                            'player_name': pred.get('player_name'),
                            'position': pred.get('position'),
                            'predictions': pred.get('predictions', {}),
                            'explanation': explanation
                        })

                        await websocket.send_text(json.dumps({
                            'type': reply_type,
                            'question': question,
                            'answer': answer,
                            'player_id': player_id
                        }))
                except Exception as e:
                    logger.error(f"Error processing question: {e}")
                    await websocket.send_text(json.dumps({
                        'type': 'chatgpt_answer' if message.get('type') == 'chatgpt_question' else 'cedar_answer',
                        'question': message.get('question'),
                        'answer': 'Sorry, I could not process your question right now.',
                        'player_id': message.get('player_id')
                    }))
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

@app.get("/api/live/diagnostics")
async def live_diagnostics():
    """Return internal live/simulation diagnostics useful for debugging the WebSocket and simulation."""
    try:
        diagnostics = {
            'connected_clients': len(manager.active_connections) if manager else 0,
            'simulation_running': bool(live_update_manager.is_running) if live_update_manager else False,
            'current_game': getattr(live_update_manager, 'current_game', None) is not None if live_update_manager else False,
            'event_index': getattr(live_update_manager, 'event_index', None) if live_update_manager else None,
            'events_loaded': len(getattr(live_update_manager, 'game_events', [])) if live_update_manager else 0
        }
        return diagnostics
    except Exception as e:
        logger.error(f"Error in diagnostics endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/live/start")
async def api_start_simulation():
    """HTTP endpoint to (re)start the live simulation. Useful for debugging when the automatic startup failed."""
    try:
        if not live_update_manager:
            raise HTTPException(status_code=500, detail='LiveUpdateManager not initialized')
        await live_update_manager.start_simulation()
        return {'status': 'started'}
    except Exception as e:
        logger.error(f"Failed to start simulation via API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/live/stop")
async def api_stop_simulation():
    """Stop the live simulation."""
    try:
        if not live_update_manager:
            raise HTTPException(status_code=500, detail='LiveUpdateManager not initialized')
        await live_update_manager.stop_simulation()
        return {'status': 'stopped'}
    except Exception as e:
        logger.error(f"Failed to stop simulation via API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
