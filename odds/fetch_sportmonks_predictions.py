"""
SportMonks Predictions Integration for SmartBet

This module provides integration with SportMonks API to fetch predictions
using the European leagues basic subscription with prediction addon.

Features:
- Fetches predictions from SportMonks prediction addon
- Integrates with existing Match model
- Handles rate limiting and retries
- Supports multiple European leagues
"""

import os
import time
import logging
import requests
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from dotenv import load_dotenv

from core.models import Match, OddsSnapshot, League

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Constants
SPORTMONKS_BASE_URL = "https://api.sportmonks.com/v3/football"
SPORTMONKS_PREDICTIONS_URL = "https://api.sportmonks.com/v3/football/predictions"
SPORTMONKS_RATE_LIMIT = 1.2  # requests per second (conservative)
SPORTMONKS_MAX_RETRIES = 3
SPORTMONKS_RETRY_DELAY = 5  # seconds

# European leagues supported by SportMonks European leagues basic + European Club Tournaments addon
SUPPORTED_LEAGUES = {
    8: "Premier League",
    564: "La Liga", 
    82: "Serie A",
    78: "Bundesliga",
    61: "Ligue 1",
    39: "Liga 1",
    # European Club Tournaments addon
    2: "UEFA Champions League",
    5: "UEFA Europa League",
    2286: "UEFA Europa Conference League",
}

def get_api_token() -> str:
    """Get the SportMonks API token from environment variables."""
    token = os.getenv("SPORTMONKS_TOKEN") or os.getenv("SPORTMONKS_API_TOKEN")
    if not token:
        raise ValueError("SPORTMONKS_TOKEN or SPORTMONKS_API_TOKEN environment variable not set")
    return token

def make_predictions_request(endpoint: str, params: Dict = None) -> Optional[Dict]:
    """
    Make a request to the SportMonks Predictions API with retry logic and rate limiting.
    
    Args:
        endpoint: API endpoint path (after base URL)
        params: Query parameters for the request
        
    Returns:
        JSON response data or None if all retries failed
    """
    token = get_api_token()
    url = f"{SPORTMONKS_PREDICTIONS_URL}/{endpoint}"
    
    if params is None:
        params = {}
    
    params['api_token'] = token
    
    for attempt in range(SPORTMONKS_MAX_RETRIES):
        try:
            # Rate limiting
            if attempt > 0:
                time.sleep(SPORTMONKS_RETRY_DELAY)
            
            logger.debug(f"Making predictions request to {url} (attempt {attempt+1})")
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 429:
                logger.warning("Rate limited, waiting 60 seconds...")
                time.sleep(60)
                continue
                
            if response.status_code == 404:
                logger.debug(f"Resource not found: {endpoint}")
                return None
            
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API error
            if "error" in data:
                logger.error(f"API Error: {data['error']['message']}")
                return None
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed (attempt {attempt+1}): {e}")
            if attempt == SPORTMONKS_MAX_RETRIES - 1:
                logger.error(f"All retries failed for {endpoint}")
                return None
            time.sleep(SPORTMONKS_RETRY_DELAY)
    
    return None

def fetch_league_predictions(league_id: int, league_name: str) -> int:
    """
    Fetch predictions for a specific league.
    
    Args:
        league_id: SportMonks league ID
        league_name: Human-readable league name
        
    Returns:
        Number of prediction snapshots created
    """
    logger.info(f"Fetching predictions for {league_name} (ID: {league_id})")
    
    try:
        # Get upcoming fixtures for the league
        fixtures_data = make_predictions_request("", {
            "filters": f"leagueId:{league_id}",
            "include": "fixture,league,teams"
        })
        
        if not fixtures_data or "data" not in fixtures_data:
            logger.warning(f"No fixtures data for {league_name}")
            return 0
        
        fixtures = fixtures_data["data"]
        predictions_created = 0
        
        for fixture in fixtures:
            try:
                # Extract prediction data
                prediction_data = _extract_prediction_data(fixture)
                if prediction_data:
                    # Create or update odds snapshot with prediction data
                    snapshot = _create_prediction_snapshot(prediction_data)
                    if snapshot:
                        predictions_created += 1
                        
            except Exception as e:
                logger.warning(f"Error processing fixture {fixture.get('id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Created {predictions_created} prediction snapshots for {league_name}")
        return predictions_created
        
    except Exception as e:
        logger.error(f"Error fetching predictions for {league_name}: {e}")
        return 0

