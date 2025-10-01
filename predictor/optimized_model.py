"""
Optimized ML model for SmartBet predictions with singleton pattern and performance monitoring.
Loads model once per application startup for maximum performance.
"""

import os
import logging
import numpy as np
import pandas as pd
import pickle
import time
from typing import Tuple, Dict, Any, Optional
from pathlib import Path
from threading import Lock

# Import the base model
from .ml_model import MatchPredictionModel, MODEL_FILE

# Configure logging
logger = logging.getLogger(__name__)

class OptimizedMatchPredictor:
    """
    Singleton pattern ML model for optimal performance.
    Loads model once and reuses for all predictions.
    """
    
    _instance = None
    _lock = Lock()
    _model = None
    _load_time = None
    _prediction_count = 0
    _total_inference_time = 0.0
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize_model()
        return cls._instance
    
    def _initialize_model(self):
        """Initialize the ML model once."""
        start_time = time.time()
        
        try:
            logger.info("🚀 Loading ML model for SmartBet predictions...")
            
            # Load the trained model
            self._model = MatchPredictionModel()
            
            # Validate model is loaded
            if self._model.pipeline is None:
                raise ValueError("Model pipeline not loaded successfully")
            
            self._load_time = time.time() - start_time
            
            # Log model info
            model_type = self._model.training_metadata.get('model_type', 'unknown')
            version = self._model.training_metadata.get('version', 'unknown')
            trained_at = self._model.training_metadata.get('trained_at', 'unknown')
            
            logger.info(f"✅ Model loaded successfully!")
            logger.info(f"   📊 Model type: {model_type}")
            logger.info(f"   🔖 Version: {version}")
            logger.info(f"   📅 Trained: {trained_at}")
            logger.info(f"   ⚡ Load time: {self._load_time:.3f}s")
            
            # Log feature importance if available
            feature_importance = self._model.training_metadata.get('feature_importance', {})
            if feature_importance:
                top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]
                logger.info(f"   🏆 Top features: {[f[0] for f in top_features]}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load ML model: {e}")
            self._model = None
            raise
    
    def predict_with_performance_tracking(
        self, 
        features: Dict[str, Any], 
        match_info: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make prediction with comprehensive performance tracking and validation.
        
        Args:
            features: Dictionary of model features
            match_info: Optional match information for logging
            
        Returns:
            Dictionary with predictions, confidence, and performance metrics
        """
        if self._model is None:
            logger.error("❌ Model not loaded. Cannot make predictions.")
            return self._get_fallback_prediction("Model not loaded")
        
        # Start timing
        start_time = time.time()
        
        try:
            # Validate input features
            validation_result = self._validate_features(features, match_info)
            if not validation_result['valid']:
                logger.warning(f"⚠️ Feature validation failed: {validation_result['message']}")
                # Still proceed but log the issue
            
            # Log fallback usage
            if validation_result.get('using_fallbacks'):
                fallback_fields = validation_result.get('fallback_fields', [])
                match_desc = f"{match_info.get('home_team')} vs {match_info.get('away_team')}" if match_info else "Unknown match"
                logger.warning(f"⚠️ Using fallback values for {match_desc}: {fallback_fields}")
            
            # Make prediction using the loaded model
            home_prob, draw_prob, away_prob = self._model.predict_outcome_probabilities(features)
            
            # Calculate additional metrics
            probabilities = (home_prob, draw_prob, away_prob)
            confidence = self._model.get_confidence(probabilities)
            predicted_outcome = self._model.get_predicted_outcome(probabilities)
            
            # Calculate inference time
            inference_time = time.time() - start_time
            
            # Update performance stats
            self._prediction_count += 1
            self._total_inference_time += inference_time
            avg_inference_time = self._total_inference_time / self._prediction_count
            
            # Log performance metrics
            match_desc = f"{match_info.get('home_team')} vs {match_info.get('away_team')}" if match_info else f"Match #{self._prediction_count}"
            logger.info(f"🎯 Prediction #{self._prediction_count} for {match_desc}")
            logger.info(f"   ⚡ Inference time: {inference_time:.4f}s (avg: {avg_inference_time:.4f}s)")
            logger.info(f"   🎲 Outcome: {predicted_outcome} (confidence: {confidence:.3f})")
            logger.info(f"   📊 Probabilities: H={home_prob:.3f}, D={draw_prob:.3f}, A={away_prob:.3f}")
            
            # Return comprehensive results
            return {
                'probabilities': {
                    'home': float(home_prob),
                    'draw': float(draw_prob),
                    'away': float(away_prob)
                },
                'predicted_outcome': predicted_outcome,
                'confidence': float(confidence),
                'model_confidence': float(max(probabilities)),  # Raw max probability
                'performance': {
                    'inference_time': inference_time,
                    'avg_inference_time': avg_inference_time,
                    'prediction_count': self._prediction_count
                },
                'model_info': {
                    'type': self._model.training_metadata.get('model_type', 'unknown'),
                    'version': self._model.training_metadata.get('version', 'unknown'),
                    'load_time': self._load_time
                },
                'feature_validation': validation_result,
                'success': True
            }
            
        except Exception as e:
            inference_time = time.time() - start_time
            logger.error(f"❌ Prediction failed after {inference_time:.4f}s: {e}")
            return self._get_fallback_prediction(f"Prediction error: {str(e)}")
    
    def _validate_features(self, features: Dict[str, Any], match_info: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Validate input features and identify fallback usage.
        
        Args:
            features: Model input features
            match_info: Optional match information
            
        Returns:
            Validation result dictionary
        """
        required_features = [
            'odds_home', 'odds_draw', 'odds_away',
            'league_id', 'team_home_rating', 'team_away_rating',
            'injured_home_starters', 'injured_away_starters',
            'recent_form_diff', 'home_goals_avg', 'away_goals_avg'
        ]
        
        issues = []
        fallback_fields = []
        
        # Check for missing features
        missing_features = [f for f in required_features if f not in features]
        if missing_features:
            issues.append(f"Missing features: {missing_features}")
        
        # Check for common fallback values
        fallback_indicators = {
            'odds_home': [2.0, 2.2],  # Common fallback odds
            'odds_draw': [3.2, 3.3],
            'odds_away': [3.0, 3.1],
            'team_home_rating': [75],  # Default rating
            'team_away_rating': [73, 75],
            'recent_form_diff': [0],   # Default form
            'home_goals_avg': [1.5],   # Default goals
            'away_goals_avg': [1.3, 1.5],
            'injured_home_starters': [0],
            'injured_away_starters': [0]
        }
        
        for feature, fallback_values in fallback_indicators.items():
            if features.get(feature) in fallback_values:
                fallback_fields.append(feature)
        
        # Check odds validity
        odds_home = features.get('odds_home', 0)
        odds_draw = features.get('odds_draw', 0)
        odds_away = features.get('odds_away', 0)
        
        if any(odds <= 1.01 for odds in [odds_home, odds_draw, odds_away]):
            issues.append("Invalid odds values (≤ 1.01)")
        
        # Calculate implied probability sum (should be > 1 due to bookmaker margin)
        if all(odds > 1.01 for odds in [odds_home, odds_draw, odds_away]):
            implied_sum = (1/odds_home) + (1/odds_draw) + (1/odds_away)
            if implied_sum < 0.95 or implied_sum > 1.2:
                issues.append(f"Unusual implied probability sum: {implied_sum:.3f}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'using_fallbacks': len(fallback_fields) > 0,
            'fallback_fields': fallback_fields,
            'message': '; '.join(issues) if issues else 'All features valid'
        }
    
    def _get_fallback_prediction(self, error_reason: str) -> Dict[str, Any]:
        """
        Return fallback prediction when model fails.
        
        Args:
            error_reason: Reason for fallback
            
        Returns:
            Fallback prediction dictionary
        """
        return {
            'probabilities': {
                'home': 0.33,
                'draw': 0.34,
                'away': 0.33
            },
            'predicted_outcome': 'draw',  # Most conservative
            'confidence': 0.01,  # Very low confidence
            'model_confidence': 0.34,
            'performance': {
                'inference_time': 0.0,
                'avg_inference_time': 0.0,
                'prediction_count': self._prediction_count
            },
            'model_info': {
                'type': 'fallback',
                'version': 'emergency_fallback',
                'load_time': 0.0
            },
            'feature_validation': {
                'valid': False,
                'issues': [error_reason],
                'using_fallbacks': True,
                'fallback_fields': [],
                'message': error_reason
            },
            'success': False,
            'error': error_reason
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        return {
            'model_loaded': self._model is not None,
            'load_time': self._load_time,
            'prediction_count': self._prediction_count,
            'total_inference_time': self._total_inference_time,
            'avg_inference_time': self._total_inference_time / max(1, self._prediction_count),
            'model_info': self._model.training_metadata if self._model else {}
        }
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from the loaded model."""
        if self._model:
            return self._model.training_metadata.get('feature_importance', {})
        return {}


# Global instance for easy access
_global_predictor = None

def get_predictor() -> OptimizedMatchPredictor:
    """Get the global optimized predictor instance."""
    global _global_predictor
    if _global_predictor is None:
        _global_predictor = OptimizedMatchPredictor()
    return _global_predictor


def predict_match_optimized(
    features: Dict[str, Any], 
    match_info: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Main prediction function with optimized performance.
    
    Args:
        features: Model input features
        match_info: Optional match information for logging
        
    Returns:
        Comprehensive prediction results
    """
    predictor = get_predictor()
    return predictor.predict_with_performance_tracking(features, match_info)


if __name__ == "__main__":
    # Test the optimized predictor
    logging.basicConfig(level=logging.INFO)
    
    # Test prediction
    test_features = {
        'odds_home': 2.1,
        'odds_draw': 3.2,
        'odds_away': 3.0,
        'league_id': 274,
        'team_home_rating': 78,
        'team_away_rating': 75,
        'injured_home_starters': 1,
        'injured_away_starters': 0,
        'recent_form_diff': 0.2,
        'home_goals_avg': 1.6,
        'away_goals_avg': 1.4
    }
    
    test_match = {
        'home_team': 'Test Home Team',
        'away_team': 'Test Away Team'
    }
    
    result = predict_match_optimized(test_features, test_match)
    print(f"Test prediction result: {result}") 