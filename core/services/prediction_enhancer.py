"""
Prediction Enhancer - Improves accuracy through smart filtering and risk assessment
WITHOUT building new ML models - uses SportMonks data more intelligently
"""

from typing import Dict, List
from datetime import datetime, timedelta
from django.utils import timezone


class PredictionEnhancer:
    """
    Enhance predictions using filters, market signals, and contextual awareness.
    Goal: Increase accuracy by being MORE SELECTIVE, not predicting better.
    """
    
    def __init__(self):
        self.confidence_floor = 0.60  # Raise from 55% to 60%
        self.ev_floor = 0.15  # Raise from 0% to 15%
        self.max_odds = 3.0  # Avoid high-variance bets
    
    def calculate_quality_score(self, prediction: Dict) -> float:
        """
        Calculate a quality score (0-100) for a prediction.
        Higher score = more likely to be accurate.
        
        Factors:
        1. Confidence level (higher = better)
        2. Expected Value (higher = better, but diminishing returns)
        3. Odds range (avoid extreme odds)
        4. Confidence-probability gap (well-calibrated?)
        5. Probability dominance (clear winner?)
        """
        score = 0.0
        
        # Factor 1: Base confidence (0-40 points)
        confidence = prediction.get('confidence', 0)
        if confidence >= 0.70:
            score += 40
        elif confidence >= 0.65:
            score += 30
        elif confidence >= 0.60:
            score += 20
        elif confidence >= 0.55:
            score += 10
        
        # Factor 2: Expected Value (0-25 points)
        ev = prediction.get('expected_value', 0) or 0
        if ev >= 0.25:
            score += 25
        elif ev >= 0.20:
            score += 20
        elif ev >= 0.15:
            score += 15
        elif ev >= 0.10:
            score += 10
        elif ev >= 0.05:
            score += 5
        
        # Factor 3: Odds range (0-15 points)
        # Moderate odds (1.6-2.5) are more predictable
        predicted_outcome = prediction.get('predicted_outcome', '').lower()
        odds_data = prediction.get('odds_data', {})
        predicted_odds = odds_data.get(predicted_outcome, 0)
        
        if 1.6 <= predicted_odds <= 2.5:
            score += 15  # Sweet spot
        elif 1.4 <= predicted_odds <= 3.0:
            score += 10  # Acceptable
        elif predicted_odds > 3.5:
            score -= 10  # High variance - risky
        
        # Factor 4: Probability dominance (0-10 points)
        # Clear winner = more confident prediction
        probs = prediction.get('probabilities', {})
        prob_home = probs.get('home', 0)
        prob_draw = probs.get('draw', 0)
        prob_away = probs.get('away', 0)
        
        sorted_probs = sorted([prob_home, prob_draw, prob_away], reverse=True)
        if len(sorted_probs) >= 2:
            gap = sorted_probs[0] - sorted_probs[1]
            if gap >= 0.30:  # 30% gap
                score += 10
            elif gap >= 0.20:  # 20% gap
                score += 5
        
        # Factor 5: Variance/consensus (0-10 points)
        variance = prediction.get('variance', 0)
        if variance and variance < 0.1:
            score += 10  # Low variance = models agree
        elif variance and variance < 0.2:
            score += 5
        
        return min(score, 100.0)
    
    def get_risk_warnings(self, prediction: Dict) -> List[str]:
        """
        Generate risk warnings for predictions that might be less reliable.
        Help users make informed decisions about which bets to actually place.
        """
        warnings = []
        
        confidence = prediction.get('confidence', 0)
        ev = prediction.get('expected_value', 0) or 0
        predicted_outcome = prediction.get('predicted_outcome', '').lower()
        odds_data = prediction.get('odds_data', {})
        predicted_odds = odds_data.get(predicted_outcome, 0)
        probs = prediction.get('probabilities', {})
        
        # Warning 1: Low confidence
        if confidence < 0.60:
            warnings.append({
                'type': 'confidence',
                'level': 'medium',
                'message': f'Moderate confidence ({confidence*100:.1f}%) - consider smaller stake',
                'icon': '⚠️'
            })
        
        # Warning 2: High odds = high variance
        if predicted_odds > 3.0:
            warnings.append({
                'type': 'variance',
                'level': 'high',
                'message': f'High odds ({predicted_odds:.2f}) = higher variance - riskier bet',
                'icon': '🎲'
            })
        
        # Warning 3: Draw prediction (hardest to predict)
        if predicted_outcome == 'draw':
            warnings.append({
                'type': 'outcome',
                'level': 'high',
                'message': 'Draw predictions are historically less accurate - bet cautiously',
                'icon': '🤝'
            })
        
        # Warning 4: Small probability gap
        sorted_probs = sorted([probs.get('home', 0), probs.get('draw', 0), probs.get('away', 0)], reverse=True)
        if len(sorted_probs) >= 2:
            gap = sorted_probs[0] - sorted_probs[1]
            if gap < 0.15:  # Less than 15% gap
                warnings.append({
                    'type': 'clarity',
                    'level': 'medium',
                    'message': 'Close probabilities - no clear favorite (consider skipping)',
                    'icon': '📊'
                })
        
        # Warning 5: Low EV despite positive
        if 0 < ev < 0.10:
            warnings.append({
                'type': 'value',
                'level': 'low',
                'message': 'Low expected value - minimal edge over bookmaker',
                'icon': '💰'
            })
        
        # Warning 6: High confidence but low odds (value mismatch)
        if confidence > 0.65 and predicted_odds < 1.5:
            implied_prob = 1 / predicted_odds
            if confidence < implied_prob + 0.05:
                warnings.append({
                    'type': 'value',
                    'level': 'medium',
                    'message': 'Low odds vs confidence - bookmaker agrees (less value)',
                    'icon': '⚖️'
                })
        
        return warnings
    
    def should_recommend(self, prediction: Dict, strict_mode: bool = False) -> tuple[bool, str]:
        """
        Determine if prediction meets quality standards.
        
        Args:
            prediction: Prediction dictionary
            strict_mode: Use stricter criteria (recommended)
        
        Returns:
            (should_recommend, reason)
        """
        confidence = prediction.get('confidence', 0)
        ev = prediction.get('expected_value', 0) or 0
        predicted_outcome = prediction.get('predicted_outcome', '').lower()
        predicted_odds = prediction.get('odds_data', {}).get(predicted_outcome, 0)
        
        # Strict mode (recommended for better accuracy)
        if strict_mode:
            # Criterion 1: Higher confidence threshold
            if confidence < 0.60:
                return False, f"Confidence too low ({confidence*100:.1f}% < 60%)"
            
            # Criterion 2: Meaningful EV
            if ev < 0.15:
                return False, f"Expected value too low ({ev*100:.1f}% < 15%)"
            
            # Criterion 3: Avoid extreme odds
            if predicted_odds > 3.5:
                return False, f"Odds too high ({predicted_odds:.2f}) - high variance"
            
            # Criterion 4: Avoid very low odds (overpriced favorites)
            if predicted_odds < 1.4:
                return False, f"Odds too low ({predicted_odds:.2f}) - minimal value"
            
            # Criterion 5: Be extra careful with draws
            if predicted_outcome == 'draw' and confidence < 0.65:
                return False, "Draw prediction requires 65%+ confidence"
            
            # Criterion 6: Require clear probability dominance
            probs = prediction.get('probabilities', {})
            sorted_probs = sorted([probs.get('home', 0), probs.get('draw', 0), probs.get('away', 0)], reverse=True)
            if len(sorted_probs) >= 2:
                gap = sorted_probs[0] - sorted_probs[1]
                if gap < 0.15:
                    return False, f"Probabilities too close ({gap*100:.1f}% gap) - no clear winner"
            
            return True, "Meets strict quality criteria"
        
        # Normal mode (current)
        else:
            if confidence >= 0.55 and ev > 0:
                return True, "Meets standard criteria"
            return False, "Below minimum standards"
    
    def add_contextual_info(self, prediction: Dict) -> Dict:
        """
        Add contextual information to help users make better decisions.
        """
        # Add quality score
        prediction['quality_score'] = self.calculate_quality_score(prediction)
        
        # Add risk warnings
        prediction['risk_warnings'] = self.get_risk_warnings(prediction)
        
        # Add recommendation strength
        quality_score = prediction['quality_score']
        if quality_score >= 75:
            prediction['recommendation_strength'] = 'Strong'
            prediction['recommendation_color'] = 'green'
        elif quality_score >= 60:
            prediction['recommendation_strength'] = 'Moderate'
            prediction['recommendation_color'] = 'yellow'
        else:
            prediction['recommendation_strength'] = 'Weak'
            prediction['recommendation_color'] = 'orange'
        
        # Add betting advice
        confidence = prediction.get('confidence', 0)
        quality_score = prediction['quality_score']
        
        if quality_score >= 75 and confidence >= 0.65:
            advice = "✅ High quality pick - standard stake recommended"
        elif quality_score >= 60:
            advice = "⚠️ Moderate quality - consider reduced stake"
        elif len(prediction['risk_warnings']) > 2:
            advice = "🚫 Multiple risk factors - skip or minimal stake"
        else:
            advice = "💡 Lower quality - advanced bettors only"
        
        prediction['betting_advice'] = advice
        
        return prediction
    
    def filter_recommendations(self, predictions: List[Dict], max_count: int = 10, strict: bool = True) -> List[Dict]:
        """
        Filter and rank predictions to show only highest quality.
        
        Args:
            predictions: List of prediction dictionaries
            max_count: Maximum number to return
            strict: Use strict filtering criteria
        
        Returns:
            Filtered and ranked predictions
        """
        # Filter by quality
        quality_predictions = []
        
        for pred in predictions:
            should_rec, reason = self.should_recommend(pred, strict_mode=strict)
            if should_rec:
                # Enhance with contextual info
                enhanced = self.add_contextual_info(pred)
                quality_predictions.append(enhanced)
        
        # Sort by quality score
        quality_predictions.sort(key=lambda x: x['quality_score'], reverse=True)
        
        # Return top N
        return quality_predictions[:max_count]

