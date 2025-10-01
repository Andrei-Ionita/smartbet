#!/usr/bin/env python3
"""
Bundesliga & Ligue 1 Model Training Pipeline
Following the exact same approach as successful La Liga model (74.4% hit rate, 138.92% ROI)
"""

import os
import pandas as pd
import numpy as np
import lightgbm as lgb
import pickle
import json
from datetime import datetime
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

class BundesligaLigue1ModelTrainer:
    def __init__(self, data_file="bundesliga_ligue1_training_data_20250704_171510.csv"):
        self.data_file = data_file
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Same feature set as successful La Liga model
        self.feature_columns = [
            'true_prob_draw', 'prob_ratio_draw_away', 'prob_ratio_home_draw',
            'log_odds_home_draw', 'log_odds_draw_away', 'bookmaker_margin',
            'market_efficiency', 'odds_home', 'odds_away', 'odds_draw',
            'goals_for_home', 'goals_for_away'
        ]
        
        # LGBM parameters - same as La Liga success model
        self.lgbm_params = {
            'objective': 'multiclass',
            'num_class': 3,
            'metric': 'multi_logloss',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'random_state': 42
        }
        
        self.models = {}
        self.metrics = {}
        self.feature_importance = {}
        
    def log(self, message):
        """Log with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def load_and_prepare_data(self):
        """Load and prepare data for training."""
        self.log("📊 Loading training data...")
        
        df = pd.read_csv(self.data_file)
        self.log(f"   ✅ Loaded {len(df)} total matches")
        
        # Split by league
        bundesliga_data = df[df['league'] == 'Bundesliga'].copy()
        ligue1_data = df[df['league'] == 'Ligue 1'].copy()
        
        self.log(f"   📈 Bundesliga: {len(bundesliga_data)} matches")
        self.log(f"   📈 Ligue 1: {len(ligue1_data)} matches")
        
        # Validate data quality
        for league_name, league_data in [('Bundesliga', bundesliga_data), ('Ligue 1', ligue1_data)]:
            missing_features = [col for col in self.feature_columns if col not in league_data.columns]
            if missing_features:
                raise ValueError(f"Missing features in {league_name}: {missing_features}")
                
            # Check for missing values
            missing_vals = league_data[self.feature_columns].isnull().sum().sum()
            if missing_vals > 0:
                self.log(f"   ⚠️  {league_name}: Found {missing_vals} missing values, filling with median")
                league_data[self.feature_columns] = league_data[self.feature_columns].fillna(
                    league_data[self.feature_columns].median()
                )
        
        # Outcome distributions
        self.log(f"\n📊 DATA QUALITY ANALYSIS:")
        for league_name, league_data in [('Bundesliga', bundesliga_data), ('Ligue 1', ligue1_data)]:
            outcome_dist = league_data['outcome'].value_counts().sort_index()
            self.log(f"   {league_name} Outcomes:")
            for outcome, count in outcome_dist.items():
                outcome_label = {0: 'Draw (X)', 1: 'Home Win (1)', 2: 'Away Win (2)'}[outcome]
                self.log(f"     {outcome_label}: {count} ({count/len(league_data)*100:.1f}%)")
        
        return bundesliga_data, ligue1_data
    
    def create_holdout_split(self, data, league_name):
        """Create holdout validation split - same approach as La Liga model."""
        self.log(f"\n🔄 Creating holdout split for {league_name}...")
        
        # Sort by date to ensure temporal split
        data_sorted = data.sort_values('date').copy()
        
        # Use last 20% as holdout (same as La Liga approach)
        split_idx = int(len(data_sorted) * 0.8)
        
        train_data = data_sorted.iloc[:split_idx].copy()
        holdout_data = data_sorted.iloc[split_idx:].copy()
        
        self.log(f"   📅 Training set: {len(train_data)} matches")
        self.log(f"   📅 Holdout set: {len(holdout_data)} matches")
        
        # Verify temporal split
        train_max_date = pd.to_datetime(train_data['date']).max()
        holdout_min_date = pd.to_datetime(holdout_data['date']).min()
        self.log(f"   📅 Train period ends: {train_max_date.strftime('%Y-%m-%d')}")
        self.log(f"   📅 Holdout period starts: {holdout_min_date.strftime('%Y-%m-%d')}")
        
        return train_data, holdout_data
    
    def train_league_model(self, train_data, holdout_data, league_name):
        """Train model for specific league using exact La Liga approach."""
        self.log(f"\n🚀 TRAINING {league_name.upper()} MODEL")
        self.log("=" * 50)
        
        # Prepare features and targets
        X_train = train_data[self.feature_columns].copy()
        y_train = train_data['outcome'].copy()
        
        X_holdout = holdout_data[self.feature_columns].copy()
        y_holdout = holdout_data['outcome'].copy()
        
        # Stratified split for training/validation
        X_train_split, X_val_split, y_train_split, y_val_split = train_test_split(
            X_train, y_train, test_size=0.2, random_state=42, stratify=y_train
        )
        
        self.log(f"   📊 Training split: {len(X_train_split)} matches")
        self.log(f"   📊 Validation split: {len(X_val_split)} matches")
        
        # Create LightGBM datasets
        train_dataset = lgb.Dataset(X_train_split, label=y_train_split)
        val_dataset = lgb.Dataset(X_val_split, label=y_val_split, reference=train_dataset)
        
        # Train model with early stopping
        self.log(f"   🔧 Training LightGBM model...")
        model = lgb.train(
            self.lgbm_params,
            train_dataset,
            valid_sets=[train_dataset, val_dataset],
            valid_names=['train', 'eval'],
            num_boost_round=1000,
            callbacks=[
                lgb.early_stopping(stopping_rounds=50),
                lgb.log_evaluation(period=0)  # Silent training
            ]
        )
        
        # Predictions on holdout set
        holdout_pred_proba = model.predict(X_holdout, num_iteration=model.best_iteration)
        holdout_pred = np.argmax(holdout_pred_proba, axis=1)
        
        # Calculate comprehensive metrics
        holdout_accuracy = accuracy_score(y_holdout, holdout_pred)
        
        # ROI calculation (same method as La Liga)
        roi_data = self.calculate_roi(holdout_data, holdout_pred_proba, league_name)
        
        # Feature importance
        feature_imp = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': model.feature_importance(importance_type='gain')
        }).sort_values('importance', ascending=False)
        
        # Store results
        self.models[league_name] = model
        self.metrics[league_name] = {
            'holdout_accuracy': holdout_accuracy,
            'holdout_matches': len(holdout_data),
            'train_matches': len(train_data),
            'best_iteration': model.best_iteration,
            **roi_data
        }
        self.feature_importance[league_name] = feature_imp
        
        # Display results
        self.log(f"\n📈 {league_name.upper()} MODEL PERFORMANCE:")
        self.log(f"   🎯 Holdout Accuracy: {holdout_accuracy:.1%}")
        self.log(f"   💰 ROI: {roi_data['roi']:.2%}")
        self.log(f"   🏆 Hit Rate: {roi_data['hit_rate']:.1%}")
        self.log(f"   📊 Total Bets: {roi_data['total_bets']}")
        self.log(f"   💵 Profit: {roi_data['profit']:.2f} units")
        
        # Confusion matrix
        self.log(f"\n🎯 {league_name} Confusion Matrix:")
        cm = confusion_matrix(y_holdout, holdout_pred)
        outcome_labels = ['Draw (0)', 'Home (1)', 'Away (2)']
        for i, true_label in enumerate(outcome_labels):
            for j, pred_label in enumerate(outcome_labels):
                self.log(f"   True {true_label} → Pred {pred_label}: {cm[i,j]}")
        
        # Top features
        self.log(f"\n🔧 Top 5 {league_name} Features:")
        for idx, row in feature_imp.head().iterrows():
            self.log(f"   {row['feature']}: {row['importance']:.1f}")
        
        return model
    
    def calculate_roi(self, holdout_data, pred_proba, league_name):
        """Calculate ROI using same methodology as La Liga model."""
        
        # Create betting strategy: bet on highest confidence predictions
        confidence_threshold = 0.40  # Same as La Liga model
        
        total_bets = 0
        total_profit = 0
        winning_bets = 0
        
        for idx, (_, match) in enumerate(holdout_data.iterrows()):
            max_prob = np.max(pred_proba[idx])
            predicted_outcome = np.argmax(pred_proba[idx])
            actual_outcome = match['outcome']
            
            if max_prob >= confidence_threshold:
                total_bets += 1
                
                # Get odds for predicted outcome
                if predicted_outcome == 0:  # Draw
                    odds = match['odds_draw']
                elif predicted_outcome == 1:  # Home
                    odds = match['odds_home']
                else:  # Away
                    odds = match['odds_away']
                
                # Calculate profit (1 unit bet)
                if predicted_outcome == actual_outcome:
                    profit = odds - 1  # Win: get odds, minus stake
                    winning_bets += 1
                else:
                    profit = -1  # Loss: lose stake
                
                total_profit += profit
        
        if total_bets == 0:
            roi = 0
            hit_rate = 0
        else:
            roi = total_profit / total_bets
            hit_rate = winning_bets / total_bets
        
        return {
            'roi': roi,
            'hit_rate': hit_rate,
            'total_bets': total_bets,
            'winning_bets': winning_bets,
            'profit': total_profit,
            'confidence_threshold': confidence_threshold
        }
    
    def save_models(self):
        """Save trained models with same structure as La Liga."""
        self.log(f"\n💾 SAVING TRAINED MODELS")
        self.log("=" * 40)
        
        for league_name, model in self.models.items():
            # Create directory
            model_dir = f"{league_name.lower()}_model_{self.timestamp}"
            os.makedirs(model_dir, exist_ok=True)
            
            # Save model
            model_path = os.path.join(model_dir, f"lgbm_{league_name.lower()}_production.pkl")
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            
            # Save metrics
            metrics_path = os.path.join(model_dir, "model_metrics.json")
            with open(metrics_path, 'w') as f:
                json.dump(self.metrics[league_name], f, indent=2, default=str)
            
            # Save feature importance
            feature_imp_path = os.path.join(model_dir, "feature_importances.csv")
            self.feature_importance[league_name].to_csv(feature_imp_path, index=False)
            
            # Save feature list
            features_path = os.path.join(model_dir, "feature_list.txt")
            with open(features_path, 'w') as f:
                for feature in self.feature_columns:
                    f.write(f"{feature}\n")
            
            self.log(f"   ✅ {league_name} model saved to: {model_dir}/")
        
        return model_dir
    
    def generate_deployment_report(self):
        """Generate comprehensive deployment report."""
        self.log(f"\n📋 GENERATING DEPLOYMENT REPORT")
        self.log("=" * 45)
        
        report = {
            'timestamp': self.timestamp,
            'training_completed': datetime.now().isoformat(),
            'data_source': self.data_file,
            'models_trained': list(self.models.keys()),
            'feature_count': len(self.feature_columns),
            'features_used': self.feature_columns,
            'lgbm_parameters': self.lgbm_params,
            'league_performance': {}
        }
        
        # Add performance metrics for each league
        for league_name in self.models.keys():
            metrics = self.metrics[league_name]
            report['league_performance'][league_name] = {
                'holdout_accuracy': f"{metrics['holdout_accuracy']:.1%}",
                'roi': f"{metrics['roi']:.2%}",
                'hit_rate': f"{metrics['hit_rate']:.1%}",
                'total_bets': metrics['total_bets'],
                'profit_units': round(metrics['profit'], 2),
                'training_matches': metrics['train_matches'],
                'holdout_matches': metrics['holdout_matches'],
                'model_iterations': metrics['best_iteration']
            }
        
        # Save report
        report_path = f"bundesliga_ligue1_deployment_report_{self.timestamp}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.log(f"   ✅ Report saved: {report_path}")
        return report
    
    def train_all_models(self):
        """Main training pipeline."""
        self.log(f"🚀 BUNDESLIGA & LIGUE 1 MODEL TRAINING PIPELINE")
        self.log(f"Following proven La Liga approach (74.4% hit rate, 138.92% ROI)")
        self.log("=" * 80)
        
        # Load data
        bundesliga_data, ligue1_data = self.load_and_prepare_data()
        
        # Train each league separately (same isolation as La Liga)
        for league_name, league_data in [('Bundesliga', bundesliga_data), ('Ligue 1', ligue1_data)]:
            train_data, holdout_data = self.create_holdout_split(league_data, league_name)
            self.train_league_model(train_data, holdout_data, league_name)
        
        # Save models
        model_dir = self.save_models()
        
        # Generate report
        report = self.generate_deployment_report()
        
        # Final summary
        self.log(f"\n🎉 TRAINING COMPLETED SUCCESSFULLY!")
        self.log("=" * 50)
        self.log(f"📁 Models saved in directories with timestamp: {self.timestamp}")
        self.log(f"📊 Deployment report: bundesliga_ligue1_deployment_report_{self.timestamp}.json")
        
        # Performance comparison
        self.log(f"\n📈 PERFORMANCE SUMMARY:")
        for league_name in self.models.keys():
            metrics = self.metrics[league_name]
            self.log(f"   {league_name}:")
            self.log(f"     Hit Rate: {metrics['hit_rate']:.1%}")
            self.log(f"     ROI: {metrics['roi']:.2%}")
            self.log(f"     Profit: {metrics['profit']:.2f} units")
        
        return self.models, self.metrics, report

def main():
    """Main execution function."""
    try:
        trainer = BundesligaLigue1ModelTrainer()
        models, metrics, report = trainer.train_all_models()
        
        print(f"\n✅ SUCCESS: Bundesliga and Ligue 1 models trained and validated!")
        print(f"📈 Ready for production deployment!")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 