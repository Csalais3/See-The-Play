# backend/services/cedar_integration.py
import logging
from typing import Dict, List, Any, Optional
import json
import random

logger = logging.getLogger(__name__)

class CedarExplainer:
    def __init__(self):
        self.explanation_cache = {}
        
    def generate_explanation(self, prediction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate human-readable explanation for predictions"""
        
        player_name = prediction_data.get('player_name', 'Player')
        position = prediction_data.get('position', 'N/A')
        predictions = prediction_data.get('predictions', {})
        explanations = prediction_data.get('explanations', {})
        
        # Generate narrative explanations
        narrative_explanations = {}
        key_factors = {}
        
        for pred_type, pred_data in predictions.items():
            predicted_value = pred_data['predicted_value']
            confidence = pred_data['confidence']
            
            # Get top contributing factors
            if pred_type in explanations:
                shap_values = explanations[pred_type]['shap_values']
                feature_names = explanations[pred_type]['feature_names']
                
                # Get top 3 positive and negative contributors
                feature_contributions = list(zip(feature_names, shap_values))
                feature_contributions.sort(key=lambda x: abs(x[1]), reverse=True)
                
                top_factors = feature_contributions[:3]
                key_factors[pred_type] = top_factors
                
                # Generate narrative
                narrative = self._generate_narrative_explanation(
                    player_name, position, pred_type, predicted_value, 
                    confidence, top_factors
                )
                narrative_explanations[pred_type] = narrative
        
        # Generate overall player summary
        overall_summary = self._generate_overall_summary(
            player_name, position, predictions, key_factors
        )
        
        # Generate what-if scenarios
        what_if_scenarios = self._generate_what_if_scenarios(
            player_name, predictions, explanations
        )
        
        return {
            'player_id': prediction_data.get('player_id'),
            'player_name': player_name,
            'overall_summary': overall_summary,
            'narrative_explanations': narrative_explanations,
            'key_factors': key_factors,
            'what_if_scenarios': what_if_scenarios,
            'confidence_explanation': self._explain_confidence_levels(predictions),
            'timestamp': prediction_data.get('timestamp')
        }
    
    def _generate_narrative_explanation(self, player_name: str, position: str, 
                                      pred_type: str, predicted_value: float, 
                                      confidence: float, top_factors: List) -> str:
        """Generate human-readable narrative explanation"""
        
        # Map prediction types to readable names
        pred_type_map = {
            'passing_yards': 'passing yards',
            'rushing_yards': 'rushing yards', 
            'receiving_yards': 'receiving yards',
            'touchdowns': 'touchdowns',
            'interceptions': 'interceptions'
        }
        
        pred_name = pred_type_map.get(pred_type, pred_type)
        
        # Start with base prediction
        narrative = f"{player_name} is projected to achieve {predicted_value} {pred_name} "
        narrative += f"with {confidence:.1%} confidence. "
        
        # Add key contributing factors
        positive_factors = [f for f in top_factors if f[1] > 0]
        negative_factors = [f for f in top_factors if f[1] < 0]
        
        if positive_factors:
            factor_name = self._humanize_feature_name(positive_factors[0][0])
            narrative += f"The main driver is {factor_name}, which strongly favors higher performance. "
        
        if negative_factors:
            factor_name = self._humanize_feature_name(negative_factors[0][0])
            narrative += f"However, {factor_name} presents some challenges that may limit output. "
        
        # Add context based on confidence level
        if confidence > 0.8:
            narrative += "This is a high-confidence prediction with strong supporting factors."
        elif confidence > 0.7:
            narrative += "This is a moderate-confidence prediction with mixed signals."
        else:
            narrative += "This is a lower-confidence prediction due to conflicting factors."
        
        return narrative
    
    def _generate_overall_summary(self, player_name: str, position: str, 
                                predictions: Dict, key_factors: Dict) -> str:
        """Generate overall player performance summary"""
        
        # Calculate overall performance expectation
        high_confidence_preds = [
            pred_type for pred_type, pred_data in predictions.items() 
            if pred_data['confidence'] > 0.75
        ]
        
        summary = f"{player_name} ({position}) is expected to have a "
        
        if len(high_confidence_preds) >= 3:
            summary += "strong overall performance today. "
        elif len(high_confidence_preds) >= 2:
            summary += "solid performance with some standout areas. "
        else:
            summary += "variable performance with uncertainty in key areas. "
        
        # Add position-specific insights
        if position == 'QB':
            passing_pred = predictions.get('passing_yards', {})
            if passing_pred.get('predicted_value', 0) > 250:
                summary += "Expect a high-volume passing game with good yardage potential. "
        elif position in ['RB', 'FB']:
            rushing_pred = predictions.get('rushing_yards', {})
            if rushing_pred.get('predicted_value', 0) > 100:
                summary += "Ground game should be productive with strong rushing output. "
        elif position in ['WR', 'TE']:
            receiving_pred = predictions.get('receiving_yards', {})
            if receiving_pred.get('predicted_value', 0) > 80:
                summary += "Should see significant targets with good receiving production. "
        
        return summary
    
    def _generate_what_if_scenarios(self, player_name: str, predictions: Dict, 
                                  explanations: Dict) -> List[Dict[str, Any]]:
        """Generate what-if scenario explanations"""
        
        scenarios = []
        
        # Scenario 1: Weather impact
        scenarios.append({
            'scenario': 'What if weather conditions worsen?',
            'impact': 'Passing game could decrease by 15-20%, rushing may increase slightly',
            'explanation': 'Poor weather typically reduces passing accuracy and increases reliance on ground game',
            'affected_stats': ['passing_yards', 'receiving_yards']
        })
        
        # Scenario 2: Opponent defensive adjustment
        scenarios.append({
            'scenario': 'What if the opponent focuses on stopping the pass?',
            'impact': f'{player_name} might see 10-15% fewer targets but higher completion rate',
            'explanation': 'Defensive focus on pass coverage often opens up underneath routes and running lanes',
            'affected_stats': ['receiving_yards', 'rushing_yards']
        })
        
        # Scenario 3: Game script changes
        scenarios.append({
            'scenario': 'What if this becomes a high-scoring game?',
            'impact': 'All offensive stats likely to increase by 20-30%',
            'explanation': 'High-scoring games increase total plays and opportunities for all players',
            'affected_stats': list(predictions.keys())
        })
        
        return scenarios
    
    def _explain_confidence_levels(self, predictions: Dict) -> Dict[str, str]:
        """Explain what different confidence levels mean"""
        
        explanations = {}
        
        for pred_type, pred_data in predictions.items():
            confidence = pred_data['confidence']
            
            if confidence > 0.85:
                explanation = "Very High - Strong consensus across all factors, minimal uncertainty"
            elif confidence > 0.75:
                explanation = "High - Most factors align, some minor conflicting signals"
            elif confidence > 0.65:
                explanation = "Moderate - Mixed signals from different factors, moderate uncertainty"
            else:
                explanation = "Low - Conflicting factors create high uncertainty in prediction"
            
            explanations[pred_type] = explanation
        
        return explanations
    
    def _humanize_feature_name(self, feature_name: str) -> str:
        """Convert technical feature names to human-readable descriptions"""
        
        feature_map = {
            'player_skill': 'player skill rating',
            'recent_form': 'recent performance form',
            'health_status': 'current health status',
            'offensive_rating': 'team offensive strength',
            'team_pace': 'team pace of play',
            'team_chemistry': 'team chemistry',
            'weather_impact': 'weather conditions',
            'home_advantage': 'home field advantage',
            'opponent_defense': 'opponent defensive strength',
            'game_importance': 'game importance level'
        }
        
        return feature_map.get(feature_name, feature_name.replace('_', ' '))
    
    def answer_question(self, question: str, player_data: Dict[str, Any]) -> str:
        """Answer specific questions about player predictions"""
        
        question_lower = question.lower()
        player_name = player_data.get('player_name', 'Player')
        predictions = player_data.get('predictions', {})
        
        # Simple question answering based on keywords
        if 'why' in question_lower and 'predict' in question_lower:
            return self._explain_prediction_reasoning(player_data)
        elif 'confidence' in question_lower:
            return self._explain_confidence_reasoning(predictions)
        elif 'yards' in question_lower:
            return self._explain_yards_prediction(player_name, predictions, question_lower)
        elif 'touchdown' in question_lower:
            return self._explain_touchdown_prediction(player_name, predictions)
        elif 'risk' in question_lower or 'concern' in question_lower:
            return self._explain_risk_factors(player_data)
        else:
            return f"I can help explain {player_name}'s predictions. Try asking about confidence levels, specific stats, or what factors influenced the predictions."
    
    def _explain_prediction_reasoning(self, player_data: Dict[str, Any]) -> str:
        """Explain the overall reasoning behind predictions"""
        
        player_name = player_data.get('player_name', 'Player')
        explanations = player_data.get('explanations', {})
        
        reasoning = f"The predictions for {player_name} are based on several key factors: "
        
        # Get most influential factors across all predictions
        all_factors = []
        for pred_type, explanation in explanations.items():
            if 'shap_values' in explanation and 'feature_names' in explanation:
                factors = list(zip(explanation['feature_names'], explanation['shap_values']))
                all_factors.extend(factors)
        
        if all_factors:
            # Group by feature name and average the impact
            factor_impacts = {}
            for feature_name, impact in all_factors:
                if feature_name not in factor_impacts:
                    factor_impacts[feature_name] = []
                factor_impacts[feature_name].append(impact)
            
            # Get top 3 most impactful features
            avg_impacts = {k: sum(v)/len(v) for k, v in factor_impacts.items()}
            top_factors = sorted(avg_impacts.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
            
            for i, (feature, impact) in enumerate(top_factors):
                if i == 0:
                    reasoning += f"primarily {self._humanize_feature_name(feature)}"
                elif i == len(top_factors) - 1:
                    reasoning += f", and {self._humanize_feature_name(feature)}"
                else:
                    reasoning += f", {self._humanize_feature_name(feature)}"
            
            reasoning += ". These factors were analyzed using advanced machine learning to provide the most accurate predictions possible."
        
        return reasoning
    
    def _explain_confidence_reasoning(self, predictions: Dict) -> str:
        """Explain confidence levels across predictions"""
        
        confidence_levels = [pred['confidence'] for pred in predictions.values()]
        avg_confidence = sum(confidence_levels) / len(confidence_levels)
        
        explanation = f"The average confidence across all predictions is {avg_confidence:.1%}. "
        
        high_conf = [k for k, v in predictions.items() if v['confidence'] > 0.8]
        low_conf = [k for k, v in predictions.items() if v['confidence'] < 0.65]
        
        if high_conf:
            pred_names = [k.replace('_', ' ') for k in high_conf]
            explanation += f"I'm most confident about {', '.join(pred_names)} due to strong supporting data. "
        
        if low_conf:
            pred_names = [k.replace('_', ' ') for k in low_conf]
            explanation += f"There's more uncertainty around {', '.join(pred_names)} due to conflicting factors. "
        
        return explanation
    
    def _explain_yards_prediction(self, player_name: str, predictions: Dict, question: str) -> str:
        """Explain yardage predictions"""
        
        yards_preds = {k: v for k, v in predictions.items() if 'yards' in k}
        
        if not yards_preds:
            return f"No yardage predictions available for {player_name}."
        
        explanation = f"{player_name}'s yardage predictions: "
        
        for pred_type, pred_data in yards_preds.items():
            stat_name = pred_type.replace('_', ' ')
            predicted_value = pred_data['predicted_value']
            confidence = pred_data['confidence']
            
            explanation += f"{stat_name}: {predicted_value} yards ({confidence:.1%} confidence). "
        
        return explanation
    
    def _explain_touchdown_prediction(self, player_name: str, predictions: Dict) -> str:
        """Explain touchdown predictions"""
        
        td_pred = predictions.get('touchdowns')
        if not td_pred:
            return f"No touchdown prediction available for {player_name}."
        
        predicted_tds = td_pred['predicted_value']
        confidence = td_pred['confidence']
        
        if predicted_tds > 1.5:
            likelihood = "strong"
        elif predicted_tds > 0.8:
            likelihood = "moderate" 
        else:
            likelihood = "low"
        
        return f"{player_name} has a {likelihood} likelihood of scoring touchdowns today, with a prediction of {predicted_tds} TDs ({confidence:.1%} confidence)."
    
    def _explain_risk_factors(self, player_data: Dict) -> str:
        """Explain potential risk factors"""
        
        player_name = player_data.get('player_name', 'Player')
        predictions = player_data.get('predictions', {})
        
        risks = []
        
        # Check for low confidence predictions
        low_conf_stats = [k for k, v in predictions.items() if v['confidence'] < 0.7]
        if low_conf_stats:
            risks.append(f"uncertainty in {', '.join([s.replace('_', ' ') for s in low_conf_stats])}")
        
        # Check for high variance predictions
        high_var_stats = [k for k, v in predictions.items() if v.get('std_deviation', 0) > v['predicted_value'] * 0.3]
        if high_var_stats:
            risks.append(f"high variability in {', '.join([s.replace('_', ' ') for s in high_var_stats])}")
        
        if risks:
            return f"Key risk factors for {player_name} include: {', and '.join(risks)}. These indicate areas where performance could significantly vary from predictions."
        else:
            return f"{player_name} has relatively low risk factors, with consistent predictions across all metrics."
