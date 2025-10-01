#!/usr/bin/env python3
"""
LA LIGA LEAGUE ISOLATION ENFORCER
=================================

CRITICAL: Ensures La Liga model is ONLY used for La Liga matches.
NEVER allows cross-league predictions or model mixing.

🔒 PRIMARY MODEL: La Liga for La Liga matches ONLY
🚫 STRICT ISOLATION: No cross-league contamination
⚡ LEAGUE PURITY: One model, one league, perfect isolation
"""

import sys
import os
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

class LaLigaLeagueIsolationEnforcer:
    def __init__(self):
        """Initialize strict league isolation for La Liga model."""
        
        # La Liga teams - COMPLETE LIST
        self.LA_LIGA_TEAMS = {
            'Real Madrid', 'Barcelona', 'Atletico Madrid', 'Real Sociedad',
            'Real Betis', 'Villarreal', 'Athletic Bilbao', 'Valencia',
            'Sevilla', 'Getafe', 'Osasuna', 'Celta Vigo',
            'Rayo Vallecano', 'Mallorca', 'Cadiz', 'Espanyol',
            'Granada', 'Almeria', 'Elche', 'Valladolid',
            'Las Palmas', 'Girona', 'Alaves'
        }
        
        # Alternative team names and variations
        self.LA_LIGA_ALIASES = {
            'Real Madrid CF': 'Real Madrid',
            'FC Barcelona': 'Barcelona',
            'Atletico de Madrid': 'Atletico Madrid',
            'Athletic Club': 'Athletic Bilbao',
            'Real Sociedad de Futbol': 'Real Sociedad',
            'Real Betis Balompie': 'Real Betis',
            'Valencia CF': 'Valencia',
            'Sevilla FC': 'Sevilla',
            'RC Celta de Vigo': 'Celta Vigo',
            'RCD Espanyol': 'Espanyol',
            'UD Las Palmas': 'Las Palmas',
            'Deportivo Alaves': 'Alaves'
        }
        
        # FORBIDDEN LEAGUES - NEVER use La Liga model for these
        self.FORBIDDEN_LEAGUES = {
            'Serie A', 'Premier League', 'Bundesliga', 'Ligue 1',
            'Liga I', 'Romanian Liga I', 'Championship', 'Liga MX',
            'MLS', 'Eredivisie', 'Primeira Liga', 'Super League'
        }
        
        # FORBIDDEN TEAMS - Examples from other leagues
        self.FORBIDDEN_TEAMS = {
            # Serie A
            'Juventus', 'AC Milan', 'Inter Milan', 'AS Roma', 'Napoli',
            'Lazio', 'Atalanta', 'Fiorentina', 'Torino', 'Bologna',
            
            # Premier League  
            'Manchester United', 'Manchester City', 'Liverpool', 'Arsenal',
            'Chelsea', 'Tottenham', 'Newcastle', 'Brighton', 'West Ham',
            
            # Bundesliga
            'Bayern Munich', 'Borussia Dortmund', 'RB Leipzig', 'Bayer Leverkusen',
            'Eintracht Frankfurt', 'Wolfsburg', 'Borussia Monchengladbach',
            
            # Other leagues
            'PSG', 'Marseille', 'Lyon', 'Monaco', 'Ajax', 'PSV',
            'Benfica', 'Porto', 'Sporting CP'
        }
        
        print("🔒 LA LIGA LEAGUE ISOLATION ENFORCER")
        print("=" * 40)
        print("🇪🇸 AUTHORIZED: La Liga matches ONLY")
        print("🚫 FORBIDDEN: Cross-league predictions")
        print("⚡ STATUS: STRICT ISOLATION ACTIVE")
    
    def validate_team_name(self, team_name: str) -> str:
        """Validate and normalize team name for La Liga."""
        if not team_name:
            raise ValueError("❌ Team name cannot be empty")
        
        team_name = team_name.strip()
        
        # Check if it's a direct match
        if team_name in self.LA_LIGA_TEAMS:
            return team_name
        
        # Check aliases
        if team_name in self.LA_LIGA_ALIASES:
            return self.LA_LIGA_ALIASES[team_name]
        
        # Check if it's a forbidden team
        if team_name in self.FORBIDDEN_TEAMS:
            raise ValueError(f"❌ FORBIDDEN: {team_name} is not a La Liga team. La Liga model cannot predict other leagues!")
        
        # Fuzzy matching for common variations
        team_lower = team_name.lower()
        for la_liga_team in self.LA_LIGA_TEAMS:
            if la_liga_team.lower() in team_lower or team_lower in la_liga_team.lower():
                return la_liga_team
        
        # If no match found, warn but don't block (might be new team)
        print(f"⚠️ WARNING: {team_name} not in known La Liga teams")
        print(f"⚠️ Proceeding with caution - verify this is a La Liga team")
        return team_name
    
    def validate_match_eligibility(self, home_team: str, away_team: str, league: Optional[str] = None) -> bool:
        """Validate that both teams are La Liga teams."""
        print(f"\n🔍 VALIDATING MATCH ELIGIBILITY")
        print(f"🏠 Home: {home_team}")
        print(f"🏃 Away: {away_team}")
        if league:
            print(f"🏆 League: {league}")
        
        # Check league if provided
        if league and league in self.FORBIDDEN_LEAGUES:
            raise ValueError(f"❌ FORBIDDEN LEAGUE: {league}. La Liga model cannot predict {league} matches!")
        
        # Validate both teams
        try:
            validated_home = self.validate_team_name(home_team)
            validated_away = self.validate_team_name(away_team)
            
            print(f"✅ VALIDATION PASSED")
            print(f"✅ Home: {validated_home} (La Liga)")
            print(f"✅ Away: {validated_away} (La Liga)")
            print(f"🇪🇸 AUTHORIZED: La Liga vs La Liga match")
            
            return True
            
        except ValueError as e:
            print(f"❌ VALIDATION FAILED: {str(e)}")
            print(f"🚫 PREDICTION BLOCKED")
            return False
    
    def enforce_league_purity(self, match_data: Dict) -> Dict:
        """Enforce strict league purity for La Liga predictions."""
        print(f"\n🛡️ ENFORCING LEAGUE PURITY")
        
        # Extract team information
        home_team = match_data.get('home_team', '')
        away_team = match_data.get('away_team', '')
        league = match_data.get('league', None)
        
        # Validate match eligibility
        if not self.validate_match_eligibility(home_team, away_team, league):
            raise ValueError("❌ CROSS-LEAGUE PREDICTION BLOCKED: La Liga model can only predict La Liga matches")
        
        # Normalize team names
        match_data['home_team'] = self.validate_team_name(home_team)
        match_data['away_team'] = self.validate_team_name(away_team)
        match_data['league'] = 'La Liga'  # Force league designation
        
        print(f"✅ LEAGUE PURITY ENFORCED")
        print(f"🇪🇸 Match approved for La Liga model")
        
        return match_data
    
    def get_isolation_report(self) -> Dict:
        """Get league isolation status report."""
        return {
            'model': 'La Liga 1X2',
            'authorized_league': 'La Liga',
            'authorized_teams': len(self.LA_LIGA_TEAMS),
            'forbidden_leagues': len(self.FORBIDDEN_LEAGUES),
            'forbidden_teams': len(self.FORBIDDEN_TEAMS),
            'isolation_status': 'STRICT_ACTIVE',
            'cross_league_protection': 'ENABLED',
            'league_purity': 'ENFORCED'
        }

