"""
Pinnacle odds fetcher module.

This module implements functions to fetch match odds from the Pinnacle Sports API
and store them in the OddsSnapshot model.
"""

import os
import time
import logging
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv
from django.utils import timezone
from django.db import transaction
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Import Django models
from core.models import Match, OddsSnapshot

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# API Constants
BASE_URL = "https://api.pinnacle.com/v1"
ODDS_ENDPOINT = f"{BASE_URL}/odds"
SPORT_ID = 29  # Soccer

# Credentials
PINNACLE_USERNAME = os.environ.get("PINNACLE_USERNAME")
PINNACLE_PASSWORD = os.environ.get("PINNACLE_PASSWORD")


def create_session_with_retry() -> requests.Session:
    """
    Create a requests session with retry configuration.
    
    Returns:
        requests.Session: Configured session object
    """
    session = requests.Session()
    
    # Configure retry strategy
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    
    # Add retry adapter to session
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    
    # Add basic auth
    session.auth = (PINNACLE_USERNAME, PINNACLE_PASSWORD)
    
    return session


def fetch_pinnacle_odds(league_ids: Optional[List[int]] = None) -> List[Dict]:
    """
    Fetch odds from Pinnacle Sports API for specified leagues.
    
    Args:
        league_ids: Optional list of league IDs to filter by
        
    Returns:
        List of dictionaries containing fetched odds data
    """
    if not PINNACLE_USERNAME or not PINNACLE_PASSWORD:
        error_msg = "Pinnacle API credentials not found. Set PINNACLE_USERNAME and PINNACLE_PASSWORD in .env file."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Prepare request parameters
    params = {
        "sportId": SPORT_ID,
    }
    
    # Add league IDs if provided
    if league_ids:
        params["leagueIds"] = ",".join(map(str, league_ids))
    
    # Create session with retry logic
    session = create_session_with_retry()
    
    try:
        # Fetch odds data
        logger.info(f"Fetching odds from Pinnacle API for sportId={SPORT_ID}")
        response = session.get(ODDS_ENDPOINT, params=params)
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        
        # Process and store odds
        processed_odds = process_pinnacle_odds(data)
        store_odds(processed_odds)
        
        logger.info(f"Successfully fetched and stored {len(processed_odds)} odds from Pinnacle")
        return processed_odds
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching odds from Pinnacle API: {e}")
        raise
    finally:
        session.close()


def process_pinnacle_odds(data: Dict) -> List[Dict]:
    """
    Process the raw Pinnacle API response to extract relevant odds data.
    
    Args:
        data: Raw API response
        
    Returns:
        List of processed odds dictionaries
    """
    processed_odds = []
    
    # Get current timestamp
    fetched_at = timezone.now()
    
    # Extract leagues data
    leagues = data.get("leagues", [])
    
    for league in leagues:
        league_id = league.get("id")
        
        # Extract events (matches)
        events = league.get("events", [])
        
        for event in events:
            fixture_id = event.get("id")
            
            # Find the 3-way (moneyline) market for soccer
            periods = event.get("periods", [])
            moneyline_market = None
            
            for period in periods:
                # Look for the full-time (0) moneyline market
                if period.get("number") == 0 and period.get("moneyline") is not None:
                    moneyline_market = period.get("moneyline")
                    break
            
            if not moneyline_market:
                logger.warning(f"No moneyline market found for fixture {fixture_id}")
                continue
            
            # Extract 3-way odds (home, draw, away)
            try:
                home_odds = moneyline_market.get("home")
                draw_odds = moneyline_market.get("draw")
                away_odds = moneyline_market.get("away")
                
                # Skip if any of the odds are missing
                if not all([home_odds, draw_odds, away_odds]):
                    logger.warning(f"Incomplete odds for fixture {fixture_id}")
                    continue
                
                # Convert American odds to decimal if needed
                home_odds = american_to_decimal(home_odds)
                draw_odds = american_to_decimal(draw_odds)
                away_odds = american_to_decimal(away_odds)
                
                processed_odds.append({
                    "fixture_id": fixture_id,
                    "league_id": league_id,
                    "odds_home": home_odds,
                    "odds_draw": draw_odds,
                    "odds_away": away_odds,
                    "bookmaker": "Pinnacle",
                    "market_type": "Match Winner",
                    "fetched_at": fetched_at,
                })
            except (KeyError, TypeError) as e:
                logger.warning(f"Error extracting odds for fixture {fixture_id}: {e}")
                continue
    
    return processed_odds


def american_to_decimal(american_odds: float) -> float:
    """
    Convert American odds format to decimal format.
    
    Args:
        american_odds: Odds in American format
        
    Returns:
        Odds in decimal format
    """
    if american_odds > 0:
        return round((american_odds / 100) + 1, 2)
    else:
        return round((100 / abs(american_odds)) + 1, 2)


@transaction.atomic
def store_odds(odds_data: List[Dict]) -> int:
    """
    Store the processed odds in the OddsSnapshot model.
    
    Args:
        odds_data: List of processed odds dictionaries
        
    Returns:
        Number of odds records stored
    """
    stored_count = 0
    
    for odds in odds_data:
        fixture_id = odds.get("fixture_id")
        
        # Find the corresponding match in our database
        try:
            match = Match.objects.get(api_ref=fixture_id)
            
            # Create OddsSnapshot instance
            snapshot = OddsSnapshot(
                match=match,
                bookmaker=odds.get("bookmaker"),
                odds_home=odds.get("odds_home"),
                odds_draw=odds.get("odds_draw"),
                odds_away=odds.get("odds_away"),
                fetched_at=odds.get("fetched_at"),
            )
            snapshot.save()
            stored_count += 1
            
        except Match.DoesNotExist:
            logger.warning(f"No match found with api_ref={fixture_id}")
            continue
        except Exception as e:
            logger.error(f"Error storing odds for fixture {fixture_id}: {e}")
            continue
    
    return stored_count


if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Example usage
    try:
        # Fetch odds for all leagues
        odds = fetch_pinnacle_odds()
        print(f"Fetched and stored {len(odds)} odds from Pinnacle")
    except Exception as e:
        print(f"Error: {e}") 