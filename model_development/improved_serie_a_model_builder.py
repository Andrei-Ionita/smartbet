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
from sklearn.preprocessing import StandardScaler
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
        
        # Historical context
        self.relegation_zone_teams = ['Salernitana', 'Frosinone', 'Lecce']
        
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
        df_enhanced['away_advantage'] = df_enhanced['true_prob_away'] / df_enhanced['true_prob_home']
        df_enhanced['home_favorite'] = (df_enhanced['avg_home_odds'] < df_enhanced['avg_away_odds']).astype(int)
        df_enhanced['away_favorite'] = (df_enhanced['avg_away_odds'] < df_enhanced['avg_home_odds']).astype(int)
        
        # 3. ODDS ANALYSIS FEATURES  
        df_enhanced['odds_variance'] = np.var([df_enhanced['avg_home_odds'], 
                                             df_enhanced['avg_away_odds'], 
                                             df_enhanced['avg_draw_odds']], axis=0)
        df_enhanced['min_odds'] = np.min([df_enhanced['avg_home_odds'], 
                                        df_enhanced['avg_away_odds'], 
                                        df_enhanced['avg_draw_odds']], axis=0)
        df_enhanced['max_odds'] = np.max([df_enhanced['avg_home_odds'], 
                                        df_enhanced['avg_away_odds'], 
                                        df_enhanced['avg_draw_odds']], axis=0)
        df_enhanced['odds_range'] = df_enhanced['max_odds'] - df_enhanced['min_odds']
        
        # 4. TEAM CONTEXT FEATURES
        df_enhanced['home_big_club'] = df_enhanced['home_team'].isin(self.big_clubs).astype(int)
        df_enhanced['away_big_club'] = df_enhanced['away_team'].isin(self.big_clubs).astype(int)
        df_enhanced['big_club_clash'] = (df_enhanced['home_big_club'] & df_enhanced['away_big_club']).astype(int)
        df_enhanced['relegation_battle'] = (
            df_enhanced['home_team'].isin(self.relegation_zone_teams) | 
            df_enhanced['away_team'].isin(self.relegation_zone_teams)
        ).astype(int)
        
        # 5. FORM DIFFERENTIAL FEATURES
        df_enhanced['form_difference'] = df_enhanced['recent_form_home'] - df_enhanced['recent_form_away']
        df_enhanced['form_ratio'] = df_enhanced['recent_form_home'] / (df_enhanced['recent_form_away'] + 0.1)
        
        # 6. PROBABILISTIC FEATURES
        # Entropy measure for outcome uncertainty
        probs = np.column_stack([df_enhanced['true_prob_home'], 
                               df_enhanced['true_prob_away'], 
                               df_enhanced['true_prob_draw']])
        df_enhanced['outcome_entropy'] = -np.sum(probs * np.log(probs + 1e-8), axis=1)
        
        # Dominance measures
        df_enhanced['home_dominance'] = df_enhanced['true_prob_home'] - np.maximum(
            df_enhanced['true_prob_away'], df_enhanced['true_prob_draw'])
        df_enhanced['away_dominance'] = df_enhanced['true_prob_away'] - np.maximum(
            df_enhanced['true_prob_home'], df_enhanced['true_prob_draw'])
        df_enhanced['draw_dominance'] = df_enhanced['true_prob_draw'] - np.maximum(
            df_enhanced['true_prob_home'], df_enhanced['true_prob_away'])
        
        # 7. MARKET EFFICIENCY INDICATORS
        df_enhanced['overround'] = df_enhanced['total_inv_odds']
        df_enhanced['profit_margin'] = df_enhanced['bookmaker_margin']
        df_enhanced['fair_odds_home'] = 1 / df_enhanced['true_prob_home']
        df_enhanced['fair_odds_away'] = 1 / df_enhanced['true_prob_away']
        df_enhanced['fair_odds_draw'] = 1 / df_enhanced['true_prob_draw']
        
        # Enhanced feature list
        self.enhanced_features = base_features + [
            'true_prob_home', 'true_prob_away', 'away_advantage', 
            'home_favorite', 'away_favorite', 'odds_variance', 
            'min_odds', 'max_odds', 'odds_range',
            'home_big_club', 'away_big_club', 'big_club_clash', 'relegation_battle',
            'form_difference', 'form_ratio', 'outcome_entropy',
            'home_dominance', 'away_dominance', 'draw_dominance',
            'overround', 'profit_margin', 'fair_odds_home', 'fair_odds_away', 'fair_odds_draw'
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
            'num_leaves': 64,           # Increased complexity
            'learning_rate': 0.03,      # Lower learning rate for stability
            'feature_fraction': 0.85,   # Use more features
            'bagging_fraction': 0.85,   # More aggressive bagging
            'bagging_freq': 3,
            'min_data_in_leaf': 15,     # Reduced for more granular learning
            'lambda_l1': 0.1,           # L1 regularization
            'lambda_l2': 0.1,           # L2 regularization
            'verbose': -1,
            'random_state': 42,
            'class_weight': 'balanced', # KEY: Handle class imbalance
            'max_depth': 8              # Control overfitting
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
        
        # Confusion matrix
        cm = confusion_matrix(y_val, val_pred)
        print(f"\n🎯 Confusion Matrix:")
        print(f"   Predicted: Home | Away | Draw")
        for i, actual in enumerate(['Home', 'Away', 'Draw']):
            print(f"   {actual:4s}: {cm[i][0]:4d} | {cm[i][1]:4d} | {cm[i][2]:4d}")
        
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
        
        # Cross-validation for robustness check
        print(f"\n🔄 Cross-Validation (5-fold)...")
        cv_scores = cross_val_score(
            lgb.LGBMClassifier(**params, n_estimators=model.best_iteration),
            X, y, cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
            scoring='accuracy'
        )
        
        print(f"   CV Accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
        
        print(f"\n💾 Files Saved:")
        print(f"   Model: {model_filename}")
        print(f"   Feature Importance: {importance_filename}")
        print(f"   Enhanced Dataset: {dataset_filename}")
        
        return model, importance_df, val_pred_proba, y_val
    
    def create_prediction_interface(self, model, importance_df):
        """Create an improved prediction interface"""
        print(f"\n🔮 Creating Improved Prediction Interface...")
        
        interface_code = f'''#!/usr/bin/env python3
"""
IMPROVED SERIE A 1X2 PREDICTOR
Enhanced production model with bias correction
Generated on: {self.timestamp}
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from typing import Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

class ImprovedSerieAPredictor:
    """Enhanced Serie A 1X2 predictor with bias correction"""
    
    def __init__(self, model_path='{self.model_name}_{self.timestamp}.txt'):
        self.model_path = model_path
        self.model = lgb.Booster(model_file=model_path)
        self.confidence_threshold = 0.55  # Lowered for better coverage
        self.class_names = ['Home Win', 'Away Win', 'Draw']
        
        # Serie A team classifications
        self.big_clubs = {', '.join([f"'{team}'" for team in self.big_clubs])}
        self.relegation_teams = {', '.join([f"'{team}'" for team in self.relegation_zone_teams])}
        
        print("🇮🇹 Improved Serie A Predictor Loaded")
        print(f"📊 Model: {{self.model_path}}")
        print(f"🎯 Confidence Threshold: {{self.confidence_threshold}}")
    
    def engineer_prediction_features(self, home_odds: float, away_odds: float, draw_odds: float,
                                   home_team: str = None, away_team: str = None) -> pd.DataFrame:
        """Engineer all enhanced features for prediction"""
        
        # Basic probability calculations
        total_inv_odds = 1/home_odds + 1/away_odds + 1/draw_odds
        true_prob_home = (1/home_odds) / total_inv_odds
        true_prob_away = (1/away_odds) / total_inv_odds
        true_prob_draw = (1/draw_odds) / total_inv_odds
        
        # Enhanced feature set
        features = {{
            # Original proven features
            'true_prob_draw': true_prob_draw,
            'prob_ratio_draw_away': true_prob_draw / true_prob_away,
            'prob_ratio_home_draw': true_prob_home / true_prob_draw,
            'log_odds_home_draw': np.log(home_odds) - np.log(draw_odds),
            'log_odds_draw_away': np.log(draw_odds) - np.log(away_odds),
            'bookmaker_margin': total_inv_odds - 1,
            'market_efficiency': 1 / total_inv_odds,
            'uncertainty_index': np.std([true_prob_home, true_prob_away, true_prob_draw]),
            'odds_draw': draw_odds,
            'goals_for_away': 1.4,  # Serie A average
            'recent_form_home': 1.5,
            'recent_form_away': 1.3,
            
            # Enhanced bias correction features
            'true_prob_home': true_prob_home,
            'true_prob_away': true_prob_away,
            'away_advantage': true_prob_away / true_prob_home,
            'home_favorite': 1 if home_odds < away_odds else 0,
            'away_favorite': 1 if away_odds < home_odds else 0,
            'odds_variance': np.var([home_odds, away_odds, draw_odds]),
            'min_odds': min(home_odds, away_odds, draw_odds),
            'max_odds': max(home_odds, away_odds, draw_odds),
            'odds_range': max(home_odds, away_odds, draw_odds) - min(home_odds, away_odds, draw_odds),
            
            # Team context features
            'home_big_club': 1 if home_team in self.big_clubs else 0,
            'away_big_club': 1 if away_team in self.big_clubs else 0,
            'big_club_clash': 1 if (home_team in self.big_clubs and away_team in self.big_clubs) else 0,
            'relegation_battle': 1 if (home_team in self.relegation_teams or away_team in self.relegation_teams) else 0,
            
            # Form and probabilistic features
            'form_difference': 1.5 - 1.3,  # Default difference
            'form_ratio': 1.5 / 1.4,
            'outcome_entropy': -np.sum([true_prob_home, true_prob_away, true_prob_draw] * 
                                     np.log([true_prob_home, true_prob_away, true_prob_draw] + 1e-8)),
            'home_dominance': true_prob_home - max(true_prob_away, true_prob_draw),
            'away_dominance': true_prob_away - max(true_prob_home, true_prob_draw),
            'draw_dominance': true_prob_draw - max(true_prob_home, true_prob_away),
            'overround': total_inv_odds,
            'profit_margin': total_inv_odds - 1,
            'fair_odds_home': 1 / true_prob_home,
            'fair_odds_away': 1 / true_prob_away,
            'fair_odds_draw': 1 / true_prob_draw
        }}
        
        return pd.DataFrame([features])
    
    def predict_match(self, home_odds: float, away_odds: float, draw_odds: float,
                     home_team: str = None, away_team: str = None) -> Dict:
        """Make enhanced prediction with bias correction"""
        
        # Engineer features
        features_df = self.engineer_prediction_features(
            home_odds, away_odds, draw_odds, home_team, away_team
        )
        
        # Generate predictions
        probabilities = self.model.predict(features_df.values, 
                                         num_iteration=self.model.best_iteration)
        probs = probabilities[0]
        
        # Get prediction
        predicted_class = np.argmax(probs)
        predicted_outcome = self.class_names[predicted_class]
        confidence = probs[predicted_class]
        
        # Enhanced recommendation logic
        meets_confidence = confidence >= self.confidence_threshold
        
        # Match context
        context = []
        if home_team and away_team:
            if home_team in self.big_clubs and away_team in self.big_clubs:
                context.append("🔥 Big Club Derby")
            elif home_team in self.big_clubs:
                context.append(f"🏆 {{home_team}} (Big Club) at home")
            elif away_team in self.big_clubs:
                context.append(f"🏆 {{away_team}} (Big Club) away")
            
            if home_team in self.relegation_teams or away_team in self.relegation_teams:
                context.append("⚠️ Relegation Battle")
        
        return {{
            'prediction': predicted_outcome,
            'confidence': confidence,
            'probabilities': {{
                'Home Win': probs[0],
                'Away Win': probs[1], 
                'Draw': probs[2]
            }},
            'recommended': meets_confidence,
            'context': ' | '.join(context) if context else "Regular match",
            'model_version': 'Improved Serie A v{self.timestamp}'
        }}

# Example usage
if __name__ == "__main__":
    predictor = ImprovedSerieAPredictor()
    
    # Test prediction
    result = predictor.predict_match(
        home_odds=2.10, away_odds=3.20, draw_odds=3.80,
        home_team="Juventus", away_team="Napoli"
    )
    
    print(f"\\nTest Prediction:")
    print(f"Match: Juventus vs Napoli")
    print(f"Prediction: {{result['prediction']}} ({{result['confidence']:.1%}})")
    print(f"Context: {{result['context']}}")
    print(f"Recommended: {{result['recommended']}}")
'''
        
        interface_filename = f"improved_serie_a_predictor_{self.timestamp}.py"
        with open(interface_filename, 'w') as f:
            f.write(interface_code)
        
        print(f"✅ Prediction interface: {interface_filename}")
        return interface_filename
        
    def run_full_pipeline(self):
        """Execute the complete improved model pipeline"""
        print(f"\n🚀 RUNNING COMPLETE IMPROVED SERIE A PIPELINE")
        print("=" * 60)
        
        # Step 1: Load and analyze
        df = self.load_and_analyze_data()
        
        # Step 2: Enhanced feature engineering
        df_enhanced = self.engineer_advanced_features(df)
        
        # Step 3: Train improved model
        model, importance_df, val_pred_proba, y_val = self.train_improved_model(df_enhanced)
        
        # Step 4: Create prediction interface
        interface_file = self.create_prediction_interface(model, importance_df)
        
        print(f"\n🏆 IMPROVED SERIE A MODEL COMPLETE!")
        print("=" * 50)
        print(f"✅ Bias correction implemented")
        print(f"✅ Class imbalance addressed") 
        print(f"✅ Advanced features engineered")
        print(f"✅ Cross-validation verified")
        print(f"🎯 Ready for validation testing!")
        
        return model, importance_df

if __name__ == "__main__":
    builder = ImprovedSerieAModelBuilder()
    model, importance_df = builder.run_full_pipeline() 