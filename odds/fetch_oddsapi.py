"""
OddsAPI integration for fetching high-quality odds from Pinnacle and other sharp bookmakers.
Includes support for historical odds fetching for opening and closing lines.
Enhanced with fuzzy team name matching to ensure proper odds linking.
"""

import os
import time
import logging
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from dotenv import load_dotenv

from core.models import Match, OddsSnapshot, League
from .team_matching import find_matching_match_enhanced, log_unmatched_odds

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Constants
ODDSAPI_BASE_URL = "https://api.the-odds-api.com/v4"
ODDSAPI_SPORT = "soccer"
ODDSAPI_REGION = "eu"
ODDSAPI_MARKET = "h2h"
ODDSAPI_BOOKMAKERS = ["pinnacle", "bet365"]
ODDSAPI_RATE_LIMIT = 1  # requests per second
ODDSAPI_MAX_RETRIES = 3
ODDSAPI_RETRY_DELAY = 5  # seconds

# Romanian league keys (add more as needed)
ROMANIAN_LEAGUE_KEYS = [
    "romania_liga_1",
    "romania_liga_2",
    "romania_cup"
]

def get_api_key() -> str:
    """Get the OddsAPI key from environment variables."""
    api_key = os.getenv("ODDSAPI_KEY")
    if not api_key:
        raise ValueError("ODDSAPI_KEY environment variable not set")
    return api_key

def get_league_keys(league_keys: Optional[List[str]] = None) -> List[str]:
    """
    Get the list of league keys to fetch odds for.
    If no specific keys are provided, use Romanian leagues.
    
    Args:
        league_keys: Optional list of specific league keys to fetch
        
    Returns:
        List of league keys to fetch odds for
    """
    if league_keys:
        return league_keys
    return ROMANIAN_LEAGUE_KEYS

def fetch_odds_with_retry(url: str, params: Dict) -> Optional[Dict]:
    """
    Fetch odds from OddsAPI with retry logic and rate limiting.
    
    Args:
        url: The API endpoint URL
        params: Query parameters for the request
        
    Returns:
        JSON response data or None if all retries failed
    """
    for attempt in range(ODDSAPI_MAX_RETRIES):
        try:
            # Rate limiting
            if attempt > 0:
                time.sleep(ODDSAPI_RETRY_DELAY)
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            # Check remaining requests
            remaining = int(response.headers.get('x-requests-remaining', 0))
            if remaining < 10:
                logger.warning(f"Low remaining requests: {remaining}")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed (attempt {attempt + 1}/{ODDSAPI_MAX_RETRIES}): {e}")
            if attempt == ODDSAPI_MAX_RETRIES - 1:
                return None
            
        # Rate limiting
        time.sleep(1 / ODDSAPI_RATE_LIMIT)
    
    return None

def find_matching_match(api_match: Dict) -> Optional[Match]:
    """
    Legacy wrapper for backwards compatibility.
    Now uses enhanced fuzzy matching system.
    
    Args:
        api_match: Match data from OddsAPI
        
    Returns:
        Matching Match object or None if not found
    """
    return find_matching_match_enhanced(api_match)

def fetch_historical_odds(match_id: str) -> Optional[Dict]:
    """
    Fetch historical odds for a specific match from OddsAPI.
    
    Args:
        match_id: OddsAPI match ID
        
    Returns:
        Historical odds data or None if failed
    """
    logger.info(f"Fetching historical odds for match ID {match_id}")
    
    api_key = get_api_key()
    url = f"{ODDSAPI_BASE_URL}/sports/{ODDSAPI_SPORT}/odds/historical/{match_id}"
    
    params = {
        'apiKey': api_key,
        'regions': ODDSAPI_REGION,
        'markets': ODDSAPI_MARKET,
        'bookmakers': ','.join(ODDSAPI_BOOKMAKERS),
        'date_format': 'iso'
    }
    
    data = fetch_odds_with_retry(url, params)
    
    if not data:
        logger.error(f"Failed to fetch historical odds for match ID {match_id}")
        return None
        
    logger.info(f"Successfully fetched historical odds for match ID {match_id}")
    return data

