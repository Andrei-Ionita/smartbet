#!/usr/bin/env python3
"""
Current Season 12 Features Collector
===================================

Fresh data fetcher to collect this season's data for the top 12 model features
based on feature importance analysis and add them to the training dataset.

Top 12 Features (by importance):
1. true_prob_draw (13634.36)
2. prob_ratio_draw_away (9295.57)
3. prob_ratio_home_draw (8642.94)
4. log_odds_home_draw (8555.35)
5. log_odds_draw_away (7818.46)
6. bookmaker_margin (5945.77)
7. market_efficiency (4885.52)
8. uncertainty_index (3276.36)
9. odds_draw (2902.82)
10. goals_for_away (2665.45)
11. recent_form_home (2535.50)
12. recent_form_away (2515.45)
"""

import os
import sys
import django
import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging
from typing import Dict, List, Optional, Tuple

# Add the parent directory to the path to import Django modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartbet.settings')
django.setup()

from core.models import League, Match, Team
from django.db import transaction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'current_season_features_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CurrentSeasonFeaturesCollector:
    """Collect current season data for the top 12 model features"""
    
    def __init__(self):
        self.api_token = os.getenv('SPORTMONKS_API_TOKEN')
        self.base_url = "https://api.sportmonks.com/v3/football"
        
        # Top 12 features we need to collect
        self.required_features = [
            'true_prob_draw',
            'prob_ratio_draw_away', 
            'prob_ratio_home_draw',
            'log_odds_home_draw',
            'log_odds_draw_away',
            'bookmaker_margin',
            'market_efficiency',
            'uncertainty_index',
            'odds_draw',
            'goals_for_away',
            'recent_form_home',
            'recent_form_away'
        ]
        
        # Load league config
        with open('config/league_config.json', 'r') as f:
            self.leagues = json.load(f)
        
        self.collected_data = []
        
    def make_api_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request with error handling"""
        try:
            url = f"{self.base_url}/{endpoint}"
            
            # Add API token to params (SportMonks uses URL parameter, not header)
            request_params = {'api_token': self.api_token}
            if params:
                request_params.update(params)
            
            logger.info(f"Making API request: {url}")
            response = requests.get(url, params=request_params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"API request successful. Items: {len(data.get('data', []))}")
                return data
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return None
    
    def get_current_season_id(self, league_id: int) -> Optional[int]:
        """Get the current season ID for a league"""
        endpoint = f"leagues/{league_id}/seasons"
        params = {
            'include': 'statistics',
            'filters': 'seasonStatuses:current,upcoming'
        }
        
        data = self.make_api_request(endpoint, params)
        if not data or not data.get('data'):
            return None
            
        # Get the most recent season
        seasons = data['data']
        current_season = max(seasons, key=lambda x: x.get('starting_at', ''))
        logger.info(f"Current season ID for league {league_id}: {current_season['id']}")
        return current_season['id']
    
    def get_season_fixtures(self, league_id: int, season_id: int) -> List[Dict]:
        """Get fixtures for a specific season"""
        endpoint = f"fixtures"
        params = {
            'include': 'scores,teams,statistics.details,bookmakers.odds',
            'filters': f'fixtureLeagues:{league_id};fixtureSeasons:{season_id}',
            'per_page': 50
        }
        
        all_fixtures = []
        page = 1
        
        while True:
            params['page'] = page
            data = self.make_api_request(endpoint, params)
            
            if not data or not data.get('data'):
                break
                
            fixtures = data['data']
            all_fixtures.extend(fixtures)
            
            logger.info(f"Page {page}: {len(fixtures)} fixtures collected")
            
            # Check if there are more pages
            pagination = data.get('pagination', {})
            if page >= pagination.get('last_page', 1):
                break
                
            page += 1
            time.sleep(0.5)  # Rate limiting
            
        logger.info(f"Total fixtures collected for season {season_id}: {len(all_fixtures)}")
        return all_fixtures
    
    def calculate_team_stats(self, fixtures: List[Dict], team_id: int) -> Dict:
        """Calculate team statistics from fixtures"""
        stats = {
            'goals_for': 0,
            'goals_against': 0,
            'matches_played': 0,
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'recent_form_points': 0  # Last 5 matches
        }
        
        team_fixtures = []
        
        for fixture in fixtures:
            if not fixture.get('scores') or fixture.get('state_id') != 5:  # Only finished matches
                continue
                
            home_team_id = fixture['localteam_id']
            away_team_id = fixture['visitorteam_id']
            
            if team_id not in [home_team_id, away_team_id]:
                continue
                
            # Get scores
            ft_score = None
            for score in fixture['scores']:
                if score['description'] == 'CURRENT':
                    ft_score = score
                    break
            
            if not ft_score:
                continue
                
            home_goals = ft_score['goals']['localteam']
            away_goals = ft_score['goals']['visitorteam']
            
            is_home = team_id == home_team_id
            team_goals = home_goals if is_home else away_goals
            opponent_goals = away_goals if is_home else home_goals
            
            stats['goals_for'] += team_goals
            stats['goals_against'] += opponent_goals
            stats['matches_played'] += 1
            
            # Result
            if team_goals > opponent_goals:
                stats['wins'] += 1
                points = 3
            elif team_goals == opponent_goals:
                stats['draws'] += 1
                points = 1
            else:
                stats['losses'] += 1
                points = 0
                
            team_fixtures.append({
                'date': fixture.get('starting_at', ''),
                'points': points
            })
        
        # Calculate recent form (last 5 matches)
        if team_fixtures:
            team_fixtures.sort(key=lambda x: x['date'], reverse=True)
            recent_matches = team_fixtures[:5]
            stats['recent_form_points'] = sum(match['points'] for match in recent_matches)
        
        return stats
    
    def extract_odds(self, fixture: Dict) -> Dict:
        """Extract odds data from fixture"""
        odds_data = {
            'odds_home': None,
            'odds_draw': None,
            'odds_away': None
        }
        
        if not fixture.get('bookmakers'):
            return odds_data
            
        # Look for main market odds (1X2)
        for bookmaker in fixture['bookmakers']:
            if not bookmaker.get('odds'):
                continue
                
            for market in bookmaker['odds']:
                if market.get('name') == 'Fulltime Result':
                    for odd in market.get('values', []):
                        if odd['value'] == '1':  # Home win
                            odds_data['odds_home'] = float(odd['odd'])
                        elif odd['value'] == 'X':  # Draw
                            odds_data['odds_draw'] = float(odd['odd'])
                        elif odd['value'] == '2':  # Away win
                            odds_data['odds_away'] = float(odd['odd'])
                    break
            
            if all(odds_data.values()):  # If we have all odds, break
                break
                
        return odds_data
    
    def calculate_derived_features(self, odds_data: Dict) -> Dict:
        """Calculate derived features from odds"""
        features = {}
        
        odds_home = odds_data.get('odds_home')
        odds_draw = odds_data.get('odds_draw') 
        odds_away = odds_data.get('odds_away')
        
        if not all([odds_home, odds_draw, odds_away]):
            return features
            
        # Implied probabilities
        implied_prob_home = 1 / odds_home
        implied_prob_draw = 1 / odds_draw
        implied_prob_away = 1 / odds_away
        
        # Overround (bookmaker margin)
        overround = implied_prob_home + implied_prob_draw + implied_prob_away
        features['bookmaker_margin'] = overround - 1
        
        # True probabilities (normalized)
        features['true_prob_draw'] = implied_prob_draw / overround
        true_prob_home = implied_prob_home / overround
        true_prob_away = implied_prob_away / overround
        
        # Probability ratios
        features['prob_ratio_draw_away'] = features['true_prob_draw'] / true_prob_away if true_prob_away > 0 else 0
        features['prob_ratio_home_draw'] = true_prob_home / features['true_prob_draw'] if features['true_prob_draw'] > 0 else 0
        
        # Log odds
        features['log_odds_home_draw'] = np.log(odds_home / odds_draw) if odds_draw > 0 else 0
        features['log_odds_draw_away'] = np.log(odds_draw / odds_away) if odds_away > 0 else 0
        
        # Market efficiency (how close to fair the odds are)
        features['market_efficiency'] = 1 / overround if overround > 0 else 0
        
        # Uncertainty index (entropy-based measure)
        probs = [true_prob_home, features['true_prob_draw'], true_prob_away]
        features['uncertainty_index'] = -sum(p * np.log(p) for p in probs if p > 0)
        
        # Add basic odds
        features['odds_draw'] = odds_draw
        
        return features
    
    def process_league_season(self, league: Dict) -> List[Dict]:
        """Process a specific league's current season"""
        league_id = league['sportmonks_id']
        league_name = league['name_en']
        
        logger.info(f"Processing {league_name} (ID: {league_id})")
        
        # Get current season
        season_id = self.get_current_season_id(league_id)
        if not season_id:
            logger.warning(f"No current season found for {league_name}")
            return []
        
        # Get fixtures
        fixtures = self.get_season_fixtures(league_id, season_id)
        if not fixtures:
            logger.warning(f"No fixtures found for {league_name} season {season_id}")
            return []
        
        # Get all teams in the league
        teams = set()
        for fixture in fixtures:
            teams.add(fixture['localteam_id'])
            teams.add(fixture['visitorteam_id'])
        
        logger.info(f"Found {len(teams)} teams in {league_name}")
        
        # Calculate team stats for each team
        team_stats = {}
        for team_id in teams:
            team_stats[team_id] = self.calculate_team_stats(fixtures, team_id)
            time.sleep(0.1)  # Small delay
        
        # Process each fixture
        processed_fixtures = []
        for fixture in fixtures:
            if fixture.get('state_id') != 5:  # Only finished matches
                continue
                
            home_team_id = fixture['localteam_id']
            away_team_id = fixture['visitorteam_id']
            
            # Get team stats
            home_stats = team_stats.get(home_team_id, {})
            away_stats = team_stats.get(away_team_id, {})
            
            # Extract odds
            odds_data = self.extract_odds(fixture)
            
            # Calculate derived features
            derived_features = self.calculate_derived_features(odds_data)
            
            # Build feature set
            feature_data = {
                'fixture_id': fixture['id'],
                'league_id': league_id,
                'league_name': league_name,
                'season_id': season_id,
                'home_team_id': home_team_id,
                'away_team_id': away_team_id,
                'match_date': fixture.get('starting_at', ''),
                
                # Top 12 features
                'goals_for_away': away_stats.get('goals_for', 0),
                'recent_form_home': home_stats.get('recent_form_points', 0),
                'recent_form_away': away_stats.get('recent_form_points', 0),
                
                # Add derived features
                **derived_features
            }
            
            # Only include if we have the key features
            required_count = sum(1 for feature in self.required_features if feature in feature_data and feature_data[feature] is not None)
            
            if required_count >= 8:  # At least 8 of 12 features
                processed_fixtures.append(feature_data)
                logger.info(f"Processed fixture {fixture['id']}: {required_count}/12 features")
        
        logger.info(f"Successfully processed {len(processed_fixtures)} fixtures for {league_name}")
        return processed_fixtures
    
    def collect_all_leagues(self) -> None:
        """Collect data for all configured leagues"""
        logger.info("Starting collection for all leagues")
        
        for league in self.leagues:
            try:
                league_data = self.process_league_season(league)
                self.collected_data.extend(league_data)
                
                logger.info(f"Completed {league['name_en']}: {len(league_data)} fixtures")
                time.sleep(1)  # Rate limiting between leagues
                
            except Exception as e:
                logger.error(f"Error processing {league['name_en']}: {str(e)}")
                continue
        
        logger.info(f"Total data collected: {len(self.collected_data)} fixtures")
    
    def save_to_csv(self) -> str:
        """Save collected data to CSV"""
        if not self.collected_data:
            logger.warning("No data to save")
            return ""
            
        df = pd.DataFrame(self.collected_data)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"current_season_12_features_{timestamp}.csv"
        
        df.to_csv(filename, index=False)
        logger.info(f"Data saved to {filename}")
        
        # Print summary
        logger.info(f"Data Summary:")
        logger.info(f"- Total fixtures: {len(df)}")
        logger.info(f"- Leagues: {df['league_name'].nunique()}")
        logger.info(f"- Features available: {len([col for col in df.columns if col in self.required_features])}")
        
        return filename
    
    def test_premier_league_only(self) -> None:
        """Test with Premier League only first"""
        logger.info("Testing with Premier League only")
        
        # Find Premier League config
        premier_league = None
        for league in self.leagues:
            if league['name_en'] == 'Premier League':
                premier_league = league
                break
        
        if not premier_league:
            logger.error("Premier League not found in config")
            return
            
        # Process just Premier League
        league_data = self.process_league_season(premier_league)
        self.collected_data = league_data
        
        if league_data:
            filename = self.save_to_csv()
            logger.info(f"Premier League test completed: {filename}")
        else:
            logger.warning("No Premier League data collected")

def main():
    """Main execution function"""
    collector = CurrentSeasonFeaturesCollector()
    
    # First test with Premier League only
    print("Starting with Premier League test...")
    collector.test_premier_league_only()
    
    # Ask user if they want to continue with all leagues
    if len(collector.collected_data) > 0:
        response = input("\nPremier League test successful! Continue with all leagues? (y/n): ")
        if response.lower() == 'y':
            collector.collected_data = []  # Reset
            collector.collect_all_leagues()
            collector.save_to_csv()
    
    print("\nCollection completed!")

if __name__ == "__main__":
    main()