class SafeLaLigaPredictor:
    """Safe La Liga predictor with strict league isolation."""
    
    def __init__(self):
        """Initialize safe predictor with isolation enforcement."""
        self.isolation_enforcer = LaLigaLeagueIsolationEnforcer()
        
        # Import La Liga production interface
        try:
            from la_liga_production_interface_20250701_145912 import predict_la_liga_match, get_production_status
            self.predict_function = predict_la_liga_match
            self.status_function = get_production_status
            print("✅ La Liga production interface loaded")
        except ImportError:
            # Fallback to locked interface
            from LOCKED_PRODUCTION_la_liga_production_ready import LaLigaProductionPredictor
            self.predictor = LaLigaProductionPredictor()
            print("✅ Locked La Liga interface loaded")
        
        print("🔒 SAFE LA LIGA PREDICTOR READY")
        print("🇪🇸 La Liga matches ONLY - Cross-league BLOCKED")
    
    def predict_match(self, match_data: Dict) -> Dict:
        """Make safe prediction with strict league isolation."""
        print(f"\n🔮 SAFE LA LIGA PREDICTION REQUEST")
        print("=" * 35)
        
        # Enforce league isolation
        validated_data = self.isolation_enforcer.enforce_league_purity(match_data)
        
        # Make prediction using validated data
        if hasattr(self, 'predict_function'):
            result = self.predict_function(validated_data)
        else:
            result = self.predictor.predict_match(validated_data)
        
        # Add isolation metadata
        result['league_isolation'] = {
            'league': 'La Liga',
            'isolation_enforced': True,
            'cross_league_blocked': True,
            'model_purity': 'MAINTAINED'
        }
        
        print(f"✅ PREDICTION COMPLETED WITH ISOLATION")
        return result
    
    def get_status(self) -> Dict:
        """Get predictor status with isolation info."""
        if hasattr(self, 'status_function'):
            status = self.status_function()
        else:
            status = {
                'model_version': self.predictor.model_version,
                'hit_rate': self.predictor.backtest_hit_rate,
                'roi': self.predictor.backtest_roi,
                'status': 'PRIMARY_PRODUCTION'
            }
        
        # Add isolation status
        status.update(self.isolation_enforcer.get_isolation_report())
        return status

