"""
PRODUCTION 1X2 PREDICTION SYSTEM
================================

Production-ready deployment script for the secured 1X2 betting model.
Uses the leak-free LightGBM model with confidence filtering.

Features:
- Load secured model (NEVER modify the model file)
- Apply 60% confidence threshold for predictions
- Clean CLI and programmatic interface
- Input validation and error handling
- Prediction explanations and confidence scores

Author: ML Engineering Team
Date: January 28, 2025
Model: SECURED_1X2_MODEL_DO_NOT_MODIFY.txt
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from datetime import datetime
import json
import warnings
warnings.filterwarnings('ignore')

class Production1X2Predictor:
    """
    Production-ready 1X2 prediction system.
    
    ❌ WARNING: Do NOT use this model for other leagues!
    This model is trained on PREMIER LEAGUE data and will NOT generalize.
    
    SECURITY NOTE: This class uses the SECURED model file that should NEVER be modified.
    """
    
    def __init__(self, model_path='SECURED_1X2_MODEL_DO_NOT_MODIFY.txt'):
        """Initialize the predictor with the secured model."""
        # 🔒 LEAGUE SAFETY ENFORCEMENT
        self.authorized_league = "Premier League"
        self.enforce_league_safety = True
        
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
    
    def validate_input_features(self, features):
        """Validate input features match model requirements."""
        if not isinstance(features, (dict, pd.DataFrame, np.ndarray)):
            raise ValueError("Features must be dict, DataFrame, or numpy array")
        
        if isinstance(features, dict):
            features_df = pd.DataFrame([features])
        elif isinstance(features, np.ndarray):
            if self.feature_names is None:
                raise ValueError("Feature names not available for numpy array input")
            features_df = pd.DataFrame(features.reshape(1, -1), columns=self.feature_names)
        else:
            features_df = features.copy()
        
        # Check for required features
        if self.feature_names:
            missing_features = set(self.feature_names) - set(features_df.columns)
            if missing_features:
                raise ValueError(f"Missing required features: {missing_features}")
            
            # Reorder columns to match model
            features_df = features_df[self.feature_names]
        
        return features_df
    
    def predict_single_match(self, features, return_probabilities=True):
        """
        Predict outcome for a single match.
        
        Args:
            features: Dict or DataFrame with match features
            return_probabilities: Whether to return class probabilities
            
        Returns:
            Dict with prediction results
        """
        # Validate and prepare features
        features_df = self.validate_input_features(features)
        
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
            'timestamp': datetime.now().isoformat()
        }
        
        if return_probabilities:
            result['probabilities'] = {
                'Home Win': float(probs[0]),
                'Away Win': float(probs[1]),
                'Draw': float(probs[2])
            }
        
        # Add recommendation
        if meets_threshold:
            result['recommendation'] = f"BET on {predicted_outcome}"
            result['betting_confidence'] = "HIGH"
        else:
            result['recommendation'] = "NO BET - Low confidence"
            result['betting_confidence'] = "LOW"
        
        return result
    
    def predict_multiple_matches(self, features_list):
        """
        Predict outcomes for multiple matches.
        
        Args:
            features_list: List of feature dicts or DataFrame
            
        Returns:
            List of prediction results
        """
        results = []
        
        for i, features in enumerate(features_list):
            try:
                result = self.predict_single_match(features)
                result['match_id'] = i
                results.append(result)
            except Exception as e:
                results.append({
                    'match_id': i,
                    'error': str(e),
                    'prediction': None,
                    'confidence': 0.0,
                    'meets_threshold': False
                })
        
        return results
    
    def create_sample_features(self):
        """Create sample features for testing."""
        # Load a sample from the clean dataset
        try:
            df = pd.read_csv('features_clean.csv')
            exclude_cols = ['fixture_id', 'date', 'home_team', 'away_team', 'season', 'target']
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            feature_cols = [col for col in numeric_cols if col not in exclude_cols]
            
            # Return first row as sample
            sample = df[feature_cols].iloc[0].to_dict()
            return sample
        except:
            # Return dummy features if dataset not available
            return {f'feature_{i}': np.random.normal(0, 1) for i in range(50)}
    
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
        
        if 'probabilities' in result:
            output.append("\n📊 Class Probabilities:")
            for outcome, prob in result['probabilities'].items():
                output.append(f"   {outcome}: {prob:.1%}")
        
        output.append(f"\n⏰ Generated: {result['timestamp']}")
        
        return "\n".join(output)

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


def create_odds_input_helper():
    """Helper function to create features from betting odds."""
    def odds_to_features(home_odds, away_odds, draw_odds):
        """
        Convert betting odds to model features.
        
        Args:
            home_odds: Decimal odds for home win
            away_odds: Decimal odds for away win  
            draw_odds: Decimal odds for draw
            
        Returns:
            Dict with calculated features
        """
        # Basic probability calculations
        home_prob = 1 / home_odds
        away_prob = 1 / away_odds
        draw_prob = 1 / draw_odds
        
        # Normalize probabilities
        total_prob = home_prob + away_prob + draw_prob
        home_prob_norm = home_prob / total_prob
        away_prob_norm = away_prob / total_prob
        draw_prob_norm = draw_prob / total_prob
        
        # Calculate derived features
        features = {
            'avg_home_odds': home_odds,
            'avg_away_odds': away_odds,
            'avg_draw_odds': draw_odds,
            'implied_prob_home': home_prob_norm,
            'implied_prob_away': away_prob_norm,
            'implied_prob_draw': draw_prob_norm,
            'prob_ratio_home_away': home_prob_norm / away_prob_norm if away_prob_norm > 0 else 1,
            'prob_ratio_home_draw': home_prob_norm / draw_prob_norm if draw_prob_norm > 0 else 1,
            'odds_spread': max(home_odds, away_odds, draw_odds) - min(home_odds, away_odds, draw_odds),
            'min_odds': min(home_odds, away_odds, draw_odds),
            'max_odds': max(home_odds, away_odds, draw_odds),
            'bookmaker_margin': total_prob - 1.0,
            'uncertainty_index': np.std([home_prob_norm, away_prob_norm, draw_prob_norm]),
            'log_odds_home': np.log(home_odds),
            'log_odds_away': np.log(away_odds),
            'log_odds_draw': np.log(draw_odds),
        }
        
        # Add dummy values for other required features (would need real data in production)
        # These are based on the actual features from our clean dataset
        dummy_features = {
            'home_big_club': 0,
            'away_big_club': 0,
            'form_differential': 0,
            'recent_form_home': 0,
            'recent_form_away': 0,
            'home_team_frequency': 1,
            'away_team_frequency': 1,
            'round_id': 20,
            'month': datetime.now().month,
            'day_of_week': datetime.now().weekday(),
            'season_progress': 0.5,
            'odds_draw': draw_odds,
            'total_prob': total_prob,
            'true_prob_draw': draw_prob_norm,
            'is_midweek': 0,
            'season_id': 2024,
            'is_weekend': 1,
            'market_margin': total_prob - 1.0,
            'is_christmas': 0,
            'max_home_odds': home_odds,
            'bookmaker_count': 20,
            'min_draw_odds': draw_odds,
            'big_club_clash': 0,
            'min_home_odds': home_odds,
            'is_spring': 0,
            'min_away_odds': away_odds,
            'season_month': datetime.now().month,
            'prob_draw': draw_prob_norm,
            'is_winter': 0,
            'max_away_odds': away_odds,
            'prob_home': home_prob_norm,
            'hour': 15,
            'true_prob_away': away_prob_norm,
            'prob_away': away_prob_norm,
            'is_evening': 0,
            'market_efficiency': 1.0 - (total_prob - 1.0),
            'true_prob_home': home_prob_norm,
            'max_draw_odds': draw_odds,
            'big_club_match': 0,
            'prob_ratio_draw_away': draw_prob_norm / away_prob_norm if away_prob_norm > 0 else 1,
            'season_encoded': 0.5
        }
        
        features.update(dummy_features)
        return features
    
    return odds_to_features


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
        print("2. Predict from sample features") 
        print("3. Test with multiple predictions")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            # Odds input
            try:
                print("\n📊 Enter betting odds:")
                home_odds = float(input("Home win odds (e.g., 2.50): "))
                away_odds = float(input("Away win odds (e.g., 3.20): "))
                draw_odds = float(input("Draw odds (e.g., 3.10): "))
                
                odds_converter = create_odds_input_helper()
                features = odds_converter(home_odds, away_odds, draw_odds)
                
                result = predictor.predict_single_match(features)
                print(f"\n{predictor.format_prediction_output(result)}")
                
            except ValueError:
                print("❌ Invalid odds format. Please enter decimal numbers.")
            except Exception as e:
                print(f"❌ Prediction error: {e}")
        
        elif choice == '2':
            # Sample features
            try:
                features = predictor.create_sample_features()
                result = predictor.predict_single_match(features)
                print(f"\n{predictor.format_prediction_output(result)}")
                
            except Exception as e:
                print(f"❌ Prediction error: {e}")
        
        elif choice == '3':
            # Multiple predictions test
            try:
                print("\n🔄 Testing multiple predictions...")
                test_features = [predictor.create_sample_features() for _ in range(3)]
                results = predictor.predict_multiple_matches(test_features)
                
                for i, result in enumerate(results):
                    print(f"\n--- Match {i+1} ---")
                    if 'error' in result:
                        print(f"❌ Error: {result['error']}")
                    else:
                        print(f"Prediction: {result['prediction']} ({result['confidence']:.1%})")
                        print(f"Recommendation: {result['recommendation']}")
                
            except Exception as e:
                print(f"❌ Multiple prediction error: {e}")
        
        elif choice == '4':
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid option. Please select 1-4.")


if __name__ == "__main__":
    main() 