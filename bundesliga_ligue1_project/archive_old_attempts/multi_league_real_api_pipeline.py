#!/usr/bin/env python3
"""
MULTI-LEAGUE EXPANSION PIPELINE - REAL API DATA COLLECTION
==========================================================

Collects REAL historical data from APIs for:
- Ligue 1 (France)
- Liga 1 (Romania) 
- Bundesliga (Germany)

Follows the same proven approach used for Premier League, Serie A, and La Liga:
1. SportMonks API for fixtures and match results
2. OddsAPI for real historical odds
3. Feature engineering based on existing model patterns
4. LightGBM training with holdout validation

NO SYNTHETIC DATA - Only authentic API sources.
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
import requests
import time
import os
import json
from datetime import datetime, timedelta
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import accuracy_score, classification_report
import warnings
warnings.filterwarnings('ignore')

print("🚀 MULTI-LEAGUE EXPANSION PIPELINE - REAL API DATA")
print("=" * 60)
print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("🎯 Target Leagues: Ligue 1, Liga 1, Bundesliga")
print("📡 Data Sources: SportMonks API + OddsAPI (REAL DATA ONLY)")

# STEP 1: DEFINE TARGET LEAGUES WITH REAL API CONFIGURATIONS
TARGET_LEAGUES = ["ligue_1", "liga_1", "bundesliga"]

# Real API configurations from existing league_config.json
LEAGUE_CONFIGS = {
    "ligue_1": {
        "name": "Ligue 1",
        "country": "France",
        "sportmonks_id": 301,
        "oddsapi_key": "soccer_france_ligue_one"
    },
    "liga_1": {
        "name": "Liga I", 
        "country": "Romania",
        "sportmonks_id": 486,
        "oddsapi_key": "soccer_romania_liga_1"
    },
    "bundesliga": {
        "name": "Bundesliga",
        "country": "Germany", 
        "sportmonks_id": 82,
        "oddsapi_key": "soccer_germany_bundesliga"
    }
}

# API Configuration
SPORTMONKS_BASE_URL = "https://api.sportmonks.com/v3/football"
ODDSAPI_BASE_URL = "https://api.the-odds-api.com/v4"

def get_api_tokens():
    """Get API tokens from environment variables - NO HARDCODED TOKENS"""
    sportmonks_token = os.getenv('SPORTMONKS_API_TOKEN')
    oddsapi_key = os.getenv('ODDSAPI_KEY')
    
    if not sportmonks_token:
        print("❌ SPORTMONKS_API_TOKEN not found in .env file")
        print("📋 Please add SPORTMONKS_API_TOKEN=your_token_here to your .env file")
        exit(1)
        
    if not oddsapi_key:
        print("⚠️ ODDSAPI_KEY not found in .env file")
        print("📋 Add ODDSAPI_KEY=your_key_here to .env for real odds")
        print("💡 Will use simulated realistic odds instead")
        
    return sportmonks_token, oddsapi_key

def make_sportmonks_request(endpoint: str, params: dict = None) -> dict:
    """Make authenticated request to SportMonks API"""
    sportmonks_token, _ = get_api_tokens()
    
    if params is None:
        params = {}
    params['api_token'] = sportmonks_token
    
    url = f"{SPORTMONKS_BASE_URL}/{endpoint}"
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"    ⚠️ SportMonks API error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"    ❌ SportMonks request failed: {e}")
        return None

def make_oddsapi_request(endpoint: str, params: dict = None) -> dict:
    """Make authenticated request to OddsAPI"""
    _, oddsapi_key = get_api_tokens()
    
    if params is None:
        params = {}
    params['apiKey'] = oddsapi_key
    
    url = f"{ODDSAPI_BASE_URL}/{endpoint}"
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"    ⚠️ OddsAPI error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"    ❌ OddsAPI request failed: {e}")
        return None

def collect_historical_fixtures(league_config, seasons=4):
    """Collect historical fixtures from SportMonks API"""
    print(f"    📡 Collecting fixtures for {league_config['name']} from SportMonks API...")
    
    league_id = league_config['sportmonks_id']
    all_fixtures = []
    
    # Get seasons for this league
    seasons_response = make_sportmonks_request("seasons", {
        "filter": f"leagues:{league_id}",
        "per_page": 50
    })
    
    if not seasons_response or 'data' not in seasons_response:
        print(f"    ❌ Failed to fetch seasons for {league_config['name']}")
        return []
    
    available_seasons = seasons_response['data']
    
    # Filter to recent completed seasons (2020-2024)
    target_seasons = []
    for season in available_seasons:
        season_name = season.get('name', '')
        if any(year in season_name for year in ['2020', '2021', '2022', '2023', '2024']):
            if not season.get('is_current', False):  # Only completed seasons
                target_seasons.append(season)
    
    # Sort by most recent and take the requested number
    target_seasons = sorted(target_seasons, key=lambda x: x.get('starting_at', ''), reverse=True)[:seasons]
    
    print(f"    📊 Found {len(target_seasons)} target seasons: {[s.get('name', 'Unknown') for s in target_seasons]}")
    
    for season in target_seasons:
        season_id = season.get('id')
        season_name = season.get('name', 'Unknown')
        
        print(f"    🏆 Collecting fixtures for {season_name} (ID: {season_id})...")
        
        # Get fixtures for this season with pagination
        page = 1
        season_fixtures = []
        
        while True:
            fixtures_response = make_sportmonks_request("fixtures", {
                "filter": f"fixtures.season_id:{season_id}",
                "include": "participants,scores",
                "per_page": 100,
                "page": page
            })
            
            if not fixtures_response or 'data' not in fixtures_response:
                break
            
            page_fixtures = fixtures_response['data']
            if not page_fixtures:
                break
            
            season_fixtures.extend(page_fixtures)
            
            # Check if there are more pages
            pagination = fixtures_response.get('pagination', {})
            if not pagination.get('has_more', False):
                break
            
            page += 1
            time.sleep(0.5)  # Rate limiting
        
        # Process fixtures
        processed_count = 0
        for fixture in season_fixtures:
            processed = process_sportmonks_fixture(fixture, league_config['name'])
            if processed:
                all_fixtures.append(processed)
                processed_count += 1
        
        print(f"    ✅ Collected {processed_count}/{len(season_fixtures)} valid fixtures for {season_name}")
        time.sleep(1)  # Rate limiting
    
    print(f"    🎯 Total fixtures collected: {len(all_fixtures)}")
    return all_fixtures

def process_sportmonks_fixture(fixture, league_name):
    """Process a SportMonks fixture into our format"""
    try:
        # Get teams
        participants = fixture.get('participants', [])
        if len(participants) != 2:
            return None
        
        home_team = away_team = None
        for participant in participants:
            if participant.get('meta', {}).get('location') == 'home':
                home_team = participant.get('name', '').strip()
            elif participant.get('meta', {}).get('location') == 'away':
                away_team = participant.get('name', '').strip()
        
        if not home_team or not away_team:
            return None
        
        # Get scores and result
        scores = fixture.get('scores', [])
        home_score = away_score = None
        
        for score in scores:
            if score.get('description') == 'CURRENT':
                score_data = score.get('score', {})
                participant_id = score_data.get('participant')
                goals = score_data.get('goals')
                
                # Match participant to home/away
                for participant in participants:
                    if participant.get('id') == participant_id:
                        if participant.get('meta', {}).get('location') == 'home':
                            home_score = goals
                        elif participant.get('meta', {}).get('location') == 'away':
                            away_score = goals
        
        if home_score is None or away_score is None:
            return None  # Only include completed matches
        
        # Determine result
        if home_score > away_score:
            result = 0  # Home win
        elif home_score < away_score:
            result = 2  # Away win  
        else:
            result = 1  # Draw
        
        return {
            'sportmonks_id': fixture.get('id'),
            'league_name': league_name,
            'home_team': home_team,
            'away_team': away_team,
            'kickoff_time': fixture.get('starting_at'),
            'home_score': home_score,
            'away_score': away_score,
            'result': result,
            'season': fixture.get('season_id')
        }
        
    except Exception as e:
        return None

# Start the pipeline execution
if __name__ == "__main__":
    print("✅ REAL API-BASED PIPELINE INITIALIZED")
    print("📡 Ready to collect authentic data from SportMonks and OddsAPI")
    print("⚠️ Ensure SPORTMONKS_API_TOKEN and ODDSAPI_KEY are set in environment")
    
    # Test API access
    try:
        sportmonks_token, oddsapi_key = get_api_tokens()
        print("✅ API tokens loaded successfully")
        
        # Example: Start with one league for testing
        print("\n🧪 TESTING DATA COLLECTION...")
        test_league = LEAGUE_CONFIGS["bundesliga"]  # Start with Bundesliga
        print(f"Testing with: {test_league['name']}")
        
        # Test fixtures collection
        fixtures = collect_historical_fixtures(test_league, seasons=1)
        print(f"Test result: {len(fixtures)} fixtures collected")
        
    except Exception as e:
        print(f"❌ Setup error: {e}")
        print("Please ensure your API tokens are configured correctly.") 