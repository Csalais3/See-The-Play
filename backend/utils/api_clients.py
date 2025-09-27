# backend/utils/api_clients.py
import requests
import logging
from typing import List, Dict, Any, Optional
from pulse_Mock.pulse_mock import NFLMockClient
import asyncio

logger = logging.getLogger(__name__)

class PulseAPIClient:
    def __init__(self, base_url: str = "http://localhost:1339"):
        self.base_url = base_url
        self.nfl_client = NFLMockClient()
        self.session = requests.Session()
        
    def get_teams(self, league: str = "NFL") -> List[Dict[str, Any]]:
        """Get all teams in the league"""
        try:
            return self.nfl_client.get_teams(league)
        except Exception as e:
            logger.error(f"Error fetching teams: {e}")
            return []
    
    def get_team_details(self, team_id: str, league: str = "NFL") -> Optional[Dict[str, Any]]:
        """Get detailed team information"""
        try:
            return self.nfl_client.get_team(team_id, league)
        except Exception as e:
            logger.error(f"Error fetching team details for {team_id}: {e}")
            return None
    
    def get_team_players(self, team_id: str, league: str = "NFL") -> List[Dict[str, Any]]:
        """Get all players for a team"""
        try:
            return self.nfl_client.get_team_players(team_id, league)
        except Exception as e:
            logger.error(f"Error fetching team players for {team_id}: {e}")
            return []
    
    def get_players_by_position(self, position: str, team_id: Optional[str] = None, league: str = "NFL") -> List[Dict[str, Any]]:
        """Get players by position"""
        try:
            return self.nfl_client.get_players_by_position(position, team_id, league)
        except Exception as e:
            logger.error(f"Error fetching players by position {position}: {e}")
            return []
    
    def get_team_games(self, team_id: str, league: str = "NFL") -> List[Dict[str, Any]]:
        """Get games for a team"""
        try:
            return self.nfl_client.get_team_games(team_id, league)
        except Exception as e:
            logger.error(f"Error fetching team games for {team_id}: {e}")
            return []
    
    def get_team_statistics(self, team_id: str, league: str = "NFL") -> Dict[str, Any]:
        """Get team statistics"""
        try:
            return self.nfl_client.get_team_statistics(team_id, league)
        except Exception as e:
            logger.error(f"Error fetching team statistics for {team_id}: {e}")
            return {}
    
    def find_team_by_name(self, team_name: str, league: str = "NFL") -> Optional[Dict[str, Any]]:
        """Find team by name"""
        try:
            return self.nfl_client.find_team_by_name(team_name, league)
        except Exception as e:
            logger.error(f"Error finding team by name {team_name}: {e}")
            return None
    
    def get_all_games(self, league: str = "NFL") -> List[Dict[str, Any]]:
        """Get all games in the league"""
        try:
            return self.nfl_client.get_all_games(league)
        except Exception as e:
            logger.error(f"Error fetching all games: {e}")
            return []