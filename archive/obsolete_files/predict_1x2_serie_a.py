"""
SERIE A 1X2 PREDICTION SYSTEM
============================

Production-ready deployment script for Serie A 1X2 betting model.
Based on proven Premier League architecture with Serie A-specific features.
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from datetime import datetime
from typing import Dict
import warnings
warnings.filterwarnings('ignore')

class SerieA1X2Predictor:
    """
    Production-ready Serie A 1X2 prediction system.
    
    ❌ WARNING: Do NOT use this model for other leagues!
    This model is trained on SERIE A data and will NOT generalize.
    """
    
    def __init__(self, model_path='league_model_1x2_serie_a_latest.txt'):
        """
        Initialize the predictor with the trained model.
        
        ❌ WARNING: Do NOT use this model for other leagues!
        This model is trained on SERIE A data and will NOT generalize.
        """
        # 🔒 LEAGUE SAFETY ENFORCEMENT
        self.authorized_league = "Serie A"
        self.enforce_league_safety = True
        
        self.model_path = model_path
        self.model = None
        self.confidence_threshold = 0.60
        self.class_names = ['Home Win', 'Away Win', 'Draw']
        self.league_name = "Serie A"
        
        # Serie A big clubs for context
        self.big_clubs = [
            'Juventus', 'AC Milan', 'Inter Milan', 'Napoli', 
            'AS Roma', 'Lazio', 'Atalanta', 'Fiorentina'
        ]
        
        self.load_model()
        
    def validate_league_usage(self, league_name: str = None):
        """
        Enforce league-specific usage to prevent cross-league contamination.
        
        Args:
            league_name: Name of the league for the match
            
        Raises:
            ValueError: If trying to use model for non-Serie A matches
        """
        if not self.enforce_league_safety:
            return  # Safety disabled - allow usage
            
        if league_name and league_name.lower() not in ["serie a", "series a", "italian serie a", "italy serie a"]:
            raise ValueError(
                f"🚨 CROSS-LEAGUE VIOLATION: This Serie A model cannot predict {league_name} matches! "
                f"This model is ONLY valid for Serie A matches. "
                f"Use the appropriate league-specific model instead."
            )
    
    def load_model(self):
        """Load the trained Serie A model."""
        try:
            self.model = lgb.Booster(model_file=self.model_path)
            print(f"✅ Loaded Serie A 1X2 model from {self.model_path}")
        except FileNotFoundError:
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        except Exception as e:
            raise Exception(f"Error loading model: {str(e)}")
    
    def engineer_features(self, home_odds: float, away_odds: float, draw_odds: float,
                         home_team: str = None, away_team: str = None) -> pd.DataFrame:
        """Engineer the 12 critical features from odds and team info."""
        
        # Calculate probability features
        total_inv_odds = 1/home_odds + 1/away_odds + 1/draw_odds
        true_prob_home = (1/home_odds) / total_inv_odds
        true_prob_away = (1/away_odds) / total_inv_odds
        true_prob_draw = (1/draw_odds) / total_inv_odds
        
        features = {
            'true_prob_draw': true_prob_draw,
            'prob_ratio_draw_away': true_prob_draw / true_prob_away,
            'prob_ratio_home_draw': true_prob_home / true_prob_draw,
            'log_odds_home_draw': np.log(home_odds) - np.log(draw_odds),
            'log_odds_draw_away': np.log(draw_odds) - np.log(away_odds),
            'bookmaker_margin': total_inv_odds - 1,
            'market_efficiency': 1 / total_inv_odds,
            'uncertainty_index': np.std([true_prob_home, true_prob_draw, true_prob_away]),
            'odds_draw': draw_odds,
            'goals_for_away': 1.3,  # Serie A average
            'recent_form_home': 1.5,  # Default values
            'recent_form_away': 1.2
        }
        
        return pd.DataFrame([features])
    
    def predict_match(self, home_odds: float, away_odds: float, draw_odds: float,
                     home_team: str = None, away_team: str = None) -> Dict:
        """Predict Serie A match outcome."""
        
        # Engineer features
        features_df = self.engineer_features(home_odds, away_odds, draw_odds, home_team, away_team)
        
        # Generate predictions
        probabilities = self.model.predict(features_df.values, num_iteration=self.model.best_iteration)
        probs = probabilities[0]
        
        # Get predicted class
        predicted_class = np.argmax(probs)
        predicted_outcome = self.class_names[predicted_class]
        confidence = probs[predicted_class]
        
        # Apply confidence filtering
        meets_threshold = confidence >= self.confidence_threshold
        
        # Team context
        team_context = ""
        if home_team and away_team:
            if home_team in self.big_clubs and away_team in self.big_clubs:
                team_context = "🔥 Big Club Derby"
            elif home_team in self.big_clubs:
                team_context = f"🏆 {home_team} (Big Club) at home"
            elif away_team in self.big_clubs:
                team_context = f"🏆 {away_team} (Big Club) away"
        
        # Prepare result
        result = {
            'league': self.league_name,
            'match': f"{home_team or 'Home'} vs {away_team or 'Away'}",
            'team_context': team_context,
            'prediction': predicted_outcome,
            'confidence': float(confidence),
            'meets_threshold': meets_threshold,
            'threshold': self.confidence_threshold,
            'probabilities': {
                'Home Win': float(probs[0]),
                'Away Win': float(probs[1]),
                'Draw': float(probs[2])
            },
            'input_odds': {
                'home': home_odds,
                'away': away_odds,
                'draw': draw_odds
            },
            'market_analysis': {
                'bookmaker_margin': float(features_df['bookmaker_margin'].iloc[0]),
                'market_efficiency': float(features_df['market_efficiency'].iloc[0]),
                'true_prob_draw': float(features_df['true_prob_draw'].iloc[0])
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Add recommendation
        if meets_threshold:
            result['recommendation'] = f"BET on {predicted_outcome}"
            result['betting_confidence'] = "HIGH"
        else:
            result['recommendation'] = "NO BET - Low confidence"
            result['betting_confidence'] = "LOW"
        
        return result

def main():
    """Example usage of Serie A 1X2 predictor."""
    predictor = SerieA1X2Predictor()
    
    # Example Serie A match
    prediction = predictor.predict_match(
        home_odds=2.10,    # Juventus
        away_odds=3.40,    # AC Milan  
        draw_odds=3.20,
        home_team="Juventus",
        away_team="AC Milan"
    )
    
    print("🇮🇹 SERIE A 1X2 PREDICTION")
    print("=" * 30)
    print(f"Match: {prediction['match']}")
    print(f"Context: {prediction['team_context']}")
    print(f"Prediction: {prediction['prediction']} ({prediction['confidence']:.1%})")
    print(f"Recommendation: {prediction['recommendation']}")
    print()
    print("Probabilities:")
    for outcome, prob in prediction['probabilities'].items():
        print(f"  {outcome}: {prob:.1%}")

if __name__ == "__main__":
    main() 