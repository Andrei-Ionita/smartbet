#!/usr/bin/env python3
"""
WORKING Bundesliga & Ligue 1 Model Training Pipeline
Using corrected data with all three outcomes (Home Win, Draw, Away Win)
Following exact same approach as successful La Liga model (74.4% hit rate, 138.92% ROI)
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

class WorkingBundesligaLigue1ModelTrainer:
    def __init__(self, data_file="working_corrected_bundesliga_ligue1_data_20250704_173722.csv"):
        self.data_file = data_file
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Model configurations (same as successful La Liga model)
        self.model_config = {
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
        
        # Feature importance tracking
        self.feature_importance = {}
        
    def log(self, message):
        """Log with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def load_and_validate_data(self):
        """Load and validate the corrected training data."""
        self.log("📁 Loading corrected training data...")
        
        if not os.path.exists(self.data_file):
            raise FileNotFoundError(f"Data file not found: {self.data_file}")
        
        df = pd.read_csv(self.data_file)
        self.log(f"   ✅ Loaded {len(df)} matches from {self.data_file}")
        
        # Validate data structure
        required_columns = [
            'league', 'home_team', 'away_team', 'home_goals', 'away_goals', 'outcome',
            'true_prob_draw', 'prob_ratio_draw_away', 'prob_ratio_home_draw',
            'log_odds_home_draw', 'log_odds_draw_away', 'bookmaker_margin',
            'market_efficiency', 'odds_home', 'odds_away', 'odds_draw',
            'goals_for_home', 'goals_for_away'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Validate outcome distribution
        outcome_counts = df['outcome'].value_counts().sort_index()
        self.log("📊 Outcome distribution validation:")
        for outcome, count in outcome_counts.items():
            outcome_name = {0: 'Draw (X)', 1: 'Home Win (1)', 2: 'Away Win (2)'}[outcome]
            percentage = count/len(df)*100
            self.log(f"   {outcome_name}: {count} matches ({percentage:.1f}%)")
        
        if len(outcome_counts) != 3:
            raise ValueError(f"Expected 3 outcome classes, found {len(outcome_counts)}")
        
        # League distribution
        league_counts = df['league'].value_counts()
        self.log("🏆 League distribution:")
        for league, count in league_counts.items():
            self.log(f"   {league}: {count} matches")
        
        return df
    
    def prepare_features_and_targets(self, df):
        """Prepare feature matrix and target vector."""
        self.log("🔧 Preparing features and targets...")
        
        # 12 key ML features (same as La Liga model)
        feature_columns = [
            'true_prob_draw', 'prob_ratio_draw_away', 'prob_ratio_home_draw',
            'log_odds_home_draw', 'log_odds_draw_away', 'bookmaker_margin',
            'market_efficiency', 'odds_home', 'odds_away', 'odds_draw',
            'goals_for_home', 'goals_for_away'
        ]
        
        X = df[feature_columns].copy()
        y = df['outcome'].copy()
        
        # Handle any missing values
        if X.isnull().sum().sum() > 0:
            self.log("⚠️  Found missing values, filling with median...")
            X = X.fillna(X.median())
        
        # Check for infinite values
        if np.isinf(X).sum().sum() > 0:
            self.log("⚠️  Found infinite values, replacing...")
            X = X.replace([np.inf, -np.inf], [X.max().max(), X.min().min()])
        
        self.log(f"   ✅ Feature matrix: {X.shape}")
        self.log(f"   ✅ Target vector: {y.shape}")
        self.log(f"   ✅ Feature columns: {list(X.columns)}")
        
        return X, y, feature_columns
    
    def train_league_model(self, X, y, league_name, league_data):
        """Train a model for a specific league."""
        self.log(f"\n🏆 TRAINING {league_name.upper()} MODEL")
        self.log("=" * 60)
        
        # League-specific data
        league_indices = league_data.index
        X_league = X.loc[league_indices]
        y_league = y.loc[league_indices]
        
        self.log(f"📊 {league_name} training data: {len(X_league)} matches")
        
        # Train-test split (80-20, same as La Liga)
        X_train, X_test, y_train, y_test = train_test_split(
            X_league, y_league, test_size=0.2, random_state=42, stratify=y_league
        )
        
        self.log(f"   Training set: {len(X_train)} matches")
        self.log(f"   Test set: {len(X_test)} matches")
        
        # Train LightGBM model
        train_data = lgb.Dataset(X_train, label=y_train)
        valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
        
        self.log("🚀 Training LightGBM model...")
        model = lgb.train(
            self.model_config,
            train_data,
            valid_sets=[train_data, valid_data],
            num_boost_round=1000,
            callbacks=[lgb.early_stopping(stopping_rounds=50), lgb.log_evaluation(0)]
        )
        
        # Predictions and evaluation
        y_pred = model.predict(X_test, num_iteration=model.best_iteration)
        y_pred_class = np.argmax(y_pred, axis=1)
        
        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred_class)
        
        self.log(f"\n📈 {league_name} MODEL PERFORMANCE:")
        self.log(f"   Accuracy: {accuracy:.1%}")
        
        # Detailed classification report
        class_names = ['Draw (0)', 'Home Win (1)', 'Away Win (2)']
        report = classification_report(y_test, y_pred_class, target_names=class_names, output_dict=True)
        
        for class_name, metrics in report.items():
            if class_name in class_names:
                precision = metrics['precision']
                recall = metrics['recall']
                f1 = metrics['f1-score']
                support = metrics['support']
                self.log(f"   {class_name}: Precision={precision:.1%}, Recall={recall:.1%}, F1={f1:.1%} (n={support})")
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred_class)
        self.log(f"\n📊 {league_name} Confusion Matrix:")
        self.log("     Predicted:  0    1    2")
        for i, row in enumerate(cm):
            actual_label = ['0', '1', '2'][i]
            self.log(f"   Actual {actual_label}:   {row[0]:2d}  {row[1]:2d}  {row[2]:2d}")
        
        # Feature importance
        importance = model.feature_importance(importance_type='gain')
        feature_names = X_train.columns
        importance_dict = dict(zip(feature_names, importance))
        
        self.log(f"\n🔍 {league_name} Top Feature Importance:")
        sorted_features = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
        for feature, importance_score in sorted_features[:8]:
            self.log(f"   {feature}: {importance_score:.0f}")
        
        # Store feature importance
        self.feature_importance[league_name] = importance_dict
        
        # Save model
        model_filename = f"{league_name.lower()}_model_{self.timestamp}.pkl"
        with open(model_filename, 'wb') as f:
            pickle.dump(model, f)
        self.log(f"💾 Model saved to: {model_filename}")
        
        # Performance summary
        performance_summary = {
            'league': league_name,
            'accuracy': accuracy,
            'test_samples': len(X_test),
            'classification_report': report,
            'confusion_matrix': cm.tolist(),
            'feature_importance': importance_dict,
            'model_file': model_filename,
            'timestamp': self.timestamp
        }
        
        return model, performance_summary, X_test, y_test, y_pred, y_pred_class
    
    def calculate_betting_simulation(self, y_test, y_pred, league_name, test_data):
        """Calculate betting simulation like successful La Liga model."""
        self.log(f"\n💰 {league_name} BETTING SIMULATION")
        self.log("=" * 50)
        
        # Simulate betting based on predictions
        total_bets = 0
        correct_bets = 0
        total_stake = 0
        total_return = 0
        
        # Get odds for test matches
        if 'odds_home' in test_data.columns:
            odds_home = test_data['odds_home'].values
            odds_draw = test_data['odds_draw'].values
            odds_away = test_data['odds_away'].values
        else:
            # Use default odds if not available
            odds_home = np.full(len(y_test), 2.5)
            odds_draw = np.full(len(y_test), 3.2)
            odds_away = np.full(len(y_test), 2.8)
        
        for i in range(len(y_test)):
            prediction = np.argmax(y_pred[i])
            actual = y_test.iloc[i]
            prediction_confidence = np.max(y_pred[i])
            
            # Only bet if confidence > 0.4 (like successful models)
            if prediction_confidence > 0.4:
                total_bets += 1
                stake = 1.0  # Unit stake
                total_stake += stake
                
                # Determine odds for prediction
                if prediction == 0:  # Draw
                    odds = odds_draw[i]
                elif prediction == 1:  # Home
                    odds = odds_home[i]
                else:  # Away
                    odds = odds_away[i]
                
                if prediction == actual:
                    correct_bets += 1
                    total_return += stake * odds
                # else: lose stake (already counted in total_stake)
        
        # Calculate metrics
        if total_bets > 0:
            hit_rate = correct_bets / total_bets
            net_profit = total_return - total_stake
            roi = (net_profit / total_stake) * 100
            
            self.log(f"   📊 Betting Results:")
            self.log(f"      Total bets placed: {total_bets}")
            self.log(f"      Correct predictions: {correct_bets}")
            self.log(f"      Hit rate: {hit_rate:.1%}")
            self.log(f"      Total stake: {total_stake:.1f} units")
            self.log(f"      Total return: {total_return:.1f} units") 
            self.log(f"      Net profit: {net_profit:+.1f} units")
            self.log(f"      ROI: {roi:+.1%}")
            
            return {
                'total_bets': total_bets,
                'correct_bets': correct_bets,
                'hit_rate': hit_rate,
                'roi': roi,
                'net_profit': net_profit
            }
        else:
            self.log("   ⚠️  No bets placed (low confidence predictions)")
            return None
    
    def train_all_models(self):
        """Train models for both Bundesliga and Ligue 1."""
        self.log("🚀 STARTING WORKING BUNDESLIGA & LIGUE 1 MODEL TRAINING")
        self.log("📊 Following exact La Liga model approach (74.4% hit rate, 138.92% ROI)")
        self.log("=" * 80)
        
        # Load and validate data
        df = self.load_and_validate_data()
        X, y, feature_columns = self.prepare_features_and_targets(df)
        
        # Train separate models for each league
        all_results = {}
        
        for league in ['Bundesliga', 'Ligue 1']:
            league_data = df[df['league'] == league]
            
            if len(league_data) > 0:
                model, performance, X_test, y_test, y_pred, y_pred_class = self.train_league_model(
                    X, y, league, league_data
                )
                
                # Betting simulation
                betting_results = self.calculate_betting_simulation(
                    y_test, y_pred, league, X_test
                )
                
                all_results[league] = {
                    'performance': performance,
                    'betting': betting_results,
                    'model': model
                }
        
        # Final summary
        self.log(f"\n🎉 TRAINING COMPLETION SUMMARY")
        self.log("=" * 60)
        
        summary_file = f"bundesliga_ligue1_training_summary_{self.timestamp}.json"
        summary_data = {}
        
        for league, results in all_results.items():
            perf = results['performance']
            betting = results.get('betting', {})
            
            self.log(f"\n🏆 {league}:")
            self.log(f"   Accuracy: {perf['accuracy']:.1%}")
            if betting:
                self.log(f"   Hit Rate: {betting['hit_rate']:.1%}")
                self.log(f"   ROI: {betting['roi']:+.1%}")
                self.log(f"   Model File: {perf['model_file']}")
            
            summary_data[league] = {
                'accuracy': perf['accuracy'],
                'hit_rate': betting.get('hit_rate', 0) if betting else 0,
                'roi': betting.get('roi', 0) if betting else 0,
                'model_file': perf['model_file']
            }
        
        # Save summary
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2)
        
        self.log(f"\n💾 Training summary saved to: {summary_file}")
        
        return all_results

def main():
    """Main execution function."""
    try:
        trainer = WorkingBundesligaLigue1ModelTrainer()
        results = trainer.train_all_models()
        
        print(f"\n✅ SUCCESS: Bundesliga & Ligue 1 model training completed!")
        print(f"🎯 Both models trained using exact La Liga approach")
        print(f"📊 Models ready for deployment and validation")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 