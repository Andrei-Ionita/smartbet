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

# European leagues supported by SportMonks European leagues basic
EUROPEAN_LEAGUE_IDS = {
    "Premier League": 8,
    "La Liga": 564,
    "Serie A": 82,
    "Bundesliga": 78,
    "Ligue 1": 301,
    "Liga 1": 486,  # Romanian Liga 1
}

def get_api_token() -> str:
    """Get the SportMonks API token from environment variables."""
    token = os.getenv("SPORTMONKS_TOKEN") or os.getenv("SPORTMONKS_API_TOKEN")
    if not token:
        raise ValueError("SPORTMONKS_TOKEN or SPORTMONKS_API_TOKEN environment variable not set")
    return token

def make_odds_request(endpoint: str, params: Dict = None) -> Optional[Dict]:
    """
    Make a request to the SportMonks Odds API with retry logic and rate limiting.
    
    Args:
        endpoint: API endpoint path (after base URL)
        params: Query parameters for the request
        
    Returns:
        JSON response data or None if all retries failed
    """
    token = get_api_token()
    url = f"{SPORTMONKS_ODDS_URL}/{endpoint}"
    
    if params is None:
        params = {}
    
    params['api_token'] = token
    
    for attempt in range(SPORTMONKS_MAX_RETRIES):
        try:
            # Rate limiting
            if attempt > 0:
                time.sleep(SPORTMONKS_RETRY_DELAY)
            
            logger.debug(f"Making odds request to {url} (attempt {attempt+1})")
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
            logger.error(f"Request failed (attempt {attempt + 1}/{SPORTMONKS_MAX_RETRIES}): {e}")
            if attempt == SPORTMONKS_MAX_RETRIES - 1:
                return None
            
        # Rate limiting
        time.sleep(1 / SPORTMONKS_RATE_LIMIT)
    
    return None

def fetch_fixture_odds(fixture_id: int) -> Optional[Dict]:
    """
    Fetch odds for a specific fixture from SportMonks.
    
    Args:
        fixture_id: SportMonks fixture ID
        
    Returns:
        Odds data dictionary or None if failed
    """
    logger.info(f"Fetching odds for fixture ID {fixture_id}")
    
    params = {
        "fixtures": fixture_id,
        "include": "bookmaker;market;outcome"
    }
    
    response = make_odds_request("odds", params)
    
    if not response or "data" not in response:
        logger.warning(f"No odds data found for fixture {fixture_id}")
        return None
    
    odds_data = response["data"]
    logger.info(f"Found {len(odds_data)} odds entries for fixture {fixture_id}")
    
    return odds_data

def fetch_league_odds(league_id: int, days_ahead: int = 14) -> List[Dict]:
    """
    Fetch odds for all fixtures in a league.
    
    Args:
        league_id: SportMonks league ID
        days_ahead: Number of days to fetch odds for
        
    Returns:
        List of odds data dictionaries
    """
    logger.info(f"Fetching odds for league ID {league_id}")
    
    # First, get fixtures for the league
    from fixtures.fetch_sportmonks import make_api_request
    
    fixtures_response = make_api_request("fixtures", {
        "leagues": league_id,
        "include": "participants"
    })
    
    if not fixtures_response or "data" not in fixtures_response:
        logger.error(f"Failed to fetch fixtures for league {league_id}")
        return []
    
    fixtures = fixtures_response["data"]
    logger.info(f"Found {len(fixtures)} fixtures for league {league_id}")
    
    all_odds = []
    
    for fixture in fixtures:
        fixture_id = fixture.get("id")
        if not fixture_id:
            continue
            
        odds_data = fetch_fixture_odds(fixture_id)
        if odds_data:
            # Add fixture info to odds data
            for odds_entry in odds_data:
                odds_entry["fixture_info"] = fixture
            all_odds.extend(odds_data)
    
    logger.info(f"Collected {len(all_odds)} odds entries for league {league_id}")
    return all_odds

