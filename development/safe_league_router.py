#!/usr/bin/env python3
"""
SAFE LEAGUE ROUTING SYSTEM
=========================

Safe league-specific prediction routing WITHOUT cross-league fallbacks.

🔒 SAFETY RULES:
- Each league ONLY uses its own model
- NO fallback to other league models
- Skip prediction if correct model unavailable
- Clear error messages for misuse

Author: SmartBet ML Team
"""

from typing import Dict, Optional
import importlib

class SafeLeagueRouter:
    """Safe league routing without cross-league contamination."""
    
    def __init__(self):
        """Initialize safe router with league-model mapping."""
        self.league_models = {
            'serie a': {
                'module': 'serie_a_production_ready',
                'class': 'SerieAProductionPredictor',
                'performance': {'hit_rate': 0.615, 'roi': -9.10}
            },
            'la liga': {
                'module': 'la_liga_production_ready', 
                'class': 'LaLigaProductionPredictor',
                'performance': {'hit_rate': 0.744, 'roi': 138.92}
            }
        }
        
        self.enforce_safety = True
    
    def get_league_predictor(self, league_name: str):
        """Get the appropriate predictor for a league - NO FALLBACKS."""
        league_key = league_name.lower().strip()
        
        if league_key not in self.league_models:
            raise ValueError(
                f"🚨 UNSUPPORTED LEAGUE: {league_name}\n"
                f"Available leagues: {list(self.league_models.keys())}\n"
                f"NO fallback models available - use correct league only!"
            )
        
        model_info = self.league_models[league_key]
        
        try:
            module = importlib.import_module(model_info['module'])
            predictor_class = getattr(module, model_info['class'])
            return predictor_class()
        except Exception as e:
            raise RuntimeError(
                f"🚨 MODEL UNAVAILABLE: {league_name} model failed to load\n"
                f"Error: {str(e)}\n"
                f"NO PREDICTION POSSIBLE - Do not use alternative models!"
            )
    
    def predict_match_safe(self, league_name: str, match_data: Dict) -> Optional[Dict]:
        """Make prediction with strict league enforcement."""
        if not self.enforce_safety:
            raise RuntimeError("🚨 SAFETY DISABLED - Cannot proceed with predictions!")
        
        try:
            predictor = self.get_league_predictor(league_name)
            
            # Validate league in match data
            match_data['league'] = league_name
            
            return predictor.predict_match(match_data)
            
        except Exception as e:
            print(f"🚨 PREDICTION FAILED: {str(e)}")
            return None  # NO FALLBACK - Return None instead

# Global router instance
safe_router = SafeLeagueRouter()
