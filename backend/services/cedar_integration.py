# backend/services/cedar_integration.py
import logging
from typing import Dict, List, Any, Optional
import json
import os
from openai import OpenAI

logger = logging.getLogger(__name__)

class ChatGPTExplainer:
    def __init__(self):
        self.explanation_cache = {}
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = OpenAI(api_key=api_key)
            self.use_gpt = True
            logger.info("✅ ChatGPT initialized with OpenAI integration")
        else:
            self.client = None
            self.use_gpt = False
            logger.warning("⚠️ OPENAI_API_KEY not found - using fallback responses")
        
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
    
    def answer_question(self, question: str, player_data: Dict[str, Any]) -> str:
        """Answer questions using ChatGPT for natural conversations
        Provides a concise answer and a short, non-sensitive explanation of the key factors that led to the result.
        Does NOT disclose internal chain-of-thought or step-by-step reasoning."""
        
        # If GPT is available, use it for smart responses
        if self.use_gpt and self.client:
            return self._answer_with_gpt(question, player_data)
        
        # Fallback to pattern matching if no API key
        return self._answer_with_patterns(question, player_data)
    
    def _answer_with_gpt(self, question: str, player_data: Dict[str, Any]) -> str:
        """Use OpenAI to provide a concise answer + brief explanation without revealing internal chain-of-thought."""
        
        player_name = player_data.get('player_name', 'Player')
        position = player_data.get('position', 'N/A')
        predictions = player_data.get('predictions', {})
        explanation = player_data.get('explanation', {})
        
        # Format predictions for GPT
        pred_summary = []
        for stat_type, data in predictions.items():
            pred_summary.append(
                f"- {stat_type.replace('_', ' ')}: {data['predicted_value']} "
                f"(confidence: {data['confidence']*100:.0f}%, "
                f"over probability: {data.get('probability_over', 0)*100:.0f}%)"
            )
        
        pred_text = "\n".join(pred_summary)
        overall_summary = explanation.get('overall_summary', '')
        
        # System prompt explicitly requests a concise final answer + short explanation and avoids chain-of-thought
        system_prompt = f"""You are ChatGPT, an assistant that explains sports predictions.

Player: {player_name} ({position})

Predictions:\n{pred_text}

Context: {overall_summary}

Instructions for the assistant:
- Provide a concise answer to the user's question (1-3 sentences) followed by a short explanation of the key factors and numeric evidence supporting the answer (2-4 bullet points or sentences).
- Do NOT reveal your internal chain-of-thought, step-by-step deliberation, or hidden internal reasoning.
- When possible, cite specific numbers from the provided prediction data.
- If the question asks about stats not present in the data, state what is missing and offer a best-effort, clearly-labeled estimate.
- Keep answers friendly and concise."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                max_tokens=300,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return "I'm having trouble connecting right now. Try asking about specific stats like 'passing yards' or 'confidence levels'."
    
    def _answer_with_patterns(self, question: str, player_data: Dict[str, Any]) -> str:
        """Fallback pattern-matching responses (original implementation)"""
        
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
    
    # Keep ALL the other helper methods from your original file
    # (_generate_narrative_explanation, _generate_overall_summary, etc.)
    # They remain unchanged below.
    
    def _generate_narrative_explanation(self, player_name: str, position: str, 
                                      pred_type: str, predicted_value: float, 
                                      confidence: float, top_factors: List) -> str:
        """Generate human-readable narrative explanation"""
        
        pred_type_map = {
            'passing_yards': 'passing yards',
            'rushing_yards': 'rushing yards', 
            'receiving_yards': 'receiving yards',
            'touchdowns': 'touchdowns',
            'interceptions': 'interceptions'
        }
        
        pred_name = pred_type_map.get(pred_type, pred_type)
        narrative = f"{player_name} is projected to achieve {predicted_value} {pred_name} "
        narrative += f"with {confidence:.1%} confidence. "
        
        positive_factors = [f for f in top_factors if f[1] > 0]
        negative_factors = [f for f in top_factors if f[1] < 0]
        
        if positive_factors:
            factor_name = self._humanize_feature_name(positive_factors[0][0])
            narrative += f"The main driver is {factor_name}, which strongly favors higher performance. "
        
        if negative_factors:
            factor_name = self._humanize_feature_name(negative_factors[0][0])
            narrative += f"However, {factor_name} presents some challenges that may limit output. "
        
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
        
        scenarios.append({
            'scenario': 'What if weather conditions worsen?',
            'impact': 'Passing game could decrease by 15-20%, rushing may increase slightly',
            'explanation': 'Poor weather typically reduces passing accuracy and increases reliance on ground game',
            'affected_stats': ['passing_yards', 'receiving_yards']
        })
        
        scenarios.append({
            'scenario': 'What if the opponent focuses on stopping the pass?',
            'impact': f'{player_name} might see 10-15% fewer targets but higher completion rate',
            'explanation': 'Defensive focus on pass coverage often opens up underneath routes and running lanes',
            'affected_stats': ['receiving_yards', 'rushing_yards']
        })
        
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
    
    # Add the other helper methods (_explain_prediction_reasoning, etc.)
    # Copy them from your current file...
    
    def _explain_prediction_reasoning(self, player_data: Dict[str, Any]) -> str:
        player_name = player_data.get('player_name', 'Player')
        return f"The predictions for {player_name} are based on player skill, recent form, team offensive strength, opponent matchup, and game context analyzed through machine learning."
    
    def _explain_confidence_reasoning(self, predictions: Dict) -> str:
        confidence_levels = [pred['confidence'] for pred in predictions.values()]
        avg_confidence = sum(confidence_levels) / len(confidence_levels)
        return f"Average confidence is {avg_confidence:.1%}. Higher confidence means stronger agreement across all prediction factors."
    
    def _explain_yards_prediction(self, player_name: str, predictions: Dict, question: str) -> str:
        yards_preds = {k: v for k, v in predictions.items() if 'yards' in k}
        if not yards_preds:
            return f"No yardage predictions available for {player_name}."
        
        explanation = f"{player_name}'s yardage predictions: "
        for pred_type, pred_data in yards_preds.items():
            stat_name = pred_type.replace('_', ' ')
            explanation += f"{stat_name}: {pred_data['predicted_value']} yards ({pred_data['confidence']:.1%} confidence). "
        return explanation
    
    def _explain_touchdown_prediction(self, player_name: str, predictions: Dict) -> str:
        td_pred = predictions.get('touchdowns')
        if not td_pred:
            return f"No touchdown prediction available for {player_name}."
        
        predicted_tds = td_pred['predicted_value']
        confidence = td_pred['confidence']
        likelihood = "high" if predicted_tds > 1.5 else "moderate" if predicted_tds > 0.8 else "low"
        
        return f"{player_name} has a {likelihood} likelihood of scoring, predicted: {predicted_tds} TDs ({confidence:.1%} confidence)."
    
    def _explain_risk_factors(self, player_data: Dict) -> str:
        player_name = player_data.get('player_name', 'Player')
        predictions = player_data.get('predictions', {})
        
        low_conf_stats = [k.replace('_', ' ') for k, v in predictions.items() if v['confidence'] < 0.7]
        
        if low_conf_stats:
            return f"Risk factors for {player_name}: uncertainty in {', '.join(low_conf_stats)}. These areas could vary significantly from predictions."
        return f"{player_name} has low risk with consistent predictions across all metrics."

# Backwards-compatible alias: keep CedarExplainer available for other modules
CedarExplainer = ChatGPTExplainer