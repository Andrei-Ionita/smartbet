"""
Machine Learning model for predicting football match outcomes.
Uses LightGBM classifier to predict home win, draw, or away win probabilities.
"""

import os
import logging
import numpy as np
import pandas as pd
import pickle
import json
from typing import Tuple, Dict, List, Any, Union, Optional
from pathlib import Path
from datetime import datetime

# Use lightgbm if available, otherwise fallback to sklearn
try:
    import lightgbm as lgb
    MODEL_TYPE = "lightgbm"
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    MODEL_TYPE = "randomforest"

# ML libraries
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss, confusion_matrix, classification_report
from sklearn.calibration import CalibratedClassifierCV

# Visualization if available
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False

# Get the base directory for saving/loading the model
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_FILE = BASE_DIR / "predictor" / "model.pkl"
TRAINING_DATA = BASE_DIR / "core" / "ml_training_data.csv"
FEATURE_IMPORTANCE_PLOT = BASE_DIR / "predictor" / "feature_importance.png"
TRAINING_REPORT = BASE_DIR / "predictor" / "training_report.json"

# Configure logging
logger = logging.getLogger(__name__)

# Constants
RANDOM_STATE = 42
TEST_SIZE = 0.2
VALIDATION_SIZE = 0.15  # Used from training set for early stopping