def process_sportmonks_odds(odds_data: Dict) -> Optional[Dict]:
    """
    Process odds data from SportMonks into OddsSnapshot format.
    
    Args:
        odds_data: Odds data from SportMonks API
        
    Returns:
        Dictionary compatible with OddsSnapshot model or None if invalid
    """
    try:
        fixture_info = odds_data.get("fixture_info", {})
        fixture_id = fixture_info.get("id")
        
        if not fixture_id:
            logger.warning("No fixture ID in odds data")
            return None
        
        # Find matching match in our database
        try:
            match = Match.objects.get(api_ref=str(fixture_id))
        except Match.DoesNotExist:
            logger.warning(f"No matching match found for fixture {fixture_id}")
            return None
        
        # Extract bookmaker info
        bookmaker_info = odds_data.get("bookmaker", {})
        bookmaker_name = bookmaker_info.get("name", "SportMonks")
        
        # Extract market info
        market_info = odds_data.get("market", {})
        market_name = market_info.get("name", "Unknown")
        
        # Extract outcomes
        outcomes = odds_data.get("outcome", [])
        
        # Process different market types
        odds_dict = {
            'match': match,
            'bookmaker': f"SportMonks ({bookmaker_name})",
            'fetched_at': timezone.now()
        }
        
        if market_name.lower() == "fulltime result" or market_name.lower() == "match result":
            # 1X2 odds
            for outcome in outcomes:
                outcome_name = outcome.get("name", "").lower()
                odds_value = outcome.get("odds", 0)
                
                if "home" in outcome_name or "1" in outcome_name:
                    odds_dict['odds_home'] = odds_value
                elif "draw" in outcome_name or "x" in outcome_name:
                    odds_dict['odds_draw'] = odds_value
                elif "away" in outcome_name or "2" in outcome_name:
                    odds_dict['odds_away'] = odds_value
        
        elif market_name.lower() == "match goals":
            # Over/Under goals
            for outcome in outcomes:
                outcome_name = outcome.get("name", "").lower()
                odds_value = outcome.get("odds", 0)
                
                if "over" in outcome_name:
                    odds_dict['odds_over'] = odds_value
                elif "under" in outcome_name:
                    odds_dict['odds_under'] = odds_value
        
        # Check if we have valid odds data
        if not any(key.startswith('odds_') for key in odds_dict.keys()):
            logger.warning(f"No valid odds found in market {market_name}")
            return None
        
        logger.info(f"Processed odds for {match}: {market_name} from {bookmaker_name}")
        return odds_dict
        
    except Exception as e:
        logger.error(f"Error processing SportMonks odds: {e}")
        return None

def store_odds_snapshot(odds_data: Dict) -> bool:
    """
    Store odds snapshot in the database.
    
    Args:
        odds_data: Dictionary with odds data
        
    Returns:
        Success flag
    """
    try:
        # Create a new snapshot
        snapshot = OddsSnapshot(
            match=odds_data['match'],
            bookmaker=odds_data['bookmaker'],
            fetched_at=odds_data['fetched_at']
        )
        
        # Add odds values if available
        if 'odds_home' in odds_data:
            snapshot.odds_home = odds_data['odds_home']
        if 'odds_draw' in odds_data:
            snapshot.odds_draw = odds_data['odds_draw']
        if 'odds_away' in odds_data:
            snapshot.odds_away = odds_data['odds_away']
        if 'odds_over' in odds_data:
            snapshot.odds_over = odds_data['odds_over']
        if 'odds_under' in odds_data:
            snapshot.odds_under = odds_data['odds_under']
        
        # Save the snapshot
        snapshot.save()
        logger.info(f"Stored odds snapshot {snapshot.id} for match {odds_data['match']}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store odds snapshot: {e}")
        return False

