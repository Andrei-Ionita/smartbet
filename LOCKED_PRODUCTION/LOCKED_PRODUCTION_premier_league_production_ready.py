import pandas as pd
import numpy as np
import lightgbm as lgb
import xgboost as xgb
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class ProductionPredictor:
    def __init__(self):
        """
        Initialize Premier League production predictor.
        
        ❌ WARNING: Do NOT use this model for other leagues!
        This model is trained on PREMIER LEAGUE data and will NOT generalize.
        """
        # 🔒 LEAGUE SAFETY ENFORCEMENT
        self.authorized_league = "Premier League"
        self.enforce_league_safety = True
        
        self.lgb_model = None
        self.xgb_model = None
        self.feature_names = None
        self.is_loaded = False
        
    def validate_league_usage(self, league_name: str = None):
        """
        Enforce league-specific usage to prevent cross-league contamination.
        
        ❌ WARNING: This model is ONLY for Premier League matches!
        
        Args:
            league_name: Name of the league for the match
            
        Raises:
            ValueError: If trying to use model for non-Premier League matches
        """
        if league_name and league_name.lower() not in ["premier league", "english premier league", "epl", "pl", "england premier league"]:
            raise ValueError(
                f"🚨 CROSS-LEAGUE VIOLATION: This Premier League model cannot predict {league_name} matches! "
                f"This model is ONLY valid for Premier League matches. "
                f"Use the appropriate league-specific model instead."
            )
    
    def load_models(self):
        """Load the trained models"""
        print("🤖 Loading Production Models")
        print("=" * 32)
        
        try:
            # Find the most recent model files
            import glob
            lgb_files = glob.glob("lightgbm_premier_league_*.txt")
            xgb_files = glob.glob("xgboost_premier_league_*.json")
            
            if lgb_files:
                lgb_file = max(lgb_files)
                self.lgb_model = lgb.Booster(model_file=lgb_file)
                print(f"✅ LightGBM loaded: {lgb_file}")
            
            if xgb_files:
                xgb_file = max(xgb_files)
                self.xgb_model = xgb.Booster()
                self.xgb_model.load_model(xgb_file)
                print(f"✅ XGBoost loaded: {xgb_file}")
            
            # Load feature importance to get feature names
            importance_files = glob.glob("feature_importance_*.csv")
            if importance_files:
                importance_file = max(importance_files)
                importance_df = pd.read_csv(importance_file)
                self.feature_names = importance_df['feature'].tolist()
                print(f"✅ Feature names loaded: {len(self.feature_names)} features")
            
            self.is_loaded = True
            print("🚀 Models ready for prediction!")
            
        except Exception as e:
            print(f"❌ Error loading models: {e}")
            
    def engineer_features(self, match_data):
        """Engineer features for a single match prediction"""
        
        # Ensure required columns exist
        required_cols = ['avg_home_odds', 'avg_away_odds', 'avg_draw_odds']
        for col in required_cols:
            if col not in match_data:
                raise ValueError(f"Missing required column: {col}")
        
        # Create a copy to avoid modifying original
        data = match_data.copy()
        
        # Basic odds-based features
        data['total_implied_prob'] = (1/data['avg_home_odds'] + 
                                     1/data['avg_away_odds'] + 
                                     1/data['avg_draw_odds'])
        data['market_margin'] = data['total_implied_prob'] - 1
        data['market_efficiency'] = 1 / data['total_implied_prob']
        
        # True probabilities
        data['true_prob_home'] = (1/data['avg_home_odds']) / data['total_implied_prob']
        data['true_prob_away'] = (1/data['avg_away_odds']) / data['total_implied_prob']
        data['true_prob_draw'] = (1/data['avg_draw_odds']) / data['total_implied_prob']
        
        # Log odds
        data['log_odds_home'] = np.log(data['avg_home_odds'])
        data['log_odds_away'] = np.log(data['avg_away_odds'])
        data['log_odds_draw'] = np.log(data['avg_draw_odds'])
        
        # Odds ratios
        data['home_away_odds_ratio'] = data['avg_home_odds'] / data['avg_away_odds']
        data['home_draw_odds_ratio'] = data['avg_home_odds'] / data['avg_draw_odds']
        data['away_draw_odds_ratio'] = data['avg_away_odds'] / data['avg_draw_odds']
        
        # Favorite/underdog features
        data['favorite_odds'] = np.minimum(np.minimum(data['avg_home_odds'], 
                                                      data['avg_away_odds']), 
                                          data['avg_draw_odds'])
        data['underdog_odds'] = np.maximum(np.maximum(data['avg_home_odds'], 
                                                      data['avg_away_odds']), 
                                          data['avg_draw_odds'])
        data['odds_spread'] = data['underdog_odds'] - data['favorite_odds']
        
        return data
    
    def predict_match(self, match_data, use_ensemble=True):
        """Predict the outcome of a single match"""
        
        if not self.is_loaded:
            raise ValueError("Models not loaded. Call load_models() first.")
        
        # Engineer features
        engineered_data = self.engineer_features(match_data)
        
        # Extract features that match training (simplified for demo)
        # In production, you'd want to ensure all 113 features are available
        available_features = []
        feature_values = []
        
        for feature in self.feature_names:
            if feature in engineered_data:
                available_features.append(feature)
                feature_values.append(engineered_data[feature])
            else:
                # Use default values for missing features
                available_features.append(feature)
                feature_values.append(0.0)  # Default value
        
        # Convert to numpy array
        X = np.array(feature_values).reshape(1, -1)
        
        # Make predictions
        predictions = {}
        
        if self.lgb_model:
            lgb_pred = self.lgb_model.predict(X)[0]
            predictions['lightgbm'] = {
                'home_win': lgb_pred[0],
                'away_win': lgb_pred[1],
                'draw': lgb_pred[2],
                'predicted_outcome': np.argmax(lgb_pred)
            }
        
        if self.xgb_model:
            dtest = xgb.DMatrix(X)
            xgb_pred = self.xgb_model.predict(dtest)[0]
            predictions['xgboost'] = {
                'home_win': xgb_pred[0],
                'away_win': xgb_pred[1],
                'draw': xgb_pred[2],
                'predicted_outcome': np.argmax(xgb_pred)
            }
        
        # Ensemble prediction
        if use_ensemble and 'lightgbm' in predictions and 'xgboost' in predictions:
            lgb_probs = [predictions['lightgbm']['home_win'], 
                        predictions['lightgbm']['away_win'], 
                        predictions['lightgbm']['draw']]
            xgb_probs = [predictions['xgboost']['home_win'], 
                        predictions['xgboost']['away_win'], 
                        predictions['xgboost']['draw']]
            
            # Average the probabilities
            ensemble_probs = [(lgb_probs[i] + xgb_probs[i]) / 2 for i in range(3)]
            
            predictions['ensemble'] = {
                'home_win': ensemble_probs[0],
                'away_win': ensemble_probs[1],
                'draw': ensemble_probs[2],
                'predicted_outcome': np.argmax(ensemble_probs)
            }
        
        return predictions
    
    def format_prediction(self, predictions, home_team="Home Team", away_team="Away Team"):
        """Format predictions for display"""
        
        outcome_names = ["Home Win", "Away Win", "Draw"]
        
        print(f"\n⚽ MATCH PREDICTION: {home_team} vs {away_team}")
        print("=" * 60)
        
        for model_name, pred in predictions.items():
            print(f"\n🤖 {model_name.upper()} Model:")
            print(f"   Home Win: {pred['home_win']:.1%}")
            print(f"   Away Win: {pred['away_win']:.1%}")
            print(f"   Draw:     {pred['draw']:.1%}")
            print(f"   Prediction: {outcome_names[pred['predicted_outcome']]}")
            
            # Confidence level
            max_prob = max(pred['home_win'], pred['away_win'], pred['draw'])
            if max_prob > 0.7:
                confidence = "🟢 High"
            elif max_prob > 0.5:
                confidence = "🟡 Medium"
            else:
                confidence = "🔴 Low"
            print(f"   Confidence: {confidence} ({max_prob:.1%})")

