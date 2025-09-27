# backend/models/game_stats.py
"""
Game statistics models and data structures for SeeThePlay
Handles real-time game stats, player performance tracking, and statistical calculations
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class GameStatus(Enum):
    """Game status enumeration"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    HALFTIME = "halftime"
    COMPLETED = "completed"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"

class EventType(Enum):
    """Game event types"""
    PASS_COMPLETION = "pass_completion"
    PASS_INCOMPLETE = "pass_incomplete"
    RUSH_ATTEMPT = "rush_attempt"
    TOUCHDOWN = "touchdown"
    FIELD_GOAL = "field_goal"
    FIELD_GOAL_MISSED = "field_goal_missed"
    INTERCEPTION = "interception"
    FUMBLE = "fumble"
    SACK = "sack"
    PENALTY = "penalty"
    TIMEOUT = "timeout"
    SAFETY = "safety"
    PUNT = "punt"
    KICKOFF = "kickoff"
    TURNOVER_ON_DOWNS = "turnover_on_downs"

class Position(Enum):
    """Player positions"""
    QB = "QB"
    RB = "RB"
    FB = "FB"
    WR = "WR"
    TE = "TE"
    K = "K"
    DEF = "DEF"
    # Defense positions
    DE = "DE"
    DT = "DT"
    LB = "LB"
    CB = "CB"
    S = "S"
    # Special teams
    P = "P"
    LS = "LS"

# =============================================================================
# CORE DATA MODELS
# =============================================================================

