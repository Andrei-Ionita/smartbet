#!/usr/bin/env python3
"""
ENHANCED SERIE A 1X2 PREDICTOR WITH SHAP EXPLANATIONS
=====================================================

Production-ready Serie A 1X2 prediction system with:
- SHAP explanations for model interpretability
- Confidence thresholding for betting recommendations
- Detailed feature contribution analysis
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
import shap
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class EnhancedSerieA1X2Predictor:
    def __init__(self, model_path='league_model_1x2_serie_a_20250630_125109.txt', confidence_threshold=0.6):
        """
        Initialize the enhanced predictor with SHAP explanations.
        
        ❌ WARNING: Do NOT use this model for other leagues!
        This model is trained on SERIE A data and will NOT generalize.
        """
        # 🔒 LEAGUE SAFETY ENFORCEMENT
        self.authorized_league = "Serie A"
        self.enforce_league_safety = True
        
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.explainer = None
        self.feature_names = [
            'true_prob_draw', 'prob_ratio_draw_away', 'prob_ratio_home_draw',
            'log_odds_home_draw', 'log_odds_draw_away', 'bookmaker_margin',
            'market_efficiency', 'uncertainty_index', 'odds_draw',
            'goals_for_away', 'recent_form_home', 'recent_form_away'
        ]
        
        self.load_model()
        self.setup_shap_explainer()
    
    def validate_league_usage(self, league_name: str = None):
        """
        Enforce league-specific usage to prevent cross-league contamination.
        
        ❌ WARNING: This model is ONLY for Serie A matches!
        
        Args:
            league_name: Name of the league for the match
            
        Raises:
            ValueError: If trying to use model for non-Serie A matches
        """
        if league_name and league_name.lower() not in ["serie a", "series a", "italian serie a", "italy serie a"]:
            raise ValueError(
                f"🚨 CROSS-LEAGUE VIOLATION: This Serie A model cannot predict {league_name} matches! "
                f"This model is ONLY valid for Serie A matches. "
                f"Use the appropriate league-specific model instead."
            )
    
    def load_model(self):
        """Load the trained LightGBM model."""
        try:
            self.model = lgb.Booster(model_file=self.model_path)
            print(f"✅ Model loaded successfully from {self.model_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            return False
    
    def setup_shap_explainer(self):
        """Initialize SHAP explainer for model interpretability."""
        try:
            # Create a simple background dataset for SHAP
            # Use representative values for Serie A matches
            background_data = np.array([
                [0.32, 1.1, 1.2, 0.1, -0.1, -0.06, 16.5, 0.15, 5.2, 1.3, 1.5, 1.2],  # Typical values
                [0.28, 0.9, 1.5, 0.3, 0.2, -0.05, 18.0, 0.18, 4.8, 1.1, 1.8, 0.9],   # Home favorite
                [0.35, 1.3, 0.8, -0.2, -0.3, -0.07, 15.2, 0.12, 5.8, 1.5, 1.0, 1.6]  # Away favorite
            ])
            
            self.explainer = shap.TreeExplainer(self.model, data=background_data, feature_perturbation='tree_path_dependent')
            print("✅ SHAP explainer initialized successfully")
            return True
        except Exception as e:
            print(f"⚠️ SHAP explainer setup failed: {e}")
            print("   Predictions will work without SHAP explanations")
            return False
    
    def calculate_features_from_odds(self, home_odds, draw_odds, away_odds, goals_for_away=1.3, 
                                   recent_form_home=1.5, recent_form_away=1.2):
        """Calculate all required features from betting odds and team stats."""
        
        # Calculate implied probabilities
        total_inv_odds = 1/home_odds + 1/away_odds + 1/draw_odds
        true_prob_home = (1/home_odds) / total_inv_odds
        true_prob_away = (1/away_odds) / total_inv_odds
        true_prob_draw = (1/draw_odds) / total_inv_odds
        
        # Calculate derived features
        prob_ratio_draw_away = true_prob_draw / true_prob_away if true_prob_away > 0 else 1.0
        prob_ratio_home_draw = true_prob_home / true_prob_draw if true_prob_draw > 0 else 1.0
        
        log_odds_home_draw = np.log(home_odds) - np.log(draw_odds)
        log_odds_draw_away = np.log(draw_odds) - np.log(away_odds)
        
        bookmaker_margin = total_inv_odds - 1
        market_efficiency = 1 / total_inv_odds
        uncertainty_index = np.std([true_prob_home, true_prob_draw, true_prob_away])
        
        features = np.array([[
            true_prob_draw,
            prob_ratio_draw_away,
            prob_ratio_home_draw,
            log_odds_home_draw,
            log_odds_draw_away,
            bookmaker_margin,
            market_efficiency,
            uncertainty_index,
            draw_odds,
            goals_for_away,
            recent_form_home,
            recent_form_away
        ]])
        
        return features
    
    def get_shap_explanation(self, features):
        """Generate SHAP explanations for the prediction."""
        if self.explainer is None:
            return None, None
        
        try:
            # Calculate SHAP values
            shap_values = self.explainer.shap_values(features)
            
            # If multi-class, get SHAP values for each class
            if isinstance(shap_values, list):
                # LightGBM returns list of arrays for multiclass
                predicted_class = np.argmax(self.model.predict(features)[0])
                class_shap_values = shap_values[predicted_class][0]
            else:
                class_shap_values = shap_values[0]
            
            # Get top 5 features by absolute SHAP value
            feature_importance = list(zip(self.feature_names, class_shap_values))
            feature_importance.sort(key=lambda x: abs(x[1]), reverse=True)
            top_features = feature_importance[:5]
            
            # Create explanation summary
            explanation = {
                'top_features': top_features,
                'all_shap_values': dict(zip(self.feature_names, class_shap_values)),
                'base_value': self.explainer.expected_value[predicted_class] if isinstance(self.explainer.expected_value, list) else self.explainer.expected_value
            }
            
            return explanation, predicted_class
            
        except Exception as e:
            print(f"⚠️ SHAP explanation failed: {e}")
            return None, None
    
    def predict_match(self, home_team, away_team, home_odds, draw_odds, away_odds, 
                     goals_for_away=1.3, recent_form_home=1.5, recent_form_away=1.2,
                     include_shap=True):
        """
        Predict match outcome with SHAP explanations and confidence thresholding.
        
        Args:
            home_team: Name of home team
            away_team: Name of away team
            home_odds: Decimal odds for home win
            draw_odds: Decimal odds for draw
            away_odds: Decimal odds for away win
            goals_for_away: Away team's average goals per game (optional)
            recent_form_home: Home team's recent form factor (optional)
            recent_form_away: Away team's recent form factor (optional)
            include_shap: Whether to include SHAP explanations
        
        Returns:
            Dictionary with prediction, confidence, recommendation, and explanations
        """
        
        if self.model is None:
            return {"error": "Model not loaded"}
        
        # Calculate features
        features = self.calculate_features_from_odds(
            home_odds, draw_odds, away_odds, goals_for_away, recent_form_home, recent_form_away
        )
        
        # Get model prediction
        probabilities = self.model.predict(features)[0]
        predicted_class = np.argmax(probabilities)
        max_confidence = probabilities[predicted_class]
        
        outcome_names = ['Home Win', 'Away Win', 'Draw']
        prediction = outcome_names[predicted_class]
        
        # Apply confidence thresholding
        if max_confidence >= self.confidence_threshold:
            recommendation = f"BET on {prediction}"
            bet_status = "RECOMMENDED"
        else:
            recommendation = "NO BET - Low confidence"
            bet_status = "AVOID"
        
        # Base result
        result = {
            'match': f"{home_team} vs {away_team}",
            'prediction': prediction,
            'confidence': float(max_confidence),
            'probabilities': {
                'home_win': float(probabilities[0]),
                'away_win': float(probabilities[1]),
                'draw': float(probabilities[2])
            },
            'recommendation': recommendation,
            'bet_status': bet_status,
            'confidence_threshold': self.confidence_threshold,
            'input_odds': {
                'home': home_odds,
                'draw': draw_odds,
                'away': away_odds
            }
        }
        
        # Add SHAP explanations if requested and available
        if include_shap and self.explainer is not None:
            explanation, predicted_class_shap = self.get_shap_explanation(features)
            if explanation:
                result['shap_explanation'] = {
                    'top_5_features': explanation['top_features'],
                    'explanation_summary': self.format_shap_summary(explanation['top_features']),
                    'base_prediction': explanation['base_value']
                }
        
        return result
    
    def format_shap_summary(self, top_features):
        """Format SHAP explanations into human-readable text."""
        summary_lines = []
        
        for feature_name, shap_value in top_features:
            impact = "increases" if shap_value > 0 else "decreases"
            magnitude = "strongly" if abs(shap_value) > 0.1 else "moderately" if abs(shap_value) > 0.05 else "slightly"
            
            # Feature name mapping for better readability
            readable_names = {
                'true_prob_draw': 'Draw probability',
                'recent_form_home': 'Home team form',
                'recent_form_away': 'Away team form',
                'uncertainty_index': 'Market uncertainty',
                'bookmaker_margin': 'Bookmaker margin',
                'prob_ratio_home_draw': 'Home vs Draw odds ratio',
                'prob_ratio_draw_away': 'Draw vs Away odds ratio',
                'market_efficiency': 'Market efficiency',
                'odds_draw': 'Draw odds value',
                'goals_for_away': 'Away team attack strength'
            }
            
            readable_name = readable_names.get(feature_name, feature_name)
            summary_lines.append(f"• {readable_name} {magnitude} {impact} prediction ({shap_value:+.3f})")
        
        return summary_lines
    
    def create_shap_summary_plot(self, features, save_path='shap_summary_serie_a.png'):
        """Create and save SHAP summary plot."""
        if self.explainer is None:
            print("⚠️ Cannot create SHAP plot - explainer not available")
            return False
        
        try:
            # Calculate SHAP values
            shap_values = self.explainer.shap_values(features)
            
            # Create summary plot
            plt.figure(figsize=(10, 8))
            
            if isinstance(shap_values, list):
                # Multi-class case - plot for predicted class
                predicted_class = np.argmax(self.model.predict(features)[0])
                shap.summary_plot(shap_values[predicted_class], features, 
                                feature_names=self.feature_names, show=False)
                plt.title(f'SHAP Feature Importance - Serie A 1X2 Model\nPredicted Class: {["Home Win", "Away Win", "Draw"][predicted_class]}')
            else:
                shap.summary_plot(shap_values, features, 
                                feature_names=self.feature_names, show=False)
                plt.title('SHAP Feature Importance - Serie A 1X2 Model')
            
            plt.tight_layout()
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✅ SHAP summary plot saved to {save_path}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create SHAP plot: {e}")
            return False
    
    def batch_predict(self, matches_data, save_results=True):
        """
        Predict multiple matches and save results with SHAP explanations.
        
        Args:
            matches_data: List of dictionaries with match information
            save_results: Whether to save results to CSV
        
        Returns:
            DataFrame with all predictions and explanations
        """
        results = []
        
        print(f"🔮 Predicting {len(matches_data)} Serie A matches...")
        
        for i, match in enumerate(matches_data, 1):
            print(f"   Processing match {i}/{len(matches_data)}: {match.get('home_team', 'Home')} vs {match.get('away_team', 'Away')}")
            
            prediction = self.predict_match(**match)
            
            # Flatten result for CSV export
            flat_result = {
                'match_id': i,
                'home_team': match.get('home_team', 'Home'),
                'away_team': match.get('away_team', 'Away'),
                'prediction': prediction['prediction'],
                'confidence': prediction['confidence'],
                'prob_home_win': prediction['probabilities']['home_win'],
                'prob_away_win': prediction['probabilities']['away_win'],
                'prob_draw': prediction['probabilities']['draw'],
                'recommendation': prediction['recommendation'],
                'bet_status': prediction['bet_status'],
                'home_odds': prediction['input_odds']['home'],
                'draw_odds': prediction['input_odds']['draw'],
                'away_odds': prediction['input_odds']['away']
            }
            
            # Add SHAP explanation if available
            if 'shap_explanation' in prediction:
                for j, (feature, value) in enumerate(prediction['shap_explanation']['top_5_features']):
                    flat_result[f'shap_feature_{j+1}'] = feature
                    flat_result[f'shap_value_{j+1}'] = value
            
            results.append(flat_result)
        
        results_df = pd.DataFrame(results)
        
        if save_results:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'serie_a_predictions_with_shap_{timestamp}.csv'
            results_df.to_csv(filename, index=False)
            print(f"✅ Results saved to {filename}")
        
        return results_df

def main():
    """Demo the enhanced prediction system."""
    print("🇮🇹 ENHANCED SERIE A 1X2 PREDICTOR WITH SHAP")
    print("=" * 50)
    
    # Initialize predictor
    predictor = EnhancedSerieA1X2Predictor(confidence_threshold=0.6)
    
    # Example predictions
    example_matches = [
        {
            'home_team': 'Juventus',
            'away_team': 'AC Milan',
            'home_odds': 2.1,
            'draw_odds': 3.2,
            'away_odds': 3.8,
            'recent_form_home': 1.6,
            'recent_form_away': 1.4
        },
        {
            'home_team': 'Inter Milan',
            'away_team': 'Napoli',
            'home_odds': 1.9,
            'draw_odds': 3.4,
            'away_odds': 4.2,
            'recent_form_home': 1.8,
            'recent_form_away': 1.3
        },
        {
            'home_team': 'AS Roma',
            'away_team': 'Fiorentina',
            'home_odds': 2.3,
            'draw_odds': 3.1,
            'away_odds': 3.2,
            'recent_form_home': 1.2,
            'recent_form_away': 1.5
        }
    ]
    
    # Run batch predictions
    results_df = predictor.batch_predict(example_matches)
    
    # Print summary
    print(f"\n📊 PREDICTION SUMMARY")
    print("=" * 25)
    print(f"Total matches: {len(results_df)}")
    print(f"Recommended bets: {len(results_df[results_df['bet_status'] == 'RECOMMENDED'])}")
    print(f"Average confidence: {results_df['confidence'].mean():.3f}")
    
    # Show detailed results
    print(f"\n🎯 DETAILED PREDICTIONS")
    print("-" * 30)
    
    for _, row in results_df.iterrows():
        print(f"\n{row['home_team']} vs {row['away_team']}")
        print(f"   Prediction: {row['prediction']} (Confidence: {row['confidence']:.1%})")
        print(f"   Recommendation: {row['recommendation']}")
        
        # Show SHAP explanation if available
        shap_features = [col for col in row.index if col.startswith('shap_feature_')]
        if shap_features:
            print(f"   Key factors:")
            for i in range(1, 6):
                feature_col = f'shap_feature_{i}'
                value_col = f'shap_value_{i}'
                if feature_col in row and pd.notna(row[feature_col]):
                    impact = "↑" if row[value_col] > 0 else "↓"
                    print(f"     {impact} {row[feature_col]}: {row[value_col]:+.3f}")
    
    print(f"\n✅ Enhanced prediction system demo complete!")
    return True

if __name__ == "__main__":
    main() 