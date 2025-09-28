# backend/routes/predictions.py
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

# Import our services (these will be created from the other artifacts)
from services.ml_model import PredictionEngine
from services.cedar_integration import CedarExplainer
from utils.api_clients import PulseAPIClient

# Set up logging
logger = logging.getLogger(__name__)

# Create the FastAPI router
router = APIRouter()

# Dependency injection functions
# These provide instances of our services to the endpoint functions
def get_pulse_client():
    """Get PulseAPIClient instance or NFLMockClient when USE_PULSE_MOCK is set"""
    import os
    if os.getenv("USE_PULSE_MOCK") == "1":
        try:
            from pulse_mock import NFLMockClient
            return NFLMockClient()
        except Exception as e:
            logger.warning(f"Failed to create NFLMockClient, falling back to real PulseAPIClient: {e}")
            return PulseAPIClient()
    return PulseAPIClient()

def get_prediction_engine():
    """Get PredictionEngine instance"""
    return PredictionEngine(get_pulse_client())

def get_cedar_explainer():
    """Get ChatGPT-based explainer instance (backwards-compatible name: CedarExplainer)."""
    return CedarExplainer()

# =============================================================================
# TEAM ENDPOINTS
# =============================================================================

@router.get("/predictions/teams", response_model=List[Dict[str, Any]])
async def get_teams(
    pulse_client: PulseAPIClient = Depends(get_pulse_client)
) -> List[Dict[str, Any]]:
    """
    Get all available NFL teams (using sample data since Pulse Mock needs cassettes)
    
    Returns:
        List of team objects with id, name, market, etc.
    
    Example Response:
    [
        {
            "id": "NFL_team_ram7VKb86QoDRToIZOIN8rH", 
            "name": "Eagles",
            "market": "Philadelphia",
            "abbreviation": "PHI"
        },
        ...
    ]
    """
    try:
        logger.info("Fetching all NFL teams")
        teams = pulse_client.get_teams()
        
        if not teams:
            logger.warning("No teams found from Pulse API")
            raise HTTPException(status_code=404, detail="No teams found")
        
        logger.info(f"Successfully fetched {len(teams)} teams")
        return teams
        
    except Exception as e:
        logger.error(f"Error fetching teams: {str(e)}")
        # Return fallback Eagles data when Pulse Mock fails
        return [{"id": "PHI", "name": "Eagles", "alias": "PHI", "market": "Philadelphia"}]

@router.get("/predictions/teams/{team_id}", response_model=Dict[str, Any])
async def get_team_details(
    team_id: str,
    pulse_client: PulseAPIClient = Depends(get_pulse_client)
) -> Dict[str, Any]:
    """
    Get detailed information about a specific team
    
    Args:
        team_id: The team's unique identifier
    
    Returns:
        Detailed team information including stats
    """
    try:
        logger.info(f"Fetching details for team {team_id}")
        
        # Get basic team info
        team_details = pulse_client.get_team_details(team_id)
        if not team_details:
            raise HTTPException(status_code=404, detail=f"Team {team_id} not found")
        
        # Get team statistics
        team_stats = pulse_client.get_team_statistics(team_id)
        
        # Get team players
        players = pulse_client.get_team_players(team_id)
        
        # Combine all team information
        result = {
            "team_details": team_details,
            "statistics": team_stats,
            "player_count": len(players),
            "players_preview": players[:5] if players else []  # First 5 players
        }
        
        logger.info(f"Successfully fetched details for team {team_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching team details for {team_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching team details: {str(e)}")

# =============================================================================
# PREDICTION ENDPOINTS
# =============================================================================

