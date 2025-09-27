
# backend/routes/health.py
from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "SeeThePlay API",
        "version": "1.0.0"
    }


# backend/routes/predictions.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
import logging

from services.ml_model import PredictionEngine
from services.cedar_integration import CedarExplainer
from utils.api_clients import PulseAPIClient

router = APIRouter()
logger = logging.getLogger(__name__)

# Dependency injection
def get_pulse_client():
    return PulseAPIClient()

def get_prediction_engine():
    return PredictionEngine(get_pulse_client())

def get_cedar_explainer():
    return CedarExplainer()

@router.get("/predictions/teams")
async def get_teams(pulse_client: PulseAPIClient = Depends(get_pulse_client)) -> List[Dict[str, Any]]:
    """Get all available teams"""
    try:
        teams = pulse_client.get_teams()
        return teams
    except Exception as e:
        logger.error(f"Error fetching teams: {e}")
        raise HTTPException(status_code=500, detail="Error fetching teams")

@router.get("/predictions/team/{team_id}")
async def get_team_predictions(
    team_id: str,
    limit: int = 10,
    prediction_engine: PredictionEngine = Depends(get_prediction_engine)
) -> Dict[str, Any]:
    """Get predictions for all players on a team"""
    try:
        predictions = prediction_engine.get_top_picks(team_id, limit)
        return {
            "team_id": team_id,
            "predictions": predictions,
            "count": len(predictions)
        }
    except Exception as e:
        logger.error(f"Error fetching team predictions: {e}")
        raise HTTPException(status_code=500, detail="Error fetching predictions")

@router.get("/predictions/player/{player_id}")
async def get_player_prediction(
    player_id: str,
    team_id: str,
    pulse_client: PulseAPIClient = Depends(get_pulse_client),
    prediction_engine: PredictionEngine = Depends(get_prediction_engine),
    cedar_explainer: CedarExplainer = Depends(get_cedar_explainer)
) -> Dict[str, Any]:
    """Get detailed prediction for a specific player"""
    try:
        # Get player data
        players = pulse_client.get_team_players(team_id)
        player = None
        for p in players:
            if p['id'] == player_id:
                player = p
                break
        
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        # Get prediction
        prediction = prediction_engine.predict_player_performance(player, team_id)
        
        # Get explanation
        explanation = cedar_explainer.generate_explanation(prediction)
        
        return {
            "prediction": prediction,
            "explanation": explanation
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching player prediction: {e}")
        raise HTTPException(status_code=500, detail="Error fetching player prediction")

@router.post("/predictions/explain")
async def explain_prediction(
    request: Dict[str, Any],
    cedar_explainer: CedarExplainer = Depends(get_cedar_explainer)
) -> Dict[str, Any]:
    """Get explanation for prediction data"""
    try:
        prediction_data = request.get("prediction_data")
        if not prediction_data:
            raise HTTPException(status_code=400, detail="prediction_data required")
        
        explanation = cedar_explainer.generate_explanation(prediction_data)
        return explanation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating explanation: {e}")
        raise HTTPException(status_code=500, detail="Error generating explanation")

@router.post("/predictions/question")
async def ask_question(
    request: Dict[str, Any],
    cedar_explainer: CedarExplainer = Depends(get_cedar_explainer)
) -> Dict[str, str]:
    """Ask a question about player predictions"""
    try:
        question = request.get("question")
        player_data = request.get("player_data")
        
        if not question or not player_data:
            raise HTTPException(status_code=400, detail="question and player_data required")
        
        answer = cedar_explainer.answer_question(question, player_data)
        
        return {
            "question": question,
            "answer": answer
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise HTTPException(status_code=500, detail="Error processing question")

