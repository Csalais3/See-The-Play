
# backend/routes/live.py  
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import logging

from services.live_updates import LiveUpdateManager
from utils.api_clients import PulseAPIClient

router = APIRouter()
logger = logging.getLogger(__name__)

def get_pulse_client():
    return PulseAPIClient()

@router.get("/live/games")
async def get_live_games(
    pulse_client: PulseAPIClient = Depends(get_pulse_client)
) -> List[Dict[str, Any]]:
    """Get all live games"""
    try:
        games = pulse_client.get_all_games()
        
        # Add simulated live status
        for game in games:
            game['is_live'] = True
            game['quarter'] = 2
            game['time_remaining'] = '8:45'
        
        return games[:5]  # Return first 5 games
        
    except Exception as e:
        logger.error(f"Error fetching live games: {e}")
        raise HTTPException(status_code=500, detail="Error fetching live games")

@router.get("/live/status")
async def get_live_status() -> Dict[str, Any]:
    """Get live update system status"""
    return {
        "status": "active",
        "connected_clients": 0,  # This would be populated by the actual manager
        "current_game": "sim_game_001",
        "events_processed": 0,
        "last_update": None
    }

@router.post("/live/scenario")
async def trigger_scenario(request: Dict[str, Any]) -> Dict[str, str]:
    """Trigger a what-if scenario for live updates"""
    try:
        scenario_type = request.get("scenario_type")
        scenario_data = request.get("data", {})
        
        # This would normally trigger the live update manager
        # For now, just return success
        
        return {
            "status": "success",
            "message": f"Scenario '{scenario_type}' triggered successfully"
        }
        
    except Exception as e:
        logger.error(f"Error triggering scenario: {e}")
        raise HTTPException(status_code=500, detail="Error triggering scenario")