def _extract_prediction_data(fixture: Dict) -> Optional[Dict]:
    """Extract prediction data from fixture response."""
    try:
        fixture_id = fixture.get("id")
        if not fixture_id:
            return None
        
        # Get prediction details
        prediction_data = make_predictions_request(f"{fixture_id}", {
            "include": "predictions"
        })
        
        if not prediction_data or "data" not in prediction_data:
            return None
        
        fixture_data = prediction_data["data"]
        
        # Extract prediction information
        predictions = fixture_data.get("predictions", {})
        
        return {
            "fixture_id": fixture_id,
            "home_team": fixture_data.get("home_team", {}).get("name", "Unknown"),
            "away_team": fixture_data.get("away_team", {}).get("name", "Unknown"),
            "match_date": fixture_data.get("starting_at"),
            "predictions": predictions,
            "home_win_prob": predictions.get("home_win_probability", 0.33),
            "draw_prob": predictions.get("draw_probability", 0.33),
            "away_win_prob": predictions.get("away_win_probability", 0.33),
            "home_win_odds": 1.0 / predictions.get("home_win_probability", 0.33) if predictions.get("home_win_probability") else 3.0,
            "draw_odds": 1.0 / predictions.get("draw_probability", 0.33) if predictions.get("draw_probability") else 3.0,
            "away_win_odds": 1.0 / predictions.get("away_win_probability", 0.33) if predictions.get("away_win_probability") else 3.0,
        }
        
    except Exception as e:
        logger.warning(f"Error extracting prediction data: {e}")
        return None

def _create_prediction_snapshot(prediction_data: Dict) -> Optional[OddsSnapshot]:
    """Create an OddsSnapshot from prediction data."""
    try:
        # Find or create the match
        match = _find_or_create_match(prediction_data)
        if not match:
            return None
        
        # Create odds snapshot
        snapshot = OddsSnapshot.objects.create(
            match=match,
            home_win_odds=prediction_data.get("home_win_odds", 3.0),
            draw_odds=prediction_data.get("draw_odds", 3.0),
            away_win_odds=prediction_data.get("away_win_odds", 3.0),
            home_win_prob=prediction_data.get("home_win_prob", 0.33),
            draw_prob=prediction_data.get("draw_prob", 0.33),
            away_win_prob=prediction_data.get("away_win_prob", 0.33),
            source="sportmonks_predictions",
            created_at=timezone.now()
        )
        
        return snapshot
        
    except Exception as e:
        logger.error(f"Error creating prediction snapshot: {e}")
        return None

def _find_or_create_match(prediction_data: Dict) -> Optional[Match]:
    """Find or create a Match object from prediction data."""
    try:
        # Try to find existing match by fixture ID
        match = Match.objects.filter(
            external_id=prediction_data.get("fixture_id")
        ).first()
        
        if match:
            return match
        
        # Create new match if not found
        match = Match.objects.create(
            external_id=prediction_data.get("fixture_id"),
            home_team_name=prediction_data.get("home_team", "Unknown"),
            away_team_name=prediction_data.get("away_team", "Unknown"),
            match_date=prediction_data.get("match_date"),
            status="scheduled"
        )
        
        return match
        
    except Exception as e:
        logger.error(f"Error finding/creating match: {e}")
        return None

def fetch_sportmonks_predictions(demo: bool = False) -> int:
    """
    Fetch predictions from SportMonks API using the prediction addon.
    
    Args:
        demo: If True, creates demo data instead of making API calls
        
    Returns:
        Number of prediction snapshots created
    """
    logger.info("Starting SportMonks predictions fetching...")
    
    if demo:
        logger.info("Demo mode: Creating sample prediction data")
        return _create_demo_predictions()
    
    # Get API token
    token = os.getenv("SPORTMONKS_TOKEN") or os.getenv("SPORTMONKS_API_TOKEN")
    if not token:
        logger.error("SportMonks token not found in environment variables")
        return 0
    
    try:
        # Fetch predictions for each supported league
        total_predictions = 0
        
        for league_id, league_name in SUPPORTED_LEAGUES.items():
            logger.info(f"Fetching predictions for {league_name} (ID: {league_id})")
            
            predictions_count = fetch_league_predictions(league_id, league_name)
            total_predictions += predictions_count
            
            # Rate limiting
            time.sleep(SPORTMONKS_RATE_LIMIT)
        
        logger.info(f"Successfully fetched {total_predictions} prediction snapshots")
        return total_predictions
        
    except Exception as e:
        logger.error(f"Error fetching SportMonks predictions: {e}")
        return 0

def _create_demo_predictions() -> int:
    """Create demo prediction data for testing."""
    logger.info("Creating demo prediction data...")
    
    demo_predictions = [
        {
            "fixture_id": "demo_1",
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "home_win_odds": 2.1,
            "draw_odds": 3.4,
            "away_win_odds": 3.2,
            "home_win_prob": 0.48,
            "draw_prob": 0.29,
            "away_win_prob": 0.31,
        },
        {
            "fixture_id": "demo_2", 
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "home_win_odds": 3.5,
            "draw_odds": 3.1,
            "away_win_odds": 2.0,
            "home_win_prob": 0.29,
            "draw_prob": 0.32,
            "away_win_prob": 0.50,
        }
    ]
    
    created_count = 0
    for prediction_data in demo_predictions:
        try:
            snapshot = _create_prediction_snapshot(prediction_data)
            if snapshot:
                created_count += 1
        except Exception as e:
            logger.warning(f"Error creating demo prediction: {e}")
    
    logger.info(f"Created {created_count} demo prediction snapshots")
    return created_count

if __name__ == "__main__":
    # Test the predictions integration
    import django
    django.setup()
    
    result = fetch_sportmonks_predictions(demo=True)
    print(f"Created {result} prediction snapshots")
