#!/usr/bin/env python3
"""
IMPROVED SERIE A MODEL BUILDER
Enhanced Serie A 1X2 betting model with bias correction and advanced feature engineering
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import accuracy_score, log_loss, classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_class_weight
import warnings
warnings.filterwarnings('ignore')

class ImprovedSerieAModelBuilder:
    """Advanced Serie A model builder with bias correction and enhanced features"""
    
    def __init__(self):
        """Initialize with Serie A specific configurations"""
        self.dataset_path = "LOCKED_PRODUCTION_serie_a_complete_training_dataset_20250630_125108.csv"
        self.model_name = "IMPROVED_serie_a_model"
        self.timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        
        # Serie A big clubs (for context features)
        self.big_clubs = [
            'Juventus', 'AC Milan', 'Inter Milan', 'Napoli', 
            'AS Roma', 'Lazio', 'Atalanta', 'Fiorentina'
        ]
        
        print("🇮🇹 IMPROVED SERIE A MODEL BUILDER")
        print("=" * 50)
        print("🎯 Addressing bias issues from previous model")
        print("⚖️  Implementing class balancing and advanced features")
        
    def load_and_analyze_data(self):
        """Load data and perform comprehensive analysis"""
        print("\n📊 Loading and Analyzing Data...")
        
        self.df = pd.read_csv(self.dataset_path)
        print(f"✅ Dataset loaded: {len(self.df)} matches")
        
        # Analyze class distribution
        target_counts = self.df['target'].value_counts()
        target_pct = self.df['target'].value_counts(normalize=True) * 100
        
        print("\n📈 Target Distribution Analysis:")
        print(f"   Home wins (0): {target_counts[0]} ({target_pct[0]:.1f}%)")
        print(f"   Away wins (1): {target_counts[1]} ({target_pct[1]:.1f}%)")  
        print(f"   Draws (2): {target_counts[2]} ({target_pct[2]:.1f}%)")
        
        # Calculate class weights for balancing
        classes = np.unique(self.df['target'])
        self.class_weights = compute_class_weight('balanced', classes=classes, y=self.df['target'])
        self.class_weight_dict = dict(zip(classes, self.class_weights))
        
        print(f"\n⚖️  Computed Class Weights:")
        for class_id, weight in self.class_weight_dict.items():
            class_name = ['Home', 'Away', 'Draw'][class_id]
            print(f"   {class_name}: {weight:.3f}")
            
        return self.df
    
    def engineer_advanced_features(self, df):
        """Advanced feature engineering to fix bias issues"""
        print("\n🧠 Engineering Advanced Features...")
        
        df_enhanced = df.copy()
        
        # 1. ORIGINAL FEATURES (verified working)
        base_features = [
            'true_prob_draw', 'prob_ratio_draw_away', 'prob_ratio_home_draw',
            'log_odds_home_draw', 'log_odds_draw_away', 'bookmaker_margin',
            'market_efficiency', 'uncertainty_index', 'odds_draw',
            'goals_for_away', 'recent_form_home', 'recent_form_away'
        ]
        
        # 2. BIAS CORRECTION FEATURES
        # True probability for all outcomes (not just draw)
        df_enhanced['true_prob_home'] = (1/df_enhanced['avg_home_odds']) / df_enhanced['total_inv_odds']
        df_enhanced['true_prob_away'] = (1/df_enhanced['avg_away_odds']) / df_enhanced['total_inv_odds']
        
        # Away team bias correction (Serie A specific)
        df_enhanced['away_advantage'] = df_enhanced['true_prob_away'] / (df_enhanced['true_prob_home'] + 0.01)
        df_enhanced['home_favorite'] = (df_enhanced['avg_home_odds'] < df_enhanced['avg_away_odds']).astype(int)
        df_enhanced['away_favorite'] = (df_enhanced['avg_away_odds'] < df_enhanced['avg_home_odds']).astype(int)
        
        # 3. ODDS ANALYSIS FEATURES  
        odds_values = np.column_stack([df_enhanced['avg_home_odds'], 
                                     df_enhanced['avg_away_odds'], 
                                     df_enhanced['avg_draw_odds']])
        df_enhanced['odds_variance'] = np.var(odds_values, axis=1)
        df_enhanced['min_odds'] = np.min(odds_values, axis=1)
        df_enhanced['max_odds'] = np.max(odds_values, axis=1)
        df_enhanced['odds_range'] = df_enhanced['max_odds'] - df_enhanced['min_odds']
        
        # 4. TEAM CONTEXT FEATURES
        df_enhanced['home_big_club'] = df_enhanced['home_team'].isin(self.big_clubs).astype(int)
        df_enhanced['away_big_club'] = df_enhanced['away_team'].isin(self.big_clubs).astype(int)
        df_enhanced['big_club_clash'] = (df_enhanced['home_big_club'] & df_enhanced['away_big_club']).astype(int)
        
        # 5. FORM DIFFERENTIAL FEATURES
        df_enhanced['form_difference'] = df_enhanced['recent_form_home'] - df_enhanced['recent_form_away']
        df_enhanced['form_ratio'] = df_enhanced['recent_form_home'] / (df_enhanced['recent_form_away'] + 0.1)
        
        # 6. PROBABILISTIC FEATURES
        # Outcome entropy
        probs = np.column_stack([df_enhanced['true_prob_home'], 
                               df_enhanced['true_prob_away'], 
                               df_enhanced['true_prob_draw']])
        df_enhanced['outcome_entropy'] = -np.sum(probs * np.log(probs + 1e-8), axis=1)
        
        # Enhanced feature list
        self.enhanced_features = base_features + [
            'true_prob_home', 'true_prob_away', 'away_advantage', 
            'home_favorite', 'away_favorite', 'odds_variance', 
            'min_odds', 'max_odds', 'odds_range',
            'home_big_club', 'away_big_club', 'big_club_clash',
            'form_difference', 'form_ratio', 'outcome_entropy'
        ]
        
        print(f"✅ Enhanced features: {len(self.enhanced_features)} total")
        print(f"📊 Added bias correction features: {len(self.enhanced_features) - len(base_features)}")
        
        return df_enhanced
    
    def train_improved_model(self, df):
        """Train improved model with bias correction"""
        print("\n🚀 Training Improved Serie A Model...")
        
        # Prepare features and target
        X = df[self.enhanced_features].copy()
        y = df['target'].copy()
        
        # Handle any NaN values
        X = X.fillna(X.mean())
        
        print(f"📊 Training data: {len(X)} samples, {len(X.columns)} features")
        print(f"🎯 Target distribution: {y.value_counts().to_dict()}")
        
        # Stratified split to maintain class distribution
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        print(f"🔄 Training set: {len(X_train)} samples")
        print(f"🔍 Validation set: {len(X_val)} samples")
        
        # IMPROVED LightGBM parameters with bias correction
        params = {
            'objective': 'multiclass',
            'num_class': 3,
            'metric': 'multi_logloss',
            'boosting_type': 'gbdt',
            'num_leaves': 64,
            'learning_rate': 0.03,
            'feature_fraction': 0.85,
            'bagging_fraction': 0.85,
            'bagging_freq': 3,
            'min_data_in_leaf': 15,
            'lambda_l1': 0.1,
            'lambda_l2': 0.1,
            'verbose': -1,
            'random_state': 42,
            'max_depth': 8
        }
        
        # Create datasets with sample weights
        sample_weights_train = np.array([self.class_weight_dict[y] for y in y_train])
        sample_weights_val = np.array([self.class_weight_dict[y] for y in y_val])
        
        train_data = lgb.Dataset(X_train, label=y_train, weight=sample_weights_train)
        val_data = lgb.Dataset(X_val, label=y_val, weight=sample_weights_val, reference=train_data)
        
        # Train with early stopping
        model = lgb.train(
            params,
            train_data,
            valid_sets=[train_data, val_data],
            num_boost_round=2000,
            callbacks=[lgb.early_stopping(100), lgb.log_evaluation(0)]
        )
        
        # Validation predictions
        val_pred_proba = model.predict(X_val, num_iteration=model.best_iteration)
        val_pred = np.argmax(val_pred_proba, axis=1)
        
        # Calculate metrics
        val_acc = accuracy_score(y_val, val_pred)
        val_logloss = log_loss(y_val, val_pred_proba)
        
        print(f"\n📈 IMPROVED MODEL RESULTS:")
        print(f"   Validation Accuracy: {val_acc:.4f}")
        print(f"   Validation Log Loss: {val_logloss:.4f}")
        
        # Detailed analysis
        print(f"\n📊 Class-wise Performance:")
        class_report = classification_report(y_val, val_pred, 
                                           target_names=['Home', 'Away', 'Draw'],
                                           output_dict=True)
        
        for outcome, metrics in class_report.items():
            if outcome in ['Home', 'Away', 'Draw']:
                print(f"   {outcome}: Precision={metrics['precision']:.3f}, "
                      f"Recall={metrics['recall']:.3f}, F1={metrics['f1-score']:.3f}")
        
        # Feature importance
        importance_df = pd.DataFrame({
            'feature': self.enhanced_features,
            'importance': model.feature_importance(importance_type='gain')
        }).sort_values('importance', ascending=False)
        
        print(f"\n🔝 Top 10 Most Important Features:")
        for i, row in importance_df.head(10).iterrows():
            print(f"   {row['feature']}: {row['importance']:.1f}")
        
        # Save improved model
        model_filename = f"{self.model_name}_{self.timestamp}.txt"
        model.save_model(model_filename)
        
        # Save feature importance
        importance_filename = f"feature_importance_{self.model_name}_{self.timestamp}.csv"
        importance_df.to_csv(importance_filename, index=False)
        
        # Save enhanced dataset
        dataset_filename = f"enhanced_training_dataset_{self.model_name}_{self.timestamp}.csv"
        df.to_csv(dataset_filename, index=False)
        
        print(f"\n💾 Files Saved:")
        print(f"   Model: {model_filename}")
        print(f"   Feature Importance: {importance_filename}")
        print(f"   Enhanced Dataset: {dataset_filename}")
        
        return model, importance_df
        
    def run_full_pipeline(self):
        """Execute the complete improved model pipeline"""
        print(f"\n🚀 RUNNING COMPLETE IMPROVED SERIE A PIPELINE")
        print("=" * 60)
        
        # Step 1: Load and analyze
        df = self.load_and_analyze_data()
        
        # Step 2: Enhanced feature engineering
        df_enhanced = self.engineer_advanced_features(df)
        
        # Step 3: Train improved model
        model, importance_df = self.train_improved_model(df_enhanced)
        
        print(f"\n🏆 IMPROVED SERIE A MODEL COMPLETE!")
        print("=" * 50)
        print(f"✅ Bias correction implemented")
        print(f"✅ Class imbalance addressed") 
        print(f"✅ Advanced features engineered")
        print(f"🎯 Ready for validation testing!")
        
        return model, importance_df

if __name__ == "__main__":
    builder = ImprovedSerieAModelBuilder()
    model, importance_df = builder.run_full_pipeline() 