@dataclass
class PlayerStats:
    """Individual player statistics for a game"""
    player_id: str
    player_name: str
    position: str
    team_id: str
    
    # Passing stats
    passing_attempts: int = 0
    passing_completions: int = 0
    passing_yards: int = 0
    passing_touchdowns: int = 0
    interceptions: int = 0
    sacks_taken: int = 0
    sack_yards_lost: int = 0
    
    # Rushing stats
    rushing_attempts: int = 0
    rushing_yards: int = 0
    rushing_touchdowns: int = 0
    fumbles: int = 0
    fumbles_lost: int = 0
    
    # Receiving stats
    targets: int = 0
    receptions: int = 0
    receiving_yards: int = 0
    receiving_touchdowns: int = 0
    
    # Kicking stats
    field_goal_attempts: int = 0
    field_goals_made: int = 0
    extra_point_attempts: int = 0
    extra_points_made: int = 0
    longest_field_goal: int = 0
    
    # Defensive stats
    tackles: int = 0
    assists: int = 0
    sacks: int = 0
    interceptions_defense: int = 0
    fumbles_recovered: int = 0
    
    # Game context
    game_id: str = ""
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Calculate derived stats after initialization"""
        self.update_derived_stats()
    
    def update_derived_stats(self):
        """Calculate derived statistics"""
        # Passing efficiency
        if self.passing_attempts > 0:
            self.completion_percentage = (self.passing_completions / self.passing_attempts) * 100
            self.yards_per_attempt = self.passing_yards / self.passing_attempts
        else:
            self.completion_percentage = 0.0
            self.yards_per_attempt = 0.0
        
        # Rushing efficiency
        if self.rushing_attempts > 0:
            self.yards_per_carry = self.rushing_yards / self.rushing_attempts
        else:
            self.yards_per_carry = 0.0
        
        # Receiving efficiency
        if self.targets > 0:
            self.catch_rate = (self.receptions / self.targets) * 100
        else:
            self.catch_rate = 0.0
        
        if self.receptions > 0:
            self.yards_per_reception = self.receiving_yards / self.receptions
        else:
            self.yards_per_reception = 0.0
        
        # Field goal percentage
        if self.field_goal_attempts > 0:
            self.field_goal_percentage = (self.field_goals_made / self.field_goal_attempts) * 100
        else:
            self.field_goal_percentage = 0.0
        
        # Total touchdowns
        self.total_touchdowns = self.passing_touchdowns + self.rushing_touchdowns + self.receiving_touchdowns
        
        # Total yards (for skill position players)
        self.total_yards = self.passing_yards + self.rushing_yards + self.receiving_yards
        
        self.last_updated = datetime.utcnow()
    
    def add_event(self, event: 'GameEvent'):
        """Update stats based on a game event"""
        if event.player_id != self.player_id:
            return
        
        event_type = event.event_type
        stats = event.stats or {}
        
        # Update stats based on event type
        if event_type == EventType.PASS_COMPLETION.value:
            self.passing_attempts += 1
            self.passing_completions += 1
            self.passing_yards += stats.get('yards', 0)
            if stats.get('touchdown', False):
                self.passing_touchdowns += 1
        
        elif event_type == EventType.PASS_INCOMPLETE.value:
            self.passing_attempts += 1
        
        elif event_type == EventType.RUSH_ATTEMPT.value:
            self.rushing_attempts += 1
            self.rushing_yards += stats.get('yards', 0)
            if stats.get('touchdown', False):
                self.rushing_touchdowns += 1
        
        elif event_type == EventType.INTERCEPTION.value:
            self.interceptions += 1
        
        elif event_type == EventType.FUMBLE.value:
            self.fumbles += 1
            if stats.get('lost', False):
                self.fumbles_lost += 1
        
        elif event_type == EventType.SACK.value:
            self.sacks_taken += 1
            self.sack_yards_lost += stats.get('yards', 0)
        
        elif event_type == EventType.FIELD_GOAL.value:
            self.field_goal_attempts += 1
            if stats.get('made', True):
                self.field_goals_made += 1
                distance = stats.get('distance', 0)
                if distance > self.longest_field_goal:
                    self.longest_field_goal = distance
        
        # Update derived stats
        self.update_derived_stats()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'player_id': self.player_id,
            'player_name': self.player_name,
            'position': self.position,
            'team_id': self.team_id,
            'game_id': self.game_id,
            
            # Passing
            'passing': {
                'attempts': self.passing_attempts,
                'completions': self.passing_completions,
                'yards': self.passing_yards,
                'touchdowns': self.passing_touchdowns,
                'interceptions': self.interceptions,
                'completion_percentage': round(self.completion_percentage, 1),
                'yards_per_attempt': round(self.yards_per_attempt, 1),
                'sacks_taken': self.sacks_taken,
                'sack_yards_lost': self.sack_yards_lost
            },
            
            # Rushing
            'rushing': {
                'attempts': self.rushing_attempts,
                'yards': self.rushing_yards,
                'touchdowns': self.rushing_touchdowns,
                'yards_per_carry': round(self.yards_per_carry, 1),
                'fumbles': self.fumbles,
                'fumbles_lost': self.fumbles_lost
            },
            
            # Receiving
            'receiving': {
                'targets': self.targets,
                'receptions': self.receptions,
                'yards': self.receiving_yards,
                'touchdowns': self.receiving_touchdowns,
                'catch_rate': round(self.catch_rate, 1),
                'yards_per_reception': round(self.yards_per_reception, 1)
            },
            
            # Kicking
            'kicking': {
                'field_goal_attempts': self.field_goal_attempts,
                'field_goals_made': self.field_goals_made,
                'field_goal_percentage': round(self.field_goal_percentage, 1),
                'longest_field_goal': self.longest_field_goal,
                'extra_point_attempts': self.extra_point_attempts,
                'extra_points_made': self.extra_points_made
            },
            
            # Summary
            'summary': {
                'total_touchdowns': self.total_touchdowns,
                'total_yards': self.total_yards
            },
            
            'last_updated': self.last_updated.isoformat()
        }

@dataclass
class TeamStats:
    """Team-level statistics for a game"""
    team_id: str
    team_name: str
    game_id: str
    
    # Team totals
    total_plays: int = 0
    total_yards: int = 0
    first_downs: int = 0
    third_down_attempts: int = 0
    third_down_conversions: int = 0
    red_zone_attempts: int = 0
    red_zone_scores: int = 0
    turnovers: int = 0
    penalties: int = 0
    penalty_yards: int = 0
    time_of_possession: timedelta = field(default_factory=lambda: timedelta(0))
    
    # Player stats
    player_stats: Dict[str, PlayerStats] = field(default_factory=dict)
    
    # Game context
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def add_player_stats(self, player_stats: PlayerStats):
        """Add or update player stats"""
        self.player_stats[player_stats.player_id] = player_stats
        self.last_updated = datetime.utcnow()
    
    def get_player_stats(self, player_id: str) -> Optional[PlayerStats]:
        """Get stats for a specific player"""
        return self.player_stats.get(player_id)
    
    def update_team_totals(self):
        """Calculate team totals from individual player stats"""
        # Reset totals
        self.total_yards = 0
        
        for player_stats in self.player_stats.values():
            self.total_yards += player_stats.total_yards
            self.turnovers += player_stats.interceptions + player_stats.fumbles_lost
        
        self.last_updated = datetime.utcnow()
    
    def get_position_stats(self, position: str) -> List[PlayerStats]:
        """Get stats for all players at a specific position"""
        return [stats for stats in self.player_stats.values() if stats.position == position]
    
    def get_top_performers(self, stat_category: str, limit: int = 5) -> List[PlayerStats]:
        """Get top performers in a specific statistical category"""
        if not self.player_stats:
            return []
        
        # Define sorting key based on stat category
        sort_keys = {
            'passing_yards': lambda p: p.passing_yards,
            'rushing_yards': lambda p: p.rushing_yards,
            'receiving_yards': lambda p: p.receiving_yards,
            'total_yards': lambda p: p.total_yards,
            'touchdowns': lambda p: p.total_touchdowns,
            'receptions': lambda p: p.receptions,
            'targets': lambda p: p.targets
        }
        
        if stat_category not in sort_keys:
            logger.warning(f"Unknown stat category: {stat_category}")
            return []
        
        sorted_players = sorted(
            self.player_stats.values(),
            key=sort_keys[stat_category],
            reverse=True
        )
        
        return sorted_players[:limit]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'team_id': self.team_id,
            'team_name': self.team_name,
            'game_id': self.game_id,
            
            'team_totals': {
                'total_plays': self.total_plays,
                'total_yards': self.total_yards,
                'first_downs': self.first_downs,
                'third_down_efficiency': f"{self.third_down_conversions}/{self.third_down_attempts}" if self.third_down_attempts > 0 else "0/0",
                'red_zone_efficiency': f"{self.red_zone_scores}/{self.red_zone_attempts}" if self.red_zone_attempts > 0 else "0/0",
                'turnovers': self.turnovers,
                'penalties': self.penalties,
                'penalty_yards': self.penalty_yards,
                'time_of_possession': str(self.time_of_possession)
            },
            
            'player_count': len(self.player_stats),
            'players': [stats.to_dict() for stats in self.player_stats.values()],
            'last_updated': self.last_updated.isoformat()
        }

@dataclass
class GameEvent:
    """Individual game event with statistics"""
    id: str
    game_id: str
    event_type: str
    quarter: int
    time_remaining: str
    timestamp: datetime
    
    # Event participants
    player_id: Optional[str] = None
    team_id: Optional[str] = None
    
    # Event details
    description: str = ""
    stats: Optional[Dict[str, Any]] = None
    
    # Event impact
    yards_gained: int = 0
    score_change: bool = False
    turnover: bool = False
    
    def __post_init__(self):
        if self.stats is None:
            self.stats = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'game_id': self.game_id,
            'event_type': self.event_type,
            'quarter': self.quarter,
            'time_remaining': self.time_remaining,
            'timestamp': self.timestamp.isoformat(),
            'player_id': self.player_id,
            'team_id': self.team_id,
            'description': self.description,
            'stats': self.stats,
            'yards_gained': self.yards_gained,
            'score_change': self.score_change,
            'turnover': self.turnover
        }

@dataclass
class GameState:
    """Complete game state with all statistics"""
    game_id: str
    home_team_id: str
    away_team_id: str
    status: GameStatus
    
    # Game timing
    quarter: int = 1
    time_remaining: str = "15:00"
    
    # Scores
    home_score: int = 0
    away_score: int = 0
    
    # Team statistics
    home_team_stats: Optional[TeamStats] = None
    away_team_stats: Optional[TeamStats] = None
    
    # Game events
    events: List[GameEvent] = field(default_factory=list)
    
    # Game metadata
    start_time: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        if self.home_team_stats is None:
            self.home_team_stats = TeamStats(
                team_id=self.home_team_id,
                team_name="Home Team",
                game_id=self.game_id
            )
        
        if self.away_team_stats is None:
            self.away_team_stats = TeamStats(
                team_id=self.away_team_id,
                team_name="Away Team", 
                game_id=self.game_id
            )
    
    def add_event(self, event: GameEvent):
        """Add a new game event and update stats"""
        self.events.append(event)
        
        # Update team stats based on event
        if event.team_id == self.home_team_id:
            team_stats = self.home_team_stats
        elif event.team_id == self.away_team_id:
            team_stats = self.away_team_stats
        else:
            logger.warning(f"Event {event.id} has unknown team_id: {event.team_id}")
            return
        
        # Update player stats if applicable
        if event.player_id and team_stats:
            player_stats = team_stats.get_player_stats(event.player_id)
            if player_stats:
                player_stats.add_event(event)
        
        # Update game state
        if event.score_change:
            # This would be updated based on the specific event
            pass
        
        self.last_updated = datetime.utcnow()
    
    def get_current_stats_summary(self) -> Dict[str, Any]:
        """Get current game statistics summary"""
        return {
            'game_id': self.game_id,
            'status': self.status.value,
            'quarter': self.quarter,
            'time_remaining': self.time_remaining,
            'score': {
                'home': self.home_score,
                'away': self.away_score
            },
            'home_team_stats': self.home_team_stats.to_dict() if self.home_team_stats else None,
            'away_team_stats': self.away_team_stats.to_dict() if self.away_team_stats else None,
            'total_events': len(self.events),
            'last_updated': self.last_updated.isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert complete game state to dictionary"""
        return {
            'game_info': {
                'game_id': self.game_id,
                'home_team_id': self.home_team_id,
                'away_team_id': self.away_team_id,
                'status': self.status.value,
                'quarter': self.quarter,
                'time_remaining': self.time_remaining,
                'home_score': self.home_score,
                'away_score': self.away_score,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'last_updated': self.last_updated.isoformat()
            },
            'team_stats': {
                'home': self.home_team_stats.to_dict() if self.home_team_stats else None,
                'away': self.away_team_stats.to_dict() if self.away_team_stats else None
            },
            'events': [event.to_dict() for event in self.events],
            'event_count': len(self.events)
        }

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_player_stats(player_data: Dict[str, Any], game_id: str, team_id: str) -> PlayerStats:
    """Create PlayerStats from player data dictionary"""
    return PlayerStats(
        player_id=player_data['id'],
        player_name=f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}".strip(),
        position=player_data.get('position', 'N/A'),
        team_id=team_id,
        game_id=game_id
    )

