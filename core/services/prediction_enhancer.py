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
    
    Data-driven thresholds (updated Feb 2026 from 46 recommended predictions):
    - Under 2.5 accuracy: 41.7% vs Over 2.5: 77.4%  → penalize Under 2.5
    - Probability gap ≥25%: 83.3% accuracy          → boost high-gap predictions
    - Admiral Bundesliga/Liga Portugal/Super Lig: 0% → league blacklist
    - Incorrect preds avg odds 3.20 vs correct 2.19  → tighter odds cap
    """
    
    # Leagues with critically poor accuracy in recommended predictions
    LEAGUE_BLACKLIST = [
        'Admiral Bundesliga',   # 0/3 = 0.0% accuracy, -$30 P/L
        'Liga Portugal',        # 0/1 = 0.0% accuracy
        'Super Lig',            # 0/0 recommended (14.3% overall)
    ]
    
    # Leagues to watch — not blocked but require extra confidence
    LEAGUE_WATCHLIST = [
        'Eredivisie',           # 2/4 = 50.0% accuracy
        'Pro League',           # 0/1 = 0.0% accuracy
    ]
    
    def __init__(self):
        self.confidence_floor = 0.60  # Minimum for Safe Bets
        self.ev_floor = 0.15  # Minimum EV for recommendations
        self.max_odds = 2.50  # Lowered from 3.0 — accuracy collapses above 2.50
    
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
        
        # Factor 4: Probability dominance (0-15 points)
        # Analysis: gap ≥25% → 83.3% accuracy (10/12)
        probs = prediction.get('probabilities', {})
        prob_home = probs.get('home', 0)
        prob_draw = probs.get('draw', 0)
        prob_away = probs.get('away', 0)
        
        sorted_probs = sorted([prob_home, prob_draw, prob_away], reverse=True)
        if len(sorted_probs) >= 2:
            gap = sorted_probs[0] - sorted_probs[1]
            if gap >= 0.40:  # 40%+ gap: 80% accuracy
                score += 15
            elif gap >= 0.25:  # 25%+ gap: 83.3% accuracy
                score += 12
            elif gap >= 0.20:  # 20% gap
                score += 5
        
        # Factor 5: Variance/consensus (0-10 points)
        variance = prediction.get('variance', 0)
        if variance and variance < 0.1:
            score += 10  # Low variance = models agree
        elif variance and variance < 0.2:
            score += 5
        
        # Factor 6: Outcome type penalty (DATA-DRIVEN)
        # Under 2.5: 41.7% accuracy vs Over 2.5: 77.4%
        outcome = prediction.get('predicted_outcome', '').lower()
        if 'under' in outcome:
            score -= 10  # Penalty for historically weak outcome type
        elif 'over' in outcome:
            score += 5   # Bonus for historically strong outcome type
        
        # Factor 7: League penalty (DATA-DRIVEN)
        league = prediction.get('league_name', '') or prediction.get('league', '')
        if league in self.LEAGUE_BLACKLIST:
            score -= 15  # Heavy penalty for 0% accuracy leagues
        elif league in self.LEAGUE_WATCHLIST:
            score -= 5   # Moderate penalty for underperforming leagues
        
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
        
        # Warning 7: Under 2.5 prediction (DATA-DRIVEN: 41.7% accuracy)
        if 'under' in predicted_outcome:
            warnings.append({
                'type': 'outcome_history',
                'level': 'medium',
                'message': 'Under 2.5 predictions historically less accurate (41.7%) - consider smaller stake',
                'icon': '📉'
            })
        
        # Warning 8: Blacklisted/watchlisted league (DATA-DRIVEN)
        league = prediction.get('league_name', '') or prediction.get('league', '')
        if league in self.LEAGUE_BLACKLIST:
            warnings.append({
                'type': 'league_history',
                'level': 'high',
                'message': f'{league}: historically poor accuracy - higher risk',
                'icon': '🚩'
            })
        elif league in self.LEAGUE_WATCHLIST:
            warnings.append({
                'type': 'league_history',
                'level': 'medium',
                'message': f'{league}: below-average accuracy - monitor',
                'icon': '👀'
            })
        
        return warnings
    
    def should_recommend(self, prediction: Dict, strict_mode: bool = False) -> tuple[bool, str]:
        """
        Determine if prediction meets quality standards.
        Now supports 'Two-Track' System:
        1. Safe Bets: High confidence (>60%), decent odds
        2. Value Bets: Moderate confidence (>35%), High EV (>10%)
        
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
        league = prediction.get('league_name', '') or prediction.get('league', '')
        
        # Strict mode (recommended for better accuracy)
        if strict_mode:
            # Absolute floor for any prediction
            if confidence < 0.35:
                 return False, f"Confidence too low ({confidence*100:.1f}% < 35%)"
            
            # DATA-DRIVEN: League blacklist (0% accuracy in recommendations)
            if league in self.LEAGUE_BLACKLIST:
                # Only allow if confidence is very high (≥70%)
                if confidence < 0.70:
                    return False, f"{league}: historically poor accuracy — requires ≥70% confidence"
            
            # DATA-DRIVEN: Under 2.5 requires higher confidence (41.7% accuracy)
            if 'under' in predicted_outcome:
                if confidence < 0.65:
                    return False, f"Under 2.5 requires ≥65% confidence (has {confidence*100:.1f}%)"
            
            # DATA-DRIVEN: Reject odds above 2.50 (accuracy collapses)
            if predicted_odds > self.max_odds:
                return False, f"Odds too high ({predicted_odds:.2f} > {self.max_odds:.2f})"
            
            # Track 1: Safe Bets (Standard)
            if confidence >= 0.60:
                # Still check for garbage odds
                if predicted_odds < 1.3:
                    return False, "Odds too low (< 1.30) - no value"
                return True, "Meets Safe Bet criteria"

            # Track 2: Value Bets (High EV, Moderate Confidence)
            # This is where Draws and Underdogs live
            if ev >= 0.10: # Requires 10% edge
                if predicted_odds > 4.5:
                     return False, "Odds too extreme (> 4.50) - lottery ticket"
                return True, "Meets Value Bet criteria"
            
            # If neither track matched
            return False, "Does not meet Safe (>60%) or Value (>10% EV) criteria"
        
        # Normal mode (legacy fallback)
        else:
            if confidence >= 0.50 and ev > 0:
                return True, "Meets standard criteria"
            return False, "Below minimum standards"
    
    def add_contextual_info(self, prediction: Dict) -> Dict:
        """
        Add contextual information to help users make better decisions.
        Tags predictions as 'Safe' or 'Value'.
        """
        # Add quality score
        prediction['quality_score'] = self.calculate_quality_score(prediction)
        
        # Add risk warnings
        prediction['risk_warnings'] = self.get_risk_warnings(prediction)
        
        # Classification: Safe vs Value
        confidence = prediction.get('confidence', 0)
        ev = prediction.get('expected_value', 0) or 0
        
        if confidence >= 0.60:
            prediction['bet_type'] = 'safe'
            prediction['bet_label'] = '🛡️ Safe Pick'
            prediction['recommendation_color'] = 'green'
        elif ev >= 0.10:
            prediction['bet_type'] = 'value'
            prediction['bet_label'] = '💎 Value Bet'
            prediction['recommendation_color'] = 'blue'
        else:
            prediction['bet_type'] = 'speculative'
            prediction['bet_label'] = '🎲 Speculative'
            prediction['recommendation_color'] = 'orange'

        # Add betting advice based on type
        if prediction['bet_type'] == 'safe':
            advice = "✅ High probability - standard stake recommended"
        elif prediction['bet_type'] == 'value':
            advice = "💎 High value opportunity - smaller stake recommended due to higher risk"
        else:
            advice = "⚠️ Speculative - minimal stake only"
        
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

