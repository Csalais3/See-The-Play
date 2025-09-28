# backend/utils/api_clients.py - FIXED VERSION
import requests
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class PulseAPIClient:
    """Client for interacting with PrizePicks Pulse Mock API"""
    
    def __init__(self, base_url: str = "http://localhost:1339"):
        self.base_url = base_url
        self.session = requests.Session()
        logger.info(f"Initialized PulseAPIClient with base URL: {base_url}")
        
    def _make_request(self, endpoint: str, method: str = "GET", **kwargs) -> Optional[Any]:
        """Make a request to the Pulse API with error handling"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.request(method, url, timeout=10, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to {endpoint}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
    
    def get_teams(self, league: str = "NFL") -> List[Dict[str, Any]]:
        """Get all teams in the league"""
        result = self._make_request(f"/v1/leagues/{league}/teams")
        return result if result else []
    
    def get_team_details(self, team_id: str, league: str = "NFL") -> Optional[Dict[str, Any]]:
        """Get detailed team information"""
        return self._make_request(f"/v1/leagues/{league}/teams/{team_id}")
    
    def get_team_players(self, team_id: str, league: str = "NFL") -> List[Dict[str, Any]]:
        """Get all players for a team"""
        result = self._make_request(f"/v1/leagues/{league}/teams/{team_id}/players")
        return result if result else []
    
    def get_players_by_position(
        self, 
        position: str, 
        team_id: Optional[str] = None, 
        league: str = "NFL"
    ) -> List[Dict[str, Any]]:
        """Get players by position"""
        endpoint = f"/v1/leagues/{league}/players?position={position}"
        if team_id:
            endpoint += f"&team_id={team_id}"
        result = self._make_request(endpoint)
        return result if result else []
    
    def get_team_games(self, team_id: str, league: str = "NFL") -> List[Dict[str, Any]]:
        """Get games for a team"""
        result = self._make_request(f"/v1/leagues/{league}/teams/{team_id}/games")
        return result if result else []
    
    def get_team_statistics(self, team_id: str, league: str = "NFL") -> Dict[str, Any]:
        """Get team statistics"""
        result = self._make_request(f"/v1/leagues/{league}/teams/{team_id}/stats")
        return result if result else {}
    
    def find_team_by_name(self, team_name: str, league: str = "NFL") -> Optional[Dict[str, Any]]:
        """Find team by name (search functionality)"""
        # Pulse Mock might not have search endpoint, so we'll filter locally
        teams = self.get_teams(league)
        for team in teams:
            if team.get('name', '').lower() == team_name.lower():
                return team
            if team.get('alias', '').lower() == team_name.lower():
                return team
            if team.get('market', '').lower() == team_name.lower():
                return team
        return None
    
    def get_all_games(self, league: str = "NFL") -> List[Dict[str, Any]]:
        """Get all games in the league"""
        result = self._make_request(f"/v1/leagues/{league}/games")
        return result if result else []
    
    def get_player_details(self, player_id: str, league: str = "NFL") -> Optional[Dict[str, Any]]:
        """Get detailed player information"""
        return self._make_request(f"/v1/leagues/{league}/players/{player_id}")
    
    def get_player_statistics(self, player_id: str, league: str = "NFL") -> Dict[str, Any]:
        """Get player statistics"""
        result = self._make_request(f"/v1/leagues/{league}/players/{player_id}/stats")
        return result if result else {}
    
    def health_check(self) -> bool:
        """Check if Pulse Mock API is accessible"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False