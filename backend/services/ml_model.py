# backend/services/ml_model.py
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import shap
import joblib
import logging
from typing import Dict, List, Any, Tuple
import random
from datetime import datetime

logger = logging.getLogger(__name__)

class PredictionEngine:
    def __init__(self, pulse_client):
        self.pulse_client = pulse_client
        self.models = {}
        self.scalers = {}
        self.feature_importances = {}
        self.shap_explainers = {}
        self._initialize_models()
        
    def _initialize_models(self):
        """Initialize ML models for different prediction types"""
        
        # Initialize models for different stats
        prediction_types = ['passing_yards', 'rushing_yards', 'receiving_yards', 'touchdowns', 'interceptions']
        
        for pred_type in prediction_types:
            # Create a simple model (in real scenario, you'd train on historical data)
            self.models[pred_type] = RandomForestRegressor(
                n_estimators=100,
                random_state=42,
                max_depth=10
            )
            self.scalers[pred_type] = StandardScaler()
            
        # Generate synthetic training data for demo purposes
        self._train_demo_models()
        
    def _train_demo_models(self):
        """Train models with synthetic data for demo purposes"""
        
        logger.info("Training demo models with synthetic data...")
        
        # Generate synthetic training data
        n_samples = 1000
        
        for pred_type in self.models.keys():
            # Create synthetic features
            X_train = np.random.rand(n_samples, 10)  # 10 features
            
            # Create synthetic targets with some patterns
            if pred_type == 'passing_yards':
                y_train = (X_train[:, 0] * 300 + X_train[:, 1] * 200 + 
                          np.random.normal(0, 50, n_samples)).clip(0, 500)
            elif pred_type == 'rushing_yards':
                y_train = (X_train[:, 2] * 150 + X_train[:, 3] * 100 + 
                          np.random.normal(0, 30, n_samples)).clip(0, 300)
            elif pred_type == 'receiving_yards':
                y_train = (X_train[:, 4] * 120 + X_train[:, 5] * 80 + 
                          np.random.normal(0, 25, n_samples)).clip(0, 250)
            elif pred_type == 'touchdowns':
                y_train = (X_train[:, 6] * 3 + X_train[:, 7] * 2 + 
                          np.random.normal(0, 1, n_samples)).clip(0, 6)
            else:  # interceptions
                y_train = (X_train[:, 8] * 2 + X_train[:, 9] * 1 + 
                          np.random.normal(0, 0.5, n_samples)).clip(0, 4)
            
            # Scale features and train model
            X_scaled = self.scalers[pred_type].fit_transform(X_train)
            self.models[pred_type].fit(X_scaled, y_train)
            
            # Store feature importances
            self.feature_importances[pred_type] = self.models[pred_type].feature_importances_
            
            # Create SHAP explainer
            self.shap_explainers[pred_type] = shap.TreeExplainer(self.models[pred_type])
            
        logger.info("Demo models trained successfully!")
    
    def _extract_player_features(self, player: Dict[str, Any], team_stats: Dict[str, Any], game_context: Dict[str, Any]) -> np.ndarray:
        """Extract features for a player prediction"""
        
        features = []
        
        # Player features
        features.append(random.uniform(0.6, 0.95))  # Player skill rating (synthetic)
        features.append(random.uniform(0.5, 1.0))   # Recent form (synthetic)
        features.append(random.uniform(0.7, 1.0))   # Health status (synthetic)
        
        # Team features
        features.append(team_stats.get('offensive_rating', random.uniform(0.5, 1.0)))
        features.append(team_stats.get('pace', random.uniform(0.6, 1.0)))
        features.append(random.uniform(0.4, 0.9))   # Team chemistry (synthetic)
        
        # Game context features
        features.append(game_context.get('weather_impact', random.uniform(0.8, 1.0)))
        features.append(game_context.get('home_advantage', random.uniform(0.9, 1.1)))
        features.append(game_context.get('opponent_defense', random.uniform(0.3, 0.8)))
        features.append(random.uniform(0.6, 1.0))   # Game importance (synthetic)
        
        return np.array(features).reshape(1, -1)
    
    def predict_player_performance(self, player: Dict[str, Any], team_id: str, game_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Predict player performance for various stats"""
        
        if game_context is None:
            game_context = {
                'weather_impact': random.uniform(0.8, 1.0),
                'home_advantage': random.uniform(0.9, 1.1),
                'opponent_defense': random.uniform(0.3, 0.8)
            }
        
        # Get team stats
        team_stats = self.pulse_client.get_team_statistics(team_id)
        if not team_stats:
            team_stats = {'offensive_rating': random.uniform(0.5, 1.0), 'pace': random.uniform(0.6, 1.0)}
        
        # Extract features
        features = self._extract_player_features(player, team_stats, game_context)
        
        predictions = {}
        explanations = {}
        
        # Generate predictions for each stat type
        for pred_type in self.models.keys():
            # Scale features
            features_scaled = self.scalers[pred_type].transform(features)
            
            # Make prediction
            prediction = self.models[pred_type].predict(features_scaled)[0]
            
            # Calculate confidence (synthetic for demo)
            confidence = random.uniform(0.65, 0.95)
            
            # Generate probability distribution
            std_dev = prediction * 0.2  # 20% std deviation
            prob_over = 1 - np.random.beta(2, 2) * 0.4  # Synthetic probability
            
            # Get SHAP explanations
            shap_values = self.shap_explainers[pred_type].shap_values(features_scaled)
            
            predictions[pred_type] = {
                'predicted_value': round(prediction, 1),
                'confidence': round(confidence, 3),
                'probability_over': round(prob_over, 3),
                'probability_under': round(1 - prob_over, 3),
                'std_deviation': round(std_dev, 2)
            }
            
            explanations[pred_type] = {
                'feature_importance': self.feature_importances[pred_type].tolist(),
                'shap_values': shap_values[0].tolist(),
                'feature_names': [
                    'player_skill', 'recent_form', 'health_status',
                    'offensive_rating', 'team_pace', 'team_chemistry',
                    'weather_impact', 'home_advantage', 'opponent_defense', 'game_importance'
                ]
            }
        
        return {
            'player_id': player['id'],
            'player_name': f"{player.get('first_name', '')} {player.get('last_name', '')}".strip(),
            'position': player.get('position', 'N/A'),
            'predictions': predictions,
            'explanations': explanations,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_top_picks(self, team_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top player predictions for a team"""
        
        players = self.pulse_client.get_team_players(team_id)
        if not players:
            return []
        
        # Get predictions for all players
        all_predictions = []
        
        for player in players[:limit]:  # Limit to avoid too many API calls
            try:
                prediction = self.predict_player_performance(player, team_id)
                
                # Calculate overall confidence score
                avg_confidence = np.mean([
                    pred['confidence'] for pred in prediction['predictions'].values()
                ])
                
                prediction['overall_confidence'] = round(avg_confidence, 3)
                all_predictions.append(prediction)
                
            except Exception as e:
                logger.error(f"Error predicting for player {player.get('id', 'unknown')}: {e}")
                continue
        
        # Sort by overall confidence
        all_predictions.sort(key=lambda x: x['overall_confidence'], reverse=True)
        
        return all_predictions[:limit]
    
    def update_predictions_with_live_data(self, live_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update predictions based on live game events"""
        
        # This would normally update model inputs based on live events
        # For demo purposes, we'll simulate some updates
        
        updated_predictions = {}
        
        for event in live_events:
            if event.get('type') == 'scoring_play':
                # Adjust predictions based on scoring
                player_id = event.get('player_id')
                if player_id:
                    # Simulate prediction adjustment
                    adjustment_factor = random.uniform(0.9, 1.1)
                    updated_predictions[player_id] = {
                        'adjustment_factor': adjustment_factor,
                        'reason': f"Scoring play: {event.get('description', 'Unknown play')}"
                    }
        
        return updated_predictions
