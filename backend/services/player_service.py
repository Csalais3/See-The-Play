"""Player service module for managing player data and predictions.

Restored to the version used when the per-player stats and robust league-wide
fallback logic were implemented. This file prefers team-level endpoints but
falls back to league-wide players and uses flexible matching across multiple
team identifier fields so the UI doesn't show "No players" when fixtures are
incomplete.
"""

from typing import List, Dict, Any, Optional
import logging
from pulse_mock import NFLMockClient
from services.ml_model import PredictionEngine

logger = logging.getLogger(__name__)

class PlayerService:
    def __init__(self, pulse_client: NFLMockClient, prediction_engine: PredictionEngine):
        self.pulse_client = pulse_client
        self.prediction_engine = prediction_engine
        # Cache for quick lookups
        self.players_cache: Dict[str, Dict[str, Any]] = {}
        self.team_players_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.teams_cache: Dict[str, Dict[str, Any]] = {}

    def _cache_team_players(self, team_id: str, players: List[Dict[str, Any]]) -> None:
        """Cache players both under the team id and individually by player id."""
        self.team_players_cache[team_id] = players
        for p in players:
            pid = p.get('id')
            if pid:
                self.players_cache[pid] = p

    def _normalize(self, val: Any) -> str:
        try:
            return str(val or "").strip().lower()
        except Exception:
            return ""

    def _matches_team(self, team_obj: Dict[str, Any], target_id: str) -> bool:
        """Flexible matching across multiple possible team fields.

        Some cassettes and player records use different keys for team identity
        (id, abbreviation, market, name, alias, short_name, team_id only string),
        so check several possibilities.
        """
        if not team_obj:
            return False
        tid = self._normalize(target_id)
        if not tid:
            return False

        candidates = [
            self._normalize(team_obj.get('id')),
            self._normalize(team_obj.get('abbreviation')),
            self._normalize(team_obj.get('name')),
            self._normalize(team_obj.get('market')),
            self._normalize(team_obj.get('alias')),
            self._normalize(team_obj.get('short_name')),
        ]

        # Also consider top-level player.team_id fields when team_obj is a player record
        if isinstance(team_obj.get('team_id'), (str, int)):
            candidates.append(self._normalize(team_obj.get('team_id')))

        if tid in candidates:
            return True

        # Allow partial matching when one side is an abbreviation
        for c in candidates:
            if c and (c == tid):
                return True
        return False

    def get_team_players(self, team_id: str, refresh: bool = False) -> List[Dict[str, Any]]:
        """Get players for a team, with robust fallbacks.

        Strategy:
        1. Use cached team list if present unless refresh requested.
        2. Attempt team-level endpoint from pulse_client.
        3. If empty, attempt to fetch league-wide players and filter by flexible matching.
        4. If still empty, return empty list (frontend shows retry options).
        """
        try:
            if not refresh and team_id in self.team_players_cache:
                return self.team_players_cache[team_id]

            players: List[Dict[str, Any]] = []
            # Try team-level endpoint
            try:
                if hasattr(self.pulse_client, 'get_team_players'):
                    players = self.pulse_client.get_team_players(team_id) or []
            except Exception as e:
                logger.debug(f"team endpoint failed for {team_id}: {e}")
                players = []

            if players:
                self._cache_team_players(team_id, players)
                return players

            # Fallback: try league-wide players and filter flexibly
            all_players: List[Dict[str, Any]] = []
            try:
                if hasattr(self.pulse_client, 'get_all_players'):
                    all_players = self.pulse_client.get_all_players() or []
                elif hasattr(self.pulse_client, 'get_players_by_league'):
                    all_players = self.pulse_client.get_players_by_league() or []
                elif hasattr(self.pulse_client, 'get_players'):
                    all_players = self.pulse_client.get_players() or []
            except Exception as e:
                logger.debug(f"league-wide players fetch failed: {e}")
                all_players = []

            if all_players:
                filtered: List[Dict[str, Any]] = []
                for p in all_players:
                    # player may have 'team' object or 'team_id' / 'team' as string
                    team_obj = p.get('team') if isinstance(p.get('team'), dict) else {
                        'id': p.get('team') or p.get('team_id') or p.get('team_id_str')
                    }
                    if self._matches_team(team_obj, team_id):
                        filtered.append(p)
                    else:
                        # also check simple top-level team_id field
                        if str(p.get('team_id') or '') == str(team_id):
                            filtered.append(p)

                if filtered:
                    logger.info(f"Found {len(filtered)} players for team {team_id} by filtering league-wide players (flex match)")
                    self._cache_team_players(team_id, filtered)
                    return filtered
                else:
                    logger.info(f"No players for team {team_id} found in league-wide players list after flexible matching")

            # Nothing found
            logger.info(f"Returning empty player list for team {team_id}")
            return []
        except Exception as e:
            logger.error(f"Error getting players for team {team_id}: {e}")
            return []

    def get_player_by_id(self, player_id: str, refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get a single player by id, using cache if available."""
        try:
            if not refresh and player_id in self.players_cache:
                return self.players_cache[player_id]

            player = None
            try:
                if hasattr(self.pulse_client, 'get_player'):
                    player = self.pulse_client.get_player(player_id)
                elif hasattr(self.pulse_client, 'get_player_details'):
                    player = self.pulse_client.get_player_details(player_id)
            except Exception as e:
                logger.debug(f"pulse_client get_player failed for {player_id}: {e}")
                player = None

            if player:
                self.players_cache[player_id] = player
            return player
        except Exception as e:
            logger.error(f"Error fetching player {player_id}: {e}")
            return None

    def get_players_by_position(self, position: str, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get players by position; optionally filter by team."""
        try:
            if team_id:
                players = self.get_team_players(team_id)
                return [p for p in players if p.get('position') == position]
            if hasattr(self.pulse_client, 'get_players_by_position'):
                return self.pulse_client.get_players_by_position(position) or []
            return []
        except Exception as e:
            logger.error(f"Error fetching players by position {position}: {e}")
            return []

    def get_player_predictions(self, player_id: str, game_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Return predictions for a player using the PredictionEngine."""
        try:
            player = self.get_player_by_id(player_id)
            if not player:
                return {}
            team_id = None
            team_field = player.get('team')
            if isinstance(team_field, dict):
                team_id = team_field.get('id')
            elif isinstance(team_field, str):
                team_id = team_field
            if not team_id:
                team_id = player.get('team_id') or player.get('teamId')
            if not team_id:
                return {}
            return self.prediction_engine.predict_player_performance(player, team_id, game_context)
        except Exception as e:
            logger.error(f"Error predicting for {player_id}: {e}")
            return {}

    def get_team_predictions(self, team_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top predictions for a team"""
        try:
            players = self.get_team_players(team_id)
            if not players:
                return []
            preds = []
            for p in players[:limit]:
                try:
                    pred = self.prediction_engine.predict_player_performance(p, team_id)
                    preds.append(pred)
                except Exception as e:
                    logger.debug(f"Error predicting for player {p.get('id')}: {e}")
            preds.sort(key=lambda x: x.get('overall_confidence', 0), reverse=True)
            return preds[:limit]
        except Exception as e:
            logger.error(f"Error getting team predictions for {team_id}: {e}")
            return []

    def find_player_by_name(self, name: str) -> List[Dict[str, Any]]:
        try:
            if hasattr(self.pulse_client, 'find_player_by_name'):
                return self.pulse_client.find_player_by_name(name) or []
            return []
        except Exception as e:
            logger.error(f"Error finding player by name {name}: {e}")
            return []

    def get_available_teams(self) -> List[Dict[str, Any]]:
        try:
            if not self.teams_cache:
                teams = self.pulse_client.get_teams() or []
                self.teams_cache = {t.get('id'): t for t in teams}
                return teams
            return list(self.teams_cache.values())
        except Exception as e:
            logger.error(f"Error fetching teams: {e}")
            return []

    def get_team_by_id(self, team_id: str) -> Optional[Dict[str, Any]]:
        try:
            if team_id in self.teams_cache:
                return self.teams_cache[team_id]
            team = None
            try:
                if hasattr(self.pulse_client, 'get_team'):
                    team = self.pulse_client.get_team(team_id)
                elif hasattr(self.pulse_client, 'get_team_details'):
                    team = self.pulse_client.get_team_details(team_id)
            except Exception as e:
                logger.debug(f"pulse_client get_team failed: {e}")
            if team:
                self.teams_cache[team_id] = team
            return team
        except Exception as e:
            logger.error(f"Error fetching team {team_id}: {e}")
            return None

    def get_mock_debug_info(self) -> Dict[str, Any]:
        info = {'available_cassettes': [], 'loaded_cassettes': [], 'interactions_count': 0, 'interactions_preview': []}
        try:
            info['available_cassettes'] = self.pulse_client.discover_available_cassettes()
        except Exception:
            info['available_cassettes'] = []
        try:
            info['loaded_cassettes'] = getattr(self.pulse_client, 'loaded_cassettes', [])
            interactions = getattr(self.pulse_client, 'interactions', [])
            info['interactions_count'] = len(interactions)
            info['interactions_preview'] = [i.get('request', {}).get('url') for i in interactions[:50]]
        except Exception:
            pass
        return info

    def force_load_all_cassettes(self) -> Dict[str, Any]:
        try:
            if hasattr(self.pulse_client, 'load_all_available_cassettes'):
                self.pulse_client.load_all_available_cassettes()
            elif hasattr(self.pulse_client, 'load_cassettes'):
                available = self.pulse_client.discover_available_cassettes()
                self.pulse_client.load_cassettes(available)
            return self.get_mock_debug_info()
        except Exception as e:
            logger.error(f"Error loading all cassettes: {e}")
            return {'error': str(e)}

    def get_player_statistics(self, player_id: str, refresh: bool = False) -> Dict[str, Any]:
        try:
            cached = self.players_cache.get(player_id)
            if cached and not refresh:
                pass
            if hasattr(self.pulse_client, 'get_player_statistics'):
                stats = self.pulse_client.get_player_statistics(player_id)
                return stats or {}
            else:
                logger.info('pulse_client has no get_player_statistics method')
                return {}
        except Exception as e:
            logger.error(f"Error fetching player statistics for {player_id}: {e}")
            return {}