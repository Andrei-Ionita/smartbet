"""
Premium ML Model Manager for SmartBet Django Integration
Handles model loading, caching, and predictions
"""

import pickle
import os
import pandas as pd
import numpy as np
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime
import logging
from typing import Dict, List, Tuple, Optional, Any
from .models import Match, OddsSnapshot, Team, League

logger = logging.getLogger(__name__)

class PremiumModelManager:
    """
    Manages the premium ML model for Django integration.
    Handles model loading, feature engineering, and predictions.
    """
    
    def __init__(self):
        self.model = None
        self.model_package = None
        self.is_loaded = False
        self.model_path = self._get_model_path()
        self.cache_timeout = 3600  # 1 hour cache
        
    def _get_model_path(self) -> str:
        """Get the path to the premium model file."""
        base_dir = getattr(settings, 'BASE_DIR', os.getcwd())
        model_path = os.path.join(
            base_dir, 
            'premium_model', 
            'smartbet_market_grade_20250611_103326',
            'lgbm_smartbet_production.pkl'
        )
        return model_path
    
    def load_model(self, force_reload: bool = False) -> bool:
        """
        Load the premium model into memory.
        
        Args:
            force_reload: Force reload even if already loaded
            
        Returns:
            bool: True if model loaded successfully
        """
        cache_key = 'premium_model_loaded'
        
        if self.is_loaded and not force_reload:
            logger.info("Premium model already loaded")
            return True
            
        # Check cache first
        if not force_reload:
            cached_package = cache.get(cache_key)
            if cached_package:
                self.model_package = cached_package
                self.model = cached_package['model']
                self.is_loaded = True
                logger.info("Premium model loaded from cache")
                return True
        
        try:
            logger.info(f"Loading premium model from: {self.model_path}")
            
            if not os.path.exists(self.model_path):
                logger.error(f"Model file not found: {self.model_path}")
                return False
            
            with open(self.model_path, 'rb') as f:
                self.model_package = pickle.load(f)
            
            self.model = self.model_package['model']
            self.is_loaded = True
            
            # Cache the model package
            cache.set(cache_key, self.model_package, self.cache_timeout)
            
            logger.info(f"Premium model loaded successfully!")
            logger.info(f"Model version: {self.model_package.get('version', 'unknown')}")
            logger.info(f"Features: {len(self.model_package['feature_columns'])}")
            logger.info(f"Classes: {self.model_package['classes']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load premium model: {str(e)}")
            self.is_loaded = False
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        if not self.is_loaded:
            return {'status': 'not_loaded', 'error': 'Model not loaded'}
        
        try:
            performance = self.model_package.get('performance', {})
            data_info = self.model_package.get('data_info', {})
            
            return {
                'status': 'loaded',
                'version': self.model_package.get('version', 'unknown'),
                'feature_count': len(self.model_package['feature_columns']),
                'classes': self.model_package['classes'],
                'accuracy': performance.get('test_accuracy', 0),
                'training_samples': data_info.get('training_samples', 0),
                'created_at': self.model_package.get('rebuilt_at', 'unknown'),
                'model_path': self.model_path
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def engineer_features(self, match: Match) -> Optional[pd.DataFrame]:
        """
        Engineer features for a match prediction.
        
        Args:
            match: Django Match object
            
        Returns:
            pd.DataFrame: Feature vector for prediction
        """
        if not self.is_loaded:
            logger.error("Model not loaded for feature engineering")
            return None
        
        try:
            # Get latest odds
            odds_snapshot = match.odds_snapshots.filter(
                bookmaker="Bet365"
            ).order_by('-fetched_at').first()
            
            if not odds_snapshot:
                logger.warning(f"No odds found for match {match.id}")
                return None
            
            # Create feature dictionary
            features = {}
            
            # Basic match info
            features['league_encoded'] = self._encode_league(match.league.name_en)
            features['weekday'] = match.kickoff.weekday()
            features['kickoff_hour'] = match.kickoff.hour
            features['is_weekend'] = 1 if match.kickoff.weekday() >= 5 else 0
            features['month'] = match.kickoff.month
            features['year'] = match.kickoff.year
            features['quarter'] = (match.kickoff.month - 1) // 3 + 1
            features['is_evening_game'] = 1 if match.kickoff.hour >= 18 else 0
            
            # Odds features
            features['odds_home'] = odds_snapshot.odds_home
            features['odds_draw'] = odds_snapshot.odds_draw
            features['odds_away'] = odds_snapshot.odds_away
            features['bookmaker'] = 0  # Bet365 encoded as 0
            
            # Derived odds features
            features['odds_min'] = min(odds_snapshot.odds_home, odds_snapshot.odds_draw, odds_snapshot.odds_away)
            features['odds_max'] = max(odds_snapshot.odds_home, odds_snapshot.odds_draw, odds_snapshot.odds_away)
            features['odds_range'] = features['odds_max'] - features['odds_min']
            features['odds_variance'] = np.var([odds_snapshot.odds_home, odds_snapshot.odds_draw, odds_snapshot.odds_away])
            
            # Implied probabilities
            total_inv_odds = 1/odds_snapshot.odds_home + 1/odds_snapshot.odds_draw + 1/odds_snapshot.odds_away
            features['implied_prob_home'] = (1/odds_snapshot.odds_home) / total_inv_odds
            features['implied_prob_draw'] = (1/odds_snapshot.odds_draw) / total_inv_odds
            features['implied_prob_away'] = (1/odds_snapshot.odds_away) / total_inv_odds
            features['bookmaker_margin'] = total_inv_odds - 1
            
            # True probabilities (normalized)
            features['true_prob_home'] = 1/odds_snapshot.odds_home
            features['true_prob_draw'] = 1/odds_snapshot.odds_draw
            features['true_prob_away'] = 1/odds_snapshot.odds_away
            
            # Log odds
            features['log_odds_home_away'] = np.log(odds_snapshot.odds_home / odds_snapshot.odds_away)
            features['log_odds_home_draw'] = np.log(odds_snapshot.odds_home / odds_snapshot.odds_draw)
            features['log_odds_draw_away'] = np.log(odds_snapshot.odds_draw / odds_snapshot.odds_away)
            
            # Probability ratios
            features['prob_ratio_home_away'] = features['implied_prob_home'] / features['implied_prob_away']
            features['prob_ratio_home_draw'] = features['implied_prob_home'] / features['implied_prob_draw']
            features['prob_ratio_draw_away'] = features['implied_prob_draw'] / features['implied_prob_away']
            
            # Favorite indicators
            features['favorite_home'] = 1 if odds_snapshot.odds_home < min(odds_snapshot.odds_draw, odds_snapshot.odds_away) else 0
            features['favorite_away'] = 1 if odds_snapshot.odds_away < min(odds_snapshot.odds_home, odds_snapshot.odds_draw) else 0
            features['heavy_favorite'] = 1 if features['odds_min'] < 1.5 else 0
            features['close_match'] = 1 if abs(odds_snapshot.odds_home - odds_snapshot.odds_away) < 0.5 else 0
            
            # Market indicators
            features['market_efficiency'] = 1 / features['bookmaker_margin'] if features['bookmaker_margin'] > 0 else 1
            features['odds_home_level'] = self._categorize_odds(odds_snapshot.odds_home)
            features['odds_away_level'] = self._categorize_odds(odds_snapshot.odds_away)
            features['odds_draw_level'] = self._categorize_odds(odds_snapshot.odds_draw)
            
            # Historical features (simplified - use match model fields if available)
            features['recent_form_home'] = match.team_form_home or 0.5
            features['recent_form_away'] = match.team_form_away or 0.5
            features['goals_for_home'] = match.avg_goals_home or 1.5
            features['goals_against_home'] = 1.5 - (match.avg_goals_home or 1.5) + 1.0
            features['goals_for_away'] = match.avg_goals_away or 1.5
            features['goals_against_away'] = 1.5 - (match.avg_goals_away or 1.5) + 1.0
            
            # H2H features (simplified)
            features['h2h_home_wins'] = 3  # Default values
            features['h2h_draws'] = 2
            features['h2h_away_wins'] = 3
            features['form_difference'] = features['recent_form_home'] - features['recent_form_away']
            
            # Strength features
            features['attack_strength_home'] = features['goals_for_home'] / 2.0
            features['attack_strength_away'] = features['goals_for_away'] / 2.0
            features['defense_strength_home'] = 2.0 / features['goals_against_home']
            features['defense_strength_away'] = 2.0 / features['goals_against_away']
            
            # Additional market features
            features['overround'] = total_inv_odds
            features['balanced_market'] = 1 if abs(features['implied_prob_home'] - features['implied_prob_away']) < 0.1 else 0
            features['uncertainty_index'] = np.std([features['implied_prob_home'], features['implied_prob_draw'], features['implied_prob_away']])
            
            # League prestige (simplified)
            league_prestige_map = {
                'Premier League': 1.0,
                'Romanian Liga I': 0.7,
                'Championship': 0.8,
                'La Liga': 1.0,
                'Serie A': 1.0,
                'Bundesliga': 1.0,
                'Ligue 1': 0.9
            }
            features['league_prestige'] = league_prestige_map.get(match.league.name_en, 0.6)
            
            # Convert to DataFrame with correct feature order
            feature_columns = self.model_package['feature_columns']
            feature_df = pd.DataFrame([features])
            
            # Ensure all expected features are present
            for col in feature_columns:
                if col not in feature_df.columns:
                    feature_df[col] = 0.0  # Default value for missing features
            
            # Select only the features the model expects
            feature_df = feature_df[feature_columns]
            
            return feature_df
            
        except Exception as e:
            logger.error(f"Feature engineering failed for match {match.id}: {str(e)}")
            return None
    
    def predict_match(self, match: Match) -> Optional[Dict[str, Any]]:
        """
        Generate prediction for a match.
        
        Args:
            match: Django Match object
            
        Returns:
            Dict with prediction results or None if failed
        """
        if not self.is_loaded:
            if not self.load_model():
                return None
        
        try:
            # Engineer features
            features = self.engineer_features(match)
            if features is None:
                return None
            
            # Make prediction
            probabilities = self.model.predict_proba(features)[0]
            prediction = self.model.predict(features)[0]
            
            # Decode prediction
            label_encoder = self.model_package['label_encoder']
            predicted_outcome = label_encoder.inverse_transform([prediction])[0]
            
            # Map probabilities to outcomes
            classes = self.model_package['classes']
            prob_dict = {
                'home': probabilities[classes.index('home')],
                'draw': probabilities[classes.index('draw')],
                'away': probabilities[classes.index('away')]
            }
            
            # Calculate confidence
            max_prob = max(prob_dict.values())
            confidence = 'high' if max_prob > 0.6 else 'medium' if max_prob > 0.45 else 'low'
            
            return {
                'predicted_outcome': predicted_outcome,
                'probabilities': prob_dict,
                'confidence': confidence,
                'max_probability': max_prob,
                'model_version': self.model_package.get('version', 'unknown'),
                'generated_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Prediction failed for match {match.id}: {str(e)}")
            return None
    
    def predict_batch(self, matches: List[Match]) -> List[Dict[str, Any]]:
        """
        Generate predictions for multiple matches.
        
        Args:
            matches: List of Django Match objects
            
        Returns:
            List of prediction dictionaries
        """
        if not self.is_loaded:
            if not self.load_model():
                return []
        
        results = []
        for match in matches:
            prediction = self.predict_match(match)
            if prediction:
                prediction['match_id'] = match.id
                prediction['match_info'] = {
                    'home_team': match.home_team.name_en,
                    'away_team': match.away_team.name_en,
                    'kickoff': match.kickoff.isoformat(),
                    'league': match.league.name_en
                }
                results.append(prediction)
        
        return results
    
    def _encode_league(self, league_name: str) -> int:
        """Encode league name to integer."""
        league_map = {
            'Premier League': 0,
            'Romanian Liga I': 1,
            'Championship': 2,
            'La Liga': 3,
            'Serie A': 4,
            'Bundesliga': 5,
            'Ligue 1': 6
        }
        return league_map.get(league_name, 7)  # 7 for unknown leagues
    
    def _categorize_odds(self, odds: float) -> int:
        """Categorize odds into levels."""
        if odds < 1.5:
            return 0  # Very low
        elif odds < 2.0:
            return 1  # Low
        elif odds < 3.0:
            return 2  # Medium
        elif odds < 5.0:
            return 3  # High
        else:
            return 4  # Very high


# Global instance
premium_model_manager = PremiumModelManager() 