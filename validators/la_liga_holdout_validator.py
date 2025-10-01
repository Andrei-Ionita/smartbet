#!/usr/bin/env python3
"""
🎯 LA LIGA MODEL - STRICT HOLDOUT VALIDATION PIPELINE
=====================================================

Complete validation pipeline to test the La Liga model on unseen data.
This ensures unbiased performance estimation using time-based holdout split.
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
import matplotlib.pyplot as plt
from datetime import datetime
import json
import os
import warnings
warnings.filterwarnings('ignore')

class LaLigaHoldoutValidator:
    def __init__(self):
        """Initialize the holdout validator."""
        self.dataset_file = 'LOCKED_PRODUCTION_la_liga_complete_training_dataset_20250630_152907.csv'
        self.model_file = 'LOCKED_PRODUCTION_league_model_1x2_la_liga_20250630_152907.txt'
        self.confidence_threshold = 0.60  # 60% minimum confidence
        self.odds_threshold = 1.5         # 1.5 minimum odds
        self.stake_per_bet = 10.0         # €10 fixed stake
        self.holdout_ratio = 0.20         # 20% holdout split
        
        # Results storage
        self.holdout_data = None
        self.model = None
        self.predictions = None
        self.simulation_results = None
        
    def step1_create_holdout_set(self):
        """Create holdout test set from most recent 20% of matches."""
        print("🚧 STEP 1: Creating Holdout Test Set")
        print("=" * 50)
        
        # Load full dataset
        if not os.path.exists(self.dataset_file):
            raise FileNotFoundError(f"❌ Dataset not found: {self.dataset_file}")
        
        df = pd.read_csv(self.dataset_file)
        print(f"📊 Loaded {len(df)} total matches from dataset")
        
        # Sort by season to ensure time-based split
        df = df.sort_values('season').reset_index(drop=True)
        
        # Calculate split point (80% train, 20% holdout)
        split_idx = int(len(df) * (1 - self.holdout_ratio))
        
        # Create splits
        training_data = df.iloc[:split_idx].copy()
        holdout_data = df.iloc[split_idx:].copy()
        
        # Save holdout set
        holdout_file = 'la_liga_holdout_test_set.csv'
        holdout_data.to_csv(holdout_file, index=False)
        
        print(f"✅ Training set: {len(training_data)} matches")
        print(f"✅ Holdout set: {len(holdout_data)} matches ({len(holdout_data)/len(df)*100:.1f}%)")
        print(f"📁 Saved holdout set: {holdout_file}")
        
        # Show split details
        print(f"\n📅 SPLIT DETAILS:")
        print(f"   Training seasons: {training_data['season'].unique()}")
        print(f"   Holdout seasons: {holdout_data['season'].unique()}")
        
        self.holdout_data = holdout_data
        return holdout_data
    
    def step2_load_frozen_model(self):
        """Load the locked production model without any modifications."""
        print("\n🔒 STEP 2: Loading Frozen Production Model")
        print("=" * 50)
        
        if not os.path.exists(self.model_file):
            raise FileNotFoundError(f"❌ Model not found: {self.model_file}")
        
        # Load the locked LightGBM model
        self.model = lgb.Booster(model_file=self.model_file)
        
        # Get model info
        model_size = os.path.getsize(self.model_file) / 1024  # KB
        num_features = self.model.num_feature()
        
        print(f"✅ Loaded locked La Liga model")
        print(f"📊 Model size: {model_size:.1f} KB")
        print(f"🎯 Features: {num_features}")
        print(f"🔒 Model Status: FROZEN (no retraining allowed)")
        
        return self.model
    
    def step3_run_holdout_inference(self):
        """Run predictions on holdout data using frozen model."""
        print("\n🧠 STEP 3: Running Holdout Inference")
        print("=" * 50)
        
        if self.holdout_data is None:
            raise ValueError("❌ Holdout data not created. Run step1 first.")
        if self.model is None:
            raise ValueError("❌ Model not loaded. Run step2 first.")
        
        # Prepare features (same as training)
        feature_columns = [
            'home_win_odds', 'away_win_odds', 'draw_odds',
            'home_recent_form', 'away_recent_form', 'recent_form_diff',
            'home_goals_for', 'home_goals_against', 'away_goals_for', 'away_goals_against',
            'home_win_rate', 'away_win_rate'
        ]
        
        X_holdout = self.holdout_data[feature_columns].copy()
        y_holdout = self.holdout_data['result'].copy()
        
        print(f"📊 Holdout features shape: {X_holdout.shape}")
        print(f"🎯 Target distribution: {y_holdout.value_counts().to_dict()}")
        
        # Run predictions
        predictions_proba = self.model.predict(X_holdout)
        predictions_class = np.argmax(predictions_proba, axis=1)
        max_confidence = np.max(predictions_proba, axis=1)
        
        # Create predictions dataframe
        self.predictions = pd.DataFrame({
            'match_id': range(len(X_holdout)),
            'home_team': self.holdout_data['home_team'].values,
            'away_team': self.holdout_data['away_team'].values,
            'season': self.holdout_data['season'].values,
            'actual_result': y_holdout.values,
            'predicted_result': predictions_class,
            'confidence_home': predictions_proba[:, 0],
            'confidence_draw': predictions_proba[:, 1], 
            'confidence_away': predictions_proba[:, 2],
            'max_confidence': max_confidence,
            'home_odds': self.holdout_data['home_win_odds'].values,
            'draw_odds': self.holdout_data['draw_odds'].values,
            'away_odds': self.holdout_data['away_win_odds'].values,
            'correct': (predictions_class == y_holdout.values).astype(int)
        })
        
        # Add predicted odds based on prediction
        predicted_odds = []
        for i, pred in enumerate(predictions_class):
            if pred == 0:  # Home win
                predicted_odds.append(self.predictions.iloc[i]['home_odds'])
            elif pred == 1:  # Draw
                predicted_odds.append(self.predictions.iloc[i]['draw_odds'])
            else:  # Away win
                predicted_odds.append(self.predictions.iloc[i]['away_odds'])
        
        self.predictions['predicted_odds'] = predicted_odds
        
        # Save predictions
        predictions_file = 'la_liga_holdout_predictions.csv'
        self.predictions.to_csv(predictions_file, index=False)
        
        # Calculate basic metrics
        accuracy = (self.predictions['correct'].sum() / len(self.predictions)) * 100
        avg_confidence = self.predictions['max_confidence'].mean() * 100
        
        print(f"✅ Completed inference on {len(self.predictions)} matches")
        print(f"🎯 Raw accuracy: {accuracy:.2f}%")
        print(f"📊 Average confidence: {avg_confidence:.2f}%")
        print(f"📁 Saved predictions: {predictions_file}")
        
        return self.predictions
    
    def step4_paper_trading_simulation(self):
        """Simulate paper trading with strict rules."""
        print("\n💹 STEP 4: Paper Trading Simulation")
        print("=" * 50)
        
        if self.predictions is None:
            raise ValueError("❌ Predictions not generated. Run step3 first.")
        
        # Apply betting filters
        betting_mask = (
            (self.predictions['max_confidence'] >= self.confidence_threshold) &
            (self.predictions['predicted_odds'] >= self.odds_threshold)
        )
        
        betting_predictions = self.predictions[betting_mask].copy()
        
        print(f"🎯 BETTING FILTERS:")
        print(f"   Confidence ≥ {self.confidence_threshold*100:.0f}%")
        print(f"   Odds ≥ {self.odds_threshold}")
        print(f"   Stake per bet: €{self.stake_per_bet}")
        print(f"")
        print(f"📊 BETTING STATS:")
        print(f"   Total predictions: {len(self.predictions)}")
        print(f"   Qualifying bets: {len(betting_predictions)}")
        print(f"   Bet ratio: {len(betting_predictions)/len(self.predictions)*100:.1f}%")
        
        if len(betting_predictions) == 0:
            print("⚠️ No bets qualify for criteria!")
            return None
        
        # Calculate simulation results
        betting_predictions['stake'] = self.stake_per_bet
        betting_predictions['payout'] = betting_predictions['stake'] * betting_predictions['predicted_odds']
        betting_predictions['profit'] = np.where(
            betting_predictions['correct'] == 1,
            betting_predictions['payout'] - betting_predictions['stake'],
            -betting_predictions['stake']
        )
        
        # Cumulative metrics
        betting_predictions['cumulative_profit'] = betting_predictions['profit'].cumsum()
        starting_bankroll = 1000.0
        betting_predictions['bankroll'] = starting_bankroll + betting_predictions['cumulative_profit']
        
        # Calculate performance metrics
        total_bets = len(betting_predictions)
        winning_bets = betting_predictions['correct'].sum()
        total_stake = betting_predictions['stake'].sum()
        total_profit = betting_predictions['profit'].sum()
        hit_rate = (winning_bets / total_bets) * 100
        roi = (total_profit / total_stake) * 100
        final_bankroll = betting_predictions['bankroll'].iloc[-1]
        
        # Risk metrics
        max_drawdown = ((betting_predictions['bankroll'].cummax() - betting_predictions['bankroll']) / 
                       betting_predictions['bankroll'].cummax() * 100).max()
        
        self.simulation_results = {
            'total_bets': total_bets,
            'winning_bets': winning_bets,
            'losing_bets': total_bets - winning_bets,
            'hit_rate': hit_rate,
            'total_stake': total_stake,
            'total_profit': total_profit,
            'roi': roi,
            'starting_bankroll': starting_bankroll,
            'final_bankroll': final_bankroll,
            'max_drawdown': max_drawdown,
            'avg_odds': betting_predictions['predicted_odds'].mean(),
            'avg_confidence': betting_predictions['max_confidence'].mean() * 100
        }
        
        print(f"\n💰 SIMULATION RESULTS:")
        print(f"   Hit Rate: {hit_rate:.2f}%")
        print(f"   ROI: {roi:.2f}%")
        print(f"   Total Profit: €{total_profit:.2f}")
        print(f"   Final Bankroll: €{final_bankroll:.2f}")
        print(f"   Max Drawdown: {max_drawdown:.2f}%")
        
        # Save transaction log
        transaction_file = 'la_liga_holdout_transactions.csv'
        betting_predictions.to_csv(transaction_file, index=False)
        print(f"📁 Saved transactions: {transaction_file}")
        
        return betting_predictions
    
    def step5_generate_reports(self):
        """Generate comprehensive validation reports."""
        print("\n📊 STEP 5: Generating Validation Reports")
        print("=" * 50)
        
        if self.simulation_results is None:
            raise ValueError("❌ Simulation not completed. Run step4 first.")
        
        # Create summary report
        summary = pd.DataFrame([self.simulation_results])
        summary_file = 'la_liga_holdout_summary.csv'
        summary.to_csv(summary_file, index=False)
        
        # Create visualization
        betting_data = pd.read_csv('la_liga_holdout_transactions.csv')
        
        plt.figure(figsize=(14, 10))
        
        # Bankroll evolution
        plt.subplot(2, 2, 1)
        plt.plot(range(len(betting_data)), betting_data['bankroll'], 
                linewidth=2, color='darkgreen', label='Bankroll')
        plt.axhline(self.simulation_results['starting_bankroll'], 
                   linestyle='--', color='gray', alpha=0.7, label='Starting Capital')
        plt.title('Holdout Bankroll Evolution', fontweight='bold')
        plt.xlabel('Bet Number')
        plt.ylabel('Bankroll (€)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Profit distribution
        plt.subplot(2, 2, 2)
        plt.hist(betting_data['profit'], bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        plt.title('Profit Distribution', fontweight='bold')
        plt.xlabel('Profit per Bet (€)')
        plt.ylabel('Frequency')
        plt.grid(True, alpha=0.3)
        
        # Confidence vs Success
        plt.subplot(2, 2, 3)
        wins = betting_data[betting_data['correct'] == 1]
        losses = betting_data[betting_data['correct'] == 0]
        plt.scatter(wins['max_confidence'], wins['predicted_odds'], 
                   color='green', alpha=0.6, label='Wins', s=30)
        plt.scatter(losses['max_confidence'], losses['predicted_odds'], 
                   color='red', alpha=0.6, label='Losses', s=30)
        plt.title('Confidence vs Odds', fontweight='bold')
        plt.xlabel('Prediction Confidence')
        plt.ylabel('Betting Odds')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Cumulative profit
        plt.subplot(2, 2, 4)
        plt.plot(range(len(betting_data)), betting_data['cumulative_profit'], 
                linewidth=2, color='navy', label='Cumulative Profit')
        plt.axhline(0, linestyle='--', color='gray', alpha=0.7, label='Breakeven')
        plt.title('Cumulative Profit', fontweight='bold')
        plt.xlabel('Bet Number')
        plt.ylabel('Cumulative Profit (€)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        chart_file = 'la_liga_holdout_bankroll.png'
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        
        print(f"✅ Summary report: {summary_file}")
        print(f"✅ Visualization: {chart_file}")
        
        return summary
    
    def step6_final_assessment(self):
        """Final PASS/FAIL assessment based on performance criteria."""
        print("\n✅ STEP 6: Final Validation Assessment")
        print("=" * 50)
        
        if self.simulation_results is None:
            raise ValueError("❌ Simulation not completed. Run step4 first.")
        
        # Validation criteria
        roi_threshold = 0.0      # ROI > 0%
        hit_rate_threshold = 55.0  # Hit rate > 55%
        min_bets = 5             # Minimum 5 bets for valid test
        
        results = self.simulation_results
        
        # Check criteria
        roi_pass = results['roi'] > roi_threshold
        hit_rate_pass = results['hit_rate'] > hit_rate_threshold
        volume_pass = results['total_bets'] >= min_bets
        
        overall_pass = roi_pass and hit_rate_pass and volume_pass
        
        print(f"🎯 VALIDATION CRITERIA:")
        print(f"   ROI > {roi_threshold}%: {'✅ PASS' if roi_pass else '❌ FAIL'} ({results['roi']:.2f}%)")
        print(f"   Hit Rate > {hit_rate_threshold}%: {'✅ PASS' if hit_rate_pass else '❌ FAIL'} ({results['hit_rate']:.2f}%)")
        print(f"   Min Bets ≥ {min_bets}: {'✅ PASS' if volume_pass else '❌ FAIL'} ({results['total_bets']} bets)")
        
        print(f"\n🏆 FINAL RESULT: {'✅ MODEL VALIDATED' if overall_pass else '❌ MODEL FAILED VALIDATION'}")
        
        # Additional performance assessment
        if overall_pass:
            if results['roi'] > 50:
                quality = "🌟 EXCEPTIONAL"
            elif results['roi'] > 20:
                quality = "⭐ EXCELLENT"
            elif results['roi'] > 10:
                quality = "✅ GOOD"
            else:
                quality = "📈 ACCEPTABLE"
            print(f"📊 Model Quality: {quality}")
        
        # Save validation status
        validation_status = {
            'model_validated': overall_pass,
            'validation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'roi_pass': roi_pass,
            'hit_rate_pass': hit_rate_pass,
            'volume_pass': volume_pass,
            'final_roi': results['roi'],
            'final_hit_rate': results['hit_rate'],
            'total_bets': results['total_bets'],
            'assessment': quality if overall_pass else "FAILED VALIDATION"
        }
        
        status_file = 'la_liga_model_validation_status.txt'
        with open(status_file, 'w') as f:
            f.write(f"LA LIGA MODEL VALIDATION STATUS\n")
            f.write(f"================================\n\n")
            f.write(f"MODEL_VALIDATED={overall_pass}\n")
            f.write(f"VALIDATION_DATE={validation_status['validation_date']}\n")
            f.write(f"FINAL_ROI={results['roi']:.2f}%\n")
            f.write(f"FINAL_HIT_RATE={results['hit_rate']:.2f}%\n")
            f.write(f"TOTAL_BETS={results['total_bets']}\n")
            f.write(f"ASSESSMENT={validation_status['assessment']}\n")
        
        print(f"📁 Validation status saved: {status_file}")
        
        return overall_pass, validation_status
    
    def run_complete_validation(self):
        """Run the complete holdout validation pipeline."""
        print("🎯 LA LIGA MODEL - HOLDOUT VALIDATION PIPELINE")
        print("=" * 60)
        print("Running complete validation to ensure unbiased performance...")
        print()
        
        try:
            # Execute all steps
            self.step1_create_holdout_set()
            self.step2_load_frozen_model()
            self.step3_run_holdout_inference()
            betting_data = self.step4_paper_trading_simulation()
            
            if betting_data is not None:
                self.step5_generate_reports()
                validation_passed, status = self.step6_final_assessment()
                
                print(f"\n" + "=" * 60)
                print(f"🎯 VALIDATION COMPLETE!")
                print(f"Final Status: {'✅ VALIDATED' if validation_passed else '❌ FAILED'}")
                print(f"=" * 60)
                
                return validation_passed, status
            else:
                print("\n❌ VALIDATION FAILED: No qualifying bets found")
                return False, None
                
        except Exception as e:
            print(f"\n❌ VALIDATION ERROR: {str(e)}")
            return False, None

def main():
    """Main execution function."""
    validator = LaLigaHoldoutValidator()
    validation_passed, status = validator.run_complete_validation()
    
    if validation_passed:
        print("\n🔥 La Liga model successfully validated on holdout data!")
    else:
        print("\n⚠️ La Liga model failed holdout validation.")
    
    return validation_passed

if __name__ == "__main__":
    main() 