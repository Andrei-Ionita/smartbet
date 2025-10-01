#!/usr/bin/env python3
"""
IMPROVED SERIE A MODEL HOLDOUT VALIDATOR
Testing the enhanced Serie A model with bias correction
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class ImprovedSerieAValidator:
    def __init__(self):
        self.model_path = "IMPROVED_serie_a_model_20250702_151054.txt"
        self.dataset_path = "enhanced_training_dataset_IMPROVED_serie_a_model_20250702_151054.csv"
        self.confidence_threshold = 0.45
        self.base_stake = 10.0
        self.initial_bankroll = 1000.0
        
        print("🇮🇹 IMPROVED SERIE A MODEL VALIDATION")
        print("=" * 50)
        
    def run_validation(self):
        # Load model and data
        print("📂 Loading Enhanced Model...")
        self.model = lgb.Booster(model_file=self.model_path)
        self.df = pd.read_csv(self.dataset_path)
        print(f"✅ Model loaded, Dataset: {len(self.df)} matches")
        
        # Enhanced features
        self.features = [
            'true_prob_draw', 'prob_ratio_draw_away', 'prob_ratio_home_draw',
            'log_odds_home_draw', 'log_odds_draw_away', 'bookmaker_margin',
            'market_efficiency', 'uncertainty_index', 'odds_draw',
            'goals_for_away', 'recent_form_home', 'recent_form_away',
            'true_prob_home', 'true_prob_away', 'away_advantage', 
            'home_favorite', 'away_favorite', 'odds_variance', 
            'min_odds', 'max_odds', 'odds_range',
            'home_big_club', 'away_big_club', 'big_club_clash',
            'form_difference', 'form_ratio', 'outcome_entropy'
        ]
        
        # Create holdout split (last 20%)
        print("🔄 Creating holdout split...")
        season_col = 'season_name' if 'season_name' in self.df.columns else 'season'
        self.df = self.df.sort_values(season_col).reset_index(drop=True)
        
        holdout_size = int(len(self.df) * 0.2)
        split_point = len(self.df) - holdout_size
        self.holdout_df = self.df.iloc[split_point:].copy()
        print(f"🎯 Holdout Set: {len(self.holdout_df)} matches")
        
        # Generate predictions
        print("🔮 Generating enhanced predictions...")
        X_holdout = self.holdout_df[self.features].fillna(0)
        probabilities = self.model.predict(X_holdout.values, num_iteration=self.model.best_iteration)
        
        # Process predictions
        predictions = []
        for i, (idx, row) in enumerate(self.holdout_df.iterrows()):
            probs = probabilities[i]
            max_prob = np.max(probs)
            predicted_class = np.argmax(probs)
            
            if max_prob >= self.confidence_threshold:
                # Map class to outcome and odds
                if predicted_class == 0:  # Home win
                    outcome = 'home'
                    odds = row['avg_home_odds']
                elif predicted_class == 1:  # Away win
                    outcome = 'away'
                    odds = row['avg_away_odds']
                else:  # Draw
                    outcome = 'draw'
                    odds = row['avg_draw_odds']
                
                # Check if correct
                actual_outcome = ['home', 'away', 'draw'][row['target']]
                correct = (predicted_class == row['target'])
                
                predictions.append({
                    'match': f"{row['home_team']} vs {row['away_team']}",
                    'predicted': outcome,
                    'actual': actual_outcome,
                    'confidence': max_prob,
                    'odds': odds,
                    'correct': correct
                })
        
        print(f"📊 Enhanced predictions: {len(predictions)} bets")
        
        # Simulate paper trading
        print("💰 Simulating enhanced paper trading...")
        current_bankroll = self.initial_bankroll
        wins = 0
        losses = 0
        total_staked = 0
        
        for bet in predictions:
            stake = self.base_stake
            total_staked += stake
            
            if bet['correct']:
                profit = stake * bet['odds'] - stake
                current_bankroll += profit
                wins += 1
            else:
                current_bankroll -= stake
                losses += 1
        
        # Calculate metrics
        total_bets = len(predictions)
        hit_rate = wins / total_bets if total_bets > 0 else 0
        total_profit = current_bankroll - self.initial_bankroll
        roi = total_profit / total_staked if total_staked > 0 else 0
        
        print(f"\n🏆 ENHANCED RESULTS:")
        print(f"   Total Bets: {total_bets}")
        print(f"   Wins: {wins} | Losses: {losses}")
        print(f"   Hit Rate: {hit_rate:.1%}")
        print(f"   Total Profit: €{total_profit:.2f}")
        print(f"   ROI: {roi:.1%}")
        print(f"   Final Bankroll: €{current_bankroll:.2f}")
        
        # Prediction distribution check
        pred_outcomes = [p['predicted'] for p in predictions]
        from collections import Counter
        outcome_counts = Counter(pred_outcomes)
        print(f"\n📈 Enhanced Prediction Distribution:")
        for outcome, count in outcome_counts.items():
            print(f"   {outcome.title()}: {count} ({count/total_bets:.1%})")
        
        # Compare to original failed model
        original_hit_rate = 0.307  # From original validation
        original_roi = -0.277
        
        print(f"\n📊 IMPROVEMENT vs ORIGINAL:")
        print(f"   Hit Rate: {hit_rate:.1%} vs {original_hit_rate:.1%} (+{(hit_rate-original_hit_rate)*100:.1f}pp)")
        print(f"   ROI: {roi:.1%} vs {original_roi:.1%} (+{(roi-original_roi)*100:.1f}pp)")
        
        if hit_rate > 0.45 and roi > 0:
            print(f"\n✅ ENHANCED MODEL PASSED VALIDATION!")
        else:
            print(f"\n⚠️ Enhanced model shows improvement but needs more work")
        
        return hit_rate, roi, total_bets

if __name__ == "__main__":
    validator = ImprovedSerieAValidator()
    validator.run_validation()