@router.get("/predictions/team/{team_id}/players", response_model=Dict[str, Any])
async def get_team_predictions(
    team_id: str,
    limit: int = Query(default=10, ge=1, le=50, description="Number of predictions to return"),
    prediction_engine: PredictionEngine = Depends(get_prediction_engine)
) -> Dict[str, Any]:
    """
    Get ML predictions for all players on a team
    
    Args:
        team_id: The team's unique identifier
        limit: Maximum number of player predictions to return (1-50)
    
    Returns:
        Dictionary containing team predictions with confidence scores
    
    Example Response:
    {
        "team_id": "NFL_team_ram7VKb86QoDRToIZOIN8rH",
        "predictions": [
            {
                "player_id": "player_001",
                "player_name": "Jalen Hurts", 
                "position": "QB",
                "predictions": {
                    "passing_yards": {
                        "predicted_value": 285.3,
                        "confidence": 0.847,
                        "probability_over": 0.73
                    },
                    "rushing_yards": {...},
                    "touchdowns": {...}
                },
                "overall_confidence": 0.807
            },
            ...
        ],
        "count": 10,
        "timestamp": "2025-01-20T10:30:00Z"
    }
    """
    try:
        logger.info(f"Generating predictions for team {team_id} (limit: {limit})")
        
        # Get predictions from ML model
        predictions = prediction_engine.get_top_picks(team_id, limit)
        
        if not predictions:
            logger.warning(f"No predictions generated for team {team_id}")
            raise HTTPException(status_code=404, detail=f"No predictions available for team {team_id}")
        
        result = {
            "team_id": team_id,
            "predictions": predictions,
            "count": len(predictions),
            "timestamp": datetime.utcnow().isoformat(),
            "model_info": {
                "version": "1.0",
                "confidence_threshold": 0.65,
                "features_used": ["player_skill", "recent_form", "team_stats", "opponent_strength"]
            }
        }
        
        logger.info(f"Successfully generated {len(predictions)} predictions for team {team_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating team predictions for {team_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating predictions: {str(e)}")

@router.get("/predictions/player/{player_id}", response_model=Dict[str, Any])
async def get_player_prediction(
    player_id: str,
    team_id: str = Query(..., description="Team ID that the player belongs to"),
    include_explanation: bool = Query(default=True, description="Include ChatGPT explanation"),
    pulse_client: PulseAPIClient = Depends(get_pulse_client),
    prediction_engine: PredictionEngine = Depends(get_prediction_engine),
    cedar_explainer: CedarExplainer = Depends(get_cedar_explainer)
) -> Dict[str, Any]:
    """
    Get detailed ML prediction for a specific player
    
    Args:
        player_id: The player's unique identifier
        team_id: The team the player belongs to
        include_explanation: Whether to include ChatGPT explanations
    
    Returns:
        Detailed player prediction with optional explanations
    
    Example Response:
    {
        "prediction": {
            "player_id": "NFL_player_SyWsd7T30Oev84KlU0vKvQrU",
            "player_name": "Jalen Hurts",
            "position": "QB",
            "predictions": {...},
            "explanations": {...}
        },
        "explanation": {
            "overall_summary": "Jalen Hurts is expected to have a strong performance...",
            "narrative_explanations": {...},
            "confidence_explanation": {...}
        }
    }
    """
    try:
        logger.info(f"Generating prediction for player {player_id} on team {team_id}")
        
        # Get player data from Pulse API
        team_players = pulse_client.get_team_players(team_id)
        player = None
        
        for p in team_players:
            if p['id'] == player_id:
                player = p
                break
        
        if not player:
            logger.warning(f"Player {player_id} not found on team {team_id}")
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found")
        
        # Generate ML prediction
        prediction = prediction_engine.predict_player_performance(player, team_id)
        
        result = {"prediction": prediction}
        
        # Add ChatGPT explanation if requested
        if include_explanation:
            logger.info(f"Generating ChatGPT explanation for player {player_id}")
            explanation = cedar_explainer.generate_explanation(prediction)
            result["explanation"] = explanation
        
        logger.info(f"Successfully generated prediction for player {player_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating player prediction for {player_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating player prediction: {str(e)}")

# =============================================================================
# EXPLANATION ENDPOINTS
# =============================================================================

