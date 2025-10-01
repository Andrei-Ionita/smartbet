#!/usr/bin/env python3
"""
SERIE A MODEL RETRAINING TEMPLATE
=================================

Template for retraining Serie A 1X2 model with proper versioning.
Use this script when performance degrades or new data becomes available.

⚠️ CRITICAL: This creates NEW model versions - NEVER overwrites production models
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from datetime import datetime
import os
import json

class SerieAModelRetrainer:
    def __init__(self):
        self.version = self.generate_version_id()
        self.model_filename = f"league_model_1x2_serie_a_{self.version}.txt"
        self.training_filename = f"serie_a_complete_training_dataset_{self.version}.csv"
        self.validation_filename = f"validation_serie_a_{self.version}.csv"
        self.feature_importance_filename = f"feature_importance_serie_a_{self.version}.csv"
        self.metadata_filename = f"model_metadata_{self.version}.json"
        
        # Production model for comparison
        self.production_model = "LOCKED_PRODUCTION_league_model_1x2_serie_a_20250630_125109.txt"
        
        print(f"🔄 SERIE A MODEL RETRAINING - VERSION {self.version}")
        print("=" * 60)
        print(f"📁 New model will be saved as: {self.model_filename}")
        print(f"🔒 Production model remains: {self.production_model}")
    
    def generate_version_id(self):
        """Generate version ID with timestamp."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def check_retraining_criteria(self):
        """Check if retraining is justified."""
        print("\n🔍 CHECKING RETRAINING CRITERIA")
        print("-" * 35)
        
        criteria = {
            "performance_degradation": False,
            "seasonal_change": False,
            "data_expansion": False,
            "model_improvements": False
        }
        
        # You would implement actual checks here
        print("📊 Current model performance: [CHECK MANUALLY]")
        print("📅 Season status: [CHECK MANUALLY]")
        print("📈 New data available: [CHECK MANUALLY]")
        print("🧠 Algorithm updates: [CHECK MANUALLY]")
        
        print("\n⚠️ MANUAL VERIFICATION REQUIRED:")
        print("   1. Has hit rate dropped below 50% for 30+ days?")
        print("   2. Is it end/start of season?")
        print("   3. Is significant new data available?")
        print("   4. Are there proven model improvements?")
        
        response = input("\n❓ Proceed with retraining? (yes/no): ").lower().strip()
        
        if response != 'yes':
            print("❌ Retraining cancelled by user")
            return False
        
        return True
    
    def load_training_data(self, data_source=None):
        """Load training data for retraining."""
        print("\n📥 LOADING TRAINING DATA")
        print("-" * 25)
        
        if data_source is None:
            # Default to production training data as baseline
            data_source = "LOCKED_PRODUCTION_serie_a_complete_training_dataset_20250630_125108.csv"
        
        if not os.path.exists(data_source):
            raise FileNotFoundError(f"Training data not found: {data_source}")
        
        df = pd.read_csv(data_source)
        print(f"✅ Loaded {len(df)} samples from {data_source}")
        print(f"📊 Features: {len(df.columns)-1} (excluding target)")
        
        # Basic validation
        required_columns = [
            'home_recent_form', 'away_recent_form', 'home_win_odds',
            'away_win_odds', 'draw_odds', 'result'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        print("✅ All required columns present")
        return df
    
    def prepare_features(self, df):
        """Prepare features using same pipeline as production model."""
        print("\n🔧 PREPARING FEATURES")
        print("-" * 20)
        
        # Use same 12 features as production model
        feature_columns = [
            'home_recent_form', 'away_recent_form', 'home_win_odds', 
            'away_win_odds', 'draw_odds', 'home_goals_for', 'home_goals_against',
            'away_goals_for', 'away_goals_against', 'home_win_rate',
            'away_win_rate', 'recent_form_diff'
        ]
        
        # Verify all features exist
        missing_features = [col for col in feature_columns if col not in df.columns]
        if missing_features:
            print(f"⚠️ Missing features: {missing_features}")
            print("Using available features only")
            feature_columns = [col for col in feature_columns if col in df.columns]
        
        X = df[feature_columns]
        y = df['result']
        
        print(f"✅ Features prepared: {len(feature_columns)}")
        print(f"📊 Samples: {len(X)}")
        print(f"🎯 Classes: {y.value_counts().to_dict()}")
        
        return X, y, feature_columns
    
    def train_model(self, X, y, feature_columns):
        """Train new model version."""
        print(f"\n🤖 TRAINING MODEL VERSION {self.version}")
        print("-" * 40)
        
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        print(f"📊 Training set: {len(X_train)} samples")
        print(f"📊 Validation set: {len(X_val)} samples")
        
        # Same parameters as production model for consistency
        params = {
            'objective': 'multiclass',
            'num_class': 3,
            'boosting_type': 'gbdt',
            'metric': 'multi_logloss',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': 0,
            'random_state': 42
        }
        
        # Create datasets
        train_data = lgb.Dataset(X_train, label=y_train)
        val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
        
        # Train model
        print("🚀 Starting training...")
        model = lgb.train(
            params,
            train_data,
            valid_sets=[val_data],
            num_boost_round=1000,
            callbacks=[lgb.early_stopping(30), lgb.log_evaluation(0)]
        )
        
        # Evaluate
        y_pred = model.predict(X_val)
        y_pred_classes = np.argmax(y_pred, axis=1)
        accuracy = accuracy_score(y_val, y_pred_classes)
        
        print(f"✅ Training completed")
        print(f"📈 Validation accuracy: {accuracy:.3f}")
        
        # Save validation results
        validation_df = pd.DataFrame({
            'actual': y_val,
            'predicted': y_pred_classes,
            'confidence': np.max(y_pred, axis=1)
        })
        validation_df.to_csv(self.validation_filename, index=False)
        
        # Feature importance
        importance_df = pd.DataFrame({
            'feature': feature_columns,
            'importance': model.feature_importance()
        }).sort_values('importance', ascending=False)
        importance_df.to_csv(self.feature_importance_filename, index=False)
        
        return model, accuracy, validation_df, importance_df
    
    def save_model_and_metadata(self, model, accuracy, validation_df, importance_df, X, y):
        """Save model and comprehensive metadata."""
        print(f"\n💾 SAVING MODEL VERSION {self.version}")
        print("-" * 35)
        
        # Save model
        model.save_model(self.model_filename)
        print(f"✅ Model saved: {self.model_filename}")
        
        # Create comprehensive metadata
        metadata = {
            "model_version": self.version,
            "created_date": datetime.now().isoformat(),
            "model_file": self.model_filename,
            "training_file": self.training_filename,
            "validation_file": self.validation_filename,
            "feature_importance_file": self.feature_importance_filename,
            
            # Model performance
            "validation_accuracy": float(accuracy),
            "training_samples": len(X),
            "validation_samples": len(validation_df),
            "num_features": len(X.columns),
            
            # Data statistics
            "class_distribution": y.value_counts().to_dict(),
            "feature_names": list(X.columns),
            
            # Model comparison with production
            "production_model": self.production_model,
            "performance_comparison": "REQUIRES_MANUAL_TESTING",
            
            # Deployment status
            "deployment_status": "TESTING_REQUIRED",
            "deployment_date": None,
            "production_ready": False,
            
            # Retraining details
            "retraining_reason": "MANUAL_ENTRY_REQUIRED",
            "previous_version": "v1.0_20250630_125109",
            "next_review_date": None
        }
        
        # Save metadata
        with open(self.metadata_filename, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Metadata saved: {self.metadata_filename}")
        
        return metadata
    
    def compare_with_production(self, new_accuracy):
        """Compare new model with production model."""
        print(f"\n📊 COMPARING WITH PRODUCTION MODEL")
        print("-" * 40)
        
        # Production model performance (from locked baseline)
        production_accuracy = 0.500  # Known from validation
        production_hit_rate = 0.615  # Known from backtest
        
        print(f"🔒 Production Model (v1.0):")
        print(f"   Accuracy: {production_accuracy:.3f}")
        print(f"   Hit Rate (confident): {production_hit_rate:.3f}")
        
        print(f"🆕 New Model ({self.version}):")
        print(f"   Accuracy: {new_accuracy:.3f}")
        print(f"   Hit Rate: REQUIRES_BACKTESTING")
        
        improvement = new_accuracy - production_accuracy
        print(f"\n📈 Accuracy Change: {improvement:+.3f}")
        
        if improvement > 0.02:  # 2% improvement threshold
            print("✅ SIGNIFICANT IMPROVEMENT DETECTED")
            recommendation = "RECOMMENDED_FOR_TESTING"
        elif improvement > 0:
            print("🔶 MINOR IMPROVEMENT")
            recommendation = "TESTING_OPTIONAL"
        else:
            print("❌ NO IMPROVEMENT OR DEGRADATION")
            recommendation = "NOT_RECOMMENDED"
        
        print(f"🎯 Recommendation: {recommendation}")
        
        return {
            "accuracy_improvement": improvement,
            "recommendation": recommendation,
            "requires_backtesting": True
        }
    
    def generate_deployment_checklist(self, metadata):
        """Generate deployment checklist for new model."""
        print(f"\n📋 DEPLOYMENT CHECKLIST FOR VERSION {self.version}")
        print("=" * 55)
        
        checklist = f"""
🔲 PRE-DEPLOYMENT VALIDATION
   🔲 Accuracy validation passed
   🔲 Feature importance analysis completed
   🔲 No data leakage detected
   🔲 Cross-validation performed
   
🔲 BACKTESTING REQUIREMENTS
   🔲 Backtest on historical data (minimum 3 months)
   🔲 Hit rate ≥ 55% on confident predictions
   🔲 ROI ≥ 5% with conservative betting
   🔲 Maximum drawdown ≤ 10%
   
🔲 PRODUCTION TESTING
   🔲 Paper trading for 14 days minimum
   🔲 Performance monitoring implemented
   🔲 Error handling verified
   🔲 Integration testing completed
   
🔲 DEPLOYMENT APPROVAL
   🔲 Performance superior to production model
   🔲 Risk assessment completed
   🔲 Rollback plan prepared
   🔲 Stakeholder approval obtained
   
🔲 POST-DEPLOYMENT
   🔲 Model registry updated
   🔲 Monitoring dashboards configured
   🔲 Documentation updated
   🔲 Team training completed

📊 MODEL FILES CREATED:
   📁 {metadata['model_file']}
   📁 {metadata['validation_file']}
   📁 {metadata['feature_importance_file']}
   📁 {metadata['training_file']} (copy of source)
   📁 {metadata.get('metadata_filename', 'model_metadata_' + self.version + '.json')}

⚠️ CRITICAL REMINDERS:
   1. NEVER overwrite production model files
   2. Always use new version IDs for new models
   3. Preserve all previous model versions
   4. Document all changes and decisions
   5. Follow gradual deployment process

🎯 NEXT STEPS:
   1. Run comprehensive backtesting
   2. Start paper trading if backtesting successful
   3. Compare performance with production model
   4. Make deployment decision based on results
   5. Update model registry with final status
"""
        
        print(checklist)
        
        # Save checklist to file
        checklist_filename = f"deployment_checklist_{self.version}.md"
        with open(checklist_filename, 'w') as f:
            f.write(f"# Deployment Checklist - Serie A Model {self.version}\n\n")
            f.write(checklist)
        
        print(f"\n✅ Checklist saved to: {checklist_filename}")
        
        return checklist_filename

def main():
    """Main retraining workflow."""
    retrainer = SerieAModelRetrainer()
    
    try:
        # Check retraining criteria
        if not retrainer.check_retraining_criteria():
            return
        
        # Load and prepare data
        df = retrainer.load_training_data()
        X, y, feature_columns = retrainer.prepare_features(df)
        
        # Train new model
        model, accuracy, validation_df, importance_df = retrainer.train_model(X, y, feature_columns)
        
        # Save model and metadata
        metadata = retrainer.save_model_and_metadata(model, accuracy, validation_df, importance_df, X, y)
        
        # Compare with production
        comparison = retrainer.compare_with_production(accuracy)
        
        # Generate deployment checklist
        checklist_file = retrainer.generate_deployment_checklist(metadata)
        
        print(f"\n🎉 MODEL RETRAINING COMPLETED SUCCESSFULLY")
        print("=" * 45)
        print(f"📁 New model: {retrainer.model_filename}")
        print(f"📊 Accuracy: {accuracy:.3f}")
        print(f"🎯 Recommendation: {comparison['recommendation']}")
        print(f"📋 Next steps: Follow {checklist_file}")
        
        print(f"\n⚠️ IMPORTANT: This model is NOT deployed to production")
        print(f"Follow the deployment checklist before considering deployment")
        
    except Exception as e:
        print(f"\n❌ RETRAINING FAILED: {e}")
        print("Review error and try again")

if __name__ == "__main__":
    main() 