#!/usr/bin/env python3
"""
SERIE A 1X2 PRODUCTION-READY PREDICTOR
======================================

Live deployment system with:
- Dual thresholding (confidence ≥ 60% AND odds ≥ 1.80)
- Paper trading logging and monitoring
- Enhanced SHAP explanations for user trust
- Live performance tracking
- Real-time recommendation engine
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
import matplotlib.pyplot as plt
import json
from datetime import datetime, timedelta
import os
import warnings
warnings.filterwarnings('ignore')

class SerieAProductionPredictor:
    def __init__(self, 
                 model_path='league_model_1x2_serie_a_20250630_125109.txt',
                 confidence_threshold=0.60,
                 odds_threshold=1.80,
                 paper_trading=True):
        """
        Initialize production-ready Serie A predictor.
        
        ❌ WARNING: Do NOT use this model for other leagues!
        This model is trained on SERIE A data and will NOT generalize.
        
        Args:
            confidence_threshold: Minimum prediction confidence (default: 60%)
            odds_threshold: Minimum acceptable odds (default: 1.80)
            paper_trading: Enable paper trading logging (default: True)
        """
        # 🔒 LEAGUE SAFETY ENFORCEMENT
        self.authorized_league = "Serie A"
        self.enforce_league_safety = True
        
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.odds_threshold = odds_threshold
        self.paper_trading = paper_trading
        self.model = None
        
        # Feature definitions
        self.feature_names = [
            'true_prob_draw', 'prob_ratio_draw_away', 'prob_ratio_home_draw',
            'log_odds_home_draw', 'log_odds_draw_away', 'bookmaker_margin',
            'market_efficiency', 'uncertainty_index', 'odds_draw',
            'goals_for_away', 'recent_form_home', 'recent_form_away'
        ]
        
        # Load components
        self.feature_importance = self.load_feature_importance()
        self.load_model()
        
        # Initialize paper trading
        if self.paper_trading:
            self.init_paper_trading()
    
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
        """Load the trained LightGBM model."""
        try:
            self.model = lgb.Booster(model_file=self.model_path)
            print(f"✅ Production model loaded: {self.model_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            return False
    
    def load_feature_importance(self):
        """Load feature importance rankings."""
        try:
            importance_df = pd.read_csv('feature_importance_serie_a_20250630_125109.csv')
            importance_dict = dict(zip(importance_df['feature'], importance_df['importance']))
            print(f"✅ Loaded feature importance for {len(importance_dict)} features")
            return importance_dict
        except Exception as e:
            print(f"⚠️ Could not load feature importance: {e}")
            return {}
    
    def init_paper_trading(self):
        """Initialize paper trading log."""
        self.paper_trade_file = f'paper_trade_log_{datetime.now().strftime("%Y%m%d")}.csv'
        
        if not os.path.exists(self.paper_trade_file):
            # Create new paper trading log
            columns = [
                'timestamp', 'match', 'home_team', 'away_team',
                'prediction', 'confidence', 'selected_odds', 'recommendation',
                'home_odds', 'draw_odds', 'away_odds',
                'top_feature_1', 'top_feature_2', 'top_feature_3',
                'market_efficiency', 'uncertainty_index',
                'actual_result', 'profit_loss', 'running_balance'
            ]
            
            pd.DataFrame(columns=columns).to_csv(self.paper_trade_file, index=False)
            print(f"✅ Paper trading log initialized: {self.paper_trade_file}")
        else:
            print(f"✅ Using existing paper trading log: {self.paper_trade_file}")
    
    def calculate_features_from_odds(self, home_odds, draw_odds, away_odds, 
                                   goals_for_away=1.3, recent_form_home=1.5, recent_form_away=1.2):
        """Calculate model features from betting odds and team stats."""
        
        # Implied probabilities
        total_inv_odds = 1/home_odds + 1/away_odds + 1/draw_odds
        true_prob_home = (1/home_odds) / total_inv_odds
        true_prob_away = (1/away_odds) / total_inv_odds
        true_prob_draw = (1/draw_odds) / total_inv_odds
        
        # Derived features
        prob_ratio_draw_away = true_prob_draw / true_prob_away if true_prob_away > 0 else 1.0
        prob_ratio_home_draw = true_prob_home / true_prob_draw if true_prob_draw > 0 else 1.0
        
        log_odds_home_draw = np.log(home_odds) - np.log(draw_odds)
        log_odds_draw_away = np.log(draw_odds) - np.log(away_odds)
        
        bookmaker_margin = total_inv_odds - 1
        market_efficiency = 1 / total_inv_odds
        uncertainty_index = np.std([true_prob_home, true_prob_draw, true_prob_away])
        
        features = np.array([[
            true_prob_draw, prob_ratio_draw_away, prob_ratio_home_draw,
            log_odds_home_draw, log_odds_draw_away, bookmaker_margin,
            market_efficiency, uncertainty_index, draw_odds,
            goals_for_away, recent_form_home, recent_form_away
        ]])
        
        # Feature dictionary for analysis
        feature_dict = dict(zip(self.feature_names, features[0]))
        
        return features, feature_dict
    
    def get_enhanced_shap_explanation(self, feature_dict, prediction, confidence):
        """Generate enhanced SHAP-style explanations with user-friendly descriptions."""
        
        # Calculate feature contributions (simplified approach)
        contributions = []
        
        for feature_name, feature_value in feature_dict.items():
            importance = self.feature_importance.get(feature_name, 0)
            
            # Normalize contribution
            contribution_score = (feature_value * importance) / 10000
            
            contributions.append({
                'feature': feature_name,
                'value': feature_value,
                'importance': importance,
                'contribution': contribution_score
            })
        
        # Sort by contribution magnitude
        contributions.sort(key=lambda x: abs(x['contribution']), reverse=True)
        top_5 = contributions[:5]
        
        # Generate user-friendly explanations
        explanations = []
        feature_insights = {
            'recent_form_home': {
                'name': 'Home Team Form',
                'positive': 'strong recent home performance',
                'negative': 'poor recent home performance'
            },
            'recent_form_away': {
                'name': 'Away Team Form', 
                'positive': 'strong recent away performance',
                'negative': 'poor recent away performance'
            },
            'uncertainty_index': {
                'name': 'Market Uncertainty',
                'positive': 'high market volatility (unpredictable match)',
                'negative': 'low market volatility (predictable match)'
            },
            'bookmaker_margin': {
                'name': 'Bookmaker Margin',
                'positive': 'high bookmaker profit margin',
                'negative': 'low bookmaker profit margin'
            },
            'market_efficiency': {
                'name': 'Market Efficiency',
                'positive': 'efficient odds pricing',
                'negative': 'inefficient odds pricing'
            },
            'true_prob_draw': {
                'name': 'Draw Probability',
                'positive': 'high likelihood of draw',
                'negative': 'low likelihood of draw'
            },
            'prob_ratio_home_draw': {
                'name': 'Home vs Draw Ratio',
                'positive': 'home win more likely than draw',
                'negative': 'draw more likely than home win'
            },
            'prob_ratio_draw_away': {
                'name': 'Draw vs Away Ratio',
                'positive': 'draw more likely than away win',
                'negative': 'away win more likely than draw'
            }
        }
        
        for contrib in top_5:
            feature = contrib['feature']
            contribution = contrib['contribution']
            
            if feature in feature_insights:
                insight = feature_insights[feature]
                direction = 'positive' if contribution > 0 else 'negative'
                magnitude = 'strongly' if abs(contribution) > 0.05 else 'moderately'
                
                explanation = f"• {insight['name']}: {insight[direction]} ({magnitude} influences {prediction.lower()})"
                explanations.append(explanation)
        
        return {
            'top_features': top_5,
            'explanations': explanations,
            'confidence_factors': {
                'market_efficiency': feature_dict.get('market_efficiency', 0),
                'uncertainty': feature_dict.get('uncertainty_index', 0),
                'form_difference': abs(feature_dict.get('recent_form_home', 1.5) - 
                                     feature_dict.get('recent_form_away', 1.2))
            }
        }
    
    def predict_match(self, home_team, away_team, home_odds, draw_odds, away_odds,
                     goals_for_away=1.3, recent_form_home=1.5, recent_form_away=1.2,
                     league_name: str = "Serie A", log_prediction=True):
        """
        Make prediction for a Serie A match.
        
        ❌ WARNING: ONLY use for Serie A matches!
        
        Args:
            home_team: Home team name
            away_team: Away team name  
            home_odds: Home win odds
            draw_odds: Draw odds
            away_odds: Away win odds
            goals_for_away: Away team goals per game (default: 1.3)
            recent_form_home: Home team recent form (default: 1.5)
            recent_form_away: Away team recent form (default: 1.2)
            league_name: League name for validation (must be Serie A)
            log_prediction: Whether to log for paper trading
            
        Returns:
            Prediction results dictionary
        """
        # 🔒 ENFORCE LEAGUE SAFETY
        self.validate_league_usage(league_name)
        
        print(f"🇮🇹 SERIE A MATCH PREDICTION")
        print("=" * 30)
        print(f"⚽ {home_team} vs {away_team}")
        print(f"🏆 League: {league_name}")
        
        if self.model is None:
            return {"error": "Model not loaded"}
        
        # Calculate features
        features, feature_dict = self.calculate_features_from_odds(
            home_odds, draw_odds, away_odds, goals_for_away, recent_form_home, recent_form_away
        )
        
        # Get model prediction
        probabilities = self.model.predict(features)[0]
        predicted_class = np.argmax(probabilities)
        max_confidence = probabilities[predicted_class]
        
        outcome_names = ['Home Win', 'Away Win', 'Draw']
        prediction = outcome_names[predicted_class]
        
        # Get odds for predicted outcome
        odds_map = {'Home Win': home_odds, 'Away Win': away_odds, 'Draw': draw_odds}
        selected_odds = odds_map[prediction]
        
        # Apply dual thresholding
        meets_confidence = max_confidence >= self.confidence_threshold
        meets_odds = selected_odds >= self.odds_threshold
        
        if meets_confidence and meets_odds:
            recommendation = f"✅ BET {prediction}"
            bet_status = "RECOMMENDED"
            recommendation_reason = f"High confidence ({max_confidence:.1%}) + Good odds ({selected_odds:.2f})"
        elif meets_confidence and not meets_odds:
            recommendation = f"⚠️ SKIP - Low odds ({selected_odds:.2f} < {self.odds_threshold})"
            bet_status = "SKIP_LOW_ODDS"
            recommendation_reason = f"Confidence OK ({max_confidence:.1%}) but odds too low"
        elif not meets_confidence and meets_odds:
            recommendation = f"⚠️ SKIP - Low confidence ({max_confidence:.1%})"
            bet_status = "SKIP_LOW_CONFIDENCE"
            recommendation_reason = f"Good odds ({selected_odds:.2f}) but confidence too low"
        else:
            recommendation = f"❌ NO BET - Low confidence + Low odds"
            bet_status = "AVOID"
            recommendation_reason = f"Both confidence ({max_confidence:.1%}) and odds ({selected_odds:.2f}) below thresholds"
        
        # Generate SHAP explanations
        shap_analysis = self.get_enhanced_shap_explanation(feature_dict, prediction, max_confidence)
        
        # Build comprehensive result
        result = {
            'match': f"{home_team} vs {away_team}",
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'prediction': prediction,
            'confidence': float(max_confidence),
            'selected_odds': selected_odds,
            'probabilities': {
                'home_win': float(probabilities[0]),
                'away_win': float(probabilities[1]),
                'draw': float(probabilities[2])
            },
            'recommendation': recommendation,
            'bet_status': bet_status,
            'recommendation_reason': recommendation_reason,
            'thresholds': {
                'confidence_threshold': self.confidence_threshold,
                'odds_threshold': self.odds_threshold,
                'meets_confidence': meets_confidence,
                'meets_odds': meets_odds
            },
            'input_odds': {
                'home': home_odds,
                'draw': draw_odds,
                'away': away_odds
            },
            'shap_analysis': shap_analysis,
            'market_analysis': {
                'efficiency': feature_dict.get('market_efficiency', 0),
                'uncertainty': feature_dict.get('uncertainty_index', 0),
                'margin': feature_dict.get('bookmaker_margin', 0),
                'value_assessment': 'Good value' if selected_odds >= 2.0 else 'Low value' if selected_odds < 1.5 else 'Fair value'
            }
        }
        
        # Log for paper trading
        if log_prediction and self.paper_trading:
            self.log_paper_trade(result, home_team, away_team)
        
        return result
    
    def log_paper_trade(self, prediction_result, home_team, away_team):
        """Log prediction for paper trading analysis."""
        try:
            # Prepare log entry
            log_entry = {
                'timestamp': prediction_result['timestamp'],
                'match': prediction_result['match'],
                'home_team': home_team,
                'away_team': away_team,
                'prediction': prediction_result['prediction'],
                'confidence': prediction_result['confidence'],
                'selected_odds': prediction_result['selected_odds'],
                'recommendation': prediction_result['bet_status'],
                'home_odds': prediction_result['input_odds']['home'],
                'draw_odds': prediction_result['input_odds']['draw'],
                'away_odds': prediction_result['input_odds']['away'],
                'top_feature_1': prediction_result['shap_analysis']['top_features'][0]['feature'] if prediction_result['shap_analysis']['top_features'] else '',
                'top_feature_2': prediction_result['shap_analysis']['top_features'][1]['feature'] if len(prediction_result['shap_analysis']['top_features']) > 1 else '',
                'top_feature_3': prediction_result['shap_analysis']['top_features'][2]['feature'] if len(prediction_result['shap_analysis']['top_features']) > 2 else '',
                'market_efficiency': prediction_result['market_analysis']['efficiency'],
                'uncertainty_index': prediction_result['market_analysis']['uncertainty'],
                'actual_result': '',  # To be filled later
                'profit_loss': '',    # To be filled later
                'running_balance': '' # To be filled later
            }
            
            # Append to log
            log_df = pd.DataFrame([log_entry])
            log_df.to_csv(self.paper_trade_file, mode='a', header=False, index=False)
            
        except Exception as e:
            print(f"⚠️ Paper trading log failed: {e}")
    
    def update_paper_trade_result(self, match_identifier, actual_result, stake=10):
        """
        Update paper trading log with actual match result.
        
        Args:
            match_identifier: String to identify match (e.g., "Juventus vs AC Milan")
            actual_result: 'Home Win', 'Away Win', or 'Draw'
            stake: Bet stake amount for profit calculation
        """
        try:
            # Load current log
            log_df = pd.read_csv(self.paper_trade_file)
            
            # Find matching prediction
            mask = log_df['match'].str.contains(match_identifier, na=False)
            
            if mask.any():
                idx = log_df[mask].index[-1]  # Get most recent if multiple
                
                # Calculate profit/loss
                predicted = log_df.loc[idx, 'prediction']
                odds = log_df.loc[idx, 'selected_odds']
                recommended = log_df.loc[idx, 'recommendation']
                
                if recommended == 'RECOMMENDED':
                    if predicted == actual_result:
                        profit_loss = stake * (odds - 1)  # Win
                    else:
                        profit_loss = -stake  # Loss
                else:
                    profit_loss = 0  # No bet placed
                
                # Update log
                log_df.loc[idx, 'actual_result'] = actual_result
                log_df.loc[idx, 'profit_loss'] = profit_loss
                
                # Calculate running balance
                current_balance = log_df.loc[:idx, 'profit_loss'].sum()
                log_df.loc[idx, 'running_balance'] = current_balance
                
                # Save updated log
                log_df.to_csv(self.paper_trade_file, index=False)
                
                print(f"✅ Updated result for {match_identifier}: {actual_result}")
                print(f"   Profit/Loss: ${profit_loss:+.2f}, Running Balance: ${current_balance:+.2f}")
                
            else:
                print(f"⚠️ Match not found in paper trading log: {match_identifier}")
                
        except Exception as e:
            print(f"❌ Failed to update paper trading result: {e}")
    
    def get_paper_trading_stats(self, days_back=7):
        """Get paper trading performance statistics."""
        try:
            log_df = pd.read_csv(self.paper_trade_file)
            
            # Filter recent predictions
            log_df['timestamp'] = pd.to_datetime(log_df['timestamp'])
            cutoff_date = datetime.now() - timedelta(days=days_back)
            recent_df = log_df[log_df['timestamp'] >= cutoff_date]
            
            # Calculate stats
            total_predictions = len(recent_df)
            recommended_bets = len(recent_df[recent_df['recommendation'] == 'RECOMMENDED'])
            
            # Only analyze bets with results
            completed_bets = recent_df[
                (recent_df['recommendation'] == 'RECOMMENDED') & 
                (recent_df['actual_result'].notna()) & 
                (recent_df['actual_result'] != '')
            ]
            
            if len(completed_bets) > 0:
                wins = len(completed_bets[completed_bets['prediction'] == completed_bets['actual_result']])
                hit_rate = wins / len(completed_bets) * 100
                total_profit = completed_bets['profit_loss'].sum()
                total_staked = len(completed_bets) * 10  # Assuming $10 per bet
                roi = (total_profit / total_staked * 100) if total_staked > 0 else 0
            else:
                hit_rate = 0
                total_profit = 0
                roi = 0
            
            stats = {
                'period_days': days_back,
                'total_predictions': total_predictions,
                'recommended_bets': recommended_bets,
                'completed_bets': len(completed_bets),
                'hit_rate_pct': hit_rate,
                'total_profit': total_profit,
                'roi_pct': roi,
                'avg_confidence': recent_df['confidence'].mean(),
                'avg_odds': recent_df[recent_df['recommendation'] == 'RECOMMENDED']['selected_odds'].mean()
            }
            
            return stats
            
        except Exception as e:
            print(f"❌ Failed to get paper trading stats: {e}")
            return {}
    
    def display_prediction_summary(self, prediction):
        """Display user-friendly prediction summary."""
        print(f"\n🎯 {prediction['match']}")
        print("=" * 50)
        
        print(f"🔮 PREDICTION: {prediction['prediction']}")
        print(f"🎯 CONFIDENCE: {prediction['confidence']:.1%}")
        print(f"💰 ODDS: {prediction['selected_odds']:.2f}")
        print(f"📊 RECOMMENDATION: {prediction['recommendation']}")
        print(f"💡 REASON: {prediction['recommendation_reason']}")
        
        print(f"\n📈 PROBABILITIES:")
        probs = prediction['probabilities']
        print(f"   Home Win: {probs['home_win']:.1%}")
        print(f"   Away Win: {probs['away_win']:.1%}")
        print(f"   Draw: {probs['draw']:.1%}")
        
        print(f"\n🧠 KEY FACTORS:")
        for explanation in prediction['shap_analysis']['explanations']:
            print(f"   {explanation}")
        
        print(f"\n📊 MARKET ANALYSIS:")
        market = prediction['market_analysis']
        print(f"   Value Assessment: {market['value_assessment']}")
        print(f"   Market Efficiency: {market['efficiency']:.3f}")
        print(f"   Uncertainty Level: {market['uncertainty']:.3f}")
        
        print(f"\n⚙️ THRESHOLDS:")
        thresh = prediction['thresholds']
        print(f"   Confidence: {thresh['meets_confidence']} (≥{thresh['confidence_threshold']:.0%})")
        print(f"   Odds: {thresh['meets_odds']} (≥{thresh['odds_threshold']:.2f})")

def main():
    """Demo the production-ready prediction system."""
    print("🇮🇹 SERIE A PRODUCTION-READY PREDICTOR")
    print("=" * 45)
    print("✅ Enhanced with dual thresholding and paper trading")
    
    # Initialize production predictor
    predictor = SerieAProductionPredictor(
        confidence_threshold=0.60,
        odds_threshold=1.80,
        paper_trading=True
    )
    
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
            'home_odds': 1.7,  # Low odds - should be filtered
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
    
    print(f"\n🎯 PRODUCTION PREDICTIONS")
    print("-" * 30)
    
    for i, match in enumerate(example_matches, 1):
        print(f"\n--- MATCH {i} ---")
        prediction = predictor.predict_match(**match)
        predictor.display_prediction_summary(prediction)
    
    # Show paper trading stats
    print(f"\n📊 PAPER TRADING STATISTICS")
    print("-" * 35)
    stats = predictor.get_paper_trading_stats()
    
    if stats:
        print(f"Total Predictions: {stats['total_predictions']}")
        print(f"Recommended Bets: {stats['recommended_bets']}")
        print(f"Average Confidence: {stats['avg_confidence']:.1%}")
        print(f"Average Odds: {stats.get('avg_odds', 0):.2f}")
    
    print(f"\n✅ Production system ready for deployment!")
    print(f"📁 Paper trading log: {predictor.paper_trade_file}")
    
    return True

if __name__ == "__main__":
    main() 