def create_game_event(event_id: str, game_id: str, event_type: str, 
                     quarter: int, time_remaining: str, 
                     description: str, player_id: str = None, 
                     team_id: str = None, **kwargs) -> GameEvent:
    """Create GameEvent with standard parameters"""
    return GameEvent(
        id=event_id,
        game_id=game_id,
        event_type=event_type,
        quarter=quarter,
        time_remaining=time_remaining,
        timestamp=datetime.utcnow(),
        player_id=player_id,
        team_id=team_id,
        description=description,
        stats=kwargs.get('stats', {}),
        yards_gained=kwargs.get('yards_gained', 0),
        score_change=kwargs.get('score_change', False),
        turnover=kwargs.get('turnover', False)
    )

def calculate_game_impact_score(event: GameEvent) -> float:
    """Calculate impact score for a game event (0-10 scale)"""
    impact = 0.0
    
    # Base impact by event type
    event_impacts = {
        EventType.TOUCHDOWN.value: 8.0,
        EventType.INTERCEPTION.value: 7.0,
        EventType.FUMBLE.value: 6.5,
        EventType.FIELD_GOAL.value: 4.0,
        EventType.SACK.value: 3.0,
        EventType.PASS_COMPLETION.value: 1.0,
        EventType.RUSH_ATTEMPT.value: 1.0,
        EventType.PENALTY.value: 2.0
    }
    
    impact = event_impacts.get(event.event_type, 1.0)
    
    # Adjust for yards gained
    if event.yards_gained > 20:
        impact += 2.0
    elif event.yards_gained > 10:
        impact += 1.0
    
    # Boost for score changes
    if event.score_change:
        impact += 3.0
    
    # Boost for turnovers
    if event.turnover:
        impact += 2.0
    
    return min(impact, 10.0)