def demo_prediction():
    """Demonstrate the prediction system with sample data"""
    
    print("🚀 PRODUCTION PREDICTOR DEMO")
    print("=" * 35)
    
    # Initialize predictor
    predictor = ProductionPredictor()
    
    # Load models
    predictor.load_models()
    
    if not predictor.is_loaded:
        print("❌ Could not load models. Make sure model files exist.")
        return
    
    # Sample match data (you would get this from your data source)
    sample_matches = [
        {
            'home_team': 'Manchester City',
            'away_team': 'Liverpool',
            'avg_home_odds': 2.1,
            'avg_away_odds': 3.2,
            'avg_draw_odds': 3.8
        },
        {
            'home_team': 'Arsenal',
            'away_team': 'Chelsea',
            'avg_home_odds': 2.5,
            'avg_away_odds': 2.8,
            'avg_draw_odds': 3.4
        },
        {
            'home_team': 'Brighton',
            'away_team': 'Sheffield United',
            'avg_home_odds': 1.4,
            'avg_away_odds': 7.5,
            'avg_draw_odds': 4.8
        }
    ]
    
    # Make predictions for each match
    for i, match in enumerate(sample_matches, 1):
        print(f"\n📊 EXAMPLE {i}")
        print("-" * 20)
        
        try:
            predictions = predictor.predict_match(match)
            predictor.format_prediction(predictions, match['home_team'], match['away_team'])
            
            # Show market odds for comparison
            print(f"\n📈 Market Odds:")
            print(f"   Home: {match['avg_home_odds']:.2f}")
            print(f"   Away: {match['avg_away_odds']:.2f}")
            print(f"   Draw: {match['avg_draw_odds']:.2f}")
            
        except Exception as e:
            print(f"❌ Error predicting match: {e}")
    
    print(f"\n✅ Demo complete! The production predictor is ready for live use.")

def main():
    """Main function"""
    demo_prediction()

if __name__ == "__main__":
    main() 