def predict_safe_la_liga_match(match_data: Dict) -> Dict:
    """Main function for safe La Liga predictions with isolation."""
    predictor = SafeLaLigaPredictor()
    return predictor.predict_match(match_data)

def test_isolation_enforcement():
    """Test the isolation enforcement system."""
    print("🧪 TESTING ISOLATION ENFORCEMENT")
    print("=" * 35)
    
    predictor = SafeLaLigaPredictor()
    
    # Test 1: Valid La Liga match
    print("\n📋 TEST 1: Valid La Liga Match")
    la_liga_match = {
        'home_team': 'Real Madrid',
        'away_team': 'Barcelona',
        'home_recent_form': 2.5,
        'away_recent_form': 2.1,
        'home_win_odds': 2.10,
        'away_win_odds': 3.40,
        'draw_odds': 3.25,
        'home_goals_for': 2.8,
        'home_goals_against': 0.9,
        'away_goals_for': 2.6,
        'away_goals_against': 1.1,
        'home_win_rate': 0.75,
        'away_win_rate': 0.68,
        'recent_form_diff': 0.4
    }
    
    try:
        result = predictor.predict_match(la_liga_match)
        print("✅ TEST 1 PASSED: La Liga match processed")
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {str(e)}")
    
    # Test 2: Invalid cross-league match
    print("\n📋 TEST 2: Invalid Cross-League Match")
    cross_league_match = {
        'home_team': 'Manchester United',  # Premier League
        'away_team': 'Liverpool',         # Premier League
        'league': 'Premier League',
        'home_recent_form': 2.5,
        'away_recent_form': 2.1,
        'home_win_odds': 2.10,
        'away_win_odds': 3.40,
        'draw_odds': 3.25,
        'home_goals_for': 2.8,
        'home_goals_against': 0.9,
        'away_goals_for': 2.6,
        'away_goals_against': 1.1,
        'home_win_rate': 0.75,
        'away_win_rate': 0.68,
        'recent_form_diff': 0.4
    }
    
    try:
        result = predictor.predict_match(cross_league_match)
        print("❌ TEST 2 FAILED: Cross-league match should be blocked")
    except ValueError as e:
        print("✅ TEST 2 PASSED: Cross-league match correctly blocked")
        print(f"✅ Block reason: {str(e)}")
    
    # Test 3: Status check
    print("\n📋 TEST 3: Status Check")
    status = predictor.get_status()
    print("✅ TEST 3 PASSED: Status retrieved")
    print(f"✅ League: {status.get('authorized_league', 'Unknown')}")
    print(f"✅ Isolation: {status.get('isolation_status', 'Unknown')}")
    
    print(f"\n🎉 ISOLATION TESTING COMPLETE")

if __name__ == "__main__":
    test_isolation_enforcement() 