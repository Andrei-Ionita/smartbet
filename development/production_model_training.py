"""
PRODUCTION MODEL TRAINING PIPELINE
=================================

Training production-ready betting models using clean, leak-free features
with proper time-series validation and comprehensive performance tracking.

Features:
- ✅ Uses only clean, pre-match features from feature_pipeline.py
- ⏰ Time-series split validation (no data leakage)
- 🤖 LightGBM + XGBoost classifiers
- 📊 Comprehensive performance metrics
- 💾 Model persistence with timestamps
- 📈 Performance tracking and reporting

Author: ML Engineering Team
Date: January 26, 2025
Version: 1.0 Production
"""

import pandas as pd
import numpy as np
from datetime import datetime
import lightgbm as lgb
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix
)
import joblib
import warnings
warnings.filterwarnings('ignore')

class ProductionModelTrainer:
    """
    Production-grade model training pipeline for football betting predictions.
    
    Features:
    - Time-series aware train/validation/test splits
    - Multiple classifier support (LightGBM, XGBoost)
    - Comprehensive performance tracking
    - Model persistence with versioning
    """
    
    def __init__(self, random_state=42):
        """Initialize the trainer with configuration."""
        self.random_state = random_state
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Model configurations
        self.lgb_params = {
            'objective': 'multiclass',
            'num_class': 3,
            'metric': 'multi_logloss',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'random_state': random_state,
            'force_row_wise': True
        }
        
        self.xgb_params = {
            'objective': 'multi:softprob',
            'num_class': 3,
            'eval_metric': 'mlogloss',
            'max_depth': 6,
            'learning_rate': 0.05,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': random_state,
            'verbosity': 0
        }
        
        # Performance tracking
        self.performance_results = []
        self.trained_models = {}
        
    def load_and_prepare_data(self, filepath='features_clean.csv'):
        """Load and prepare the clean feature dataset."""
        print("📊 Loading Clean Feature Dataset")
        print("=" * 40)
        
        # Load data
        df = pd.read_csv(filepath)
        print(f"✅ Loaded dataset: {df.shape}")
        
        # Identify feature columns (exclude identifiers and target)
        exclude_cols = ['fixture_id', 'date', 'home_team', 'away_team', 'season', 'target']
        
        # Get all numeric columns for ML
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        feature_cols = [col for col in numeric_cols if col not in exclude_cols]
        
        print(f"📈 ML Features identified: {len(feature_cols)}")
        print(f"🎯 Target column: {'target' if 'target' in df.columns else 'NOT FOUND'}")
        
        # Prepare features and target
        if 'target' not in df.columns:
            raise ValueError("Target column 'target' not found in dataset!")
        
        X = df[feature_cols].copy()
        y = df['target'].copy()
        dates = pd.to_datetime(df['date']) if 'date' in df.columns else None
        
        # Validate data quality
        print(f"\n🔍 Data Quality Check:")
        print(f"   Features shape: {X.shape}")
        print(f"   Target shape: {y.shape}")
        print(f"   Missing values in features: {X.isnull().sum().sum()}")
        print(f"   Missing values in target: {y.isnull().sum()}")
        
        # Target distribution
        target_dist = y.value_counts().sort_index()
        print(f"   Target distribution: {dict(target_dist)}")
        
        return X, y, dates, feature_cols
    
    def create_time_series_splits(self, X, y, dates):
        """Create time-series aware train/validation/test splits."""
        print(f"\n⏰ Creating Time-Series Splits")
        print("-" * 30)
        
        if dates is None:
            # If no dates, use sequential splits based on index
            n = len(X)
            train_end = int(n * 0.6)
            val_end = int(n * 0.8)
            
            train_idx = list(range(0, train_end))
            val_idx = list(range(train_end, val_end))
            test_idx = list(range(val_end, n))
            
            print(f"📅 Sequential splits (no dates available):")
        else:
            # Sort by date
            sort_idx = dates.argsort()
            X = X.iloc[sort_idx].reset_index(drop=True)
            y = y.iloc[sort_idx].reset_index(drop=True)
            dates = dates.iloc[sort_idx].reset_index(drop=True)
            
            # Time-based splits
            date_range = dates.max() - dates.min()
            train_cutoff = dates.min() + date_range * 0.6
            val_cutoff = dates.min() + date_range * 0.8
            
            train_idx = dates[dates <= train_cutoff].index.tolist()
            val_idx = dates[(dates > train_cutoff) & (dates <= val_cutoff)].index.tolist()
            test_idx = dates[dates > val_cutoff].index.tolist()
            
            print(f"📅 Time-based splits:")
            print(f"   Train period: {dates.iloc[train_idx].min()} to {dates.iloc[train_idx].max()}")
            print(f"   Val period: {dates.iloc[val_idx].min()} to {dates.iloc[val_idx].max()}")
            print(f"   Test period: {dates.iloc[test_idx].min()} to {dates.iloc[test_idx].max()}")
        
        # Create splits
        X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
        X_val, y_val = X.iloc[val_idx], y.iloc[val_idx]
        X_test, y_test = X.iloc[test_idx], y.iloc[test_idx]
        
        print(f"\n📊 Split Sizes:")
        print(f"   Training: {len(X_train)} samples")
        print(f"   Validation: {len(X_val)} samples")
        print(f"   Test: {len(X_test)} samples")
        
        # Validate splits have all classes
        for split_name, split_y in [('Train', y_train), ('Val', y_val), ('Test', y_test)]:
            unique_classes = split_y.unique()
            print(f"   {split_name} classes: {sorted(unique_classes)}")
        
        return (X_train, X_val, X_test), (y_train, y_val, y_test)
    
    def train_lightgbm(self, X_train, y_train, X_val, y_val):
        """Train LightGBM classifier."""
        print(f"\n🚀 Training LightGBM Model")
        print("-" * 25)
        
        # Create datasets
        train_data = lgb.Dataset(X_train, label=y_train)
        val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
        
        # Train model
        model = lgb.train(
            self.lgb_params,
            train_data,
            num_boost_round=1000,
            valid_sets=[train_data, val_data],
            valid_names=['train', 'val'],
            callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)]
        )
        
        print(f"✅ LightGBM training completed")
        print(f"   Best iteration: {model.best_iteration}")
        print(f"   Best score: {model.best_score['val']['multi_logloss']:.4f}")
        
        return model
    
    def train_xgboost(self, X_train, y_train, X_val, y_val):
        """Train XGBoost classifier."""
        print(f"\n🚀 Training XGBoost Model")
        print("-" * 24)
        
        # Create DMatrix
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dval = xgb.DMatrix(X_val, label=y_val)
        
        # Train model
        evallist = [(dtrain, 'train'), (dval, 'val')]
        model = xgb.train(
            self.xgb_params,
            dtrain,
            num_boost_round=1000,
            evals=evallist,
            early_stopping_rounds=50,
            verbose_eval=False
        )
        
        print(f"✅ XGBoost training completed")
        print(f"   Best iteration: {model.best_iteration}")
        print(f"   Best score: {model.best_score:.4f}")
        
        return model
    
    def evaluate_model(self, model, X_test, y_test, model_name):
        """Comprehensive model evaluation."""
        print(f"\n📊 Evaluating {model_name}")
        print("-" * (12 + len(model_name)))
        
        # Make predictions
        if model_name == 'LightGBM':
            y_pred_proba = model.predict(X_test, num_iteration=model.best_iteration)
            y_pred = np.argmax(y_pred_proba, axis=1)
        else:  # XGBoost
            dtest = xgb.DMatrix(X_test)
            y_pred_proba = model.predict(dtest, iteration_range=(0, model.best_iteration))
            y_pred = np.argmax(y_pred_proba, axis=1)
        
        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average=None, zero_division=0)
        recall = recall_score(y_test, y_pred, average=None, zero_division=0)
        f1 = f1_score(y_test, y_pred, average=None, zero_division=0)
        
        # Detailed classification report
        class_names = ['Home Win', 'Away Win', 'Draw']
        report = classification_report(y_test, y_pred, target_names=class_names, output_dict=True)
        
        print(f"🎯 Overall Performance:")
        print(f"   Accuracy: {accuracy:.4f}")
        print(f"   Macro Avg Precision: {precision.mean():.4f}")
        print(f"   Macro Avg Recall: {recall.mean():.4f}")
        print(f"   Macro Avg F1: {f1.mean():.4f}")
        
        print(f"\n📈 Per-Class Performance:")
        for i, class_name in enumerate(class_names):
            if i < len(precision):
                print(f"   {class_name}:")
                print(f"     Precision: {precision[i]:.4f}")
                print(f"     Recall: {recall[i]:.4f}")
                print(f"     F1-Score: {f1[i]:.4f}")
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        print(f"\n🔄 Confusion Matrix:")
        print(f"   Predicted:  H   A   D")
        for i, actual in enumerate(['Home', 'Away', 'Draw']):
            print(f"   {actual:6s}: {cm[i]}")
        
        # Store results
        result = {
            'model': model_name,
            'timestamp': self.timestamp,
            'accuracy': accuracy,
            'precision_home': precision[0] if len(precision) > 0 else 0,
            'precision_away': precision[1] if len(precision) > 1 else 0,
            'precision_draw': precision[2] if len(precision) > 2 else 0,
            'recall_home': recall[0] if len(recall) > 0 else 0,
            'recall_away': recall[1] if len(recall) > 1 else 0,
            'recall_draw': recall[2] if len(recall) > 2 else 0,
            'f1_home': f1[0] if len(f1) > 0 else 0,
            'f1_away': f1[1] if len(f1) > 1 else 0,
            'f1_draw': f1[2] if len(f1) > 2 else 0,
            'macro_precision': precision.mean(),
            'macro_recall': recall.mean(),
            'macro_f1': f1.mean(),
            'test_samples': len(y_test)
        }
        
        self.performance_results.append(result)
        return result
    
    def save_models(self, lgb_model, xgb_model):
        """Save trained models to disk with timestamps."""
        print(f"\n💾 Saving Models to Disk")
        print("-" * 22)
        
        # Save LightGBM
        lgb_filename = f'production_lightgbm_{self.timestamp}.txt'
        lgb_model.save_model(lgb_filename)
        print(f"✅ LightGBM saved: {lgb_filename}")
        
        # Save XGBoost
        xgb_filename = f'production_xgboost_{self.timestamp}.json'
        xgb_model.save_model(xgb_filename)
        print(f"✅ XGBoost saved: {xgb_filename}")
        
        # Save model metadata
        metadata = {
            'timestamp': self.timestamp,
            'lgb_model': lgb_filename,
            'xgb_model': xgb_filename,
            'lgb_params': self.lgb_params,
            'xgb_params': self.xgb_params,
            'random_state': self.random_state
        }
        
        metadata_filename = f'model_metadata_{self.timestamp}.json'
        import json
        with open(metadata_filename, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"✅ Metadata saved: {metadata_filename}")
        
        return lgb_filename, xgb_filename, metadata_filename
    
    def save_performance_report(self):
        """Save performance tracking report."""
        print(f"\n📈 Saving Performance Report")
        print("-" * 28)
        
        if not self.performance_results:
            print("❌ No performance results to save")
            return None
        
        # Create DataFrame
        df_results = pd.DataFrame(self.performance_results)
        
        # Save to CSV
        report_filename = f'model_performance_report_{self.timestamp}.csv'
        df_results.to_csv(report_filename, index=False)
        print(f"✅ Performance report saved: {report_filename}")
        
        # Also append to master report if it exists
        master_filename = 'model_performance_report.csv'
        try:
            master_df = pd.read_csv(master_filename)
            updated_df = pd.concat([master_df, df_results], ignore_index=True)
            updated_df.to_csv(master_filename, index=False)
            print(f"✅ Updated master report: {master_filename}")
        except FileNotFoundError:
            df_results.to_csv(master_filename, index=False)
            print(f"✅ Created master report: {master_filename}")
        
        return report_filename
    
    def run_full_training_pipeline(self, filepath='features_clean.csv'):
        """Run the complete training pipeline."""
        print("🚀 PRODUCTION MODEL TRAINING PIPELINE")
        print("=" * 45)
        print(f"⏰ Training session: {self.timestamp}")
        
        try:
            # 1. Load and prepare data
            X, y, dates, feature_cols = self.load_and_prepare_data(filepath)
            
            # 2. Create time-series splits
            (X_train, X_val, X_test), (y_train, y_val, y_test) = self.create_time_series_splits(X, y, dates)
            
            # 3. Train LightGBM
            lgb_model = self.train_lightgbm(X_train, y_train, X_val, y_val)
            
            # 4. Train XGBoost
            xgb_model = self.train_xgboost(X_train, y_train, X_val, y_val)
            
            # 5. Evaluate both models
            lgb_results = self.evaluate_model(lgb_model, X_test, y_test, 'LightGBM')
            xgb_results = self.evaluate_model(xgb_model, X_test, y_test, 'XGBoost')
            
            # 6. Save models
            lgb_file, xgb_file, metadata_file = self.save_models(lgb_model, xgb_model)
            
            # 7. Save performance report
            report_file = self.save_performance_report()
            
            # 8. Final summary
            print(f"\n🎊 TRAINING PIPELINE COMPLETED SUCCESSFULLY!")
            print("=" * 45)
            print(f"📊 Results Summary:")
            print(f"   LightGBM Accuracy: {lgb_results['accuracy']:.4f}")
            print(f"   XGBoost Accuracy: {xgb_results['accuracy']:.4f}")
            print(f"   Best Model: {'LightGBM' if lgb_results['accuracy'] > xgb_results['accuracy'] else 'XGBoost'}")
            
            print(f"\n📁 Files Created:")
            print(f"   • {lgb_file}")
            print(f"   • {xgb_file}")
            print(f"   • {metadata_file}")
            print(f"   • {report_file}")
            print(f"   • model_performance_report.csv")
            
            print(f"\n✅ Production models ready for deployment!")
            
            return {
                'lgb_model': lgb_model,
                'xgb_model': xgb_model,
                'lgb_results': lgb_results,
                'xgb_results': xgb_results,
                'files': {
                    'lgb_model': lgb_file,
                    'xgb_model': xgb_file,
                    'metadata': metadata_file,
                    'report': report_file
                }
            }
            
        except Exception as e:
            print(f"\n❌ TRAINING PIPELINE FAILED!")
            print(f"Error: {str(e)}")
            raise


def main():
    """Main execution function."""
    print("🎯 PRODUCTION BETTING MODEL TRAINING")
    print("=" * 40)
    print("Building production-ready models using clean, leak-free features")
    print("Features: Time-series validation, LightGBM + XGBoost, Performance tracking")
    print()
    
    # Initialize trainer
    trainer = ProductionModelTrainer(random_state=42)
    
    # Run training pipeline
    results = trainer.run_full_training_pipeline('features_clean.csv')
    
    print(f"\n🚀 Ready for live betting predictions!")


if __name__ == "__main__":
    main() 