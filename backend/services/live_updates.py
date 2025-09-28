# backend/services/live_updates.py - COMPLETE FIXED VERSION
import asyncio
import logging
from typing import Dict, List, Any, Optional
import json
import random
import re
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
        self.game_clock_seconds = None
        self._clock_task: Optional[asyncio.Task] = None
        
    async def start_simulation(self):
        """Start the live game simulation"""
        try:
            self.is_running = True
            
            # Initialize game data
            await self._initialize_game()
            
            # Start the simulation loop
            asyncio.create_task(self._simulation_loop())
            # Start the game clock task
            if self._clock_task is None or self._clock_task.done():
                self._clock_task = asyncio.create_task(self._game_clock_loop())
            
            logger.info("✅ Live simulation started successfully")
        except Exception as e:
            logger.error(f"❌ Error starting simulation: {e}")
    
    async def stop_simulation(self):
        """Stop the live simulation"""
        self.is_running = False
        # Cancel clock task if running
        if self._clock_task and not self._clock_task.done():
            self._clock_task.cancel()
            self._clock_task = None
        logger.info("Live simulation stopped")

    async def reset_game(self, game_data: Dict[str, Any] = None):
        """Reset the game state and restart simulation"""
        try:
            logger.info("🔄 Resetting game state...")
            
            # Stop current simulation
            await self.stop_simulation()
            
            # Reset game state
            if game_data:
                self.current_game.update({
                    'quarter': game_data.get('quarter', 1),
                    'time_remaining': game_data.get('time_remaining', '15:00'),
                    'home_score': game_data.get('home_score', 0),
                    'away_score': game_data.get('away_score', 0),
                    'status': 'in_progress'
                })
            else:
                # Reset to default state
                self.current_game.update({
                    'quarter': 1,
                    'time_remaining': '15:00',
                    'home_score': 0,
                    'away_score': 0,
                    'status': 'in_progress'
                })
            
            # Reset game clock
            self.game_clock_seconds = 15 * 60
            
            # Reset event index to start generating new events
            self.event_index = 0
            
            # Generate new game events
            self._generate_game_events()
            
            # Restart simulation
            self.is_running = True
            if self._clock_task is None or self._clock_task.done():
                self._clock_task = asyncio.create_task(self._game_clock_loop())
            
            # Broadcast reset state
            await self._broadcast_game_state()
            
            logger.info("✅ Game reset complete")
            
        except Exception as e:
            logger.error(f"❌ Error resetting game: {e}")
            raise

    async def handle_websocket_message(self, message: Dict[str, Any]):
        """Handle incoming WebSocket messages"""
        try:
            message_type = message.get('type')
            
            if message_type == 'game_reset':
                await self.reset_game(message.get('data'))
            elif message_type in ('cedar_question', 'chatgpt_question'):
                # Handle AI questions (legacy 'cedar' name supported)
                question = message.get('question')
                player_id = message.get('player_id')
                reply_type = 'chatgpt_answer' if message_type == 'chatgpt_question' else 'cedar_answer'

                player_obj = None
                if self.current_game:
                    for p in self.current_game.get('players', []):
                        if p.get('id') == player_id:
                            player_obj = p
                            break

                if not player_obj:
                    await self.connection_manager.broadcast({
                        'type': reply_type,
                        'question': question,
                        'answer': f'Player with id {player_id} not found',
                        'player_id': player_id
                    })
                    return

                try:
                    # Generate latest prediction and explanation for the player
                    pred = self.prediction_engine.predict_player_performance(player_obj, self.current_game['home_team']['id'])
                    explanation = self.cedar_explainer.generate_explanation(pred)

                    answer = self.cedar_explainer.answer_question(question, {
                        'player_name': pred.get('player_name'),
                        'position': pred.get('position'),
                        'predictions': pred.get('predictions', {}),
                        'explanation': explanation
                    })

                    await self.connection_manager.broadcast({
                        'type': reply_type,
                        'question': question,
                        'answer': answer,
                        'player_id': player_id
                    })
                except Exception as e:
                    logger.error(f"Error processing question in LiveUpdateManager: {e}")
                    await self.connection_manager.broadcast({
                        'type': reply_type,
                        'question': question,
                        'answer': 'Sorry, I could not process your question right now.',
                        'player_id': player_id
                    })
            elif message_type == 'scenario_change':
                # Handle scenario changes
                await self.handle_scenario_change(message.get('data', {}))
            
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
    
    async def _initialize_game(self):
        """Initialize current game and generate events"""
        
        # Get Eagles team
        eagles = self.pulse_client.find_team_by_name("Eagles")
        if not eagles:
            logger.error("Could not find Eagles team data")
            # Create fallback data
            eagles = {'id': 'eagles_fallback', 'name': 'Eagles', 'market': 'Philadelphia'}
        
        # Get Eagles players
        eagles_players = self.pulse_client.get_team_players(eagles['id'])
        if not eagles_players or len(eagles_players) == 0:
            logger.warning("No Eagles players found, using sample data")
            # Create sample players
            eagles_players = [
                {'id': 'jh1', 'first_name': 'Jalen', 'last_name': 'Hurts', 'position': 'QB'},
                {'id': 'db1', 'first_name': 'DeVonta', 'last_name': 'Smith', 'position': 'WR'},
                {'id': 'ajb1', 'first_name': 'A.J.', 'last_name': 'Brown', 'position': 'WR'},
                {'id': 'ds1', 'first_name': 'Dallas', 'last_name': 'Goedert', 'position': 'TE'},
                {'id': 'ks1', 'first_name': 'Kenneth', 'last_name': 'Gainwell', 'position': 'RB'},
            ]
        
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
        # Initialize game clock (start of quarter: 15 minutes)
        self.game_clock_seconds = 15 * 60
        self.current_game['time_remaining'] = f"{self.game_clock_seconds // 60:02d}:{self.game_clock_seconds % 60:02d}"
        
        logger.info(f"Game initialized with {len(self.current_game['players'])} players")
        
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
            # 10-15 events per quarter
            num_events = random.randint(10, 15)
            
            for i in range(num_events):
                event_time = current_time + timedelta(seconds=i*5)
                
                event_types = [
                    'pass_completion', 'rush_attempt', 'reception', 'touchdown', 
                    'field_goal', 'interception', 'fumble', 'sack',
                    'timeout', 'penalty'
                ]
                
                # Weighted probabilities for event types
                event_type = random.choices(
                    event_types,
                    weights=[20, 15, 18, 8, 5, 3, 2, 4, 10, 15]
                )[0]
                
                # Select random player for the event
                player = random.choice(self.current_game['players'])
                
                event = {
                    'id': f"event_{quarter}_{i}",
                    'type': event_type,
                    'quarter': quarter,
                    'timestamp': event_time.isoformat(),
                    'player_id': player['id'],
                    'player_name': f"{player.get('first_name', '')} {player.get('last_name', '')}".strip(),
                    'description': self._generate_event_description(event_type, player),
                    'impact': self._calculate_event_impact(event_type)
                }
                
                events.append(event)
        
        self.game_events = events
        logger.info(f"Generated {len(events)} game events for simulation")
    
    def _generate_event_description(self, event_type: str, player: Dict) -> str:
        """Generate realistic event descriptions"""
        
        player_name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
        
        descriptions = {
            'pass_completion': f"{player_name} completes pass for {random.randint(8, 25)} yards",
            'rush_attempt': f"{player_name} rushes for {random.randint(2, 15)} yards",
            'reception': f"{player_name} catches pass for {random.randint(8, 20)} yards",
            'touchdown': f"TOUCHDOWN! {player_name} scores!",
            'field_goal': f"Field goal attempt by {player_name}",
            'interception': f"INTERCEPTION! {player_name} picked off!",
            'fumble': f"{player_name} fumbles the ball",
            'sack': f"{player_name} sacked for loss",
            'timeout': f"{player_name}'s team calls timeout",
            'penalty': f"Penalty called on the play involving {player_name}"
        }
        
        return descriptions.get(event_type, f"{player_name} - {event_type}")
    
    def _calculate_event_impact(self, event_type: str) -> Dict[str, Any]:
        """Calculate how an event impacts predictions"""
        
        impacts = {
            'pass_completion': {'passing_yards': 1.02, 'confidence_boost': 0.01},
            'rush_attempt': {'rushing_yards': 1.01, 'confidence_boost': 0.005},
            'reception': {'receiving_yards': 1.02, 'confidence_boost': 0.01},
            'touchdown': {'touchdowns': 1.1, 'confidence_boost': 0.05},
            'field_goal': {'confidence_boost': 0.01},
            'interception': {'interceptions': 1.1, 'passing_yards': 0.98, 'confidence_penalty': 0.02},
            'fumble': {'all_stats': 0.98, 'confidence_penalty': 0.02},
            'sack': {'passing_yards': 0.98, 'confidence_penalty': 0.01},
            'timeout': {'confidence_boost': 0.005},
            'penalty': {'all_stats': 0.99, 'confidence_penalty': 0.01}
        }
        
        return impacts.get(event_type, {})
    
    async def _simulation_loop(self):
        """Main simulation loop that processes events"""
        
        logger.info("🎮 Starting event simulation loop...")
        
        while self.is_running and self.event_index < len(self.game_events):
            # Wait 5-8 seconds between events
            await asyncio.sleep(random.uniform(5, 8))
            
            if not self.is_running:
                break
            
            # Get next event
            event = self.game_events[self.event_index]
            self.event_index += 1
            
            # Process the event
            await self._process_event(event)
            
        logger.info("✅ Simulation loop completed")
    
    async def _game_clock_loop(self):
        """Background task that decrements the game clock and advances quarters."""
        try:
            while self.is_running and self.current_game and self.current_game.get('status') == 'in_progress':
                await asyncio.sleep(1)

                # Ensure clock initialized
                if self.game_clock_seconds is None:
                    self.game_clock_seconds = 15 * 60

                # Decrement clock
                self.game_clock_seconds = max(0, self.game_clock_seconds - 1)
                mins = self.game_clock_seconds // 60
                secs = self.game_clock_seconds % 60
                self.current_game['time_remaining'] = f"{mins:02d}:{secs:02d}"

                # If clock hits zero, advance quarter or end game
                if self.game_clock_seconds == 0:
                    if self.current_game['quarter'] < 4:
                        self.current_game['quarter'] += 1
                        # reset clock for next quarter
                        self.game_clock_seconds = 15 * 60
                        self.current_game['time_remaining'] = '15:00'
                    else:
                        # Auto-reset game when Q4 ends
                        await self.reset_game()

                # Broadcast tick (small update) so clients update clocks
                try:
                    await self.connection_manager.broadcast({
                        'type': 'tick',
                        'timestamp': datetime.now().isoformat(),
                        'game_state': self._get_current_game_state()
                    })
                except Exception as e:
                    logger.debug(f"Failed to broadcast tick: {e}")

            logger.info('Game clock loop exiting')
        except asyncio.CancelledError:
            logger.info('Game clock task cancelled')
        except Exception as e:
            logger.error(f"Game clock error: {e}")
    
    async def _process_event(self, event: Dict[str, Any]):
        """Process a single game event and update predictions"""
        
        try:
            # Update game state based on event
            self._update_game_state(event)
            
            # Get affected player
            player_id = event['player_id']
            affected_player = None
            
            for player in self.current_game['players']:
                if player['id'] == player_id:
                    affected_player = player
                    break
            
            if not affected_player:
                logger.warning(f"Player {player_id} not found in current game")
                # Still broadcast the event
                await self.connection_manager.broadcast({
                    'type': 'live_update',
                    'timestamp': datetime.now().isoformat(),
                    'event': event,
                    'game_state': self._get_current_game_state()
                })
                return
            
            # Get updated prediction for affected player
            updated_prediction = self.prediction_engine.predict_player_performance(
                affected_player,
                self.current_game['home_team']['id']
            )
            
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
            logger.info(f"📡 Broadcast event: {event['type']} - {event['description']}")
            
        except Exception as e:
            logger.error(f"Error processing event: {e}")
    
    def _update_game_state(self, event: Dict[str, Any]):
        """Update game state based on event"""
        
        if not self.current_game:
            return
        
        # Update quarter
        self.current_game['quarter'] = event['quarter']
        
        # Update score for touchdowns/field goals
        if event['type'] == 'touchdown':
            self.current_game['home_score'] += 7
        elif event['type'] == 'field_goal':
            self.current_game['home_score'] += 3
    
    def _generate_impact_analysis(self, event: Dict[str, Any], prediction: Dict[str, Any]) -> str:
        """Generate human-readable impact analysis"""
        
        event_type = event['type']
        player_name = event['player_name']
        
        if event_type == 'touchdown':
            return f"🔥 {player_name}'s touchdown significantly boosts their scoring potential for the rest of the game."
        elif event_type == 'pass_completion':
            return f"✅ {player_name} is finding rhythm - expect continued passing success."
        elif event_type == 'rush_attempt':
            return f"🏃 Ground game is working for {player_name} - likely to see more carries."
        elif event_type == 'interception':
            return f"⚠️ The interception may limit {player_name}'s passing opportunities going forward."
        elif event_type == 'reception':
            return f"🎯 {player_name} is being targeted - watch for more receptions."
        else:
            return f"This {event_type} may influence {player_name}'s remaining game performance."
    
    def _get_current_game_state(self) -> Dict[str, Any]:
        """Get current game state for broadcasting"""
        
        if not self.current_game:
            return {}
        
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
        """Broadcast initial game state with predictions"""
        
        if not self.current_game:
            logger.error("No current game to broadcast")
            return
        
        # Get initial predictions for top players
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
        logger.info(f"📤 Broadcast initial game state with {len(initial_predictions)} predictions")
    
    async def handle_scenario_change(self, scenario_data: Dict[str, Any]):
        """Handle scenario changes from the frontend"""
        
        if not self.current_game:
            return
        
        scenario_type = scenario_data.get('type')
        
        logger.info(f"🎲 Handling scenario change: {scenario_type}")
        
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
            logger.info(f"📡 Broadcast scenario update: {scenario_type}")
        
        elif scenario_type == 'high_scoring':
            # Simulate high scoring game scenario
            updated_predictions = []
            
            for player in self.current_game['players'][:3]:
                prediction = self.prediction_engine.predict_player_performance(
                    player,
                    self.current_game['home_team']['id'],
                    game_context={'scoring_environment': 'high'}
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
                    'description': "High scoring game environment activated"
                },
                'updated_predictions': updated_predictions
            }
            
            await self.connection_manager.broadcast(scenario_message)
            logger.info(f"📡 Broadcast scenario update: {scenario_type}")