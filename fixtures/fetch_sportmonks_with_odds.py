"""
SportMonks API integration for fetching fixtures with integrated odds data.

This module handles fetching fixtures and odds from SportMonks API using the
European leagues basic subscription with prediction addon.

Features:
- Fetches fixtures with integrated odds
- Uses SportMonks prediction addon
- Handles European leagues (Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Liga 1)
- Stores both fixture and odds data
"""

import os
import time
import logging
import requests
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from dotenv import load_dotenv

from core.models import Match, Team, League, MatchMetadata, OddsSnapshot

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Constants
SPORTMONKS_BASE_URL = "https://api.sportmonks.com/v3/football"
SPORTMONKS_ODDS_URL = "https://api.sportmonks.com/v3/odds"
SPORTMONKS_RATE_LIMIT = 1.2  # requests per second
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

def make_api_request(endpoint: str, params: Dict = None, base_url: str = None) -> Optional[Dict]:
    """Make API request with error handling and rate limiting."""
    if base_url is None:
        base_url = SPORTMONKS_BASE_URL
        
    url = f"{base_url}/{endpoint}"
    
    if params is None:
        params = {}
    
    params['api_token'] = get_api_token()
    
    for attempt in range(SPORTMONKS_MAX_RETRIES):
        try:
            time.sleep(1 / SPORTMONKS_RATE_LIMIT)
            
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
            
            if "error" in data:
                logger.error(f"API Error: {data['error']['message']}")
                return None
                
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed (attempt {attempt + 1}/{SPORTMONKS_MAX_RETRIES}): {e}")
            if attempt == SPORTMONKS_MAX_RETRIES - 1:
                return None
            time.sleep(SPORTMONKS_RETRY_DELAY)
    
    return None

def fetch_fixture_odds(fixture_id: int) -> Optional[Dict]:
    """Fetch odds for a specific fixture from SportMonks."""
    logger.info(f"Fetching odds for fixture ID {fixture_id}")
    
    params = {
        "fixtures": fixture_id,
        "include": "bookmaker;market;outcome"
    }
    
    response = make_api_request("odds", params, SPORTMONKS_ODDS_URL)
    
    if not response or "data" not in response:
        logger.warning(f"No odds data found for fixture {fixture_id}")
        return None
    
    odds_data = response["data"]
    logger.info(f"Found {len(odds_data)} odds entries for fixture {fixture_id}")
    
    return odds_data

