
# backend/services/live_updates.py
import asyncio
import logging
from typing import Dict, List, Any, Optional
import json
import random
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class LiveUpdateManager:
    def __init__(self, pulse_client, prediction_engine, cedar_explainer, connection_manager):
        self.pulse_client = pulse_client
        self.prediction_engine = prediction_engine
        self.cedar_explainer = cedar_explainer
        self.connection_manager = connection_manager
        self.is_running = False
        self.current_game = None
        self.game_events = []
        self.event_index = 0
        
    async def start_simulation(self):
        """Start the live game simulation"""
        self.is_running = True
        
        # Initialize game data
        await self._initialize_game()
        
        # Start the simulation loop
        asyncio.create_task(self._simulation_loop())
        
        logger.info("Live simulation started")
    
    async def stop_simulation(self):
        """Stop the live simulation"""
        self.is_running = False
        logger.info("Live simulation stopped")
    
    async def _initialize_game(self):
        """Initialize current game and generate events"""
        
        # Get Eagles team (we have full data for them)
        eagles = self.pulse_client.find_team_by_name("Eagles")
        if not eagles:
            logger.error("Could not find Eagles team data")
            return
        
        # Get Eagles players
        eagles_players = self.pulse_client.get_team_players(eagles['id'])
        if not eagles_players:
            logger.error("Could not get Eagles players")
            return
        
        # Create a simulated game
        self.current_game = {
            'id': 'sim_game_001',
            'home_team': eagles,
            'away_team': {'id': 'opp_001', 'name': 'Opponents', 'market': 'Generic'},
            'status': 'in_progress',
            'quarter': 1,
            'time_remaining': '15:00',
            'home_score': 0,
            'away_score': 0,
            'players': eagles_players[:10]  # Use first 10 players
        }
        
        # Generate game events
        self._generate_game_events()
        
        # Send initial game state
        await self._broadcast_game_state()
    
    def _generate_game_events(self):
        """Generate realistic game events for simulation"""
        
        events = []
        current_time = datetime.now()
        
        # Generate events for 4 quarters
        for quarter in range(1, 5):
            quarter_events = []
            
            # 8-12 events per quarter
            num_events = random.randint(8, 12)
            
            for i in range(num_events):
                event_time = current_time + timedelta(minutes=i*2, seconds=random.randint(0, 59))
                
                event_types = [
                    'pass_completion', 'rush_attempt', 'touchdown', 
                    'field_goal', 'interception', 'fumble', 'sack',
                    'timeout', 'penalty'
                ]
                
                event_type = random.choices(
                    event_types,
                    weights=[25, 20, 8, 5, 3, 2, 4, 15, 18]  # Realistic probabilities
                )[0]
                
                # Select random player for the event
                player = random.choice(self.current_game['players'])
                
                event = {
                    'id': f"event_{quarter}_{i}",
                    'type': event_type,
                    'quarter': quarter,
                    'time': event_time.isoformat(),
                    'player_id': player['id'],
                    'player_name': f"{player.get('first_name', '')} {player.get('last_name', '')}".strip(),
                    'description': self._generate_event_description(event_type, player),
                    'impact': self._calculate_event_impact(event_type)
                }
                
                quarter_events.append(event)
            
            events.extend(quarter_events)
        
        self.game_events = events
        logger.info(f"Generated {len(events)} game events")
    
    def _generate_event_description(self, event_type: str, player: Dict) -> str:
        """Generate realistic event descriptions"""
        
        player_name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
        
        descriptions = {
            'pass_completion': f"{player_name} completes pass for {random.randint(5, 25)} yards",
            'rush_attempt': f"{player_name} rushes for {random.randint(1, 15)} yards",
            'touchdown': f"TOUCHDOWN! {player_name} scores from {random.randint(1, 25)} yards out",
            'field_goal': f"Field goal good from {random.randint(25, 50)} yards",
            'interception': f"Pass intercepted by defense",
            'fumble': f"{player_name} fumbles, recovered by defense",
            'sack': f"{player_name} sacked for {random.randint(3, 12)} yard loss",
            'timeout': f"Timeout called by team",
            'penalty': f"Penalty: {random.choice(['Holding', 'False Start', 'Pass Interference'])} on offense"
        }
        
        return descriptions.get(event_type, f"Game event: {event_type}")
    
    def _calculate_event_impact(self, event_type: str) -> Dict[str, float]:
        """Calculate how events impact future predictions"""
        
        impacts = {
            'pass_completion': {'passing_yards': 1.05, 'confidence_boost': 0.02},
            'rush_attempt': {'rushing_yards': 1.03, 'confidence_boost': 0.01},
            'touchdown': {'touchdowns': 1.2, 'confidence_boost': 0.05},
            'field_goal': {'confidence_boost': 0.01},
            'interception': {'interceptions': 1.1, 'passing_yards': 0.95, 'confidence_penalty': 0.03},
            'fumble': {'all_stats': 0.98, 'confidence_penalty': 0.02},
            'sack': {'passing_yards': 0.97, 'confidence_penalty': 0.01},
            'timeout': {'confidence_boost': 0.005},
            'penalty': {'all_stats': 0.99, 'confidence_penalty': 0.01}
        }
        
        return impacts.get(event_type, {})
    
    async def _simulation_loop(self):
        """Main simulation loop that processes events"""
        
        while self.is_running and self.event_index < len(self.game_events):
            await asyncio.sleep(random.uniform(3, 8))  # 3-8 seconds between events
            
            if not self.is_running:
                break
            
            # Get next event
            event = self.game_events[self.event_index]
            self.event_index += 1
            
            # Process the event
            await self._process_event(event)
            
        logger.info("Simulation loop completed")
    
    async def _process_event(self, event: Dict[str, Any]):
        """Process a single game event"""
        
        # Update game state based on event
        self._update_game_state(event)
        
        # Get updated predictions for affected player
        player_id = event['player_id']
        affected_player = None
        
        for player in self.current_game['players']:
            if player['id'] == player_id:
                affected_player = player
                break
        
        if not affected_player:
            return
        
        # Get updated predictions
        try:
            updated_prediction = self.prediction_engine.predict_player_performance(
                affected_player, 
                self.current_game['home_team']['id']
            )
            
            # Apply event impact to predictions
            self._apply_event_impact(updated_prediction, event)
            
            # Generate explanation
            explanation = self.cedar_explainer.generate_explanation(updated_prediction)
            
            # Broadcast the update
            update_message = {
                'type': 'live_update',
                'timestamp': datetime.now().isoformat(),
                'event': event,
                'game_state': self._get_current_game_state(),
                'updated_prediction': updated_prediction,
                'explanation': explanation,
                'impact_analysis': self._generate_impact_analysis(event, updated_prediction)
            }
            
            await self.connection_manager.broadcast(update_message)
            
        except Exception as e:
            logger.error(f"Error processing event {event['id']}: {e}")
    
    def _update_game_state(self, event: Dict[str, Any]):
        """Update the current game state based on event"""
        
        # Update quarter and time (simplified)
        if event['quarter'] != self.current_game['quarter']:
            self.current_game['quarter'] = event['quarter']
            self.current_game['time_remaining'] = '15:00'
        
        # Update score for scoring events
        if event['type'] == 'touchdown':
            self.current_game['home_score'] += 7  # TD + XP
        elif event['type'] == 'field_goal':
            self.current_game['home_score'] += 3
    
    def _apply_event_impact(self, prediction: Dict[str, Any], event: Dict[str, Any]):
        """Apply event impact to prediction values"""
        
        impact = event.get('impact', {})
        predictions = prediction.get('predictions', {})
        
        for stat_type, pred_data in predictions.items():
            # Apply specific stat impacts
            if stat_type in impact:
                multiplier = impact[stat_type]
                pred_data['predicted_value'] *= multiplier
                pred_data['predicted_value'] = round(pred_data['predicted_value'], 1)
            
            # Apply general impacts
            if 'all_stats' in impact:
                multiplier = impact['all_stats']
                pred_data['predicted_value'] *= multiplier
                pred_data['predicted_value'] = round(pred_data['predicted_value'], 1)
            
            # Apply confidence adjustments
            if 'confidence_boost' in impact:
                pred_data['confidence'] = min(1.0, pred_data['confidence'] + impact['confidence_boost'])
            elif 'confidence_penalty' in impact:
                pred_data['confidence'] = max(0.0, pred_data['confidence'] - impact['confidence_penalty'])
            
            pred_data['confidence'] = round(pred_data['confidence'], 3)
    
    def _generate_impact_analysis(self, event: Dict[str, Any], prediction: Dict[str, Any]) -> str:
        """Generate analysis of how the event impacted predictions"""
        
        event_type = event['type']
        player_name = event['player_name']
        
        if event_type == 'touchdown':
            return f"{player_name}'s touchdown increases their likelihood of continued scoring success this game."
        elif event_type == 'interception':
            return f"The interception may indicate defensive pressure, potentially limiting passing opportunities."
        elif event_type == 'pass_completion':
            return f"Successful completion shows {player_name} is finding rhythm in the passing game."
        elif event_type == 'rush_attempt':
            return f"Ground game involvement suggests {player_name} will continue to see carries."
        else:
            return f"This {event_type} may influence {player_name}'s remaining opportunities in the game."
    
    def _get_current_game_state(self) -> Dict[str, Any]:
        """Get current game state for broadcasting"""
        
        return {
            'game_id': self.current_game['id'],
            'quarter': self.current_game['quarter'],
            'time_remaining': self.current_game['time_remaining'],
            'home_team': self.current_game['home_team']['name'],
            'away_team': self.current_game['away_team']['name'],
            'home_score': self.current_game['home_score'],
            'away_score': self.current_game['away_score'],
            'status': self.current_game['status']
        }
    
    async def _broadcast_game_state(self):
        """Broadcast initial game state"""
        
        # Get initial predictions for all players
        initial_predictions = []
        
        for player in self.current_game['players'][:5]:  # Top 5 players
            try:
                prediction = self.prediction_engine.predict_player_performance(
                    player,
                    self.current_game['home_team']['id']
                )
                explanation = self.cedar_explainer.generate_explanation(prediction)
                
                initial_predictions.append({
                    'prediction': prediction,
                    'explanation': explanation
                })
            except Exception as e:
                logger.error(f"Error generating initial prediction for {player.get('id')}: {e}")
        
        initial_message = {
            'type': 'game_initialized',
            'timestamp': datetime.now().isoformat(),
            'game_state': self._get_current_game_state(),
            'initial_predictions': initial_predictions,
            'message': 'Game simulation started! Watch for live updates as events unfold.'
        }
        
        await self.connection_manager.broadcast(initial_message)
    
    async def handle_scenario_change(self, scenario_data: Dict[str, Any]):
        """Handle scenario changes from the frontend"""
        
        scenario_type = scenario_data.get('type')
        
        if scenario_type == 'weather_change':
            # Simulate weather impact
            weather_impact = scenario_data.get('severity', 0.1)
            
            # Update predictions for all players
            updated_predictions = []
            
            for player in self.current_game['players'][:3]:
                prediction = self.prediction_engine.predict_player_performance(
                    player,
                    self.current_game['home_team']['id'],
                    game_context={'weather_impact': 1.0 - weather_impact}
                )
                
                explanation = self.cedar_explainer.generate_explanation(prediction)
                updated_predictions.append({
                    'prediction': prediction,
                    'explanation': explanation
                })
            
            scenario_message = {
                'type': 'scenario_update',
                'timestamp': datetime.now().isoformat(),
                'scenario': {
                    'type': scenario_type,
                    'description': f"Weather conditions have changed (impact: {weather_impact*100:.0f}%)"
                },
                'updated_predictions': updated_predictions
            }
            
            await self.connection_manager.broadcast(scenario_message)
