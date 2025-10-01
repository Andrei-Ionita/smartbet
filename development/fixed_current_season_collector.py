#!/usr/bin/env python3
"""
Fixed Current Season 12 Features Collector
==========================================

Fresh data fetcher using the correct SportMonks API format
to collect this season's data for the top 12 model features.

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

class FixedCurrentSeasonCollector:
    """Collect current season data for the top 12 model features using correct API format"""
    
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
        """Make API request with correct SportMonks authentication"""
        try:
            url = f"{self.base_url}/{endpoint}"
            
            # SportMonks uses api_token as URL parameter
            request_params = {'api_token': self.api_token}
            if params:
                request_params.update(params)
            
            logger.info(f"Making API request: {url}")
            response = requests.get(url, params=request_params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                items_count = len(data.get('data', [])) if isinstance(data.get('data'), list) else 1
                logger.info(f"API request successful. Items: {items_count}")
                return data
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            return None
    
    def get_recent_premier_league_seasons(self) -> List[Dict]:
        """Get recent Premier League seasons"""
        logger.info("Getting recent Premier League seasons")
        
        # Use the correct seasons endpoint format
        data = self.make_api_request("seasons", {
            'filters': 'seasonLeagues:8',  # Premier League ID = 8
            'per_page': 20
        })
        
        if not data or not data.get('data'):
            logger.error("Failed to fetch seasons")
            return []
            
        seasons = data['data']
        
        # Look for recent seasons based on actual available seasons
        # Target the most recent completed seasons and current season
        target_season_names = ['2024/2025', '2023/2024', '2022/2023', '2021/2022']
        target_season_ids = [23614, 21646, 19734, 18378]  # Known IDs from API
        
        recent_seasons = []
        for season in seasons:
            season_name = season.get('name', '')
            season_id = season.get('id')
            
            # Match by name or ID
            if season_name in target_season_names or season_id in target_season_ids:
                recent_seasons.append(season)
                logger.info(f"Found target season: {season_name} (ID: {season_id})")
        
        # Sort by season ID (newer seasons have higher IDs)
        recent_seasons.sort(key=lambda x: x.get('id', 0), reverse=True)
        
        return recent_seasons[:3]  # Return up to 3 most recent
    
    def get_season_fixtures_using_schedules(self, season_id: int) -> List[Dict]:
        """Get fixtures using the fixtures endpoint with proper filters"""
        logger.info(f"Getting fixtures for season {season_id} using fixtures endpoint")
        
        # Use the correct fixtures endpoint with filters
        data = self.make_api_request("fixtures", {
            'include': 'participants;scores;state',
            'filters': f'fixtureSeasons:{season_id};fixtureLeagues:8',  # Premier League = 8
            'per_page': 50
        })
        
        if not data or not data.get('data'):
            logger.warning(f"No fixture data found for season {season_id}")
            return []
        
        fixtures = data['data']
        logger.info(f"Found {len(fixtures)} fixtures in season {season_id}")
        
        # Check pagination and get more if needed
        pagination = data.get('pagination', {})
        if pagination.get('has_more', False):
            logger.info(f"Multiple pages available - total: {pagination.get('count', 'unknown')}")
            
            # Get additional pages
            page = 2
            while page <= pagination.get('last_page', 1):
                logger.info(f"Fetching page {page}...")
                
                page_data = self.make_api_request("fixtures", {
                    'include': 'participants;scores;state',
                    'filters': f'fixtureSeasons:{season_id};fixtureLeagues:8',
                    'per_page': 50,
                    'page': page
                })
                
                if page_data and page_data.get('data'):
                    fixtures.extend(page_data['data'])
                    logger.info(f"Added {len(page_data['data'])} more fixtures")
                
                page += 1
                time.sleep(0.5)  # Rate limiting
        
        logger.info(f"Total fixtures collected for season {season_id}: {len(fixtures)}")
        return fixtures
    
    def calculate_team_recent_form(self, fixtures: List[Dict], team_id: int, match_date: str) -> int:
        """Calculate team's recent form (last 5 matches before given date)"""
        team_matches = []
        
        # Filter matches for this team before the given date
        for fixture in fixtures:
            fixture_date = fixture.get('starting_at', '')
            if fixture_date < match_date and fixture.get('state_id') == 5:  # Finished matches
                
                home_team = fixture.get('localteam_id')
                away_team = fixture.get('visitorteam_id')
                
                if team_id in [home_team, away_team]:
                    # Get score from scores array
                    scores = fixture.get('scores', [])
                    home_goals = None
                    away_goals = None
                    
                    for score in scores:
                        if score.get('description') == 'CURRENT':
                            home_goals = score.get('goals', {}).get('localteam', 0)
                            away_goals = score.get('goals', {}).get('visitorteam', 0)
                            break
                    
                    if home_goals is not None and away_goals is not None:
                        if team_id == home_team:
                            if home_goals > away_goals:
                                points = 3
                            elif home_goals == away_goals:
                                points = 1
                            else:
                                points = 0
                        else:
                            if away_goals > home_goals:
                                points = 3
                            elif away_goals == home_goals:
                                points = 1
                            else:
                                points = 0
                        
                        team_matches.append({
                            'date': fixture_date,
                            'points': points
                        })
        
        # Sort by date and take last 5
        team_matches.sort(key=lambda x: x['date'], reverse=True)
        recent_matches = team_matches[:5]
        
        return sum(match['points'] for match in recent_matches)
    
    def calculate_team_goals(self, fixtures: List[Dict], team_id: int, match_date: str) -> Dict:
        """Calculate team's goals for/against before given date"""
        goals_for = 0
        goals_against = 0
        
        for fixture in fixtures:
            fixture_date = fixture.get('starting_at', '')
            if fixture_date < match_date and fixture.get('state_id') == 5:  # Finished matches
                
                home_team = fixture.get('localteam_id')
                away_team = fixture.get('visitorteam_id')
                
                if team_id in [home_team, away_team]:
                    # Get score from scores array
                    scores = fixture.get('scores', [])
                    home_goals = None
                    away_goals = None
                    
                    for score in scores:
                        if score.get('description') == 'CURRENT':
                            home_goals = score.get('goals', {}).get('localteam', 0)
                            away_goals = score.get('goals', {}).get('visitorteam', 0)
                            break
                    
                    if home_goals is not None and away_goals is not None:
                        if team_id == home_team:
                            goals_for += home_goals
                            goals_against += away_goals
                        else:
                            goals_for += away_goals
                            goals_against += home_goals
        
        return {'goals_for': goals_for, 'goals_against': goals_against}
    
    def extract_odds_from_fixture(self, fixture: Dict) -> Dict:
        """Extract 1X2 odds from fixture bookmakers data"""
        odds_data = {
            'odds_home': None,
            'odds_draw': None,
            'odds_away': None
        }
        
        # Look for bookmakers data
        bookmakers = fixture.get('bookmakers', [])
        if not bookmakers:
            return odds_data
            
        # Search through bookmakers for 1X2 odds
        for bookmaker in bookmakers:
            odds_markets = bookmaker.get('odds', [])
            
            for market in odds_markets:
                if market.get('name') == 'Fulltime Result':
                    values = market.get('values', [])
                    
                    for value in values:
                        if value.get('value') == '1':  # Home win
                            odds_data['odds_home'] = float(value.get('odd', 0))
                        elif value.get('value') == 'X':  # Draw
                            odds_data['odds_draw'] = float(value.get('odd', 0))
                        elif value.get('value') == '2':  # Away win
                            odds_data['odds_away'] = float(value.get('odd', 0))
                    
                    # If we found all odds, we can break
                    if all(odds_data.values()):
                        return odds_data
        
        return odds_data
    
    def calculate_derived_features(self, odds_data: Dict) -> Dict:
        """Calculate derived features from basic odds"""
        features = {}
        
        odds_home = odds_data.get('odds_home')
        odds_draw = odds_data.get('odds_draw') 
        odds_away = odds_data.get('odds_away')
        
        if not all([odds_home, odds_draw, odds_away]) or any(x <= 1.0 for x in [odds_home, odds_draw, odds_away]):
            return features
            
        try:
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
            if true_prob_away > 0:
                features['prob_ratio_draw_away'] = features['true_prob_draw'] / true_prob_away
            if features['true_prob_draw'] > 0:
                features['prob_ratio_home_draw'] = true_prob_home / features['true_prob_draw']
            
            # Log odds
            features['log_odds_home_draw'] = np.log(odds_home / odds_draw)
            features['log_odds_draw_away'] = np.log(odds_draw / odds_away)
            
            # Market efficiency
            features['market_efficiency'] = 1 / overround if overround > 0 else 0
            
            # Uncertainty index (entropy)
            probs = [true_prob_home, features['true_prob_draw'], true_prob_away]
            features['uncertainty_index'] = -sum(p * np.log(p) for p in probs if p > 0)
            
            # Basic odds
            features['odds_draw'] = odds_draw
            
        except (ValueError, ZeroDivisionError, TypeError) as e:
            logger.warning(f"Error calculating derived features: {e}")
            
        return features
    
    def process_premier_league_data(self) -> List[Dict]:
        """Process Premier League data for current/recent seasons"""
        logger.info("Starting Premier League data collection")
        
        # Get recent seasons
        seasons = self.get_recent_premier_league_seasons()
        if not seasons:
            logger.error("No recent Premier League seasons found")
            return []
        
        all_data = []
        
        for season in seasons:
            season_id = season['id']
            season_name = season.get('name', 'Unknown')
            logger.info(f"Processing season {season_name} (ID: {season_id})")
            
            # Get fixtures using fixtures endpoint
            fixtures = self.get_season_fixtures_using_schedules(season_id)
            if not fixtures:
                logger.warning(f"No fixtures found for season {season_id}")
                continue
            
            # Process each fixture
            for fixture in fixtures:
                try:
                    # Check for finished matches using state_id (5 = finished)
                    state_id = fixture.get('state_id')
                    if state_id != 5:  # Only process finished matches
                        continue
                    
                    home_team_id = fixture.get('localteam_id')
                    away_team_id = fixture.get('visitorteam_id')
                    match_date = fixture.get('starting_at', '')
                    
                    if not all([home_team_id, away_team_id, match_date]):
                        continue
                    
                    # Calculate team stats
                    home_form = self.calculate_team_recent_form(fixtures, home_team_id, match_date)
                    away_form = self.calculate_team_recent_form(fixtures, away_team_id, match_date)
                    away_goals = self.calculate_team_goals(fixtures, away_team_id, match_date)
                    
                    # Extract odds
                    odds_data = self.extract_odds_from_fixture(fixture)
                    
                    # Calculate derived features
                    derived_features = self.calculate_derived_features(odds_data)
                    
                    if not derived_features:  # Skip if no valid odds
                        continue
                    
                    # Build feature record
                    feature_record = {
                        'fixture_id': fixture.get('id'),
                        'season_id': season_id,
                        'season_name': season_name,
                        'home_team_id': home_team_id,
                        'away_team_id': away_team_id,
                        'match_date': match_date,
                        
                        # Top 12 features
                        'recent_form_home': home_form,
                        'recent_form_away': away_form,
                        'goals_for_away': away_goals.get('goals_for', 0),
                        
                        # Add all derived features
                        **derived_features
                    }
                    
                    # Count how many of the 12 features we have
                    feature_count = sum(1 for feat in self.required_features 
                                      if feat in feature_record and feature_record[feat] is not None)
                    
                    if feature_count >= 8:  # At least 8 of 12 features
                        all_data.append(feature_record)
                        logger.info(f"Added fixture {fixture.get('id')}: {feature_count}/12 features")
                
                except Exception as e:
                    logger.warning(f"Error processing fixture {fixture.get('id', 'unknown')}: {e}")
                    continue
            
            time.sleep(1)  # Rate limiting between seasons
        
        logger.info(f"Total processed fixtures: {len(all_data)}")
        return all_data
    
    def save_to_csv(self, data: List[Dict]) -> str:
        """Save collected data to CSV"""
        if not data:
            logger.warning("No data to save")
            return ""
            
        df = pd.DataFrame(data)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"premier_league_12_features_{timestamp}.csv"
        
        df.to_csv(filename, index=False)
        logger.info(f"Data saved to {filename}")
        
        # Print summary
        logger.info(f"Data Summary:")
        logger.info(f"- Total fixtures: {len(df)}")
        logger.info(f"- Seasons: {df['season_name'].nunique()}")
        logger.info(f"- Date range: {df['match_date'].min()} to {df['match_date'].max()}")
        
        # Feature availability summary
        feature_availability = {}
        for feature in self.required_features:
            if feature in df.columns:
                non_null_count = df[feature].notna().sum()
                feature_availability[feature] = f"{non_null_count}/{len(df)} ({non_null_count/len(df)*100:.1f}%)"
        
        logger.info("Feature Availability:")
        for feature, availability in feature_availability.items():
            logger.info(f"  {feature}: {availability}")
        
        return filename

def main():
    """Main execution function"""
    print("🚀 Starting Fixed Current Season 12 Features Collection")
    print("=" * 60)
    
    collector = FixedCurrentSeasonCollector()
    
    # Process Premier League data
    data = collector.process_premier_league_data()
    
    if data:
        filename = collector.save_to_csv(data)
        print(f"\n✅ Collection completed successfully!")
        print(f"📊 Data saved to: {filename}")
        print(f"🎯 Total fixtures collected: {len(data)}")
    else:
        print("\n❌ No data collected")
    
    print("\nCollection process finished!")

if __name__ == "__main__":
    main()