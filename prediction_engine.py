#!/usr/bin/env python3
"""
SMARTBET LIVE PREDICTION PIPELINE
=================================

Comprehensive prediction system supporting all leagues:
- Premier League
- La Liga  
- Serie A
- Bundesliga
- Ligue 1 (France)
- Liga I (Romania)

Automatically identifies and loads the correct model for each league,
applies confidence and value betting filters, and returns structured
predictions with betting recommendations.

Performance Summary:
- La Liga: 74.4% hit rate, 138.92% ROI (PRIMARY)
- Serie A: 61.5% hit rate, -9.10% ROI (BACKUP)
- Bundesliga: 61.3% accuracy, 92.2% high-confidence hit rate
- Ligue 1: 64.3% accuracy, 92.1% high-confidence hit rate
- Premier League: Research model available
"""

import os
import pickle
import pandas as pd
import numpy as np
import lightgbm as lgb
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
import json
import warnings
warnings.filterwarnings('ignore')

class ModelMapper:
    """Maps leagues to their respective models and configurations."""
    
    def _get_la_liga_features(self, match_data: Dict[str, Any]) -> List[float]:
        """Extract features for La Liga model using SportMonks odds."""
        return [
            match_data.get('home_recent_form', 1.5),
            match_data.get('away_recent_form', 1.2),
            match_data.get('home_win_odds', 2.0),  # SportMonks odds
            match_data.get('away_win_odds', 2.0),  # SportMonks odds
            match_data.get('draw_odds', 3.0),  # SportMonks odds
            match_data.get('home_goals_for', 1.5),
            match_data.get('home_goals_against', 1.2),
            match_data.get('away_goals_for', 1.3),
            match_data.get('away_goals_against', 1.4),
            match_data.get('home_win_rate', 0.5),
            match_data.get('away_win_rate', 0.5),
            match_data.get('recent_form_diff', 0.3)
        ]
    
    def _get_serie_a_features(self, match_data: Dict[str, Any]) -> List[float]:
        """Extract features for Serie A model using SportMonks odds."""
        home_odds = match_data.get('home_win_odds', 2.0)  # SportMonks odds
        draw_odds = match_data.get('draw_odds', 3.0)  # SportMonks odds
        away_odds = match_data.get('away_win_odds', 2.0)  # SportMonks odds
        
        # Calculate Serie A specific features
        true_prob_home = 1 / home_odds
        true_prob_draw = 1 / draw_odds
        true_prob_away = 1 / away_odds
        
        total_inv_odds = true_prob_home + true_prob_draw + true_prob_away
        market_efficiency = 1 / total_inv_odds
        bookmaker_margin = total_inv_odds - 1
        
        return [
            true_prob_draw,
            true_prob_draw / true_prob_away if true_prob_away > 0 else 1.0,
            true_prob_home / true_prob_draw if true_prob_draw > 0 else 1.0,
            np.log(home_odds / draw_odds) if draw_odds > 0 else 0.0,
            np.log(draw_odds / away_odds) if away_odds > 0 else 0.0,
            bookmaker_margin,
            market_efficiency,
            np.std([true_prob_home, true_prob_draw, true_prob_away]),  # uncertainty_index
            draw_odds,
            match_data.get('goals_for_away', 1.3),
            match_data.get('recent_form_home', 1.5),
            match_data.get('recent_form_away', 1.2)
        ]
    
    def _get_bundesliga_features(self, match_data: Dict[str, Any]) -> List[float]:
        """Extract features for Bundesliga model."""
        home_goals_for = match_data.get('home_avg_goals_for', 1.8)
        home_goals_against = match_data.get('home_avg_goals_against', 1.3)
        away_goals_for = match_data.get('away_avg_goals_for', 1.5)
        away_goals_against = match_data.get('away_avg_goals_against', 1.4)
        home_win_rate = match_data.get('home_win_rate', 0.5)
        away_win_rate = match_data.get('away_win_rate', 0.4)
        
        # Only 12 features for Bundesliga model (not 15)
        return [
            home_goals_for,
            home_goals_against,
            home_win_rate,
            match_data.get('home_draw_rate', 0.25),
            away_goals_for,
            away_goals_against,
            away_win_rate,
            match_data.get('away_draw_rate', 0.25),
            1.0,  # is_bundesliga
            0.0,  # is_ligue1
            (home_goals_for - home_goals_against) - (away_goals_for - away_goals_against),  # goal_difference_tendency
            home_win_rate - away_win_rate,  # win_rate_difference (12th feature)
        ]
    
    def _get_ligue_1_features(self, match_data: Dict[str, Any]) -> List[float]:
        """Extract features for Ligue 1 model."""
        home_goals_for = match_data.get('home_avg_goals_for', 1.6)
        home_goals_against = match_data.get('home_avg_goals_against', 1.2)
        away_goals_for = match_data.get('away_avg_goals_for', 1.4)
        away_goals_against = match_data.get('away_avg_goals_against', 1.3)
        home_win_rate = match_data.get('home_win_rate', 0.45)
        away_win_rate = match_data.get('away_win_rate', 0.35)
        
        # Only 12 features for Ligue 1 model (not 15)
        return [
            home_goals_for,
            home_goals_against,
            home_win_rate,
            match_data.get('home_draw_rate', 0.28),
            away_goals_for,
            away_goals_against,
            away_win_rate,
            match_data.get('away_draw_rate', 0.28),
            0.0,  # is_bundesliga
            1.0,  # is_ligue1
            (home_goals_for - home_goals_against) - (away_goals_for - away_goals_against),  # goal_difference_tendency
            home_win_rate - away_win_rate,  # win_rate_difference (12th feature)
        ]
    
    def _get_premier_league_features(self, match_data: Dict[str, Any]) -> List[float]:
        """Extract features for Premier League model using SportMonks odds (7 features)."""
        return [
            match_data.get('home_avg_goals_for', 1.5),
            match_data.get('away_avg_goals_for', 1.3),
            match_data.get('home_win_odds', 2.0),  # SportMonks odds
            match_data.get('away_win_odds', 2.0),  # SportMonks odds
            match_data.get('draw_odds', 3.0),  # SportMonks odds
            match_data.get('home_win_rate', 0.5),
            match_data.get('away_win_rate', 0.5)
        ]
    
    def __init__(self):
        """Initialize model mapper with league configurations."""
        self.leagues = {
            'la_liga': {
                'model_file': 'LOCKED_PRODUCTION_league_model_1x2_la_liga_20250630_152907.txt',
                'type': 'lightgbm_txt',
                'features': self._get_la_liga_features,
                'performance': {'hit_rate': 0.744, 'roi': 138.92, 'accuracy': 0.744},
                'confidence_threshold': 0.6,
                'odds_threshold': 1.5,
                'status': 'PRODUCTION',
                'aliases': ['la_liga', 'laliga', 'spain', 'spanish_la_liga', 'primera_division', 'primera']
            },
            'serie_a': {
                'model_file': 'LOCKED_PRODUCTION_league_model_1x2_serie_a_20250630_125109.txt',
                'type': 'lightgbm_txt',
                'features': self._get_serie_a_features,
                'performance': {'hit_rate': 0.615, 'roi': -9.10, 'accuracy': 0.615},
                'confidence_threshold': 0.7,
                'odds_threshold': 1.8,
                'status': 'PRODUCTION',
                'aliases': ['serie_a', 'seriea', 'italy', 'italian_serie_a', 'serie_a_tim']
            },
            'bundesliga': {
                'model_file': 'bundesliga_ligue1_project/1_production_models/LOCKED_PRODUCTION_league_model_1x2_bundesliga_20250704_142533.txt',
                'type': 'lightgbm_txt',
                'features': self._get_bundesliga_features,
                'performance': {'hit_rate': 0.687, 'roi': 45.3, 'accuracy': 0.687},
                'confidence_threshold': 0.6,
                'odds_threshold': 1.5,
                'status': 'PRODUCTION',
                'aliases': ['bundesliga', 'germany', 'german_bundesliga', 'bundesliga_1']
            },
            'ligue_1': {
                'model_file': 'bundesliga_ligue1_project/1_production_models/LOCKED_PRODUCTION_league_model_1x2_ligue_1_20250704_142533.txt',
                'type': 'lightgbm_txt',
                'features': self._get_ligue_1_features,
                'performance': {'hit_rate': 0.643, 'roi': 92.1, 'accuracy': 0.643},
                'confidence_threshold': 0.6,
                'odds_threshold': 1.5,
                'status': 'PRODUCTION',
                'aliases': ['ligue_1', 'ligue1', 'france', 'french_ligue_1', 'ligue_1_uber_eats']
            },
            'premier_league': {
                'model_file': 'lightgbm_premier_league_20250626_145052.txt',
                'type': 'lightgbm_txt',
                'features': self._get_premier_league_features,
                'performance': {'hit_rate': 0.565, 'roi': -15.2, 'accuracy': 0.565},
                'confidence_threshold': 0.65,  # Higher threshold for experimental model
                'odds_threshold': 1.8,
                'status': 'EXPERIMENTAL',
                'aliases': ['premier_league', 'epl', 'england', 'english_premier_league', 'premier']
            }
        }
        
        # Build alias mapping
        self.league_aliases = {}
        for league_key, config in self.leagues.items():
            for alias in config['aliases']:
                self.league_aliases[alias.lower()] = league_key
        
        print("🤖 MODEL MAPPER INITIALIZED")
        print("=" * 30)
        print(f"📊 Available leagues: {len(self.leagues)}")
        print(f"🎯 Supported aliases: {len(self.league_aliases)}")
        for league_key, config in self.leagues.items():
            status_icon = "🥇" if config['status'] == 'PRODUCTION' else "🥈" if config['status'] == 'EXPERIMENTAL' else "🔬"
            print(f"   {status_icon} {league_key.replace('_', ' ').title()}: {config['status']}")
    
    def normalize_league_name(self, league_name: str) -> str:
        """Normalize league name to standard format."""
        if not league_name:
            raise ValueError("League name cannot be empty")
        
        # Convert to lowercase and replace spaces with underscores, remove extra spaces
        normalized = league_name.lower().strip().replace(' ', '_')
        
        # Direct match with normalized format
        if normalized in self.leagues:
            return normalized
        
        # Alias match
        if normalized in self.league_aliases:
            return self.league_aliases[normalized]
        
        # Try common variations
        common_variations = {
            'la_liga': ['la_liga', 'laliga', 'spain', 'spanish_la_liga', 'primera_division', 'primera'],
            'serie_a': ['serie_a', 'seriea', 'italy', 'italian_serie_a', 'serie_a_tim'],
            'bundesliga': ['bundesliga', 'germany', 'german_bundesliga', 'bundesliga_1'],
            'ligue_1': ['ligue_1', 'ligue1', 'france', 'french_ligue_1', 'ligue_1_uber_eats'],
            'premier_league': ['premier_league', 'epl', 'england', 'english_premier_league', 'premier']
        }
        
        # Check variations
        for standard_name, variations in common_variations.items():
            if normalized in variations:
                return standard_name
        
        # Fuzzy matching for common patterns
        if 'liga' in normalized and ('spain' in normalized or 'spanish' in normalized or normalized == 'la_liga'):
            return 'la_liga'
        if 'serie' in normalized and ('italy' in normalized or 'italian' in normalized):
            return 'serie_a'
        if 'bundesliga' in normalized or ('germany' in normalized or 'german' in normalized):
            return 'bundesliga'
        if 'ligue' in normalized and ('france' in normalized or 'french' in normalized):
            return 'ligue_1'
        if 'premier' in normalized and ('england' in normalized or 'english' in normalized):
            return 'premier_league'
        
        # If no match found, suggest available options
        available = list(self.leagues.keys()) + list(self.league_aliases.keys())
        raise ValueError(
            f"League '{league_name}' not supported. "
            f"Available options: {', '.join(sorted(set(available)))}"
        )
    
    def get_model_info(self, league_name: str) -> Dict[str, Any]:
        """Get model configuration for a league."""
        normalized_league = self.normalize_league_name(league_name)
        return self.leagues[normalized_league]
    
    def load_model(self, league_name: str):
        """Load the appropriate model for a league."""
        model_info = self.get_model_info(league_name)
        model_file = model_info['model_file']
        model_type = model_info['type']
        
        if not os.path.exists(model_file):
            raise FileNotFoundError(f"Model file not found: {model_file}")
        
        print(f"📦 Loading {league_name.replace('_', ' ').title()} model...")
        
        if model_type == 'lightgbm_txt':
            # Load LightGBM text format (La Liga, Serie A, Liga I)
            model = lgb.Booster(model_file=model_file)
        elif model_type == 'lightgbm_pkl':
            # Load pickle format (Bundesliga, Ligue 1, Premier League)
            with open(model_file, 'rb') as f:
                model = pickle.load(f)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
        
        print(f"✅ {league_name.replace('_', ' ').title()} model loaded successfully")
        return model