# =============================================================================
# STATISTICAL ANALYSIS FUNCTIONS
# =============================================================================

def calculate_player_efficiency_rating(stats: PlayerStats) -> float:
    """Calculate overall player efficiency rating (0-100 scale)"""
    if stats.position == Position.QB.value:
        return calculate_qb_rating(stats)
    elif stats.position in [Position.RB.value, Position.FB.value]:
        return calculate_rb_efficiency(stats)
    elif stats.position in [Position.WR.value, Position.TE.value]:
        return calculate_receiver_efficiency(stats)
    else:
        return 50.0  # Default neutral rating

def calculate_qb_rating(stats: PlayerStats) -> float:
    """Calculate QB passer rating"""
    if stats.passing_attempts == 0:
        return 0.0
    
    # Standard NFL passer rating formula (simplified)
    comp_pct = (stats.passing_completions / stats.passing_attempts) * 100
    yds_per_att = stats.passing_yards / stats.passing_attempts
    td_pct = (stats.passing_touchdowns / stats.passing_attempts) * 100
    int_pct = (stats.interceptions / stats.passing_attempts) * 100
    
    # Simplified rating calculation
    rating = (comp_pct * 0.3) + (yds_per_att * 4) + (td_pct * 2) - (int_pct * 2)
    
    return max(0, min(100, rating))