def process_historical_odds(api_match: Dict) -> Optional[Dict]:
    """
    Process historical odds data from OddsAPI into OddsSnapshot format.
    
    Args:
        api_match: Historical match data from OddsAPI
        
    Returns:
        Dictionary with opening and closing odds or None if invalid
    """
    try:
        # Find matching match in our database
        match = find_matching_match(api_match)
        if not match:
            return None
        
        # Process historical bookmaker data to find opening and closing odds
        historical_data = fetch_historical_odds(api_match.get('id'))
        if not historical_data or not historical_data.get('bookmakers'):
            logger.warning(f"No historical odds data found for match {match.id}")
            return None
            
        # Extract bookmakers data
        bookmakers_data = historical_data.get('bookmakers', [])
        pinnacle_data = None
        
        # Find Pinnacle data (or Bet365 as fallback)
        for bookmaker in bookmakers_data:
            if bookmaker['key'].lower() == 'pinnacle':
                pinnacle_data = bookmaker
                logger.info(f"Found Pinnacle historical odds for match {match.id}")
                break
        
        if not pinnacle_data:
            for bookmaker in bookmakers_data:
                if bookmaker['key'].lower() == 'bet365':
                    pinnacle_data = bookmaker
                    logger.info(f"Found Bet365 historical odds for match {match.id}")
                    break
        
        if not pinnacle_data or not pinnacle_data.get('history'):
            logger.warning(f"No historical odds history found for match {match.id}")
            return None
            
        # Get odds history
        odds_history = pinnacle_data.get('history', [])
        if not odds_history:
            return None
            
        # Sort history by timestamp
        odds_history.sort(key=lambda x: x.get('timestamp', ''))
        
        # Get opening and closing odds
        opening_odds = odds_history[0] if odds_history else None
        closing_odds = odds_history[-1] if odds_history else None
        
        # Process current odds
        current_odds = process_odds_data(api_match)
        if not current_odds:
            return None
            
        # Extract opening odds
        opening_odds_data = {}
        if opening_odds and opening_odds.get('markets'):
            for market in opening_odds.get('markets', []):
                if market.get('key') == 'h2h':
                    for outcome in market.get('outcomes', []):
                        if outcome['name'] == api_match['home_team']:
                            opening_odds_data['opening_odds_home'] = outcome['price']
                        elif outcome['name'] == api_match['away_team']:
                            opening_odds_data['opening_odds_away'] = outcome['price']
                        elif outcome['name'].lower() == 'draw':
                            opening_odds_data['opening_odds_draw'] = outcome['price']
        
        # Extract closing odds
        closing_odds_data = {}
        if closing_odds and closing_odds.get('markets'):
            for market in closing_odds.get('markets', []):
                if market.get('key') == 'h2h':
                    for outcome in market.get('outcomes', []):
                        if outcome['name'] == api_match['home_team']:
                            closing_odds_data['closing_odds_home'] = outcome['price']
                        elif outcome['name'] == api_match['away_team']:
                            closing_odds_data['closing_odds_away'] = outcome['price']
                        elif outcome['name'].lower() == 'draw':
                            closing_odds_data['closing_odds_draw'] = outcome['price']
        
        # Merge all odds data
        odds_data = {**current_odds, **opening_odds_data, **closing_odds_data}
        
        # Log the historical odds we found
        logger.info(
            f"Processed historical odds for {match}: "
            f"Opening: H={odds_data.get('opening_odds_home', 'N/A')}, "
            f"D={odds_data.get('opening_odds_draw', 'N/A')}, "
            f"A={odds_data.get('opening_odds_away', 'N/A')} | "
            f"Closing: H={odds_data.get('closing_odds_home', 'N/A')}, "
            f"D={odds_data.get('closing_odds_draw', 'N/A')}, "
            f"A={odds_data.get('closing_odds_away', 'N/A')}"
        )
        
        return odds_data
        
    except Exception as e:
        logger.error(f"Error processing historical odds data: {e}")
        return None