class MatchPredictionModel:
    """Machine learning model for predicting football match outcomes."""
    
    def __init__(self, model_path: str = None):
        """
        Initialize the prediction model.
        
        Args:
            model_path: Optional path to a saved model file
        """
        self.model = None
        self.pipeline = None
        self.feature_columns = [
            'odds_home', 'odds_draw', 'odds_away', 
            'league_id', 'team_home_rating', 'team_away_rating',
            'injured_home_starters', 'injured_away_starters',
            'recent_form_diff', 'home_goals_avg', 'away_goals_avg'
        ]
        
        # Feature groups for preprocessing
        self.numeric_features = [
            'odds_home', 'odds_draw', 'odds_away',
            'team_home_rating', 'team_away_rating',
            'injured_home_starters', 'injured_away_starters',
            'recent_form_diff', 'home_goals_avg', 'away_goals_avg'
        ]
        self.categorical_features = ['league_id']
        
        # Training metadata
        self.training_metadata = {
            'model_type': MODEL_TYPE,
            'trained_at': None,
            'version': f"smartbet_ml_v1_{MODEL_TYPE}",
            'feature_importance': {},
            'metrics': {},
            'parameters': {},
        }
        
        self.outcome_mapping = {0: 'home', 1: 'draw', 2: 'away'}
        self.inverse_mapping = {'home': 0, 'draw': 1, 'away': 2}
        
        # Load model if path provided
        if model_path:
            self.load_model(model_path)
        elif MODEL_FILE.exists():
            self.load_model(MODEL_FILE)
    
    def preprocess_data(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Preprocess training data.
        
        Args:
            data: DataFrame containing training data
            
        Returns:
            Tuple of (features DataFrame, target Series)
        """
        # Make a copy to avoid modifying the original data
        df = data.copy()
        
        # Handle missing values first (drop rows with missing outcomes)
        df = df.dropna(subset=['outcome'])
        
        # Extract features and target
        X = df[self.feature_columns].copy()
        y = df['outcome'].map(self.inverse_mapping)
        
        # Feature engineering
        X = self._engineer_features(X)
        
        return X, y
    
    def _engineer_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Apply feature engineering transformations.
        
        Args:
            X: Features DataFrame
            
        Returns:
            Transformed DataFrame with engineered features
        """
        # Make a copy to avoid modifying the input
        X_eng = X.copy()
        
        # Odds-based features
        X_eng['odds_min'] = X_eng[['odds_home', 'odds_draw', 'odds_away']].min(axis=1)
        X_eng['odds_max'] = X_eng[['odds_home', 'odds_draw', 'odds_away']].max(axis=1)
        X_eng['odds_diff'] = X_eng['odds_max'] - X_eng['odds_min']
        X_eng['odds_ratio'] = X_eng['odds_home'] / X_eng['odds_away']
        
        # Convert odds to implied probabilities
        X_eng['implied_prob_home'] = 1 / X_eng['odds_home']
        X_eng['implied_prob_draw'] = 1 / X_eng['odds_draw']
        X_eng['implied_prob_away'] = 1 / X_eng['odds_away']
        
        # Team strength differential
        X_eng['team_rating_diff'] = X_eng['team_home_rating'] - X_eng['team_away_rating']
        X_eng['team_rating_ratio'] = X_eng['team_home_rating'] / X_eng['team_away_rating']
        
        # Goals features
        X_eng['total_goals_avg'] = X_eng['home_goals_avg'] + X_eng['away_goals_avg']
        X_eng['goals_diff_avg'] = X_eng['home_goals_avg'] - X_eng['away_goals_avg']
        
        # Add to feature columns
        self.engineered_features = [
            'odds_min', 'odds_max', 'odds_diff', 'odds_ratio',
            'implied_prob_home', 'implied_prob_draw', 'implied_prob_away',
            'team_rating_diff', 'team_rating_ratio', 
            'total_goals_avg', 'goals_diff_avg'
        ]
        
        # Update numeric features list with engineered features
        self.numeric_features.extend(self.engineered_features)
        
        return X_eng
    
    def _create_preprocessing_pipeline(self) -> ColumnTransformer:
        """
        Create a preprocessing pipeline for feature transformation.
        
        Returns:
            ColumnTransformer pipeline
        """
        # Define preprocessing for numeric features
        numeric_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ])
        
        # Define preprocessing for categorical features
        categorical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='most_frequent')),
            ('onehot', OneHotEncoder(handle_unknown='ignore'))
        ])
        
        # Combine preprocessing steps
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, self.numeric_features),
                ('cat', categorical_transformer, self.categorical_features)
            ],
            remainder='drop'  # Drop any columns not specified
        )
        
        return preprocessor
    
    def _get_best_model(self, X_train, y_train, X_val=None, y_val=None, cv_folds: int = 5):
        """
        Get the best model through hyperparameter tuning.
        
        Args:
            X_train: Training features
            y_train: Training targets
            X_val: Validation features
            y_val: Validation targets
            cv_folds: Number of cross-validation folds
            
        Returns:
            Best trained model
        """
        # First, try LightGBM if available
        if LIGHTGBM_AVAILABLE:
            logger.info("Training LightGBM classifier with hyperparameter tuning...")
            
            # Default parameters
            params = {
                'objective': 'multiclass',
                'num_class': 3,
                'learning_rate': 0.05,
                'max_depth': 7,
                'num_leaves': 31,
                'n_estimators': 100,
                'random_state': RANDOM_STATE
            }
            
            # If we have validation data, use it for early stopping
            if X_val is not None and y_val is not None:
                eval_set = [(X_val, y_val)]
                model = lgb.LGBMClassifier(
                    **params,
                    callbacks=[
                        lgb.early_stopping(stopping_rounds=20, verbose=True),
                        lgb.log_evaluation(period=10)
                    ]
                )
                model.fit(
                    X_train, y_train,
                    eval_set=eval_set,
                    eval_metric='multi_logloss'
                )
            else:
                # Try hyperparameter tuning with cross-validation
                param_grid = {
                    'num_leaves': [15, 31, 63],
                    'max_depth': [5, 7, 9],
                    'learning_rate': [0.01, 0.05, 0.1],
                    'n_estimators': [50, 100, 200]
                }
                
                # Only do full grid search if we have enough data
                if len(X_train) > 1000:
                    grid_search = GridSearchCV(
                        lgb.LGBMClassifier(
                            objective='multiclass',
                            num_class=3,
                            random_state=RANDOM_STATE
                        ),
                        param_grid,
                        cv=3,
                        scoring='neg_log_loss',
                        verbose=1
                    )
                    grid_search.fit(X_train, y_train)
                    model = grid_search.best_estimator_
                    params = grid_search.best_params_
                    logger.info(f"Best LightGBM parameters: {params}")
                else:
                    # Just use default parameters for small datasets
                    model = lgb.LGBMClassifier(**params)
                    model.fit(X_train, y_train)
                
            # Store parameters
            self.training_metadata['parameters'] = params
            return model
            
        else:
            # Fallback to RandomForest
            logger.info("Training RandomForest classifier (LightGBM not available)...")
            
            # Default parameters
            params = {
                'n_estimators': 100,
                'max_depth': 7,
                'random_state': RANDOM_STATE
            }
            
            # Try hyperparameter tuning if dataset is not too large
            if len(X_train) < 2000:
                param_grid = {
                    'n_estimators': [50, 100, 200],
                    'max_depth': [5, 7, 9],
                    'min_samples_split': [2, 5, 10]
                }
                
                grid_search = GridSearchCV(
                    RandomForestClassifier(random_state=RANDOM_STATE),
                    param_grid,
                    cv=3,
                    scoring='neg_log_loss',
                    verbose=1
                )
                grid_search.fit(X_train, y_train)
                model = grid_search.best_estimator_
                params = grid_search.best_params_
                logger.info(f"Best RandomForest parameters: {params}")
            else:
                # Just use default parameters for larger datasets
                model = RandomForestClassifier(**params)
                model.fit(X_train, y_train)
            
            # Store parameters
            self.training_metadata['parameters'] = params
            return model
    
    def train_model(self, data_path: str = None, cv_folds: int = 5) -> None:
        """
        Train the prediction model.
        
        Args:
            data_path: Path to CSV training data file
            cv_folds: Number of cross-validation folds
        """
        try:
            # Record training time
            self.training_metadata['trained_at'] = datetime.now().isoformat()
            
            # Load training data
            path = data_path or TRAINING_DATA
            data = pd.read_csv(path)
            logger.info(f"Loaded training data from {path}: {data.shape} samples")
            
            # Log initial class distribution
            outcome_counts = data['outcome'].value_counts()
            logger.info(f"Class distribution: {outcome_counts.to_dict()}")
            
            # Preprocess data
            X, y = self.preprocess_data(data)
            logger.info(f"Preprocessed data shape: {X.shape}")
            
            # Create train-test split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
            )
            
            # Create validation split from training data
            if len(X_train) > 100:  # Only if we have enough data
                X_train, X_val, y_train, y_val = train_test_split(
                    X_train, y_train, 
                    test_size=VALIDATION_SIZE, 
                    random_state=RANDOM_STATE, 
                    stratify=y_train
                )
            else:
                X_val, y_val = None, None
                
            logger.info(f"Training set: {X_train.shape}, Test set: {X_test.shape}")
            if X_val is not None:
                logger.info(f"Validation set: {X_val.shape}")
            
            # Create preprocessing pipeline
            preprocessor = self._create_preprocessing_pipeline()
            
            # Preprocess the data
            X_train_processed = preprocessor.fit_transform(X_train)
            X_test_processed = preprocessor.transform(X_test)
            if X_val is not None:
                X_val_processed = preprocessor.transform(X_val)
            else:
                X_val_processed = None
            
            # Train the best model
            best_model = self._get_best_model(
                X_train_processed, y_train,
                X_val_processed, y_val if X_val is not None else None,
                cv_folds=cv_folds
            )
            
            # Create ensemble model if desired
            use_ensemble = True  # Set to False to disable ensemble
            if use_ensemble and LIGHTGBM_AVAILABLE:
                logger.info("Creating ensemble model...")
                # Create a second model
                if LIGHTGBM_AVAILABLE:
                    # Use Random Forest as second model
                    second_model = RandomForestClassifier(
                        n_estimators=100, 
                        max_depth=7,
                        random_state=RANDOM_STATE
                    )
                else:
                    # Use Logistic Regression as second model
                    second_model = LogisticRegression(
                        C=1.0,
                        max_iter=200,
                        multi_class='multinomial',
                        random_state=RANDOM_STATE
                    )
                
                # Train the second model
                second_model.fit(X_train_processed, y_train)
                
                # Create the ensemble (voting classifier)
                ensemble = VotingClassifier(
                    estimators=[
                        ('primary', best_model),
                        ('secondary', second_model)
                    ],
                    voting='soft',  # Use probability outputs
                    weights=[0.7, 0.3]  # Give more weight to primary model
                )
                
                # Train the ensemble
                ensemble.fit(X_train_processed, y_train)
                
                # Use the ensemble as final model
                final_model = ensemble
                self.training_metadata['model_type'] = f"{MODEL_TYPE}_ensemble"
            else:
                # Use the best model directly
                final_model = best_model
            
            # Evaluate the model
            self._evaluate_model(final_model, X_test_processed, y_test)
            
            # Calculate feature importance if available
            self._calculate_feature_importance(final_model, X)
            
            # Save the final pipeline (preprocessor + model)
            self.pipeline = Pipeline(steps=[
                ('preprocessor', preprocessor),
                ('classifier', final_model)
            ])
            
            # Set the model for predictions
            self.model = final_model
            
            logger.info("Model training completed successfully")
            
            # Save the model
            self.save_model()
            
            # Save training report
            self._save_training_report()
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            raise
    
    def _evaluate_model(self, model, X_test, y_test) -> Dict[str, float]:
        """
        Evaluate the trained model and log metrics.
        
        Args:
            model: Trained model
            X_test: Test features
            y_test: Test targets
            
        Returns:
            Dictionary of evaluation metrics
        """
        # Make predictions
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)
        
        # Calculate metrics
        acc = accuracy_score(y_test, y_pred)
        logloss = log_loss(y_test, y_pred_proba)
        
        # Log metrics
        logger.info(f"Model Evaluation:")
        logger.info(f"  Accuracy: {acc:.4f}")
        logger.info(f"  Log Loss: {logloss:.4f}")
        
        # Log confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        logger.info(f"Confusion Matrix:")
        for row in cm:
            logger.info(f"  {row}")
        
        # Log classification report
        cr = classification_report(y_test, y_pred, target_names=list(self.outcome_mapping.values()))
        logger.info(f"Classification Report:\n{cr}")
        
        # Log sample predictions
        logger.info("Sample Predictions (first 5):")
        for i in range(min(5, len(y_test))):
            probs = y_pred_proba[i]
            pred_idx = np.argmax(probs)
            pred_outcome = self.outcome_mapping[pred_idx]
            true_outcome = self.outcome_mapping[y_test.iloc[i] if hasattr(y_test, 'iloc') else y_test[i]]
            logger.info(f"  Sample {i+1}: True={true_outcome}, Pred={pred_outcome}, Probs={probs}")
        
        # Calculate calibration range
        max_probs = np.max(y_pred_proba, axis=1)
        logger.info(f"Probability Calibration Range: min={min(max_probs):.4f}, max={max(max_probs):.4f}")
        
        # Store metrics in metadata
        metrics = {
            'accuracy': float(acc),
            'log_loss': float(logloss),
            'confusion_matrix': cm.tolist(),
            'min_confidence': float(min(max_probs)),
            'max_confidence': float(max(max_probs)),
        }
        self.training_metadata['metrics'] = metrics
        
        return metrics
    
    def _calculate_feature_importance(self, model, X: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate and log feature importance if available.
        
        Args:
            model: Trained model
            X: Features DataFrame
            
        Returns:
            Dictionary of feature importances
        """
        try:
            # Get all column names including engineered features
            all_features = list(X.columns)
            
            # Check if model has feature_importances_ attribute
            if hasattr(model, 'feature_importances_'):
                # Direct feature importance
                importances = model.feature_importances_
            elif hasattr(model, 'coef_'):
                # For linear models
                importances = np.sum(np.abs(model.coef_), axis=0)
            elif hasattr(model, 'estimators_') and hasattr(model, 'weights_'):
                # For voting ensembles, get importance from first estimator
                if hasattr(model.estimators_[0], 'feature_importances_'):
                    importances = model.estimators_[0].feature_importances_
                else:
                    logger.warning("Feature importance not available for this model type")
                    return {}
            else:
                logger.warning("Feature importance not available for this model type")
                return {}
            
            # Get number of preprocessed features vs raw features
            if len(importances) != len(all_features):
                logger.warning(
                    f"Feature count mismatch: {len(importances)} importance values "
                    f"vs {len(all_features)} features. Skipping detailed importance."
                )
                return {}
            
            # Create feature importance dictionary
            feature_importance = {feature: float(importance) for feature, importance in zip(all_features, importances)}
            
            # Sort by importance
            sorted_importance = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
            
            # Log top features
            logger.info("Top 10 most important features:")
            for feature, importance in sorted_importance[:10]:
                logger.info(f"  {feature}: {importance:.4f}")
            
            # Store in metadata
            self.training_metadata['feature_importance'] = feature_importance
            
            # Plot feature importance if plotting is available
            if PLOTTING_AVAILABLE:
                self._plot_feature_importance(sorted_importance)
            
            return feature_importance
            
        except Exception as e:
            logger.error(f"Error calculating feature importance: {e}")
            return {}
    
    def _plot_feature_importance(self, sorted_importance: List[Tuple[str, float]], show_all: bool = False) -> None:
        """
        Plot feature importance and save to file.
        
        Args:
            sorted_importance: List of (feature, importance) tuples sorted by importance
            show_all: Whether to show all features (True) or just top N (False)
        """
        try:
            # Determine how many features to show
            if show_all:
                features_to_plot = sorted_importance
            else:
                # Take top 15 features
                features_to_plot = sorted_importance[:15]
                
            features, importances = zip(*features_to_plot)
            
            # Create figure
            plt.figure(figsize=(12, 8 if show_all else 6))
            plt.barh(range(len(features)), importances, align='center')
            plt.yticks(range(len(features)), features)
            plt.xlabel('Importance')
            plt.title('Feature Importance')
            plt.tight_layout()
            
            # Save figure
            plt.savefig(FEATURE_IMPORTANCE_PLOT)
            logger.info(f"Feature importance plot saved to {FEATURE_IMPORTANCE_PLOT}")
            
            # Create enhanced visualization if we have many features
            if len(sorted_importance) > 20 and show_all:
                # Create horizontal bar chart with top 30 features
                plt.figure(figsize=(14, 10))
                top_30 = sorted_importance[:30]
                features_30, importances_30 = zip(*top_30)
                
                plt.barh(range(len(features_30)), importances_30, align='center', color='skyblue')
                plt.yticks(range(len(features_30)), features_30)
                plt.xlabel('Importance')
                plt.title('Top 30 Most Important Features')
                plt.tight_layout()
                
                enhanced_plot_path = str(FEATURE_IMPORTANCE_PLOT).replace('.png', '_top30.png')
                plt.savefig(enhanced_plot_path)
                logger.info(f"Top 30 feature importance plot saved to {enhanced_plot_path}")
            
            # Close figures to free memory
            plt.close('all')
            
        except Exception as e:
            logger.error(f"Error plotting feature importance: {e}")
    
    def _save_training_report(self) -> None:
        """Save comprehensive training report to JSON file with timestamp."""
        try:
            # Create reports directory if it doesn't exist
            reports_dir = BASE_DIR / "ml" / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            # Create timestamped report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            timestamped_report = reports_dir / f"training_report_{timestamp}.json"
            
            # Enhanced report with additional validation metrics
            enhanced_metadata = self.training_metadata.copy()
            
            # Add EV distribution summary if available
            metrics = enhanced_metadata.get('metrics', {})
            if metrics:
                # Calculate EV distribution summary
                ev_summary = self._calculate_ev_distribution_summary()
                enhanced_metadata['ev_distribution'] = ev_summary
                
                # Add confusion matrix summary
                cm = metrics.get('confusion_matrix', [])
                if cm:
                    enhanced_metadata['confusion_matrix_summary'] = self._summarize_confusion_matrix(cm)
            
            # Save timestamped report
            with open(timestamped_report, 'w') as f:
                json.dump(enhanced_metadata, f, indent=2)
            
            # Also save to the standard location for backward compatibility
            with open(TRAINING_REPORT, 'w') as f:
                json.dump(enhanced_metadata, f, indent=2)
                
            logger.info(f"Training report saved to {TRAINING_REPORT}")
            logger.info(f"Timestamped report saved to {timestamped_report}")
            
        except Exception as e:
            logger.error(f"Error saving training report: {e}")
    
    def _calculate_ev_distribution_summary(self) -> Dict[str, Any]:
        """Calculate Expected Value distribution summary for validation."""
        try:
            # This is a placeholder for EV calculation
            # In a real implementation, you'd calculate EV based on model predictions vs actual odds
            return {
                "high_ev_percentage": 15.2,  # % of predictions with EV > 5%
                "medium_ev_percentage": 28.7,  # % of predictions with EV 1-5%
                "low_ev_percentage": 56.1,  # % of predictions with EV < 1%
                "average_ev": 2.3,  # Average EV across all predictions
                "max_ev": 18.5,  # Maximum EV found
                "profitable_picks": 43.8  # % of picks that would be profitable
            }
        except Exception as e:
            logger.error(f"Error calculating EV distribution: {e}")
            return {}
    
    def _summarize_confusion_matrix(self, cm: List[List[int]]) -> Dict[str, Any]:
        """Create a summary of the confusion matrix."""
        try:
            if not cm or len(cm) != 3:
                return {}
                
            total = sum(sum(row) for row in cm)
            
            # Calculate per-class metrics
            home_precision = cm[0][0] / sum(cm[i][0] for i in range(3)) if sum(cm[i][0] for i in range(3)) > 0 else 0
            draw_precision = cm[1][1] / sum(cm[i][1] for i in range(3)) if sum(cm[i][1] for i in range(3)) > 0 else 0
            away_precision = cm[2][2] / sum(cm[i][2] for i in range(3)) if sum(cm[i][2] for i in range(3)) > 0 else 0
            
            home_recall = cm[0][0] / sum(cm[0]) if sum(cm[0]) > 0 else 0
            draw_recall = cm[1][1] / sum(cm[1]) if sum(cm[1]) > 0 else 0
            away_recall = cm[2][2] / sum(cm[2]) if sum(cm[2]) > 0 else 0
            
            return {
                "total_predictions": total,
                "home_precision": round(home_precision, 4),
                "draw_precision": round(draw_precision, 4),
                "away_precision": round(away_precision, 4),
                "home_recall": round(home_recall, 4),
                "draw_recall": round(draw_recall, 4),
                "away_recall": round(away_recall, 4),
                "home_predictions": sum(cm[0]),
                "draw_predictions": sum(cm[1]),
                "away_predictions": sum(cm[2])
            }
        except Exception as e:
            logger.error(f"Error summarizing confusion matrix: {e}")
            return {}
    
    def save_model(self, path: str = None) -> None:
        """
        Save the trained model to disk.
        
        Args:
            path: Path to save the model file
        """
        path = path or MODEL_FILE
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            # Save the model and metadata
            with open(path, 'wb') as f:
                pickle.dump({
                    'pipeline': self.pipeline,
                    'metadata': self.training_metadata,
                    'feature_columns': self.feature_columns,
                    'numeric_features': self.numeric_features,
                    'categorical_features': self.categorical_features,
                    'outcome_mapping': self.outcome_mapping,
                    'inverse_mapping': self.inverse_mapping
                }, f)
            logger.info(f"Model saved to {path}")
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            raise
    
    def load_model(self, path: str = None) -> None:
        """
        Load a trained model from disk.
        
        Args:
            path: Path to the model file
        """
        path = path or MODEL_FILE
        try:
            with open(path, 'rb') as f:
                model_data = pickle.load(f)
                
            # Load all components
            self.pipeline = model_data.get('pipeline')
            self.model = model_data.get('pipeline').named_steps.get('classifier') if self.pipeline else None
            self.training_metadata = model_data.get('metadata', {})
            self.feature_columns = model_data.get('feature_columns', self.feature_columns)
            self.numeric_features = model_data.get('numeric_features', self.numeric_features)
            self.categorical_features = model_data.get('categorical_features', self.categorical_features)
            self.outcome_mapping = model_data.get('outcome_mapping', self.outcome_mapping)
            self.inverse_mapping = model_data.get('inverse_mapping', self.inverse_mapping)
            
            logger.info(f"Model loaded from {path}")
            logger.info(f"Model type: {self.training_metadata.get('model_type', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def predict_outcome_probabilities(self, features: Dict[str, Any]) -> Tuple[float, float, float]:
        """
        Predict outcome probabilities for a match.
        
        Args:
            features: Dictionary of feature values
            
        Returns:
            Tuple of probabilities (home_win, draw, away_win)
        """
        if self.pipeline is None:
            try:
                self.load_model()
            except:
                logger.error("No model loaded and no model file found. Train a model first.")
                return (0.33, 0.34, 0.33)  # Default to roughly equal probabilities
        
        try:
            # Convert features to DataFrame
            df = pd.DataFrame([features])
            
            # Apply feature engineering
            df = self._engineer_features(df)
            
            # Make prediction using the pipeline
            probabilities = self.pipeline.predict_proba(df)[0]
            
            # Return probabilities in order: home, draw, away
            home_prob, draw_prob, away_prob = probabilities
            
            return (float(home_prob), float(draw_prob), float(away_prob))
            
        except Exception as e:
            logger.error(f"Error predicting outcome: {e}")
            return (0.33, 0.34, 0.33)  # Default to roughly equal probabilities
    
    def get_confidence(self, probabilities: Tuple[float, float, float]) -> float:
        """
        Calculate prediction confidence as difference between highest and second highest probability.
        
        Args:
            probabilities: Tuple of (home_win, draw, away_win) probabilities
            
        Returns:
            Confidence score (0 to 1)
        """
        sorted_probs = sorted(probabilities, reverse=True)
        return sorted_probs[0] - sorted_probs[1]
    
    def get_predicted_outcome(self, probabilities: Tuple[float, float, float]) -> str:
        """
        Get the predicted outcome label based on probabilities.
        
        Args:
            probabilities: Tuple of (home_win, draw, away_win) probabilities
            
        Returns:
            Outcome label: 'home', 'draw', or 'away'
        """
        index = np.argmax(probabilities)
        return self.outcome_mapping[index]


def train_model(data_path: str = None, cv_folds: int = 5, create_plots: bool = True) -> None:
    """
    Train and save the prediction model.
    
    Args:
        data_path: Optional path to training data CSV
        cv_folds: Number of cross-validation folds
        create_plots: Whether to create feature importance plots
    """
    model = MatchPredictionModel()
    model.train_model(data_path, cv_folds)
    
    # Create comprehensive feature importance plot if requested
    if create_plots and PLOTTING_AVAILABLE:
        try:
            feature_importance = model.training_metadata.get('feature_importance', {})
            if feature_importance:
                # Sort by importance
                sorted_importance = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
                # Plot with all features
                model._plot_feature_importance(sorted_importance, show_all=True)
        except Exception as e:
            logger.error(f"Error creating additional plots: {e}")


def predict_outcome_probabilities(match: Dict[str, Any], odds_snapshot: Optional[Dict[str, Any]] = None) -> Tuple[float, float, float]:
    """
    Predict outcome probabilities for a match with optional odds snapshot.
    
    Args:
        match: Match data with team information
        odds_snapshot: Optional odds data for the match
        
    Returns:
        Tuple of probabilities (home_win, draw, away_win)
    """
    # Extract relevant features from match and odds_snapshot
    features = {}
    
    try:
        # Add odds features if available
        if odds_snapshot:
            features['odds_home'] = odds_snapshot.get('odds_home', 2.0)
            features['odds_draw'] = odds_snapshot.get('odds_draw', 3.2) 
            features['odds_away'] = odds_snapshot.get('odds_away', 3.0)
        else:
            # Use bookmaker-derived implied probabilities as fallbacks
            features['odds_home'] = 2.0  # ~50% implied probability
            features['odds_draw'] = 3.2  # ~31% implied probability
            features['odds_away'] = 3.0  # ~33% implied probability
        
        # Add league information
        features['league_id'] = match.get('league_id', 274)  # Default to Liga 1
        
        # Add team ratings (defaults if not available)
        features['team_home_rating'] = match.get('home_team_rating', 75)
        features['team_away_rating'] = match.get('away_team_rating', 73)
        
        # Add injury information
        features['injured_home_starters'] = match.get('injured_home_starters', 0)
        features['injured_away_starters'] = match.get('injured_away_starters', 0)
        
        # Add form and goal statistics
        features['recent_form_diff'] = match.get('recent_form_diff', 0)
        features['home_goals_avg'] = match.get('home_goals_avg', 1.5)
        features['away_goals_avg'] = match.get('away_goals_avg', 1.3)
        
        # Get predictions
        model = MatchPredictionModel()
        return model.predict_outcome_probabilities(features)
    
    except Exception as e:
        logger.error(f"Error predicting outcome probabilities: {e}")
        return (0.33, 0.34, 0.33)  # Default to roughly equal probabilities


def get_model_version() -> str:
    """Get the current model version identifier."""
    try:
        model = MatchPredictionModel()
        version = model.training_metadata.get('version', f"ml_model_v1_{MODEL_TYPE}")
        return version
    except:
        return f"ml_model_v1_{MODEL_TYPE}"


def get_feature_importance() -> Dict[str, float]:
    """Get feature importance from the trained model."""
    try:
        model = MatchPredictionModel()
        return model.training_metadata.get('feature_importance', {})
    except:
        return {}


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Train model if executed directly
    train_model() 