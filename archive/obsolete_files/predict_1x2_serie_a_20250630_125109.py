"""
SERIE A 1X2 PREDICTION SYSTEM
============================
Production-ready deployment script for Serie A 1X2 betting model.
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from datetime import datetime

class SerieA1X2Predictor:
    def __init__(self, model_path='league_model_1x2_serie_a_20250630_125109.txt'):
        self.model_path = model_path
        self.model = lgb.Booster(model_file=model_path)
        self.confidence_threshold = 0.60
        
    def predict_match(self, home_odds, away_odds, draw_odds, home_team=None, away_team=None):
        # Engineer features
        total_inv_odds = 1/home_odds + 1/away_odds + 1/draw_odds
        true_prob_draw = (1/draw_odds) / total_inv_odds
        true_prob_home = (1/home_odds) / total_inv_odds
        true_prob_away = (1/away_odds) / total_inv_odds
        
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
            'goals_for_away': 1.3,
            'recent_form_home': 1.5,
            'recent_form_away': 1.2
        }
        
        features_df = pd.DataFrame([features])
        probs = self.model.predict(features_df.values)[0]
        
        prediction = ['Home Win', 'Away Win', 'Draw'][np.argmax(probs)]
        confidence = max(probs)
        
        return {
            'prediction': prediction,
            'confidence': confidence,
            'probabilities': {'Home Win': probs[0], 'Away Win': probs[1], 'Draw': probs[2]},
            'recommendation': f"BET on {prediction}" if confidence >= self.confidence_threshold else "NO BET"
        }

# Example usage
if __name__ == "__main__":
    predictor = SerieA1X2Predictor()
    result = predictor.predict_match(2.10, 3.40, 3.20, "Juventus", "AC Milan")
    print(f"Prediction: {result['prediction']}")
    print(f"Confidence: {result['confidence']:.1%}")
    print(f"Recommendation: {result['recommendation']}")
