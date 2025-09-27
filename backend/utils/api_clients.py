# backend/utils/api_clients.py
import requests
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class PulseAPIClient:
    def __init__(self, base_url: str = "http://localhost:1339"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def get_teams(self, league: str = "NFL") -> List[Dict[str, Any]]:
        """Get all teams in the league"""
        try:
            response = self.session.get(f"{self.base_url}/v1/leagues/{league}/teams")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching teams: {e}")
            return []
    
    def get_team_details(self, team_id: str, league: str = "NFL") -> Optional[Dict[str, Any]]:
        """Get detailed team information"""
        try:
            response = self.session.get(f"{self.base_url}/v1/leagues/{league}/teams/{team_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching team details for {team_id}: {e}")
            return None
    
    def get_team_players(self, team_id: str, league: str = "NFL") -> List[Dict[str, Any]]:
        """Get all players for a team"""
        try:
            response = self.session.get(f"{self.base_url}/v1/leagues/{league}/teams/{team_id}/players")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching team players for {team_id}: {e}")
            return []
    
    def get_players_by_position(self, position: str, team_id: Optional[str] = None, league: str = "NFL") -> List[Dict[str, Any]]:
        """Get players by position"""
        try:
            url = f"{self.base_url}/v1/leagues/{league}/players?position={position}"
            if team_id:
                url += f"&team_id={team_id}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching players by position {position}: {e}")
            return []
    
    def get_team_games(self, team_id: str, league: str = "NFL") -> List[Dict[str, Any]]:
        """Get games for a team"""
        try:
            response = self.session.get(f"{self.base_url}/v1/leagues/{league}/teams/{team_id}/games")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching team games for {team_id}: {e}")
            return []
    
    def get_team_statistics(self, team_id: str, league: str = "NFL") -> Dict[str, Any]:
        """Get team statistics"""
        try:
            response = self.session.get(f"{self.base_url}/v1/leagues/{league}/teams/{team_id}/stats")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching team statistics for {team_id}: {e}")
            return {}
    
    def find_team_by_name(self, team_name: str, league: str = "NFL") -> Optional[Dict[str, Any]]:
        """Find team by name"""
        try:
            response = self.session.get(f"{self.base_url}/v1/leagues/{league}/teams/search?name={team_name}")
            response.raise_for_status()
            teams = response.json()
            return teams[0] if teams else None
        except Exception as e:
            logger.error(f"Error finding team by name {team_name}: {e}")
            return None
    
    def get_all_games(self, league: str = "NFL") -> List[Dict[str, Any]]:
        """Get all games in the league"""
        try:
            response = self.session.get(f"{self.base_url}/v1/leagues/{league}/games")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching all games: {e}")
            return []