def process_fixture_with_odds(fixture_data: Dict) -> Optional[Dict]:
    """
    Process fixture data with integrated odds from SportMonks.
    
    Args:
        fixture_data: Fixture data from SportMonks API
        
    Returns:
        Dictionary with match and odds data or None if invalid
    """
    try:
        fixture_id = fixture_data.get("id")
        
        # Extract league data
        league_id = fixture_data.get("league_id")
        league_name = next((name for name, lid in EUROPEAN_LEAGUE_IDS.items() if lid == league_id), f"League {league_id}")
        
        # Get or create league
        league, _ = League.objects.get_or_create(
            name_en=league_name,
            defaults={
                "name_ro": league_name,
                "country": "Europe",
                "api_id": league_id
            }
        )
        
        # Extract team data
        participants = fixture_data.get("participants", [])
        if len(participants) < 2:
            logger.error(f"Fixture {fixture_id} doesn't have enough participants")
            return None
            
        # Find home and away teams
        home_team_data = next((p for p in participants if p.get("meta", {}).get("location") == "home"), None)
        away_team_data = next((p for p in participants if p.get("meta", {}).get("location") == "away"), None)
        
        if not home_team_data or not away_team_data:
            logger.error(f"Couldn't determine home/away teams for fixture {fixture_id}")
            return None
        
        # Create teams
        home_team, _ = Team.objects.get_or_create(
            name_en=home_team_data.get("name", "Unknown"),
            defaults={
                "name_ro": home_team_data.get("name", "Unknown"),
                "slug": home_team_data.get("name", "unknown").lower().replace(" ", "-"),
                "api_id": str(home_team_data.get("id", ""))
            }
        )
        
        away_team, _ = Team.objects.get_or_create(
            name_en=away_team_data.get("name", "Unknown"),
            defaults={
                "name_ro": away_team_data.get("name", "Unknown"),
                "slug": away_team_data.get("name", "unknown").lower().replace(" ", "-"),
                "api_id": str(away_team_data.get("id", ""))
            }
        )
        
        # Parse fixture datetime
        kickoff_str = fixture_data.get("starting_at")
        if kickoff_str:
            if '+' in kickoff_str or 'Z' in kickoff_str:
                kickoff = datetime.fromisoformat(kickoff_str.replace('Z', '+00:00'))
            else:
                kickoff = datetime.strptime(kickoff_str, "%Y-%m-%d %H:%M:%S")
                kickoff = timezone.make_aware(kickoff)
        else:
            kickoff = timezone.now() + timedelta(days=1)
        
        # Extract status
        state_id = fixture_data.get("state_id", 1)
        status_map = {
            1: "NS", 2: "1H", 3: "HT", 4: "2H", 5: "ET", 6: "BT", 7: "PEN",
            8: "FT", 9: "AET", 10: "APEN", 11: "LIVE", 12: "CANC", 13: "TBA",
            14: "WO", 15: "ABAND", 16: "SUSP", 17: "INT", 18: "POSTP", 19: "AWARDED"
        }
        status = status_map.get(state_id, "NS")
        
        # Extract scores
        scores = fixture_data.get("scores", [])
        home_score = None
        away_score = None
        
        for score in scores:
            if score.get("description") in ["CURRENT", "FULLTIME"]:
                for participant in participants:
                    if participant.get("id") == score.get("participant_id"):
                        if participant.get("meta", {}).get("location") == "home":
                            home_score = score.get("score", {}).get("goals", 0)
                        elif participant.get("meta", {}).get("location") == "away":
                            away_score = score.get("score", {}).get("goals", 0)
        
        # Create match data
        match_data = {
            "league": league,
            "home_team": home_team,
            "away_team": away_team,
            "kickoff": kickoff,
            "status": status,
            "api_ref": str(fixture_id),
            "home_score": home_score,
            "away_score": away_score,
            "venue": fixture_data.get("venue", {}).get("name", "")
        }
        
        # Fetch odds for this fixture
        odds_data = fetch_fixture_odds(fixture_id)
        processed_odds = None
        
        if odds_data:
            # Process odds data
            for odds_entry in odds_data:
                bookmaker_info = odds_entry.get("bookmaker", {})
                market_info = odds_entry.get("market", {})
                outcomes = odds_entry.get("outcome", [])
                
                if market_info.get("name", "").lower() == "fulltime result":
                    odds_dict = {
                        'match': None,  # Will be set after match creation
                        'bookmaker': f"SportMonks ({bookmaker_info.get('name', 'Unknown')})",
                        'fetched_at': timezone.now()
                    }
                    
                    for outcome in outcomes:
                        outcome_name = outcome.get("name", "").lower()
                        odds_value = outcome.get("odds", 0)
                        
                        if "home" in outcome_name or "1" in outcome_name:
                            odds_dict['odds_home'] = odds_value
                        elif "draw" in outcome_name or "x" in outcome_name:
                            odds_dict['odds_draw'] = odds_value
                        elif "away" in outcome_name or "2" in outcome_name:
                            odds_dict['odds_away'] = odds_value
                    
                    if any(key.startswith('odds_') for key in odds_dict.keys()):
                        processed_odds = odds_dict
                        break
        
        # Prepare metadata
        metadata = {
            "sportmonks_id": fixture_id,
            "league_id": league_id,
            "season_id": fixture_data.get("season_id"),
            "round_id": fixture_data.get("round_id"),
            "stage_id": fixture_data.get("stage_id"),
            "venue_id": fixture_data.get("venue_id"),
            "raw_scores": scores,
            "raw_participants": participants,
            "odds_available": odds_data is not None,
            "odds_count": len(odds_data) if odds_data else 0
        }
        
        if fixture_data.get("venue"):
            metadata["venue_data"] = fixture_data.get("venue")
        
        logger.info(f"✅ Processed fixture with odds: {home_team.name_en} vs {away_team.name_en} (ID: {fixture_id})")
        
        return {
            "match_data": match_data,
            "metadata": metadata,
            "odds_data": processed_odds
        }
        
    except Exception as e:
        logger.exception(f"Error processing fixture with odds: {e}")
        return None