def process_odds_data(api_match: Dict) -> Optional[Dict]:
    """
    Process odds data from OddsAPI into OddsSnapshot format.
    
    Args:
        api_match: Match data from OddsAPI
        
    Returns:
        Dictionary compatible with OddsSnapshot model or None if invalid
    """
    try:
        # Find matching match in our database
        match = find_matching_match(api_match)
        if not match:
            return None
        
        # Get Pinnacle odds if available
        pinnacle_odds = None
        for bookmaker in api_match.get('bookmakers', []):
            if bookmaker['key'].lower() == 'pinnacle':
                pinnacle_odds = bookmaker
                logger.info(f"Found Pinnacle odds for match {match.id}")
                break
        
        # If no Pinnacle odds, try Bet365
        if not pinnacle_odds:
            for bookmaker in api_match.get('bookmakers', []):
                if bookmaker['key'].lower() == 'bet365':
                    pinnacle_odds = bookmaker
                    logger.info(f"Found Bet365 odds for match {match.id}")
                    break
        
        if not pinnacle_odds:
            logger.warning(f"No Pinnacle or Bet365 odds found for match {match.id}")
            return None
        
        # Extract odds
        odds_data = {
            'match': match,
            'bookmaker': f"OddsAPI ({pinnacle_odds['key']})",
            'fetched_at': timezone.now()
        }
        
        for outcome in pinnacle_odds.get('markets', [{}])[0].get('outcomes', []):
            if outcome['name'] == api_match['home_team']:
                odds_data['odds_home'] = outcome['price']
            elif outcome['name'] == api_match['away_team']:
                odds_data['odds_away'] = outcome['price']
            elif outcome['name'].lower() == 'draw':
                odds_data['odds_draw'] = outcome['price']
        
        if not all(k in odds_data for k in ['odds_home', 'odds_draw', 'odds_away']):
            logger.warning(f"Incomplete odds data for match {match.id}")
            return None
        
        # Log the odds we found
        logger.info(
            f"Processed odds for {match}: "
            f"Home={odds_data['odds_home']:.2f}, "
            f"Draw={odds_data['odds_draw']:.2f}, "
            f"Away={odds_data['odds_away']:.2f} "
            f"({pinnacle_odds['key']})"
        )
        
        return odds_data
        
    except Exception as e:
        logger.error(f"Error processing odds data: {e}")
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
        # Create a new snapshot with all the odds data
        snapshot = OddsSnapshot(
            match=odds_data['match'],
            bookmaker=odds_data['bookmaker'],
            odds_home=odds_data['odds_home'],
            odds_draw=odds_data['odds_draw'],
            odds_away=odds_data['odds_away'],
            fetched_at=odds_data['fetched_at']
        )
        
        # Add historical odds if available
        if 'opening_odds_home' in odds_data:
            snapshot.opening_odds_home = odds_data['opening_odds_home']
        if 'opening_odds_draw' in odds_data:
            snapshot.opening_odds_draw = odds_data['opening_odds_draw']
        if 'opening_odds_away' in odds_data:
            snapshot.opening_odds_away = odds_data['opening_odds_away']
            
        if 'closing_odds_home' in odds_data:
            snapshot.closing_odds_home = odds_data['closing_odds_home']
        if 'closing_odds_draw' in odds_data:
            snapshot.closing_odds_draw = odds_data['closing_odds_draw']
        if 'closing_odds_away' in odds_data:
            snapshot.closing_odds_away = odds_data['closing_odds_away']
        
        # Save the snapshot
        snapshot.save()
        logger.info(f"Stored odds snapshot {snapshot.id} for match {odds_data['match']}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store odds snapshot: {e}")
        return False