def calculate_rb_efficiency(stats: PlayerStats) -> float:
    """Calculate running back efficiency rating"""
    efficiency = 50.0  # Base rating
    
    if stats.rushing_attempts > 0:
        efficiency += (stats.yards_per_carry - 4.0) * 10  # 4.0 YPC is average
    
    if stats.rushing_touchdowns > 0:
        efficiency += stats.rushing_touchdowns * 15
    
    if stats.receiving_yards > 0:
        efficiency += stats.receiving_yards * 0.1  # Bonus for receiving
    
    return max(0, min(100, efficiency))

def calculate_receiver_efficiency(stats: PlayerStats) -> float:
    """Calculate receiver efficiency rating"""
    efficiency = 50.0  # Base rating
    
    if stats.targets > 0:
        catch_rate_bonus = (stats.catch_rate - 60) * 0.5  # 60% is average
        efficiency += catch_rate_bonus
    
    if stats.receptions > 0:
        yac_bonus = (stats.yards_per_reception - 12) * 2  # 12 YPR is average
        efficiency += yac_bonus
    
    if stats.receiving_touchdowns > 0:
        efficiency += stats.receiving_touchdowns * 20
    
    return max(0, min(100, efficiency))

def get_game_momentum(events: List[GameEvent], team_id: str, last_n_events: int = 5) -> float:
    """Calculate team momentum based on recent events (-1.0 to 1.0)"""
    if not events:
        return 0.0
    
    # Get recent events for the team
    team_events = [e for e in events[-last_n_events:] if e.team_id == team_id]
    
    if not team_events:
        return 0.0
    
    momentum = 0.0
    
    for event in team_events:
        impact = calculate_game_impact_score(event)
        
        # Positive events
        if event.event_type in [EventType.TOUCHDOWN.value, EventType.FIELD_GOAL.value]:
            momentum += impact / 10.0
        elif event.event_type == EventType.PASS_COMPLETION.value and event.yards_gained > 15:
            momentum += 0.3
        elif event.event_type == EventType.RUSH_ATTEMPT.value and event.yards_gained > 10:
            momentum += 0.2
        
        # Negative events
        elif event.event_type in [EventType.INTERCEPTION.value, EventType.FUMBLE.value]:
            momentum -= impact / 10.0
        elif event.event_type == EventType.SACK.value:
            momentum -= 0.3
        elif event.event_type == EventType.PENALTY.value:
            momentum -= 0.2
    
    # Normalize to -1.0 to 1.0 range
    return max(-1.0, min(1.0, momentum / len(team_events)))


# Example usage and testing functions
if __name__ == "__main__":
    # Example of creating and using game statistics
    
    # Create a sample game
    game = GameState(
        game_id="test_game_001",
        home_team_id="eagles",
        away_team_id="opponents",
        status=GameStatus.IN_PROGRESS
    )
    
    # Create sample player stats
    qb_stats = PlayerStats(
        player_id="qb_001",
        player_name="Jalen Hurts", 
        position="QB",
        team_id="eagles",
        game_id="test_game_001"
    )
    
    # Add some sample stats
    qb_stats.passing_attempts = 15
    qb_stats.passing_completions = 10
    qb_stats.passing_yards = 185
    qb_stats.passing_touchdowns = 2
    qb_stats.rushing_yards = 45
    qb_stats.rushing_touchdowns = 1
    
    # Update derived stats
    qb_stats.update_derived_stats()
    
    # Add to team
    game.home_team_stats.add_player_stats(qb_stats)
    
    # Create sample event
    td_event = create_game_event(
        event_id="event_001",
        game_id="test_game_001",
        event_type=EventType.TOUCHDOWN.value,
        quarter=2,
        time_remaining="5:30",
        description="Jalen Hurts 15-yard rushing touchdown",
        player_id="qb_001",
        team_id="eagles",
        yards_gained=15,
        score_change=True
    )
    
    # Add event to game
    game.add_event(td_event)
    
    # Print stats
    print("Game Statistics Example:")
    print(f"QB Rating: {calculate_qb_rating(qb_stats):.1f}")
    print(f"Total Events: {len(game.events)}")
    print(f"Game Summary: {game.get_current_stats_summa