@router.post("/predictions/explain", response_model=Dict[str, Any])
async def explain_prediction(
    request: Dict[str, Any],
    cedar_explainer: CedarExplainer = Depends(get_cedar_explainer)
) -> Dict[str, Any]:
    """
    Generate ChatGPT explanation for existing prediction data

    Request Body:
    {
        "prediction_data": { ... }
    }

    Returns:
        Comprehensive explanation with narratives, factors, what-if scenarios
    """
    try:
        prediction_data = request.get("prediction_data")
        if not prediction_data:
            raise HTTPException(status_code=400, detail="prediction_data is required")
        
        logger.info(f"Generating explanation for prediction data")
        
        # Generate comprehensive explanation using ChatGPT
        explanation = cedar_explainer.generate_explanation(prediction_data)
        
        logger.info("Successfully generated prediction explanation")
        return explanation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating explanation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating explanation: {str(e)}")

@router.post("/predictions/question", response_model=Dict[str, str])
async def ask_question(
    request: Dict[str, Any],
    cedar_explainer: CedarExplainer = Depends(get_cedar_explainer)
) -> Dict[str, str]:
    """
    Ask a question about player predictions using ChatGPT

    Request Body:
    {
        "question": "Why is Jalen Hurts predicted for 285 passing yards?",
        "player_data": { ... }
    }

    Returns:
    {
        "question": "...",
        "answer": "...",
        "model": "chatgpt",
        "timestamp": "..."
    }
    """
    try:
        question = request.get("question")
        player_data = request.get("player_data")
        
        if not question or not player_data:
            raise HTTPException(
                status_code=400, 
                detail="Both 'question' and 'player_data' are required"
            )
        
        logger.info(f"Processing question: {question[:50]}...")
        
        # Get answer from ChatGPT-based explainer
        answer = cedar_explainer.answer_question(question, player_data)
        
        result = {
            "question": question,
            "answer": answer,
            "model": "chatgpt",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info("Successfully answered question")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@router.get("/predictions/players/search", response_model=List[Dict[str, Any]])
async def search_players(
    name: str = Query(..., min_length=2, description="Player name to search for"),
    position: Optional[str] = Query(None, description="Filter by position (QB, RB, WR, etc.)"),
    team_id: Optional[str] = Query(None, description="Filter by team"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum results to return"),
    pulse_client: PulseAPIClient = Depends(get_pulse_client)
) -> List[Dict[str, Any]]:
    """
    Search for players by name, position, or team
    
    Query Parameters:
        name: Player name to search for (minimum 2 characters)
        position: Optional position filter (QB, RB, WR, TE, etc.)
        team_id: Optional team filter
        limit: Maximum number of results (1-100)
    
    Returns:
        List of matching players
    """
    try:
        logger.info(f"Searching players: name='{name}', position='{position}', team='{team_id}'")
        
        results = []
        
        if team_id:
            # Search within specific team
            if position:
                players = pulse_client.get_players_by_position(position, team_id)
            else:
                players = pulse_client.get_team_players(team_id)
            
            # Filter by name
            for player in players:
                full_name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip().lower()
                if name.lower() in full_name:
                    results.append(player)
                    if len(results) >= limit:
                        break
        else:
            # Search across all teams (for demo, we'll search Eagles since we have their data)
            eagles = pulse_client.find_team_by_name("Eagles")
            if eagles:
                if position:
                    players = pulse_client.get_players_by_position(position, eagles['id'])
                else:
                    players = pulse_client.get_team_players(eagles['id'])
                
                for player in players:
                    full_name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip().lower()
                    if name.lower() in full_name:
                        results.append(player)
                        if len(results) >= limit:
                            break
        
        logger.info(f"Found {len(results)} matching players")
        return results[:limit]
        
    except Exception as e:
        logger.error(f"Error searching players: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching players: {str(e)}")

@router.get("/predictions/positions", response_model=List[str])
async def get_positions(
    pulse_client: PulseAPIClient = Depends(get_pulse_client)
) -> List[str]:
    """
    Get all available player positions
    
    Returns:
        List of position abbreviations (QB, RB, WR, etc.)
    """
    try:
        logger.info("Fetching available positions")
        
        # Get Eagles players (we have full data for them)
        eagles = pulse_client.find_team_by_name("Eagles")
        if not eagles:
            return ["QB", "RB", "WR", "TE", "K", "DEF"]  # Default positions
        
        players = pulse_client.get_team_players(eagles['id'])
        positions = list(set(player.get('position', 'N/A') for player in players))
        positions = [pos for pos in positions if pos != 'N/A']
        positions.sort()
        
        logger.info(f"Found positions: {positions}")
        return positions
        
    except Exception as e:
        logger.error(f"Error fetching positions: {str(e)}")
        # Return default positions if there's an error
        return ["QB", "RB", "WR", "TE", "K", "DEF"]

# =============================================================================
# BATCH OPERATIONS
# =============================================================================

@router.post("/predictions/batch", response_model=Dict[str, Any])
async def get_batch_predictions(
    request: Dict[str, Any],
    prediction_engine: PredictionEngine = Depends(get_prediction_engine),
    cedar_explainer: CedarExplainer = Depends(get_cedar_explainer)
) -> Dict[str, Any]:
    """
    Get predictions for multiple players at once
    
    Request Body:
    {
        "players": [
            {"player_id": "...", "team_id": "..."},
            {"player_id": "...", "team_id": "..."}
        ],
        "include_explanations": true
    }
    
    Returns:
        Batch predictions with optional explanations
    """
    try:
        players = request.get("players", [])
        include_explanations = request.get("include_explanations", False)
        
        if not players or len(players) > 20:
            raise HTTPException(
                status_code=400, 
                detail="Must provide 1-20 players for batch prediction"
            )
        
        logger.info(f"Processing batch prediction for {len(players)} players")
        
        results = []
        pulse_client = PulseAPIClient()
        
        for player_request in players:
            player_id = player_request.get("player_id")
            team_id = player_request.get("team_id")
            
            if not player_id or not team_id:
                continue
            
            try:
                # Get player data
                team_players = pulse_client.get_team_players(team_id)
                player = next((p for p in team_players if p['id'] == player_id), None)
                
                if player:
                    # Generate prediction
                    prediction = prediction_engine.predict_player_performance(player, team_id)
                    
                    result_item = {"prediction": prediction}
                    
                    # Add explanation if requested
                    if include_explanations:
                        explanation = cedar_explainer.generate_explanation(prediction)
                        result_item["explanation"] = explanation
                    
                    results.append(result_item)
                    
            except Exception as e:
                logger.error(f"Error processing player {player_id}: {str(e)}")
                continue
        
        batch_result = {
            "results": results,
            "successful_predictions": len(results),
            "requested_predictions": len(players),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Completed batch prediction: {len(results)}/{len(players)} successful")
        return batch_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing batch predictions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing batch predictions: {str(e)}")

# =============================================================================
# STATISTICS ENDPOINTS
# =============================================================================

@router.get("/predictions/stats", response_model=Dict[str, Any])
async def get_prediction_stats(
    prediction_engine: PredictionEngine = Depends(get_prediction_engine)
) -> Dict[str, Any]:
    """
    Get overall prediction system statistics
    
    Returns:
        System stats like model performance, confidence distributions, etc.
    """
    try:
        logger.info("Generating prediction system statistics")
        
        # This would normally come from a database of historical predictions
        # For demo purposes, we'll return simulated stats
        stats = {
            "model_info": {
                "version": "1.0",
                "last_updated": datetime.utcnow().isoformat(),
                "features_count": 10,
                "supported_stats": ["passing_yards", "rushing_yards", "receiving_yards", "touchdowns", "interceptions"]
            },
            "performance": {
                "average_confidence": 0.782,
                "predictions_today": 156,
                "high_confidence_predictions": 89,  # >80% confidence
                "moderate_confidence_predictions": 52,  # 70-80% confidence
                "low_confidence_predictions": 15  # <70% confidence
            },
            "coverage": {
                "teams_covered": 32,
                "players_covered": 2400,
                "active_games": 1,
                "positions_supported": ["QB", "RB", "WR", "TE", "K"]
            }
        }
        
        logger.info("Successfully generated prediction statistics")
        return stats
        
    except Exception as e:
        logger.error(f"Error fetching teams: {str(e)}")
        # Return fallback Eagles data
        return [{"id": "PHI", "name": "Eagles", "alias": "PHI", "market": "Philadelphia"}]