def store_match_with_odds(match_data: Dict, metadata: Dict, odds_data: Optional[Dict]) -> Tuple[Match, bool]:
    """
    Store match with integrated odds data.
    
    Args:
        match_data: Match data dictionary
        metadata: Metadata dictionary
        odds_data: Odds data dictionary or None
        
    Returns:
        Tuple of (Match object, created flag)
    """
    try:
        # Create or update the match
        match, created = Match.objects.update_or_create(
            api_ref=match_data['api_ref'],
            defaults=match_data
        )
        
        # Store metadata
        match_metadata, _ = MatchMetadata.objects.get_or_create(
            match=match,
            defaults={"data": metadata}
        )
        match_metadata.data = metadata
        match_metadata.updated_at = timezone.now()
        match_metadata.save()
        
        # Store odds if available
        if odds_data:
            odds_data['match'] = match
            snapshot = OddsSnapshot(
                match=odds_data['match'],
                bookmaker=odds_data['bookmaker'],
                fetched_at=odds_data['fetched_at']
            )
            
            if 'odds_home' in odds_data:
                snapshot.odds_home = odds_data['odds_home']
            if 'odds_draw' in odds_data:
                snapshot.odds_draw = odds_data['odds_draw']
            if 'odds_away' in odds_data:
                snapshot.odds_away = odds_data['odds_away']
            
            snapshot.save()
            logger.info(f"Stored odds for match {match.id}")
        
        return match, created
        
    except Exception as e:
        logger.error(f"Error storing match with odds: {e}")
        return None, False

def fetch_and_store_fixtures_with_odds(league_ids: List[int] = None, days_ahead: int = 7) -> Tuple[int, int, int, int]:
    """
    Fetch and store fixtures with integrated odds for European leagues.
    
    Args:
        league_ids: Optional list of league IDs to fetch
        days_ahead: Number of days to fetch fixtures for
        
    Returns:
        Tuple of (created_count, updated_count, failed_count, odds_count)
    """
    if league_ids is None:
        league_ids = list(EUROPEAN_LEAGUE_IDS.values())
    
    created_count = 0
    updated_count = 0
    failed_count = 0
    odds_count = 0
    
    logger.info(f"🔍 Starting SportMonks fixtures + odds ingestion for {len(league_ids)} leagues...")
    
    for league_id in league_ids:
        league_name = next((name for name, lid in EUROPEAN_LEAGUE_IDS.items() if lid == league_id), f"League {league_id}")
        logger.info(f"Fetching fixtures with odds for {league_name} (ID: {league_id})")
        
        # Fetch fixtures for this league
        params = {
            "leagues": league_id,
            "include": "participants;venue;scores"
        }
        
        response = make_api_request("fixtures", params)
        
        if not response or "data" not in response:
            logger.error(f"Failed to fetch fixtures for league {league_id}")
            continue
        
        fixtures = response["data"]
        logger.info(f"Found {len(fixtures)} fixtures for {league_name}")
        
        for fixture_data in fixtures:
            processed_data = process_fixture_with_odds(fixture_data)
            
            if not processed_data:
                logger.error(f"Failed to process fixture: {fixture_data.get('id')}")
                failed_count += 1
                continue
            
            match_data = processed_data['match_data']
            metadata = processed_data['metadata']
            odds_data = processed_data['odds_data']
            
            match, created = store_match_with_odds(match_data, metadata, odds_data)
            
            if match:
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                
                if odds_data:
                    odds_count += 1
            else:
                failed_count += 1
    
    logger.info(f"✅ SportMonks fixtures + odds ingestion complete:")
    logger.info(f"   📊 Created: {created_count}")
    logger.info(f"   📊 Updated: {updated_count}")
    logger.info(f"   📊 Failed: {failed_count}")
    logger.info(f"   📊 With Odds: {odds_count}")
    
    return created_count, updated_count, failed_count, odds_count
