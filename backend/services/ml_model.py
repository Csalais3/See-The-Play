# backend/services/ml_model.py - COMPLETE FIXED VERSION

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import shap
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

class PredictionEngine:
    def __init__(self, pulse_client):
        self.pulse_client = pulse_client
        self.models = {}
        self.scalers = {}
        self.feature_importances = {}
        self.shap_explainers = {}
        
        # Store baseline stats for players (simulates historical data)
        self.player_baselines = {}
        
        # Track live game stats
        self.live_game_stats = defaultdict(lambda: {
            'passing_yards': 0,
            'rushing_yards': 0,
            'receiving_yards': 0,
            'touchdowns': 0,
            'interceptions': 0,
            'targets': 0,
            'receptions': 0,
            'carries': 0
        })
        
        self._initialize_models()
        self._load_realistic_baselines()
        
    def _load_realistic_baselines(self):
        """Load realistic baseline stats for NFL players by position"""
        
        # These are based on actual NFL averages per game
        self.position_baselines = {
            'QB': {
                'passing_yards': {'mean': 245, 'std': 45, 'min': 150, 'max': 400},
                'rushing_yards': {'mean': 15, 'std': 20, 'min': 0, 'max': 80},
                'touchdowns': {'mean': 1.8, 'std': 0.8, 'min': 0, 'max': 5},
                'interceptions': {'mean': 0.8, 'std': 0.6, 'min': 0, 'max': 3}
            },
            'RB': {
                'rushing_yards': {'mean': 75, 'std': 35, 'min': 20, 'max': 180},
                'receiving_yards': {'mean': 25, 'std': 20, 'min': 0, 'max': 100},
                'touchdowns': {'mean': 0.7, 'std': 0.5, 'min': 0, 'max': 3},
                'fumbles': {'mean': 0.2, 'std': 0.3, 'min': 0, 'max': 2}
            },
            'WR': {
                'receiving_yards': {'mean': 70, 'std': 35, 'min': 10, 'max': 180},
                'touchdowns': {'mean': 0.5, 'std': 0.4, 'min': 0, 'max': 3},
                'targets': {'mean': 7, 'std': 3, 'min': 2, 'max': 15},
                'receptions': {'mean': 4.5, 'std': 2, 'min': 1, 'max': 12}
            },
            'TE': {
                'receiving_yards': {'mean': 45, 'std': 25, 'min': 10, 'max': 120},
                'touchdowns': {'mean': 0.4, 'std': 0.3, 'min': 0, 'max': 2},
                'targets': {'mean': 5, 'std': 2, 'min': 1, 'max': 10},
                'receptions': {'mean': 3.5, 'std': 1.5, 'min': 1, 'max': 8}
            }
        }
        
        # Player skill multipliers (simulates player quality)
        self.player_skill_tiers = {
            'elite': 1.3,      # Top 10% of players
            'very_good': 1.15, # Top 25%
            'good': 1.0,       # Average starters
            'backup': 0.7      # Backup players
        }
        
    def _initialize_models(self):
        """Initialize ML models for different prediction types"""
        
        prediction_types = ['passing_yards', 'rushing_yards', 'receiving_yards', 'touchdowns', 'interceptions']
        
        for pred_type in prediction_types:
            self.models[pred_type] = RandomForestRegressor(
                n_estimators=100,
                random_state=42,
                max_depth=10
            )
            self.scalers[pred_type] = StandardScaler()
        
        # Train with dummy data (in production, use historical data)
        self._train_dummy_models()
    
    def _train_dummy_models(self):
        """Train models with synthetic data"""
        
        n_samples = 1000
        
        for pred_type in self.models.keys():
            # Generate synthetic training data
            X = np.random.rand(n_samples, 10)  # 10 features
            
            # Generate synthetic targets with realistic distributions
            if 'yards' in pred_type:
                y = np.random.normal(200, 50, n_samples)
            elif 'touchdowns' in pred_type:
                y = np.random.poisson(1.5, n_samples)
            else:
                y = np.random.poisson(0.8, n_samples)
            
            # Fit scaler and model
            X_scaled = self.scalers[pred_type].fit_transform(X)
            self.models[pred_type].fit(X_scaled, y)
    
    def _get_stat_types_for_position(self, position: str) -> List[str]:
        """Get relevant stat types for a position"""
        
        position_stats = {
            'QB': ['passing_yards', 'rushing_yards', 'touchdowns', 'interceptions'],
            'RB': ['rushing_yards', 'receiving_yards', 'touchdowns'],
            'WR': ['receiving_yards', 'touchdowns', 'receptions', 'targets'],
            'TE': ['receiving_yards', 'touchdowns', 'receptions', 'targets'],
            'K': ['field_goals', 'extra_points'],
        }
        
        return position_stats.get(position, ['touchdowns'])
    
    def _create_player_baseline(self, player: Dict[str, Any], position: str):
        """Create baseline stats for a player"""
        
        player_id = player.get('id')
        
        # Assign random skill tier
        skill_tier = np.random.choice(
            list(self.player_skill_tiers.keys()),
            p=[0.1, 0.15, 0.5, 0.25]  # Elite, Very Good, Good, Backup
        )
        skill_multiplier = self.player_skill_tiers[skill_tier]
        
        # Get position baselines
        position_stats = self.position_baselines.get(position, {})
        
        # Create player-specific baseline
        player_baseline = {}
        for stat_type, stat_info in position_stats.items():
            player_baseline[stat_type] = {
                'mean': stat_info['mean'] * skill_multiplier,
                'std': stat_info['std'] * 0.8,  # Slightly less variance than position average
                'min': stat_info['min'],
                'max': stat_info['max']
            }
        
        self.player_baselines[player_id] = player_baseline
        logger.info(f"Created baseline for {player.get('first_name')} {player.get('last_name')} ({position}) - Tier: {skill_tier}")
    
    def _extract_player_features(self, player: Dict[str, Any], 
                                 team_stats: Dict[str, Any],
                                 game_context: Dict[str, Any]) -> np.ndarray:
        """Extract features for ML prediction"""
        
        # Feature 1: Player skill level (0-1)
        player_skill = np.random.uniform(0.6, 0.95)
        
        # Feature 2: Recent form (0-1)
        recent_form = np.random.uniform(0.5, 1.0)
        
        # Feature 3: Opponent defense strength (0-1, lower is better for offense)
        opponent_defense = game_context.get('opponent_defense', np.random.uniform(0.4, 0.8))
        
        # Feature 4: Home/Away advantage
        home_advantage = game_context.get('home_advantage', np.random.choice([1.0, 1.1]))
        
        # Feature 5: Weather impact (0-1)
        weather_impact = game_context.get('weather_impact', 1.0)
        
        # Feature 6: Game script (passing vs rushing game)
        game_script = np.random.uniform(0.3, 0.7)
        
        # Feature 7: Team pace (plays per game)
        team_pace = team_stats.get('pace', 1.0)
        
        # Feature 8: Red zone efficiency
        red_zone_eff = np.random.uniform(0.6, 0.9)
        
        # Feature 9: Target share (for receivers)
        position = player.get('position', '')
        if position in ['WR', 'TE']:
            target_share = np.random.uniform(0.6, 0.95)
        else:
            target_share = 0.5
        
        # Feature 10: Health status
        health_status = 1.0  # Assume healthy
        
        features = np.array([
            player_skill, recent_form, opponent_defense, home_advantage,
            weather_impact, game_script, team_pace, red_zone_eff,
            target_share, health_status
        ]).reshape(1, -1)
        
        return features
    
    def predict_player_performance(self, player: Dict[str, Any], team_id: str, 
                                   game_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate predictions for a player's performance
        """
        try:
            position = player.get('position', 'UNKNOWN')
            player_id = player.get('id')
            player_name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
            
            # Get or create baseline for this player
            if player_id not in self.player_baselines:
                self._create_player_baseline(player, position)
            
            baseline = self.player_baselines.get(player_id, {})
            
            # Generate predictions for each stat type
            predictions = {}
            
            # Determine which stats to predict based on position
            stat_types = self._get_stat_types_for_position(position)
            
            for stat_type in stat_types:
                if stat_type not in baseline:
                    continue
                
                base_value = baseline[stat_type]['mean']
                std_dev = baseline[stat_type]['std']
                
                # Add some randomness
                variance = np.random.normal(0, std_dev * 0.3)
                predicted_value = base_value + variance
                
                # Apply game context if provided
                if game_context:
                    if 'weather_impact' in game_context:
                        predicted_value *= game_context['weather_impact']
                    if 'scoring_environment' in game_context and game_context['scoring_environment'] == 'high':
                        predicted_value *= 1.15
                
                # Get live stats if available
                live_stats = self.live_game_stats.get(player_id, {})
                current_stat = live_stats.get(stat_type, 0)
                
                # Adjust prediction based on current performance
                if current_stat > 0:
                    remaining_predicted = max(0, predicted_value - current_stat)
                    predicted_value = current_stat + remaining_predicted * 0.8
                
                # Calculate confidence - FIXED: No more .clip() error
                base_confidence = 0.75 + np.random.uniform(-0.1, 0.1)
                
                # Adjust confidence based on variance
                if std_dev > 0:
                    variance_factor = abs(variance) / std_dev
                    # Use max/min instead of .clip()
                    confidence_adjustment = -0.1 * min(variance_factor, 1.0)
                else:
                    confidence_adjustment = 0
                
                confidence = base_confidence + confidence_adjustment
                
                # Ensure confidence is between 0.5 and 0.95 - FIXED
                confidence = max(0.5, min(0.95, confidence))
                
                # Calculate over/under probabilities
                prob_over = confidence if predicted_value > base_value else 1 - confidence
                prob_under = 1 - prob_over
                
                # Ensure probabilities sum to 1 and are in valid range
                prob_over = max(0.1, min(0.9, prob_over))
                prob_under = 1 - prob_over
                
                predictions[stat_type] = {
                    'predicted_value': round(predicted_value, 1),
                    'confidence': round(confidence, 2),
                    'probability_over': round(prob_over, 2),
                    'probability_under': round(prob_under, 2),
                    'baseline': round(base_value, 1),
                    'live_stats': current_stat
                }
            
            # Calculate overall confidence
            if predictions:
                confidences = [p['confidence'] for p in predictions.values()]
                overall_confidence = sum(confidences) / len(confidences)
            else:
                overall_confidence = 0.7
            
            return {
                'player_id': player_id,
                'player_name': player_name,
                'position': position,
                'team_id': team_id,
                'predictions': predictions,
                'overall_confidence': round(overall_confidence, 2),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error predicting performance for {player.get('id')}: {e}")
            # Return a basic prediction as fallback
            return {
                'player_id': player.get('id'),
                'player_name': f"{player.get('first_name', '')} {player.get('last_name', '')}".strip(),
                'position': player.get('position', 'UNKNOWN'),
                'team_id': team_id,
                'predictions': {},
                'overall_confidence': 0.7,
                'timestamp': datetime.now().isoformat()
            }
    
    def update_live_stats(self, player_id: str, event_data: Dict[str, Any]):
        """Update live game stats for a player"""
        
        event_type = event_data.get('type')
        yards = event_data.get('yards', 0)
        is_touchdown = event_data.get('touchdown', False)
        
        if event_type in ['pass_completion', 'rush_attempt', 'reception']:
            if 'pass' in event_type:
                self.live_game_stats[player_id]['passing_yards'] += yards
            elif 'rush' in event_type:
                self.live_game_stats[player_id]['rushing_yards'] += yards
            elif 'reception' in event_type:
                self.live_game_stats[player_id]['receiving_yards'] += yards
                self.live_game_stats[player_id]['receptions'] += 1
        
        if is_touchdown:
            self.live_game_stats[player_id]['touchdowns'] += 1
        
        if event_type == 'interception':
            self.live_game_stats[player_id]['interceptions'] += 1
    
    def get_top_picks(self, team_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top prediction picks for a team"""
        
        try:
            # Get team players
            players = self.pulse_client.get_team_players(team_id)
            
            if not players:
                logger.warning(f"No players found for team {team_id}")
                return []
            
            # Generate predictions for all players
            all_predictions = []
            
            for player in players[:limit]:
                prediction = self.predict_player_performance(player, team_id)
                all_predictions.append(prediction)
            
            # Sort by overall confidence
            all_predictions.sort(key=lambda x: x['overall_confidence'], reverse=True)
            
            return all_predictions[:limit]
            
        except Exception as e:
            logger.error(f"Error getting top picks for team {team_id}: {e}")
            return []
    
    def get_feature_importance(self, prediction_type: str) -> Dict[str, float]:
        """Get feature importance for a prediction type"""
        
        if prediction_type not in self.models:
            return {}
        
        feature_names = [
            'player_skill', 'recent_form', 'opponent_defense', 'home_advantage',
            'weather_impact', 'game_script', 'team_pace', 'red_zone_eff',
            'target_share', 'health_status'
        ]
        
        importances = self.models[prediction_type].feature_importances_
        
        return dict(zip(feature_names, importances.tolist()))