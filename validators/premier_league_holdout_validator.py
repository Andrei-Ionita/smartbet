#!/usr/bin/env python3
"""
Premier League Model Holdout Validation Pipeline
Comprehensive paper trading evaluation using locked production model
Following identical methodology to La Liga validation for fair comparison
"""

import pandas as pd
import numpy as np
import pickle
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class PremierLeagueHoldoutValidator:
    """Validates Premier League model using holdout data with paper trading simulation"""
    
    def __init__(self):
        """Initialize validator with Premier League model configuration"""
        self.model_path = "LOCKED_PRODUCTION_premier_league_model_20250611_103326.pkl"
        self.dataset_path = "LOCKED_PRODUCTION_premier_league_training_dataset_20250611_103326.csv"
        self.feature_importance_path = "LOCKED_PRODUCTION_premier_league_feature_importance_20250611_103326.csv"
        
        # Trading parameters (IDENTICAL to La Liga for fair comparison)
        self.confidence_threshold = 0.6  # Must be ≥60% confident
        self.odds_threshold = 1.5        # Minimum odds for betting
        self.base_stake = 10.0          # €10 per bet
        self.bankroll = 1000.0          # €1000 starting bankroll
        
        # Validation parameters
        self.holdout_percentage = 0.2   # 20% most recent data
        self.min_bets_required = 5      # Minimum bets for valid test
        
        print("🏴󐁧󐁢󐁥󐁮󐁧󐁿 Premier League Model Holdout Validator Initialized")
        print(f"📊 Model: {self.model_path}")
        print(f"📈 Confidence Threshold: {self.confidence_threshold*100}%")
        print(f"💰 Odds Threshold: {self.odds_threshold}")
        print(f"🎯 Base Stake: €{self.base_stake}")
        
    def load_model_and_data(self):
        """Load production model and dataset"""
        print("\n📂 Loading Premier League Production Assets...")
        
        # Load model
        try:
            with open(self.model_path, 'rb') as f:
                model_dict = pickle.load(f)
                
            # Extract actual model from dictionary structure
            if isinstance(model_dict, dict) and 'model' in model_dict:
                self.model = model_dict['model']
                self.model_info = model_dict
                print(f"✅ Model loaded from dict: {type(self.model).__name__}")
                print(f"📋 Model version: {model_dict.get('version', 'unknown')}")
                print(f"🏆 Model classes: {model_dict.get('classes', 'unknown')}")
            else:
                self.model = model_dict
                self.model_info = None
                print(f"✅ Model loaded directly: {type(self.model).__name__}")
                
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
            
            # Use features from model dictionary if available (more reliable)
            if self.model_info and 'feature_columns' in self.model_info:
                expected_features = self.model_info['feature_columns']
                print(f"✅ Features from model dict: {len(expected_features)} features")
            else:
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
        
        # Convert kickoff_time to datetime
        self.df['kickoff_time'] = pd.to_datetime(self.df['kickoff_time'])
        
        # Sort by date to ensure proper chronological split
        self.df = self.df.sort_values('kickoff_time').reset_index(drop=True)
        
        # Calculate split point (most recent 20%)
        total_matches = len(self.df)
        holdout_size = int(total_matches * self.holdout_percentage)
        split_point = total_matches - holdout_size
        
        # Create splits
        self.train_df = self.df.iloc[:split_point].copy()
        self.holdout_df = self.df.iloc[split_point:].copy()
        
        print(f"📊 Training Set: {len(self.train_df)} matches")
        print(f"🎯 Holdout Set: {len(self.holdout_df)} matches")
        print(f"📅 Holdout Date Range: {self.holdout_df['kickoff_time'].min()} to {self.holdout_df['kickoff_time'].max()}")
        
        # Save holdout for reference
        holdout_filename = "premier_league_holdout_test_set.csv"
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
        
        # Handle categorical variables if label encoder is available
        if self.model_info and 'label_encoder' in self.model_info:
            label_encoder = self.model_info['label_encoder']
            print(f"🔧 Applying label encoding for categorical variables...")
            
            # Check for object columns that need encoding
            object_columns = X_holdout.select_dtypes(include=['object']).columns
            if len(object_columns) > 0:
                print(f"📋 Object columns found: {list(object_columns)}")
                
                for col in object_columns:
                    # For bookmaker column, which only has one value, encode to 0
                    if col == 'bookmaker':
                        X_holdout[col] = 0  # Since all values are the same, encode as 0
                        print(f"✅ Encoded column {col} (single value) to 0")
                    else:
                        # For other categorical columns, try to encode or default to 0
                        try:
                            X_holdout[col] = label_encoder.transform(X_holdout[col])
                            print(f"✅ Encoded column: {col}")
                        except Exception as e:
                            print(f"⚠️  Could not encode {col}: {e}, setting to 0")
                            X_holdout[col] = 0
        
        # Ensure all columns are numeric
        X_holdout = X_holdout.select_dtypes(include=[np.number])
        print(f"📊 Final features shape: {X_holdout.shape}")
        
        # Generate predictions (probabilities for each class)
        try:
            prediction_probs = self.model.predict_proba(X_holdout)
            print(f"✅ Predictions generated: {prediction_probs.shape}")
            
            # Get class labels (numeric from model)
            numeric_classes = self.model.classes_
            
            # Get text class labels from model info
            if self.model_info and 'classes' in self.model_info:
                text_classes = self.model_info['classes']
                class_mapping = {numeric_classes[i]: text_classes[i] for i in range(len(numeric_classes))}
                print(f"📋 Class mapping: {class_mapping}")
            else:
                # Fallback mapping based on typical order
                class_mapping = {0: 'away', 1: 'draw', 2: 'home'}
                text_classes = ['away', 'draw', 'home']
                print(f"📋 Using fallback class mapping: {class_mapping}")
            
        except Exception as e:
            raise Exception(f"❌ Prediction failed: {e}")
        
        # Create predictions dataframe
        pred_df = self.holdout_df[['api_football_id', 'home_team', 'away_team', 'kickoff_time', 
                                  'final_result', 'odds_home', 'odds_draw', 'odds_away']].copy()
        
        # Add prediction probabilities using text labels
        for i, class_label in enumerate(text_classes):
            pred_df[f'prob_{class_label}'] = prediction_probs[:, i]
        
        # Determine recommended bet
        pred_df['max_prob'] = prediction_probs.max(axis=1)
        
        # Convert numeric predictions to text labels
        numeric_predictions = [numeric_classes[np.argmax(row)] for row in prediction_probs]
        pred_df['predicted_outcome'] = [class_mapping[pred] for pred in numeric_predictions]
        
        # Add confidence and recommendation
        pred_df['confidence'] = pred_df['max_prob']
        pred_df['meets_confidence'] = pred_df['confidence'] >= self.confidence_threshold
        
        # Get corresponding odds for predicted outcome
        pred_df['predicted_odds'] = pred_df.apply(
            lambda row: row[f'odds_{row["predicted_outcome"]}'], axis=1
        )
        pred_df['meets_odds_threshold'] = pred_df['predicted_odds'] >= self.odds_threshold
        
        # Final recommendation
        pred_df['recommend_bet'] = pred_df['meets_confidence'] & pred_df['meets_odds_threshold']
        pred_df['recommendation'] = pred_df['recommend_bet'].apply(
            lambda x: "BET" if x else "SKIP"
        )
        
        # Save predictions
        pred_filename = "premier_league_holdout_predictions.csv"
        pred_df.to_csv(pred_filename, index=False)
        print(f"💾 Predictions saved: {pred_filename}")
        
        self.predictions_df = pred_df
        
        # Summary statistics
        total_predictions = len(pred_df)
        recommended_bets = pred_df['recommend_bet'].sum()
        avg_confidence = pred_df['confidence'].mean()
        
        print(f"📊 Prediction Summary:")
        print(f"   Total Predictions: {total_predictions}")
        print(f"   Recommended Bets: {recommended_bets} ({recommended_bets/total_predictions*100:.1f}%)")
        print(f"   Average Confidence: {avg_confidence:.3f} ({avg_confidence*100:.1f}%)")
        print(f"   High Confidence (≥60%): {pred_df['meets_confidence'].sum()}")
        print(f"   Good Odds (≥1.5): {pred_df['meets_odds_threshold'].sum()}")
        
        return pred_df
    
    def simulate_paper_trading(self):
        """Simulate paper trading based on predictions"""
        print("\n💰 Simulating Paper Trading...")
        
        # Filter to recommended bets only
        bet_df = self.predictions_df[self.predictions_df['recommend_bet']].copy()
        
        if len(bet_df) == 0:
            print("❌ No bets recommended - cannot validate model!")
            return None
        
        print(f"🎯 Simulating {len(bet_df)} recommended bets...")
        
        # Initialize tracking variables
        current_bankroll = self.bankroll
        transactions = []
        
        for idx, row in bet_df.iterrows():
            # Determine if bet won
            actual_outcome = row['final_result']
            predicted_outcome = row['predicted_outcome']
            won_bet = (actual_outcome == predicted_outcome)
            
            # Calculate stake and potential return
            stake = self.base_stake
            odds = row['predicted_odds']
            
            if won_bet:
                profit = stake * (odds - 1)  # Profit = stake * (odds - 1)
                current_bankroll += profit
                result = "WIN"
            else:
                profit = -stake  # Loss = -stake
                current_bankroll += profit  # This will subtract the stake
                result = "LOSS"
            
            # Record transaction
            transaction = {
                'match_id': row['api_football_id'],
                'date': row['kickoff_time'],
                'home_team': row['home_team'],
                'away_team': row['away_team'],
                'predicted_outcome': predicted_outcome,
                'actual_outcome': actual_outcome,
                'confidence': row['confidence'],
                'odds': odds,
                'stake': stake,
                'result': result,
                'profit': profit,
                'bankroll': current_bankroll
            }
            transactions.append(transaction)
        
        # Convert to DataFrame
        self.transactions_df = pd.DataFrame(transactions)
        
        # Save transactions
        trans_filename = "premier_league_holdout_transactions.csv"
        self.transactions_df.to_csv(trans_filename, index=False)
        print(f"💾 Transactions saved: {trans_filename}")
        
        # Calculate metrics
        total_bets = len(self.transactions_df)
        wins = len(self.transactions_df[self.transactions_df['result'] == 'WIN'])
        losses = total_bets - wins
        hit_rate = wins / total_bets if total_bets > 0 else 0
        
        total_profit = self.transactions_df['profit'].sum()
        total_staked = total_bets * self.base_stake
        roi = (total_profit / total_staked) if total_staked > 0 else 0
        
        final_bankroll = current_bankroll
        bankroll_roi = ((final_bankroll - self.bankroll) / self.bankroll) if self.bankroll > 0 else 0
        
        # Trading summary
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
            'avg_confidence': bet_df['confidence'].mean(),
            'avg_odds': bet_df['predicted_odds'].mean()
        }
        
        self.trading_summary = summary
        
        # Save summary
        summary_df = pd.DataFrame([summary])
        summary_filename = "premier_league_holdout_summary.csv"
        summary_df.to_csv(summary_filename, index=False)
        print(f"💾 Summary saved: {summary_filename}")
        
        print(f"\n📊 Paper Trading Results:")
        print(f"   Total Bets: {total_bets}")
        print(f"   Wins: {wins} | Losses: {losses}")
        print(f"   Hit Rate: {hit_rate:.3f} ({hit_rate*100:.1f}%)")
        print(f"   Total Profit: €{total_profit:.2f}")
        print(f"   ROI: {roi:.3f} ({roi*100:.1f}%)")
        print(f"   Final Bankroll: €{final_bankroll:.2f}")
        print(f"   Bankroll ROI: {bankroll_roi:.3f} ({bankroll_roi*100:.1f}%)")
        
        return summary
    
    def validate_model(self):
        """Final model validation assessment"""
        print("\n🎯 Model Validation Assessment...")
        
        if not hasattr(self, 'trading_summary'):
            print("❌ No trading summary available!")
            return False
        
        summary = self.trading_summary
        
        # Validation criteria (IDENTICAL to La Liga)
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
            'model_name': 'Premier League 1X2 Predictor',
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
        status_filename = "premier_league_model_validation_status.txt"
        with open(status_filename, 'w') as f:
            f.write("PREMIER LEAGUE MODEL VALIDATION STATUS\n")
            f.write("=" * 50 + "\n\n")
            for key, value in status.items():
                f.write(f"{key.upper()}: {value}\n")
        
        print(f"💾 Validation status saved: {status_filename}")
        
        self.validation_status = status
        return validation_passed
    
    def run_complete_validation(self):
        """Execute complete holdout validation pipeline"""
        print("🚀 Starting Premier League Model Holdout Validation...")
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
                print("🎉 PREMIER LEAGUE MODEL VALIDATION COMPLETED SUCCESSFULLY!")
                print("✅ Model is ready for production deployment")
            else:
                print("⚠️  PREMIER LEAGUE MODEL VALIDATION FAILED")
                print("❌ Model needs review before production use")
            
            return validation_passed
            
        except Exception as e:
            print(f"\n❌ Validation failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Main execution function"""
    print("🏴󐁧󐁢󐁥󐁮󐁧󐁿 PREMIER LEAGUE MODEL HOLDOUT VALIDATION")
    print("Following identical methodology to La Liga for fair comparison")
    print("=" * 70)
    
    validator = PremierLeagueHoldoutValidator()
    success = validator.run_complete_validation()
    
    if success:
        print("\n🎯 Ready for production comparison with La Liga model!")
    else:
        print("\n⚠️  Model requires further development")
    
    return success

if __name__ == "__main__":
    main() 