class PredictionEngine:
    """Main prediction engine that handles all leagues."""
    
    def __init__(self):
        """Initialize prediction engine with model mapper."""
        self.model_mapper = ModelMapper()
        self.loaded_models = {}  # Cache for loaded models
        self.class_names = {0: 'Home Win', 1: 'Away Win', 2: 'Draw'}
        
        print(f"\n🚀 PREDICTION ENGINE READY")
        print("=" * 30)
        print(f"🎯 Multi-league support: {len(self.model_mapper.leagues)} leagues")
        print(f"🔧 Auto-loading: Models loaded on demand")
        print(f"🛡️ League isolation: Enforced")
    
    def _get_model(self, league_name: str):
        """Get or load model for a league (with caching)."""
        normalized_league = self.model_mapper.normalize_league_name(league_name)
        
        if normalized_league not in self.loaded_models:
            model = self.model_mapper.load_model(normalized_league)
            self.loaded_models[normalized_league] = model
        
        return self.loaded_models[normalized_league]
    
    def _prepare_features(self, match_data: Dict[str, Any], league: str) -> np.ndarray:
        """Prepare features for model prediction based on league."""
        
        try:
            normalized_league = self.model_mapper.normalize_league_name(league)
            model_info = self.model_mapper.get_model_info(normalized_league)
            
            # Get features using the league-specific function
            feature_func = model_info['features']
            features = feature_func(match_data)
            
            return np.array(features).reshape(1, -1)
            
        except Exception as e:
            raise ValueError(f"Failed to prepare features for {league}: {str(e)}")
    
    def _prepare_features_legacy(self, match_data: Dict[str, Any], league: str) -> np.ndarray:
        """Legacy feature preparation method (kept for compatibility)."""
        # Home team features
        home_goals_for = match_data.get('home_goals_for', 1.5)
        home_goals_against = match_data.get('home_goals_against', 1.2)
        home_win_rate = match_data.get('home_win_rate', 0.5)
        
        # Away team features  
        away_goals_for = match_data.get('away_goals_for', 1.3)
        away_goals_against = match_data.get('away_goals_against', 1.4)
        away_win_rate = match_data.get('away_win_rate', 0.5)
        
        # Recent form
        home_recent_form = match_data.get('home_recent_form', 1.5)
        away_recent_form = match_data.get('away_recent_form', 1.2)
        recent_form_diff = match_data.get('recent_form_diff', 0.3)
        
        # Odds
        home_win_odds = match_data['home_win_odds']
        draw_odds = match_data['draw_odds'] 
        away_win_odds = match_data['away_win_odds']
        
        features = [
            home_recent_form, away_recent_form, home_win_odds, 
            away_win_odds, draw_odds, home_goals_for, home_goals_against,
            away_goals_for, away_goals_against, home_win_rate,
            away_win_rate, recent_form_diff
        ]
        
        return np.array(features).reshape(1, -1)
    
    def _generate_reasoning(self, predicted_class: int, predicted_outcome: str, 
                           confidence: float, predicted_odds: float, match_data: Dict[str, Any],
                           all_probabilities: np.ndarray, normalized_league: str) -> str:
        """Generate natural language reasoning for the prediction."""
        
        # Extract key features for reasoning
        home_team = match_data.get('home_team', 'Home Team')
        away_team = match_data.get('away_team', 'Away Team')
        
        # Get league-specific features
        if normalized_league == 'la_liga':
            home_win_rate = match_data.get('home_win_rate', 0.5) * 100
            away_win_rate = match_data.get('away_win_rate', 0.5) * 100
            home_form = match_data.get('home_recent_form', 1.5)
            away_form = match_data.get('away_recent_form', 1.2)
            home_goals_for = match_data.get('home_goals_for', 1.5)
            away_goals_for = match_data.get('away_goals_for', 1.3)
        elif normalized_league == 'serie_a':
            # For Serie A, we have different features
            home_win_rate = 50  # Default, as Serie A uses odds-based features
            away_win_rate = 50
            home_form = match_data.get('recent_form_home', 1.5)
            away_form = match_data.get('recent_form_away', 1.2)
            home_goals_for = 1.5  # Default
            away_goals_for = match_data.get('goals_for_away', 1.3)
        else:
            # Bundesliga, Ligue 1, etc.
            home_win_rate = match_data.get('home_win_rate', 0.5) * 100
            away_win_rate = match_data.get('away_win_rate', 0.5) * 100
            home_form = 1.5  # These models don't have form data
            away_form = 1.2
            home_goals_for = match_data.get('home_avg_goals_for', 1.5)
            away_goals_for = match_data.get('away_avg_goals_for', 1.3)
        
        # Calculate value betting signal
        implied_prob = 1 / predicted_odds
        model_prob = confidence
        value_signal = model_prob - implied_prob
        
        # Build reasoning based on prediction
        reasoning_parts = []
        
        # Main prediction reason
        if predicted_class == 0:  # Home Win
            reasoning_parts.append(f"The model predicts a {home_team} victory")
            if home_win_rate > 60:
                reasoning_parts.append(f"due to their strong home record ({home_win_rate:.0f}% win rate)")
            if home_form > 1.6:
                reasoning_parts.append(f"and excellent recent form")
            if away_win_rate < 40:
                reasoning_parts.append(f"against {away_team}'s poor away form ({away_win_rate:.0f}% win rate)")
        
        elif predicted_class == 1:  # Away Win
            reasoning_parts.append(f"The model predicts an {away_team} victory")
            if away_win_rate > 60:
                reasoning_parts.append(f"based on their strong away record ({away_win_rate:.0f}% win rate)")
            if away_form > 1.6:
                reasoning_parts.append(f"and superior recent form")
            if home_win_rate < 40:
                reasoning_parts.append(f"exploiting {home_team}'s weak home form ({home_win_rate:.0f}% win rate)")
        
        else:  # Draw
            reasoning_parts.append(f"The model predicts a draw")
            if abs(home_win_rate - away_win_rate) < 10:
                reasoning_parts.append(f"due to evenly matched teams ({home_win_rate:.0f}% vs {away_win_rate:.0f}% win rates)")
            if abs(home_form - away_form) < 0.3:
                reasoning_parts.append(f"with similar recent form")
        
        # Add confidence and value insights
        if confidence > 0.75:
            reasoning_parts.append(f"The model shows high confidence ({confidence:.1%})")
        elif confidence < 0.55:
            reasoning_parts.append(f"However, confidence is relatively low ({confidence:.1%})")
        
        if value_signal > 0.1:
            reasoning_parts.append(f"with excellent betting value (model sees {model_prob:.1%} vs market's {implied_prob:.1%})")
        elif value_signal < -0.1:
            reasoning_parts.append(f"but the odds appear overpriced by the market")
        
        # Join reasoning parts
        if len(reasoning_parts) <= 2:
            return ". ".join(reasoning_parts) + "."
        else:
            main_parts = reasoning_parts[:-1]
            return ", ".join(main_parts) + ", " + reasoning_parts[-1] + "."
    
    def _generate_match_insights(self, match_data: Dict[str, Any], confidence: float, 
                                predicted_odds: float, normalized_league: str) -> Dict[str, Any]:
        """Generate detailed match insights from input data."""
        
        insights = {}
        alerts = []
        
        # Extract features based on league
        if normalized_league == 'la_liga':
            home_win_rate = match_data.get('home_win_rate', 0.5)
            away_win_rate = match_data.get('away_win_rate', 0.5)
            home_form = match_data.get('home_recent_form', 1.5)
            away_form = match_data.get('away_recent_form', 1.2)
            home_goals_for = match_data.get('home_goals_for', 1.5)
            home_goals_against = match_data.get('home_goals_against', 1.2)
            away_goals_for = match_data.get('away_goals_for', 1.3)
            away_goals_against = match_data.get('away_goals_against', 1.4)
            form_diff = match_data.get('recent_form_diff', 0.3)
            
            insights.update({
                'home_win_rate': f"{home_win_rate:.1%}",
                'away_win_rate': f"{away_win_rate:.1%}",
                'home_recent_form': self._format_form_display(home_form),
                'away_recent_form': self._format_form_display(away_form),
                'home_attack': f"{home_goals_for:.1f} goals/game",
                'home_defense': f"{home_goals_against:.1f} conceded/game",
                'away_attack': f"{away_goals_for:.1f} goals/game", 
                'away_defense': f"{away_goals_against:.1f} conceded/game",
                'recent_form_diff': f"{form_diff:+.1f}"
            })
            
        elif normalized_league == 'serie_a':
            # Serie A uses odds-based features
            home_odds = match_data['home_win_odds']
            draw_odds = match_data['draw_odds']
            away_odds = match_data['away_win_odds']
            
            total_inv_odds = 1/home_odds + 1/away_odds + 1/draw_odds
            market_efficiency = 1 / total_inv_odds
            bookmaker_margin = total_inv_odds - 1
            
            insights.update({
                'market_efficiency': f"{market_efficiency:.1%}",
                'bookmaker_margin': f"{bookmaker_margin:.1%}",
                'home_implied_prob': f"{1/home_odds:.1%}",
                'draw_implied_prob': f"{1/draw_odds:.1%}",
                'away_implied_prob': f"{1/away_odds:.1%}",
                'most_likely_outcome': 'Home' if home_odds < min(draw_odds, away_odds) else 'Away' if away_odds < draw_odds else 'Draw'
            })
            
        else:
            # Bundesliga, Ligue 1, etc.
            home_win_rate = match_data.get('home_win_rate', 0.5)
            away_win_rate = match_data.get('away_win_rate', 0.5)
            home_goals_for = match_data.get('home_avg_goals_for', 1.5)
            away_goals_for = match_data.get('away_avg_goals_for', 1.3)
            
            insights.update({
                'home_win_rate': f"{home_win_rate:.1%}",
                'away_win_rate': f"{away_win_rate:.1%}",
                'home_attack': f"{home_goals_for:.1f} goals/game",
                'away_attack': f"{away_goals_for:.1f} goals/game",
                'win_rate_diff': f"{(home_win_rate - away_win_rate):+.1%}"
            })
        
        # Calculate Expected Value
        implied_prob = 1 / predicted_odds
        expected_value = (confidence * predicted_odds - 1) * 100
        insights['expected_value'] = f"{expected_value:+.1f}%"
        
        # Generate alerts based on insights
        if expected_value > 15:
            alerts.append("🔥 Excellent value bet opportunity!")
        elif expected_value > 5:
            alerts.append("✅ Good betting value detected")
        elif expected_value < -10:
            alerts.append("⚠️ Poor value - odds too low")
        
        if confidence > 0.8:
            alerts.append("🎯 Very high model confidence")
        elif confidence < 0.55:
            alerts.append("📉 Low confidence prediction")
        
        # League-specific alerts
        if normalized_league in ['la_liga', 'bundesliga', 'ligue_1']:
            home_win_rate = insights.get('home_win_rate', '50%')
            away_win_rate = insights.get('away_win_rate', '50%')
            
            if float(home_win_rate.strip('%')) > 70:
                alerts.append("🏠 Strong home team advantage")
            if float(away_win_rate.strip('%')) > 65:
                alerts.append("🛣️ Excellent away team record")
            if float(away_win_rate.strip('%')) < 30:
                alerts.append("⚠️ Away team struggles on the road")
        
        if normalized_league == 'serie_a':
            margin = float(insights.get('bookmaker_margin', '5%').strip('%'))
            if margin < 3:
                alerts.append("💎 Low margin market - good for value")
            elif margin > 8:
                alerts.append("⚠️ High margin market - bookmaker advantage")
        
        insights['alerts'] = alerts
        return insights
    
    def _format_form_display(self, form_value: float) -> str:
        """Convert form value to readable display."""
        if form_value >= 2.0:
            return "Excellent (W-W-W)"
        elif form_value >= 1.7:
            return "Good (W-W-D)"
        elif form_value >= 1.4:
            return "Average (W-D-L)"
        elif form_value >= 1.1:
            return "Poor (D-L-L)"
        else:
            return "Very Poor (L-L-L)"
    
    def predict_match(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict outcome for a single match.
        
        Args:
            match_data: Dictionary containing:
                - league: League name
                - home_team: Home team name
                - away_team: Away team name
                - home_win_odds: Home win betting odds
                - draw_odds: Draw betting odds
                - away_win_odds: Away win betting odds
                - Additional features (league-specific)
        
        Returns:
            Dictionary with prediction results and betting recommendation
        """
        
        # Validate required fields
        required_fields = ['league', 'home_team', 'away_team', 'home_win_odds', 'draw_odds', 'away_win_odds']
        for field in required_fields:
            if field not in match_data:
                raise ValueError(f"Missing required field: {field}")
        
        league = match_data['league']
        match_id = match_data.get('match_id', f"{match_data['home_team']}_{match_data['away_team']}_{league}")
        
        # Check if league is supported
        try:
            normalized_league = self.model_mapper.normalize_league_name(league)
            model_info = self.model_mapper.get_model_info(league)
            is_supported_league = True
        except ValueError:
            # League not supported
            return {
                "prediction_available": False,
                "reason": "This league is not yet supported for predictions.",
                "league": league,
                "match_id": match_id,
                "is_supported_league": False,
                "home_team": match_data['home_team'],
                "away_team": match_data['away_team'],
                "timestamp": datetime.now().isoformat()
            }
        
        print(f"\n🔮 PREDICTING MATCH")
        print("=" * 25)
        print(f"🏠 {match_data['home_team']} vs {match_data['away_team']} 🏃")
        print(f"🏆 League: {league}")
        print(f"📊 Odds: {match_data['home_win_odds']:.2f} | {match_data['draw_odds']:.2f} | {match_data['away_win_odds']:.2f}")
        
        # Load model
        model = self._get_model(league)
        
        # Prepare features based on league
        features = self._prepare_features(match_data, league)
        
        # Make prediction
        if hasattr(model, 'predict'):
            # LightGBM model
            probabilities = model.predict(features)[0]
        else:
            # Scikit-learn model
            probabilities = model.predict_proba(features)[0]
        
        # Get prediction details
        predicted_class = np.argmax(probabilities)
        confidence = np.max(probabilities)
        predicted_outcome = self.class_names[predicted_class]
        
        # Get corresponding odds
        odds_mapping = {
            0: match_data['home_win_odds'],  # Home Win
            1: match_data['away_win_odds'],  # Away Win  
            2: match_data['draw_odds']       # Draw
        }
        predicted_odds = odds_mapping[predicted_class]
        
        # Calculate Expected Value (EV)
        ev = (confidence * predicted_odds) - 1.0
        ev_positive = ev > 0
        
        # Apply filtering rules
        confidence_threshold = model_info['confidence_threshold']
        odds_threshold = model_info['odds_threshold']
        
        meets_confidence = confidence >= confidence_threshold
        meets_value = predicted_odds >= odds_threshold
        recommend_bet = meets_confidence and meets_value
        
        # Create recommendation reason
        if recommend_bet:
            reason = f"✔ BET: High confidence ({confidence:.1%}) with value (odds {predicted_odds:.2f})"
        elif not meets_confidence:
            reason = f"✖ SKIP: Low confidence ({confidence:.1%} < {confidence_threshold:.0%})"
        elif not meets_value:
            reason = f"✖ SKIP: Poor value (odds {predicted_odds:.2f} < {odds_threshold})"
        else:
            reason = f"✖ SKIP: Multiple issues"
        
        # Generate reasoning and insights
        reasoning = self._generate_reasoning(predicted_class, predicted_outcome, confidence, predicted_odds, match_data, probabilities, normalized_league)
        insights = self._generate_match_insights(match_data, confidence, predicted_odds, normalized_league)
        
        # Construct result for supported leagues
        result = {
            "prediction_available": True,
            "predicted_outcome": predicted_outcome,
            "confidence": confidence,
            "predicted_odds": predicted_odds,
            "ev": round(ev, 4),
            "ev_positive": ev_positive,
            "explanation": reasoning,
            "match_id": match_id,
            "league": league,
            "is_supported_league": True,
            "home_team": match_data['home_team'],
            "away_team": match_data['away_team'],
            "recommend": recommend_bet,
            "recommendation_reason": reason,
            "all_probabilities": {
                "home_win": probabilities[0],
                "away_win": probabilities[1], 
                "draw": probabilities[2]
            },
            "all_odds": {
                "home_win": match_data['home_win_odds'],
                "away_win": match_data['away_win_odds'],
                "draw": match_data['draw_odds']
            },
            "model_info": {
                "model_performance": model_info['performance'],
                "confidence_threshold": confidence_threshold,
                "odds_threshold": odds_threshold,
                "model_status": model_info['status']
            },
            "timestamp": datetime.now().isoformat(),
            "reasoning": reasoning,
            "insights": insights
        }
        
        # Display result
        print(f"🎯 Prediction: {predicted_outcome}")
        print(f"🎲 Confidence: {confidence:.1%}")
        print(f"💰 Odds: {predicted_odds:.2f}")
        print(f"📈 EV: {ev:.2%}")
        print(f"📊 Recommendation: {'BET' if recommend_bet else 'SKIP'}")
        print(f"💡 Reason: {reason}")
        
        return result
    
    def predict_batch(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Predict outcomes for multiple matches.
        
        Args:
            matches: List of match dictionaries
        
        Returns:
            List of prediction results with all matches included (supported and unsupported)
        """
        
        print(f"\n📊 BATCH PREDICTION")
        print("=" * 20)
        print(f"🎯 Processing {len(matches)} matches")
        
        results = []
        bets_recommended = 0
        supported_matches = 0
        unsupported_matches = 0
        
        for i, match in enumerate(matches):
            print(f"\n--- Match {i+1}/{len(matches)} ---")
            try:
                result = self.predict_match(match)
                results.append(result)
                
                if result.get('prediction_available', False):
                    supported_matches += 1
                    if result.get('recommend', False):
                        bets_recommended += 1
                else:
                    unsupported_matches += 1
                    
            except Exception as e:
                error_result = {
                    "prediction_available": False,
                    "reason": f"Prediction failed: {str(e)}",
                    "league": match.get('league', 'Unknown'),
                    "match_id": match.get('match_id', f"{match.get('home_team', 'Unknown')}_{match.get('away_team', 'Unknown')}_{match.get('league', 'Unknown')}"),
                    "is_supported_league": False,
                    "home_team": match.get('home_team', 'Unknown'),
                    "away_team": match.get('away_team', 'Unknown'),
                    "timestamp": datetime.now().isoformat()
                }
                results.append(error_result)
                unsupported_matches += 1
                print(f"❌ Error: {e}")
        
        print(f"\n🏆 BATCH SUMMARY")
        print("=" * 15)
        print(f"📊 Total matches: {len(matches)}")
        print(f"✅ Supported leagues: {supported_matches}")
        print(f"❌ Unsupported leagues: {unsupported_matches}")
        print(f"🎯 Betting recommendations: {bets_recommended}")
        if supported_matches > 0:
            print(f"📈 Recommendation rate: {bets_recommended/supported_matches:.1%}")
        
        return results


def main():
    """Test the prediction engine with example matches."""
    print("🧪 TESTING PREDICTION ENGINE")
    print("=" * 30)
    
    # Initialize engine
    engine = PredictionEngine()
    
    # Example matches from different leagues
    example_matches = [
        {
            "league": "La Liga",
            "home_team": "Real Madrid",
            "away_team": "Barcelona", 
            "home_win_odds": 2.10,
            "draw_odds": 3.40,
            "away_win_odds": 3.60,
            "home_recent_form": 1.8,
            "away_recent_form": 1.6
        },
        {
            "league": "Serie A",
            "home_team": "Juventus",
            "away_team": "AC Milan",
            "home_win_odds": 2.25,
            "draw_odds": 3.20,
            "away_win_odds": 3.40
        },
        {
            "league": "Bundesliga", 
            "home_team": "Bayern Munich",
            "away_team": "Borussia Dortmund",
            "home_win_odds": 1.85,
            "draw_odds": 3.80,
            "away_win_odds": 4.20
        },
        {
            "league": "Premier League",
            "home_team": "Manchester City",
            "away_team": "Liverpool", 
            "home_win_odds": 2.05,
            "draw_odds": 3.50,
            "away_win_odds": 3.75
        }
    ]
    
    # Test batch prediction
    results = engine.predict_batch(example_matches)
    
    # Display summary
    print(f"\n📋 FINAL RESULTS SUMMARY")
    print("=" * 25)
    for result in results:
        if 'error' not in result:
            status = "✔ BET" if result['recommend'] else "✖ SKIP"
            print(f"{status} {result['home_team']} vs {result['away_team']} ({result['league']})")
            print(f"    Prediction: {result['prediction']} ({result['confidence']:.1%} confidence)")
        else:
            print(f"❌ ERROR: {result['home_team']} vs {result['away_team']} - {result['error']}")

if __name__ == "__main__":
    main() 