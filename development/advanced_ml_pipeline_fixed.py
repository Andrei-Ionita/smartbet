import pandas as pd
import numpy as np
import lightgbm as lgb
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import accuracy_score, log_loss, classification_report
import shap
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class AdvancedMLPipeline:
    def __init__(self):
        self.model_lgb = None
        self.model_xgb = None
        self.feature_names = None
        self.scaler = None
        self.explainer = None
        
    def load_protected_dataset(self):
        """Load the protected training dataset (creates a working copy)"""
        print("🔒 Loading Protected Training Dataset")
        print("=" * 40)
        
        # Load from protected file
        df = pd.read_csv('FINAL_PREMIER_LEAGUE_TRAINING_DATASET_WITH_ODDS_DO_NOT_MODIFY.csv')
        
        print(f"✅ Loaded {len(df):,} records")
        print(f"✅ {df['fixture_id'].nunique():,} unique matches")
        print(f"✅ {len(df.columns)} features")
        
        # Create working copy
        working_filename = f"ML_WORKING_COPY_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(working_filename, index=False)
        print(f"✅ Working copy created: {working_filename}")
        
        return df
    
    def clean_dataset(self, df):
        """Remove extreme outlier matches and prepare clean training set"""
        print("\n🧹 Cleaning Dataset")
        print("=" * 25)
        
        original_count = len(df)
        unique_matches_before = df['fixture_id'].nunique()
        
        # Remove extreme odds outliers (>15 for conservative modeling)
        clean_df = df[
            (df['avg_home_odds'] <= 15) & 
            (df['avg_away_odds'] <= 15) & 
            (df['avg_draw_odds'] <= 15) &
            (df['avg_home_odds'] >= 1.01) & 
            (df['avg_away_odds'] >= 1.01) & 
            (df['avg_draw_odds'] >= 1.01)
        ].copy()
        
        # Keep only one record per match (remove multiple bookmaker entries)
        # Use the first record for each fixture_id (already has aggregated avg odds)
        clean_df = clean_df.drop_duplicates('fixture_id', keep='first')
        
        removed_records = original_count - len(clean_df)
        unique_matches_after = clean_df['fixture_id'].nunique()
        
        print(f"🗑️  Removed {removed_records:,} outlier/duplicate records")
        print(f"📊 Unique matches before: {unique_matches_before:,}")
        print(f"📊 Unique matches after: {unique_matches_after:,}")
        print(f"✅ Clean dataset: {len(clean_df):,} matches ready for training")
        
        return clean_df
    
    def feature_engineering(self, df):
        """Advanced feature engineering pipeline"""
        print("\n⚙️ Feature Engineering Pipeline")
        print("=" * 35)
        
        # Convert date
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # 1. ODDS-BASED FEATURES
        print("1️⃣ Creating odds-based features...")
        
        # Market margin and efficiency
        df['total_implied_prob'] = (1/df['avg_home_odds'] + 1/df['avg_away_odds'] + 1/df['avg_draw_odds'])
        df['market_margin'] = df['total_implied_prob'] - 1
        df['market_efficiency'] = 1 / df['total_implied_prob']
        
        # True probabilities (remove market margin)
        df['true_prob_home'] = (1/df['avg_home_odds']) / df['total_implied_prob']
        df['true_prob_away'] = (1/df['avg_away_odds']) / df['total_implied_prob']
        df['true_prob_draw'] = (1/df['avg_draw_odds']) / df['total_implied_prob']
        
        # Log odds (more ML-friendly)
        df['log_odds_home'] = np.log(df['avg_home_odds'])
        df['log_odds_away'] = np.log(df['avg_away_odds'])
        df['log_odds_draw'] = np.log(df['avg_draw_odds'])
        
        # Odds ratios
        df['home_away_odds_ratio'] = df['avg_home_odds'] / df['avg_away_odds']
        df['home_draw_odds_ratio'] = df['avg_home_odds'] / df['avg_draw_odds']
        df['away_draw_odds_ratio'] = df['avg_away_odds'] / df['avg_draw_odds']
        
        # Favorite/underdog features
        df['favorite_odds'] = np.minimum(np.minimum(df['avg_home_odds'], df['avg_away_odds']), df['avg_draw_odds'])
        df['underdog_odds'] = np.maximum(np.maximum(df['avg_home_odds'], df['avg_away_odds']), df['avg_draw_odds'])
        df['odds_spread'] = df['underdog_odds'] - df['favorite_odds']
        
        # 2. GOAL DIFFERENCE AND ATTACKING/DEFENSIVE STRENGTH
        print("2️⃣ Creating goal and strength features...")
        
        df['goal_difference'] = df['home_score'] - df['away_score']
        df['total_goals'] = df['home_score'] + df['away_score']
        df['high_scoring'] = (df['total_goals'] > 2.5).astype(int)
        df['low_scoring'] = (df['total_goals'] < 1.5).astype(int)
        
        # 3. TEMPORAL FEATURES
        print("3️⃣ Creating temporal features...")
        
        df['month'] = df['date'].dt.month
        df['day_of_week'] = df['date'].dt.dayofweek
        df['is_weekend'] = ((df['day_of_week'] == 5) | (df['day_of_week'] == 6)).astype(int)
        
        # Season progress (0-1 through the season)
        df['season_start'] = pd.to_datetime(df['season_name'].str[:4] + '-08-01')
        df['days_into_season'] = (df['date'] - df['season_start']).dt.days
        df['season_progress'] = df['days_into_season'] / 365
        
        # 4. BOOKMAKER VARIANCE FEATURES
        print("4️⃣ Creating bookmaker variance features...")
        
        # Find all bookmaker odds columns
        bookmaker_home_cols = [col for col in df.columns if col.endswith('_home_odds') and not col.startswith('avg_')]
        bookmaker_away_cols = [col for col in df.columns if col.endswith('_away_odds') and not col.startswith('avg_')]
        bookmaker_draw_cols = [col for col in df.columns if col.endswith('_draw_odds') and not col.startswith('avg_')]
        
        if bookmaker_home_cols:
            # Variance in bookmaker odds (market disagreement)
            df['home_odds_variance'] = df[bookmaker_home_cols].var(axis=1, skipna=True)
            df['away_odds_variance'] = df[bookmaker_away_cols].var(axis=1, skipna=True)
            df['draw_odds_variance'] = df[bookmaker_draw_cols].var(axis=1, skipna=True)
            
            # Best and worst odds available
            df['best_home_odds'] = df[bookmaker_home_cols].max(axis=1, skipna=True)
            df['worst_home_odds'] = df[bookmaker_home_cols].min(axis=1, skipna=True)
            df['best_away_odds'] = df[bookmaker_away_cols].max(axis=1, skipna=True)
            df['worst_away_odds'] = df[bookmaker_away_cols].min(axis=1, skipna=True)
            
            # Odds range (betting opportunities)
            df['home_odds_range'] = df['best_home_odds'] - df['worst_home_odds']
            df['away_odds_range'] = df['best_away_odds'] - df['worst_away_odds']
        
        print(f"✅ Feature engineering complete! Total features: {len(df.columns)}")
        
        return df
    
    def prepare_for_training(self, df):
        """Prepare features and target variables for ML training"""
        print("\n🎯 Preparing for ML Training")
        print("=" * 30)
        
        # Define target variable (match outcome)
        df['outcome'] = df.apply(lambda row: 
            0 if row['home_score'] > row['away_score'] else  # Home win
            1 if row['home_score'] < row['away_score'] else  # Away win  
            2, axis=1)  # Draw
        
        # Select features for training (exclude target and metadata)
        exclude_cols = [
            'fixture_id', 'season_id', 'round_id', 'date', 'season_start',
            'home_team', 'away_team', 'home_score', 'away_score', 'outcome',
            'season_name', 'api_home_team', 'api_away_team', 'commence_time', 'match_date'
        ]
        
        # Also exclude individual bookmaker columns to avoid overfitting
        bookmaker_cols = [col for col in df.columns if any(bm in col for bm in 
            ['marathonbet_', 'paddypower_', 'betclic_', 'skybet_', 'betfair_', 'williamhill_'])]
        
        exclude_cols.extend(bookmaker_cols)
        
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        X = df[feature_cols].copy()
        y = df['outcome'].copy()
        
        # Handle missing values
        X = X.fillna(X.median())
        
        # Remove any remaining inf or -inf values
        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.fillna(X.median())
        
        print(f"✅ Features selected: {len(feature_cols)}")
        print(f"✅ Training samples: {len(X):,}")
        print(f"✅ Target distribution:")
        print(f"   Home wins: {(y==0).sum():,} ({(y==0).mean()*100:.1f}%)")
        print(f"   Away wins: {(y==1).sum():,} ({(y==1).mean()*100:.1f}%)")
        print(f"   Draws: {(y==2).sum():,} ({(y==2).mean()*100:.1f}%)")
        
        self.feature_names = feature_cols
        
        return X, y, df
    
    def create_time_splits(self, df):
        """Create time-based train/validation/test splits"""
        print("\n📅 Creating Time-Based Splits")
        print("=" * 32)
        
        # Convert season to year for splitting
        df['season_year'] = df['season_name'].str[:4].astype(int)
        
        # Training: 2021-2023 seasons
        train_mask = df['season_year'].isin([2021, 2022, 2023])
        
        # Validation: 2024 season (part of 2023/2024)
        val_mask = (df['season_name'] == '2023/2024') & (df['date'] >= '2024-01-01')
        
        # Test: 2024-2025 season (most recent)
        test_mask = df['season_name'] == '2024/2025'
        
        print(f"📊 Training set: {train_mask.sum():,} matches")
        print(f"📊 Validation set: {val_mask.sum():,} matches")
        print(f"📊 Test set: {test_mask.sum():,} matches")
        
        return train_mask, val_mask, test_mask
    
    def train_models(self, X, y, train_mask, val_mask):
        """Train LightGBM and XGBoost models"""
        print("\n🤖 Training ML Models")
        print("=" * 25)
        
        X_train, y_train = X[train_mask], y[train_mask]
        X_val, y_val = X[val_mask], y[val_mask]
        
        print(f"Training samples: {len(X_train):,}")
        print(f"Validation samples: {len(X_val):,}")
        
        # 1. LIGHTGBM MODEL
        print("\n1️⃣ Training LightGBM...")
        
        lgb_params = {
            'objective': 'multiclass',
            'num_class': 3,
            'metric': 'multi_logloss',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,  # Reduced to prevent overfitting
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'min_data_in_leaf': 20,  # Added to prevent overfitting
            'verbose': -1,
            'random_state': 42
        }
        
        train_data = lgb.Dataset(X_train, label=y_train)
        val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
        
        self.model_lgb = lgb.train(
            lgb_params,
            train_data,
            valid_sets=[train_data, val_data],
            num_boost_round=500,  # Reduced to prevent overfitting
            callbacks=[lgb.early_stopping(stopping_rounds=30), lgb.log_evaluation(period=0)]
        )
        
        # Validation predictions
        lgb_val_pred = self.model_lgb.predict(X_val, num_iteration=self.model_lgb.best_iteration)
        lgb_val_pred_class = np.argmax(lgb_val_pred, axis=1)
        lgb_val_acc = accuracy_score(y_val, lgb_val_pred_class)
        lgb_val_logloss = log_loss(y_val, lgb_val_pred)
        
        print(f"✅ LightGBM Validation Accuracy: {lgb_val_acc:.4f}")
        print(f"✅ LightGBM Validation Log Loss: {lgb_val_logloss:.4f}")
        
        # 2. XGBOOST MODEL
        print("\n2️⃣ Training XGBoost...")
        
        xgb_params = {
            'objective': 'multi:softprob',
            'num_class': 3,
            'eval_metric': 'mlogloss',
            'max_depth': 4,  # Reduced to prevent overfitting
            'learning_rate': 0.05,  # Reduced to prevent overfitting
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_weight': 5,  # Added to prevent overfitting
            'random_state': 42,
            'verbosity': 0
        }
        
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dval = xgb.DMatrix(X_val, label=y_val)
        
        self.model_xgb = xgb.train(
            xgb_params,
            dtrain,
            evals=[(dtrain, 'train'), (dval, 'val')],
            num_boost_round=500,  # Reduced to prevent overfitting
            early_stopping_rounds=30,
            verbose_eval=False
        )
        
        # Validation predictions
        xgb_val_pred = self.model_xgb.predict(dval)
        xgb_val_pred_class = np.argmax(xgb_val_pred, axis=1)
        xgb_val_acc = accuracy_score(y_val, xgb_val_pred_class)
        xgb_val_logloss = log_loss(y_val, xgb_val_pred)
        
        print(f"✅ XGBoost Validation Accuracy: {xgb_val_acc:.4f}")
        print(f"✅ XGBoost Validation Log Loss: {xgb_val_logloss:.4f}")
        
        return lgb_val_acc, xgb_val_acc
    
    def evaluate_on_test(self, X, y, test_mask):
        """Evaluate both models on test set"""
        print("\n📊 Test Set Evaluation")
        print("=" * 25)
        
        X_test, y_test = X[test_mask], y[test_mask]
        print(f"Test samples: {len(X_test):,}")
        
        # LightGBM predictions
        lgb_pred = self.model_lgb.predict(X_test, num_iteration=self.model_lgb.best_iteration)
        lgb_pred_class = np.argmax(lgb_pred, axis=1)
        lgb_test_acc = accuracy_score(y_test, lgb_pred_class)
        lgb_test_logloss = log_loss(y_test, lgb_pred)
        
        # XGBoost predictions
        dtest = xgb.DMatrix(X_test)
        xgb_pred = self.model_xgb.predict(dtest)
        xgb_pred_class = np.argmax(xgb_pred, axis=1)
        xgb_test_acc = accuracy_score(y_test, xgb_pred_class)
        xgb_test_logloss = log_loss(y_test, xgb_pred)
        
        print(f"\n🏆 FINAL TEST RESULTS:")
        print(f"LightGBM - Accuracy: {lgb_test_acc:.4f}, Log Loss: {lgb_test_logloss:.4f}")
        print(f"XGBoost  - Accuracy: {xgb_test_acc:.4f}, Log Loss: {xgb_test_logloss:.4f}")
        
        # Detailed classification report for best model
        best_model = "LightGBM" if lgb_test_acc > xgb_test_acc else "XGBoost"
        best_pred = lgb_pred_class if lgb_test_acc > xgb_test_acc else xgb_pred_class
        
        print(f"\n📋 Detailed Results ({best_model}):")
        target_names = ['Home Win', 'Away Win', 'Draw']
        print(classification_report(y_test, best_pred, target_names=target_names))
        
        return lgb_test_acc, xgb_test_acc
    
    def generate_shap_explanations(self, X, test_mask):
        """Generate SHAP values for model interpretability"""
        print("\n🔍 Generating SHAP Explanations")
        print("=" * 35)
        
        X_test = X[test_mask]
        
        # Use LightGBM for SHAP (generally faster)
        print("Creating SHAP explainer...")
        self.explainer = shap.TreeExplainer(self.model_lgb)
        
        # Calculate SHAP values for test set (sample if too large)
        sample_size = min(100, len(X_test))  # Reduced sample size for stability
        X_sample = X_test.sample(sample_size, random_state=42)
        
        print(f"Calculating SHAP values for {sample_size} samples...")
        shap_values = self.explainer.shap_values(X_sample)
        
        # Feature importance from model directly (more stable)
        feature_importance = self.model_lgb.feature_importance(importance_type='gain')
        
        # Ensure arrays have same length
        if len(feature_importance) == len(self.feature_names):
            importance_df = pd.DataFrame({
                'feature': self.feature_names,
                'importance': feature_importance
            }).sort_values('importance', ascending=False)
            
            print(f"\n🏆 Top 15 Most Important Features:")
            for i, (_, row) in enumerate(importance_df.head(15).iterrows(), 1):
                print(f"{i:2d}. {row['feature']}: {row['importance']:.2f}")
            
            # Save feature importance
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            importance_df.to_csv(f'feature_importance_{timestamp}.csv', index=False)
            print(f"\n💾 Feature importance saved: feature_importance_{timestamp}.csv")
        else:
            print("⚠️  Feature importance array length mismatch, using default ranking")
            importance_df = pd.DataFrame({
                'feature': self.feature_names,
                'importance': range(len(self.feature_names), 0, -1)
            })
        
        return shap_values, importance_df
    
    def save_models(self):
        """Save trained models"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save LightGBM
        lgb_filename = f'lightgbm_premier_league_{timestamp}.txt'
        self.model_lgb.save_model(lgb_filename)
        
        # Save XGBoost
        xgb_filename = f'xgboost_premier_league_{timestamp}.json'
        self.model_xgb.save_model(xgb_filename)
        
        print(f"\n💾 Models saved:")
        print(f"   LightGBM: {lgb_filename}")
        print(f"   XGBoost: {xgb_filename}")
        
        return lgb_filename, xgb_filename

def main():
    """Main execution pipeline"""
    print("🚀 ADVANCED ML PIPELINE FOR PREMIER LEAGUE PREDICTIONS")
    print("=" * 60)
    
    # Initialize pipeline
    pipeline = AdvancedMLPipeline()
    
    # 1. Load protected dataset
    df = pipeline.load_protected_dataset()
    
    # 2. Clean dataset
    clean_df = pipeline.clean_dataset(df)
    
    # 3. Feature engineering
    engineered_df = pipeline.feature_engineering(clean_df)
    
    # 4. Prepare for training
    X, y, final_df = pipeline.prepare_for_training(engineered_df)
    
    # 5. Create time splits
    train_mask, val_mask, test_mask = pipeline.create_time_splits(final_df)
    
    # 6. Train models
    lgb_val_acc, xgb_val_acc = pipeline.train_models(X, y, train_mask, val_mask)
    
    # 7. Evaluate on test set
    lgb_test_acc, xgb_test_acc = pipeline.evaluate_on_test(X, y, test_mask)
    
    # 8. Generate SHAP explanations
    shap_values, importance_df = pipeline.generate_shap_explanations(X, test_mask)
    
    # 9. Save models
    lgb_file, xgb_file = pipeline.save_models()
    
    # Final summary
    print(f"\n🎯 PIPELINE COMPLETE!")
    print("=" * 25)
    print(f"✅ Clean training samples: {len(X):,}")
    print(f"✅ Features engineered: {len(pipeline.feature_names)}")
    print(f"✅ Best test accuracy: {max(lgb_test_acc, xgb_test_acc):.4f}")
    print(f"✅ Models saved and ready for production!")

if __name__ == "__main__":
    main() 