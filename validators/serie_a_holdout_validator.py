#!/usr/bin/env python3
"""
Serie A Model Holdout Validation Pipeline
Comprehensive paper trading evaluation using locked production model
Following identical methodology to La Liga and Premier League validation for fair comparison
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class SerieAHoldoutValidator:
    """Validates Serie A model using holdout data with paper trading simulation"""
    
    def __init__(self):
        """Initialize validator with Serie A model configuration"""
        self.model_path = "LOCKED_PRODUCTION_league_model_1x2_serie_a_20250630_125109.txt"
        self.dataset_path = "LOCKED_PRODUCTION_serie_a_complete_training_dataset_20250630_125108.csv"
        self.feature_importance_path = "LOCKED_PRODUCTION_feature_importance_serie_a_20250630_125109.csv"
        
        # Trading parameters (IDENTICAL to La Liga and Premier League for fair comparison)
        self.confidence_threshold = 0.6  # Must be ≥60% confident
        self.odds_threshold = 1.5        # Minimum odds for betting
        self.base_stake = 10.0          # €10 per bet
        self.bankroll = 1000.0          # €1000 starting bankroll
        
        # Validation parameters
        self.holdout_percentage = 0.2   # 20% most recent data
        self.min_bets_required = 5      # Minimum bets for valid test
        
        print("🇮🇹 Serie A Model Holdout Validator Initialized")
        print(f"📊 Model: {self.model_path}")
        print(f"📈 Confidence Threshold: {self.confidence_threshold*100}%")
        print(f"💰 Odds Threshold: {self.odds_threshold}")
        print(f"🎯 Base Stake: €{self.base_stake}")
        
    def load_model_and_data(self):
        """Load production model and dataset"""
        print("\n📂 Loading Serie A Production Assets...")
        
        # Load model
        try:
            self.model = lgb.Booster(model_file=self.model_path)
            print(f"✅ Model loaded: {type(self.model).__name__}")
                
        except Exception as e:
            raise Exception(f"❌ Failed to load model: {e}")
        
        # Load dataset
        try:
            self.df = pd.read_csv(self.dataset_path)
            print(f"✅ Dataset loaded: {len(self.df)} matches")
        except Exception as e:
            raise Exception(f"❌ Failed to load dataset: {e}")
        
        # Load feature importance
        try:
            self.feature_importance = pd.read_csv(self.feature_importance_path)
            
            # Get expected features from file
            expected_features = self.feature_importance['feature'].tolist()
            print(f"✅ Features from importance file: {len(expected_features)} features")
            
            # Verify all expected features exist
            missing_features = [f for f in expected_features if f not in self.df.columns]
            if missing_features:
                print(f"⚠️  Missing features: {missing_features}")
                # Filter to only available features
                available_features = [f for f in expected_features if f in self.df.columns]
                print(f"📊 Using {len(available_features)} available features out of {len(expected_features)} expected")
                self.feature_columns = available_features
            else:
                self.feature_columns = expected_features
                print(f"✅ All {len(self.feature_columns)} features verified")
            
        except Exception as e:
            raise Exception(f"❌ Failed to load feature importance: {e}")
    
    def create_holdout_split(self):
        """Create holdout test set using most recent 20% of data"""
        print("\n🔄 Creating Holdout Split...")
        
        # Sort by season to ensure proper chronological split
        # Check if we have 'season' or 'season_name' column
        season_col = 'season' if 'season' in self.df.columns else 'season_name'
        self.df = self.df.sort_values(season_col).reset_index(drop=True)
        
        # Calculate split point (most recent 20%)
        total_matches = len(self.df)
        holdout_size = int(total_matches * self.holdout_percentage)
        split_point = total_matches - holdout_size
        
        # Create splits
        self.train_df = self.df.iloc[:split_point].copy()
        self.holdout_df = self.df.iloc[split_point:].copy()
        
        print(f"📊 Training Set: {len(self.train_df)} matches")
        print(f"🎯 Holdout Set: {len(self.holdout_df)} matches")
        
        # Show season distribution
        if season_col in self.holdout_df.columns:
            holdout_seasons = self.holdout_df[season_col].value_counts().sort_index()
            print(f"📅 Holdout Seasons: {dict(holdout_seasons)}")
        
        # Save holdout for reference
        holdout_filename = "serie_a_holdout_test_set.csv"
        self.holdout_df.to_csv(holdout_filename, index=False)
        print(f"💾 Holdout test set saved: {holdout_filename}")
        
        return self.holdout_df
    
    def generate_predictions(self):
        """Generate predictions on holdout data using locked model"""
        print("\n🔮 Generating Predictions on Holdout Data...")
        
        # Prepare features for prediction
        X_holdout = self.holdout_df[self.feature_columns].copy()
        
        print(f"📊 Features shape: {X_holdout.shape}")
        print(f"🎯 Feature columns: {len(self.feature_columns)}")
        
        # Ensure all columns are numeric
        X_holdout = X_holdout.select_dtypes(include=[np.number])
        print(f"📊 Final features shape: {X_holdout.shape}")
        
        # Generate predictions (probabilities for each class)
        try:
            prediction_probs = self.model.predict(X_holdout)
            print(f"✅ Predictions generated: {prediction_probs.shape}")
            
            # LightGBM class mapping: 0=home, 1=draw, 2=away
            text_classes = ['home', 'draw', 'away']
            class_mapping = {0: 'home', 1: 'draw', 2: 'away'}
            print(f"📋 Class mapping: {class_mapping}")
            
        except Exception as e:
            raise Exception(f"❌ Prediction failed: {e}")
        
        # Create predictions dataframe
        pred_df = self.holdout_df[['home_team', 'away_team', 'season', 
                                  'result', 'home_win_odds', 'draw_odds', 'away_win_odds']].copy()
        
        # Add prediction probabilities using text labels
        for i, class_label in enumerate(text_classes):
            pred_df[f'prob_{class_label}'] = prediction_probs[:, i]
        
        # Determine recommended bet
        pred_df['max_prob'] = prediction_probs.max(axis=1)
        
        # Convert numeric predictions to text labels
        numeric_predictions = [np.argmax(row) for row in prediction_probs]
        pred_df['predicted_outcome'] = [class_mapping[pred] for pred in numeric_predictions]
        
        # Get odds for predicted outcome
        predicted_odds = []
        for i, pred_outcome in enumerate(pred_df['predicted_outcome']):
            if pred_outcome == 'home':
                predicted_odds.append(pred_df.iloc[i]['home_win_odds'])
            elif pred_outcome == 'draw':
                predicted_odds.append(pred_df.iloc[i]['draw_odds'])
            else:  # away
                predicted_odds.append(pred_df.iloc[i]['away_win_odds'])
        
        pred_df['predicted_odds'] = predicted_odds
        
        # Determine correct predictions
        pred_df['correct'] = (pred_df['predicted_outcome'] == pred_df['result']).astype(int)
        
        # Apply confidence and odds filters
        confidence_mask = pred_df['max_prob'] >= self.confidence_threshold
        odds_mask = pred_df['predicted_odds'] >= self.odds_threshold
        
        pred_df['meets_confidence'] = confidence_mask
        pred_df['meets_odds'] = odds_mask
        pred_df['recommended'] = confidence_mask & odds_mask
        
        # Statistics
        total_predictions = len(pred_df)
        high_confidence = confidence_mask.sum()
        good_odds = odds_mask.sum()
        final_recommendations = pred_df['recommended'].sum()
        
        print(f"📊 Prediction Statistics:")
        print(f"   Total predictions: {total_predictions}")
        print(f"   High confidence (≥{self.confidence_threshold*100}%): {high_confidence} ({high_confidence/total_predictions*100:.1f}%)")
        print(f"   Good odds (≥{self.odds_threshold}): {good_odds} ({good_odds/total_predictions*100:.1f}%)")
        print(f"   Final recommendations: {final_recommendations} ({final_recommendations/total_predictions*100:.1f}%)")
        
        # Save predictions
        predictions_filename = "serie_a_holdout_predictions.csv"
        pred_df.to_csv(predictions_filename, index=False)
        print(f"💾 Predictions saved: {predictions_filename}")
        
        self.predictions_df = pred_df
        return pred_df
    
    def simulate_paper_trading(self):
        """Simulate paper trading using recommended bets"""
        print("\n💰 Simulating Paper Trading...")
        
        if not hasattr(self, 'predictions_df'):
            raise Exception("❌ Predictions not generated. Run generate_predictions() first.")
        
        # Filter to recommended bets only
        betting_df = self.predictions_df[self.predictions_df['recommended']].copy()
        
        if len(betting_df) == 0:
            print("❌ No recommended bets found!")
            return None
        
        print(f"🎯 Simulating {len(betting_df)} recommended bets...")
        
        # Initialize trading simulation
        current_bankroll = self.bankroll
        transactions = []
        
        for idx, bet in betting_df.iterrows():
            # Calculate profit/loss
            if bet['correct']:
                profit = self.base_stake * bet['predicted_odds'] - self.base_stake
                result_text = "WIN"
            else:
                profit = -self.base_stake
                result_text = "LOSS"
            
            current_bankroll += profit
            
            # Record transaction
            transaction = {
                'bet_id': len(transactions) + 1,
                'home_team': bet['home_team'],
                'away_team': bet['away_team'],
                'season': bet['season'],
                'predicted_outcome': bet['predicted_outcome'],
                'actual_result': bet['result'],
                'confidence': bet['max_prob'],
                'predicted_odds': bet['predicted_odds'],
                'stake': self.base_stake,
                'profit': profit,
                'result': result_text,
                'bankroll': current_bankroll
            }
            transactions.append(transaction)
        
        # Create transactions dataframe
        transactions_df = pd.DataFrame(transactions)
        
        # Calculate summary statistics
        total_bets = len(transactions_df)
        wins = len(transactions_df[transactions_df['result'] == 'WIN'])
        losses = len(transactions_df[transactions_df['result'] == 'LOSS'])
        hit_rate = wins / total_bets if total_bets > 0 else 0
        
        total_staked = total_bets * self.base_stake
        total_profit = transactions_df['profit'].sum()
        roi = total_profit / total_staked if total_staked > 0 else 0
        final_bankroll = current_bankroll
        bankroll_roi = (final_bankroll - self.bankroll) / self.bankroll
        
        avg_confidence = betting_df['max_prob'].mean()
        avg_odds = betting_df['predicted_odds'].mean()
        
        # Save transactions
        transactions_filename = "serie_a_holdout_transactions.csv"
        transactions_df.to_csv(transactions_filename, index=False)
        print(f"💾 Transactions saved: {transactions_filename}")
        
        # Summary
        summary = {
            'total_bets': total_bets,
            'wins': wins,
            'losses': losses,
            'hit_rate': hit_rate,
            'total_profit': total_profit,
            'total_staked': total_staked,
            'roi': roi,
            'starting_bankroll': self.bankroll,
            'final_bankroll': final_bankroll,
            'bankroll_roi': bankroll_roi,
            'avg_confidence': avg_confidence,
            'avg_odds': avg_odds
        }
        
        # Save summary
        summary_filename = "serie_a_holdout_summary.csv"
        summary_df = pd.DataFrame([summary])
        summary_df.to_csv(summary_filename, index=False)
        print(f"💾 Summary saved: {summary_filename}")
        
        # Display results
        print(f"\n🏆 PAPER TRADING RESULTS:")
        print(f"   Total Bets: {total_bets}")
        print(f"   Wins: {wins} | Losses: {losses}")
        print(f"   Hit Rate: {hit_rate:.3f} ({hit_rate*100:.1f}%)")
        print(f"   Total Profit: €{total_profit:.2f}")
        print(f"   ROI: {roi:.3f} ({roi*100:.1f}%)")
        print(f"   Final Bankroll: €{final_bankroll:.2f}")
        print(f"   Bankroll ROI: {bankroll_roi:.3f} ({bankroll_roi*100:.1f}%)")
        
        self.trading_summary = summary
        return summary
    
    def validate_model(self):
        """Final model validation assessment"""
        print("\n🎯 Model Validation Assessment...")
        
        if not hasattr(self, 'trading_summary'):
            print("❌ No trading summary available!")
            return False
        
        summary = self.trading_summary
        
        # Validation criteria (IDENTICAL to La Liga and Premier League)
        roi_threshold = 0.0      # ROI must be > 0%
        hit_rate_threshold = 0.55  # Hit rate must be > 55%
        min_bets = self.min_bets_required  # At least 5 bets
        
        # Check criteria
        roi_pass = summary['roi'] > roi_threshold
        hit_rate_pass = summary['hit_rate'] > hit_rate_threshold
        volume_pass = summary['total_bets'] >= min_bets
        
        validation_passed = roi_pass and hit_rate_pass and volume_pass
        
        print(f"\n📋 Validation Criteria:")
        print(f"   ROI > {roi_threshold*100}%: {'✅ PASS' if roi_pass else '❌ FAIL'} ({summary['roi']*100:.1f}%)")
        print(f"   Hit Rate > {hit_rate_threshold*100}%: {'✅ PASS' if hit_rate_pass else '❌ FAIL'} ({summary['hit_rate']*100:.1f}%)")
        print(f"   Min Bets ≥ {min_bets}: {'✅ PASS' if volume_pass else '❌ FAIL'} ({summary['total_bets']} bets)")
        
        print(f"\n🏆 FINAL VALIDATION: {'✅ MODEL VALIDATED' if validation_passed else '❌ MODEL FAILED'}")
        
        # Create validation status file
        status = {
            'model_name': 'Serie A 1X2 Predictor',
            'validation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'holdout_matches': len(self.holdout_df),
            'total_bets': summary['total_bets'],
            'hit_rate': summary['hit_rate'],
            'roi': summary['roi'],
            'final_bankroll': summary['final_bankroll'],
            'roi_pass': roi_pass,
            'hit_rate_pass': hit_rate_pass,
            'volume_pass': volume_pass,
            'validation_passed': validation_passed,
            'model_status': 'VALIDATED' if validation_passed else 'FAILED'
        }
        
        # Save validation status
        status_filename = "serie_a_model_validation_status.txt"
        with open(status_filename, 'w') as f:
            f.write("SERIE A MODEL VALIDATION STATUS\n")
            f.write("=" * 50 + "\n\n")
            for key, value in status.items():
                f.write(f"{key.upper()}: {value}\n")
        
        print(f"💾 Validation status saved: {status_filename}")
        
        self.validation_status = status
        return validation_passed
    
    def run_complete_validation(self):
        """Execute complete holdout validation pipeline"""
        print("🚀 Starting Serie A Model Holdout Validation...")
        print("=" * 60)
        
        try:
            # Load assets
            self.load_model_and_data()
            
            # Create holdout split
            self.create_holdout_split()
            
            # Generate predictions
            self.generate_predictions()
            
            # Simulate trading
            self.simulate_paper_trading()
            
            # Validate model
            validation_passed = self.validate_model()
            
            print("\n" + "=" * 60)
            if validation_passed:
                print("🎉 SERIE A MODEL VALIDATION COMPLETED SUCCESSFULLY!")
                print("✅ Model is ready for production deployment")
            else:
                print("⚠️  SERIE A MODEL VALIDATION FAILED")
                print("❌ Model needs review before production use")
            
            return validation_passed
            
        except Exception as e:
            print(f"\n❌ Validation failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Main execution function"""
    print("🇮🇹 SERIE A MODEL HOLDOUT VALIDATION")
    print("Following identical methodology to La Liga and Premier League for fair comparison")
    print("=" * 70)
    
    validator = SerieAHoldoutValidator()
    success = validator.run_complete_validation()
    
    if success:
        print("\n🎯 Ready for production comparison with La Liga and Premier League models!")
    else:
        print("\n⚠️  Model requires further development")
    
    return success

if __name__ == "__main__":
    main() 