def fetch_oddsapi_odds(league_ids: Optional[List[int]] = None, demo: bool = False) -> int:
    """
    Fetch and store odds from OddsAPI for specified leagues.
    Enhanced with fuzzy matching and unmatched odds logging.
    
    Args:
        league_ids: Optional list of specific league IDs to filter by
        demo: If True, use demo data instead of real API
        
    Returns:
        Number of odds snapshots stored
    """
    # Check if demo mode is enabled or we don't have an API key
    api_key = os.getenv("ODDSAPI_KEY")
    if demo or not api_key:
        logger.info("Using demo mode for odds generation")
        return generate_demo_odds()
        
    # Real API mode
    # First, map league IDs to league keys if provided
    league_keys = None
    if league_ids:
        # Get all leagues matching the specified IDs
        leagues = League.objects.filter(api_id__in=league_ids)
        if not leagues.exists():
            logger.warning(f"No leagues found with IDs: {league_ids}")
            return 0
        
        # For now, we'll still use default Romanian leagues
        # In real implementation, you'd map league IDs to OddsAPI's league keys
        logger.info(f"Filtering leagues by IDs: {league_ids}")
    
    leagues_to_fetch = get_league_keys(league_keys)
    
    odds_snapshots = []
    stored_count = 0
    unmatched_events = []  # Track unmatched odds events
    
    logger.info(f"🔍 Starting odds ingestion for {len(leagues_to_fetch)} leagues...")
    
    for league in leagues_to_fetch:
        logger.info(f"Fetching odds for league: {league}")
        
        url = f"{ODDSAPI_BASE_URL}/sports/{ODDSAPI_SPORT}/odds"
        params = {
            'apiKey': api_key,
            'regions': ODDSAPI_REGION,
            'markets': ODDSAPI_MARKET,
            'bookmakers': ','.join(ODDSAPI_BOOKMAKERS),
            'league': league
        }
        
        data = fetch_odds_with_retry(url, params)
        if not data:
            logger.error(f"Failed to fetch odds for league {league}")
            continue
        
        logger.info(f"Found {len(data)} matches for league {league}")
        
        for match_data in data:
            # Try to get historical odds (opening and closing)
            odds_snapshot = process_historical_odds(match_data)
            
            # If historical odds failed, fall back to current odds only
            if not odds_snapshot:
                odds_snapshot = process_odds_data(match_data)
                
            if odds_snapshot:
                if demo:
                    # In demo mode, just collect the data but don't store it
                    odds_snapshots.append(odds_snapshot)
                    logger.info(f"DEMO: Would store odds for {odds_snapshot['match']}")
                else:
                    # Actually store the odds snapshot
                    if store_odds_snapshot(odds_snapshot):
                        stored_count += 1
            else:
                # Track unmatched event for debugging
                unmatched_event = {
                    'league': league,
                    'home_team': match_data.get('home_team', 'Unknown'),
                    'away_team': match_data.get('away_team', 'Unknown'),
                    'commence_time': match_data.get('commence_time', 'Unknown'),
                    'id': match_data.get('id', 'Unknown'),
                    'reason': 'No matching fixture found or odds processing failed'
                }
                unmatched_events.append(unmatched_event)
                logger.warning(f"❌ Unmatched event: {unmatched_event['home_team']} vs {unmatched_event['away_team']}")
    
    # Log unmatched events for debugging
    if unmatched_events:
        log_unmatched_odds(unmatched_events, filename="unmatched_odds.json")
        logger.warning(f"📊 ODDS INGESTION SUMMARY:")
        logger.warning(f"   ✅ Successfully matched and stored: {stored_count}")
        logger.warning(f"   ❌ Unmatched events: {len(unmatched_events)}")
        logger.warning(f"   📄 Unmatched events logged to: unmatched_odds.json")
    else:
        logger.info(f"✅ Perfect match rate! All {stored_count} odds events successfully matched and stored.")
    
    if demo:
        logger.info(f"DEMO: Would have stored {len(odds_snapshots)} odds snapshots")
        return len(odds_snapshots)
    else:
        logger.info(f"Successfully stored {stored_count} odds snapshots")
        return stored_count

# For demo/testing purposes
def generate_demo_odds() -> int:
    """
    Generate demo odds data for recent and upcoming matches.
    Uses actual team IDs from the database instead of hardcoded values.
    
    Returns:
        Number of odds snapshots stored
    """
    logger.info("Generating demo odds data for testing...")
    
    # Get upcoming matches in the next 7 days
    now = timezone.now()
    upcoming_matches = Match.objects.filter(
        kickoff__gte=now,
        kickoff__lte=now + timedelta(days=7)
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
        
        # Generate opening odds (slightly different from current)
        opening_home = round(home_odds * (0.9 + 0.2 * (match.id % 3) / 10), 2)
        opening_draw = round(draw_odds * (0.9 + 0.2 * (match.away_team.id % 3) / 10), 2)
        opening_away = round(away_odds * (0.9 + 0.2 * (match.home_team.id % 3) / 10), 2)
        
        # Create odds data with historical odds
        odds_data = {
            'match': match,
            'bookmaker': "Demo Bookmaker",
            'odds_home': home_odds,
            'odds_draw': draw_odds,
            'odds_away': away_odds,
            'opening_odds_home': opening_home,
            'opening_odds_draw': opening_draw,
            'opening_odds_away': opening_away,
            'closing_odds_home': home_odds,  # Current odds are closing odds
            'closing_odds_draw': draw_odds,
            'closing_odds_away': away_odds,
            'fetched_at': timezone.now()
        }
        
        # Store the odds
        if store_odds_snapshot(odds_data):
            stored_count += 1
            logger.info(f"Generated demo odds for match: {match}")
            
    logger.info(f"Generated {stored_count} demo odds snapshots")
    return stored_count 