def fetch_sportmonks_odds(league_ids: Optional[List[int]] = None, demo: bool = False) -> int:
    """
    Fetch and store odds from SportMonks for specified leagues.
    
    Args:
        league_ids: Optional list of specific league IDs to filter by
        demo: If True, use demo data instead of real API
        
    Returns:
        Number of odds snapshots stored
    """
    if demo:
        logger.info("Using demo mode for odds generation")
        return generate_demo_odds()
    
    # Use European leagues if no specific leagues provided
    if not league_ids:
        league_ids = list(EUROPEAN_LEAGUE_IDS.values())
    
    stored_count = 0
    
    logger.info(f"🔍 Starting SportMonks odds ingestion for {len(league_ids)} leagues...")
    
    for league_id in league_ids:
        league_name = next((name for name, lid in EUROPEAN_LEAGUE_IDS.items() if lid == league_id), f"League {league_id}")
        logger.info(f"Fetching odds for {league_name} (ID: {league_id})")
        
        # Fetch odds for this league
        all_odds = fetch_league_odds(league_id)
        
        logger.info(f"Found {len(all_odds)} odds entries for {league_name}")
        
        for odds_data in all_odds:
            processed_odds = process_sportmonks_odds(odds_data)
            
            if processed_odds:
                if store_odds_snapshot(processed_odds):
                    stored_count += 1
            else:
                logger.warning(f"Failed to process odds data: {odds_data.get('id', 'Unknown')}")
    
    logger.info(f"Successfully stored {stored_count} odds snapshots from SportMonks")
    return stored_count

def generate_demo_odds() -> int:
    """
    Generate demo odds data for testing.
    
    Returns:
        Number of odds snapshots stored
    """
    logger.info("Generating demo odds data for testing...")
    
    # Get upcoming matches in the next 14 days
    now = timezone.now()
    upcoming_matches = Match.objects.filter(
        kickoff__gte=now,
        kickoff__lte=now + timedelta(days=14)
    )[:10]  # Limit to 10 matches
    
    if not upcoming_matches.exists():
        logger.warning("No upcoming matches found for demo odds generation")
        return 0
    
    stored_count = 0
    
    for match in upcoming_matches:
        # Generate realistic looking odds
        home_odds = round(2 + 0.5 * (match.home_team.id % 5), 2)  # Between 2.0 and 4.5
        draw_odds = round(3 + 0.25 * (match.id % 5), 2)  # Between 3.0 and 4.0
        away_odds = round(2.5 + match.away_team.id % 4, 2)  # Between 2.5 and 5.5
        
        # Create odds data
        odds_data = {
            'match': match,
            'bookmaker': "SportMonks (Demo)",
            'odds_home': home_odds,
            'odds_draw': draw_odds,
            'odds_away': away_odds,
            'fetched_at': timezone.now()
        }
        
        # Store the odds
        if store_odds_snapshot(odds_data):
            stored_count += 1
            logger.info(f"Generated demo odds for match: {match}")
            
    logger.info(f"Generated {stored_count} demo odds snapshots")
    return stored_count

def get_odds_for_fixture(fixture: Match) -> Optional[OddsSnapshot]:
    """
    Get the latest odds for a fixture from SportMonks.
    
    Args:
        fixture: The match to get odds for
        
    Returns:
        The latest OddsSnapshot for the match, or None if no odds available
    """
    try:
        # Try to get SportMonks odds first
        sportmonks_odds = OddsSnapshot.objects.filter(
            match=fixture, 
            bookmaker__startswith="SportMonks"
        ).order_by('-fetched_at').first()
        
        if sportmonks_odds:
            logger.info(f"Using SportMonks odds for match {fixture.id}")
            return sportmonks_odds
        
        # Fallback to any available odds
        any_odds = OddsSnapshot.objects.filter(
            match=fixture
        ).order_by('-fetched_at').first()
        
        if any_odds:
            logger.info(f"Using fallback odds for match {fixture.id}")
            return any_odds
            
        logger.warning(f"No odds available for match {fixture.id}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting odds for match {fixture.id}: {e}")
        return None
