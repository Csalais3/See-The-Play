"""Routes for player-related endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from services.player_service import PlayerService
from services.ml_model import PredictionEngine
from pulse_mock import NFLMockClient

router = APIRouter()

# Initialize services
pulse_client = NFLMockClient()
prediction_engine = PredictionEngine(pulse_client)
player_service = PlayerService(pulse_client, prediction_engine)

@router.get("/teams")
async def get_teams():
    """Get all available teams."""
    teams = player_service.get_available_teams()
    if not teams:
        raise HTTPException(status_code=404, detail="No teams found")
    return teams

@router.get("/teams/{team_id}")
async def get_team(team_id: str):
    """Get a specific team by ID."""
    team = player_service.get_team_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found")
    return team

@router.get("/teams/{team_id}/players")
async def get_team_players(team_id: str, refresh: bool = False):
    """Get all players for a team.

    Returns an empty array (200) when players are not available in the data source
    instead of raising a 404. This makes the frontend more robust when the mock
    client does not contain player fixtures for every team.
    """
    players = player_service.get_team_players(team_id, refresh)

    # If the player service could not find players, return an empty list with a helpful message
    if not players:
        # Log a warning on the backend
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"No players available for team {team_id}; returning empty list.")
        except Exception:
            pass
        return []

    return players

@router.get("/players/{player_id}")
async def get_player(player_id: str, refresh: bool = False):
    """Get a specific player by ID."""
    player = player_service.get_player_by_id(player_id, refresh)
    if not player:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found")
    return player

@router.get("/players/{player_id}/predictions")
async def get_player_predictions(
    player_id: str,
    weather_impact: Optional[float] = None,
    scoring_environment: Optional[str] = None
):
    """Get predictions for a specific player."""
    game_context = {}
    if weather_impact is not None:
        game_context['weather_impact'] = max(0.5, min(1.0, weather_impact))
    if scoring_environment:
        game_context['scoring_environment'] = scoring_environment

    predictions = player_service.get_player_predictions(player_id, game_context)
    if not predictions:
        raise HTTPException(status_code=404, detail=f"No predictions found for player {player_id}")
    return predictions

@router.get("/teams/{team_id}/predictions")
async def get_team_predictions(team_id: str, limit: int = Query(10, ge=1, le=53)):
    """Get predictions for top players in a team."""
    predictions = player_service.get_team_predictions(team_id, limit)
    if not predictions:
        raise HTTPException(status_code=404, detail=f"No predictions found for team {team_id}")
    return predictions

@router.get("/players")
async def find_players(
    name: Optional[str] = None,
    position: Optional[str] = None,
    team_id: Optional[str] = None
):
    """Find players by name, position, or team."""
    if name:
        players = player_service.find_player_by_name(name)
    elif position and team_id:
        players = player_service.get_players_by_position(position, team_id)
    elif position:
        players = player_service.get_players_by_position(position)
    elif team_id:
        players = player_service.get_team_players(team_id)
    else:
        raise HTTPException(status_code=400, detail="At least one search parameter is required")
    
    if not players:
        raise HTTPException(status_code=404, detail="No players found")
    return players

@router.get("/debug/pulse_mock")
async def pulse_mock_debug():
    """Return diagnostic information about the pulse mock client (available/loaded cassettes and interactions)."""
    try:
        info = player_service.get_mock_debug_info()
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/debug/pulse_mock/load_all")
async def pulse_mock_force_load():
    """Force the mock client to load all available cassettes and return diagnostics."""
    try:
        info = player_service.force_load_all_cassettes()
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/teams/{team_id}/stats")
async def get_team_stats(team_id: str):
    """Get statistics for a specific team."""
    try:
        stats = player_service.get_team_statistics(team_id)
        if not stats:
            # Return empty structure instead of 404 so frontend can show a friendly message
            return {}
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/players/{player_id}/stats")
async def get_player_stats(player_id: str):
    """Get statistics for a specific player."""
    try:
        stats = player_service.get_player_statistics(player_id)
        if not stats:
            return {}
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))