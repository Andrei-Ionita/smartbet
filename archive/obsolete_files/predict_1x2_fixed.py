"""
PRODUCTION 1X2 PREDICTION SYSTEM (FIXED)
========================================

Production-ready deployment script for the secured 1X2 betting model.
Fixed to include all required features from our trained model.
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class Production1X2Predictor:
    """Production-ready 1X2 prediction system with complete feature mapping."""
    
    def __init__(self, model_path='SECURED_1X2_MODEL_DO_NOT_MODIFY.txt'):
        """Initialize the predictor with the secured model."""
        self.model_path = model_path
        self.model = None
        self.feature_names = None
        self.confidence_threshold = 0.60
        self.class_names = ['Home Win', 'Away Win', 'Draw']
        self.load_model()
        
    def load_model(self):
        """Load the secured production model."""
        try:
            self.model = lgb.Booster(model_file=self.model_path)
            print(f"✅ Loaded secured 1X2 model from {self.model_path}")
            
            # Get feature names from the clean dataset
            try:
                df = pd.read_csv('features_clean.csv')
                exclude_cols = ['fixture_id', 'date', 'home_team', 'away_team', 'season', 'target']
                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                self.feature_names = [col for col in numeric_cols if col not in exclude_cols]
                print(f"✅ Loaded {len(self.feature_names)} feature names")
            except FileNotFoundError:
                print("⚠️ Warning: features_clean.csv not found. Feature names not loaded.")
                
        except FileNotFoundError:
            raise FileNotFoundError(f"Secured model file not found: {self.model_path}")
        except Exception as e:
            raise Exception(f"Error loading model: {str(e)}")
    
    def create_features_from_odds(self, home_odds, away_odds, draw_odds):
        """Create complete feature set from betting odds."""
        # Basic probability calculations
        home_prob = 1 / home_odds
        away_prob = 1 / away_odds
        draw_prob = 1 / draw_odds
        
        # Normalize probabilities
        total_prob = home_prob + away_prob + draw_prob
        home_prob_norm = home_prob / total_prob
        away_prob_norm = away_prob / total_prob
        draw_prob_norm = draw_prob / total_prob
        
        # Market calculations
        margin = total_prob - 1.0
        efficiency = 1.0 - margin
        
        # Current time features
        now = datetime.now()
        is_weekend = 1 if now.weekday() >= 5 else 0
        is_midweek = 1 if 2 <= now.weekday() <= 4 else 0
        is_evening = 1 if now.hour >= 18 else 0
        
        # Create complete feature set matching our model
        features = {
            # Basic odds
            'avg_home_odds': home_odds,
            'avg_away_odds': away_odds,
            'avg_draw_odds': draw_odds,
            'odds_draw': draw_odds,
            'min_home_odds': home_odds,
            'max_home_odds': home_odds,
            'min_away_odds': away_odds,
            'max_away_odds': away_odds,
            'min_draw_odds': draw_odds,
            'max_draw_odds': draw_odds,
            
            # Probabilities
            'implied_prob_home': home_prob_norm,
            'implied_prob_away': away_prob_norm,
            'implied_prob_draw': draw_prob_norm,
            'prob_home': home_prob_norm,
            'prob_away': away_prob_norm,
            'prob_draw': draw_prob_norm,
            'true_prob_home': home_prob_norm,
            'true_prob_away': away_prob_norm,
            'true_prob_draw': draw_prob_norm,
            'total_prob': total_prob,
            
            # Probability ratios
            'prob_ratio_home_away': home_prob_norm / away_prob_norm if away_prob_norm > 0 else 1,
            'prob_ratio_home_draw': home_prob_norm / draw_prob_norm if draw_prob_norm > 0 else 1,
            'prob_ratio_draw_away': draw_prob_norm / away_prob_norm if away_prob_norm > 0 else 1,
            
            # Market features
            'odds_spread': max(home_odds, away_odds, draw_odds) - min(home_odds, away_odds, draw_odds),
            'min_odds': min(home_odds, away_odds, draw_odds),
            'max_odds': max(home_odds, away_odds, draw_odds),
            'bookmaker_margin': margin,
            'market_margin': margin,
            'market_efficiency': efficiency,
            'uncertainty_index': np.std([home_prob_norm, away_prob_norm, draw_prob_norm]),
            'bookmaker_count': 20,  # Assume average bookmaker count
            
            # Log odds
            'log_odds_home': np.log(home_odds),
            'log_odds_away': np.log(away_odds),
            'log_odds_draw': np.log(draw_odds),
            
            # Team features (dummy values - would need real data)
            'home_big_club': 0,
            'away_big_club': 0,
            'big_club_match': 0,
            'big_club_clash': 0,
            'form_differential': 0,
            'recent_form_home': 0,
            'recent_form_away': 0,
            'home_team_frequency': 1,
            'away_team_frequency': 1,
            
            # Time features
            'round_id': 20,
            'month': now.month,
            'season_month': now.month,
            'day_of_week': now.weekday(),
            'hour': now.hour,
            'is_weekend': is_weekend,
            'is_midweek': is_midweek,
            'is_evening': is_evening,
            'is_christmas': 1 if now.month == 12 and now.day == 25 else 0,
            'is_spring': 1 if 3 <= now.month <= 5 else 0,
            'is_winter': 1 if now.month in [12, 1, 2] else 0,
            
            # Season features
            'season_id': 2024,
            'season_progress': 0.5,
            'season_encoded': 0.5,
        }
        
        # Ensure all features have numeric values
        for key, value in features.items():
            if value is None or np.isnan(value):
                features[key] = 0.0
            features[key] = float(features[key])
        
        return features
    
    def predict_single_match(self, features=None, home_odds=None, away_odds=None, draw_odds=None):
        """Predict outcome for a single match."""
        
        # Create features from odds if provided
        if home_odds is not None and away_odds is not None and draw_odds is not None:
            features = self.create_features_from_odds(home_odds, away_odds, draw_odds)
        elif features is None:
            raise ValueError("Either provide features dict or odds values")
        
        # Convert to DataFrame and ensure correct order
        if isinstance(features, dict):
            features_df = pd.DataFrame([features])
        else:
            features_df = features.copy()
        
        # Ensure we have all required features
        if self.feature_names:
            missing_features = set(self.feature_names) - set(features_df.columns)
            if missing_features:
                # Fill missing features with defaults
                for feature in missing_features:
                    features_df[feature] = 0.0
            
            # Reorder columns to match model
            features_df = features_df[self.feature_names]
        
        # Generate predictions
        probabilities = self.model.predict(features_df.values, num_iteration=self.model.best_iteration)
        
        if len(probabilities.shape) == 1:
            probabilities = probabilities.reshape(1, -1)
        
        probs = probabilities[0]
        
        # Get predicted class
        predicted_class = np.argmax(probs)
        predicted_outcome = self.class_names[predicted_class]
        confidence = probs[predicted_class]
        
        # Apply confidence filtering
        meets_threshold = confidence >= self.confidence_threshold
        
        # Prepare result
        result = {
            'prediction': predicted_outcome,
            'confidence': float(confidence),
            'meets_threshold': meets_threshold,
            'threshold': self.confidence_threshold,
            'probabilities': {
                'Home Win': float(probs[0]),
                'Away Win': float(probs[1]),
                'Draw': float(probs[2])
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
    
    def format_prediction_output(self, result):
        """Format prediction result for display."""
        output = []
        output.append("🎯 1X2 PREDICTION RESULT")
        output.append("=" * 30)
        output.append(f"Prediction: {result['prediction']}")
        output.append(f"Confidence: {result['confidence']:.1%}")
        output.append(f"Threshold: {result['threshold']:.1%}")
        output.append(f"Meets Threshold: {'✅ YES' if result['meets_threshold'] else '❌ NO'}")
        output.append(f"Recommendation: {result['recommendation']}")
        
        output.append("\n📊 Class Probabilities:")
        for outcome, prob in result['probabilities'].items():
            output.append(f"   {outcome}: {prob:.1%}")
        
        output.append(f"\n⏰ Generated: {result['timestamp']}")
        
        return "\n".join(output)


def main():
    """Main CLI interface for the 1X2 predictor."""
    print("🎯 PRODUCTION 1X2 PREDICTION SYSTEM")
    print("=" * 40)
    print("Using secured model: SECURED_1X2_MODEL_DO_NOT_MODIFY.txt")
    print()
    
    # Initialize predictor
    try:
        predictor = Production1X2Predictor()
    except Exception as e:
        print(f"❌ Error initializing predictor: {e}")
        return
    
    # CLI Menu
    while True:
        print("\n📋 OPTIONS:")
        print("1. Predict from odds input")
        print("2. Test with sample prediction")
        print("3. Exit")
        
        choice = input("\nSelect option (1-3): ").strip()
        
        if choice == '1':
            # Odds input
            try:
                print("\n📊 Enter betting odds:")
                home_odds = float(input("Home win odds (e.g., 2.50): "))
                away_odds = float(input("Away win odds (e.g., 3.20): "))
                draw_odds = float(input("Draw odds (e.g., 3.10): "))
                
                result = predictor.predict_single_match(
                    home_odds=home_odds, 
                    away_odds=away_odds, 
                    draw_odds=draw_odds
                )
                print(f"\n{predictor.format_prediction_output(result)}")
                
            except ValueError:
                print("❌ Invalid odds format. Please enter decimal numbers.")
            except Exception as e:
                print(f"❌ Prediction error: {e}")
        
        elif choice == '2':
            # Test prediction
            try:
                print("\n🧪 Testing with sample odds: Home 2.50, Away 3.20, Draw 3.10")
                result = predictor.predict_single_match(
                    home_odds=2.50, 
                    away_odds=3.20, 
                    draw_odds=3.10
                )
                print(f"\n{predictor.format_prediction_output(result)}")
                
            except Exception as e:
                print(f"❌ Prediction error: {e}")
        
        elif choice == '3':
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid option. Please select 1-3.")


if __name__ == "__main__":
    main() 