"""
SportMonks API integration for fetching fixtures and match data.

This module handles fetching live and upcoming fixtures from SportMonks API, 
along with lineups, injuries, and team stats. Data is stored in the Match model
and enriched with additional metadata.
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

from core.models import Match, Team, League, MatchMetadata

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Constants
SPORTMONKS_BASE_URL = "https://api.sportmonks.com/v3/football"
SPORTMONKS_RATE_LIMIT = 1  # requests per second
SPORTMONKS_MAX_RETRIES = 3
SPORTMONKS_RETRY_DELAY = 5  # seconds

# Global list for tracking skipped fixtures
skipped_fixtures = []

# Romanian League IDs (update with actual SportMonks IDs)
ROMANIAN_LEAGUE_IDS = {
    "Liga 1": 274,  # Liga 1
    "Liga 2": 332,  # Liga 2
    "Romanian Cup": 333,  # Romanian Cup
}

def get_api_token() -> str:
    """Get the SportMonks API token from environment variables."""
    # Try both possible environment variable names
    token = os.getenv("SPORTMONKS_TOKEN") or os.getenv("SPORTMONKS_API_TOKEN")
    if not token:
        raise ValueError("SPORTMONKS_TOKEN or SPORTMONKS_API_TOKEN environment variable not set")
    return token

def log_skipped_fixture(fixture_data: Dict, reason: str):
    """Log a fixture that was skipped due to invalid data."""
    global skipped_fixtures
    
    participants = fixture_data.get("participants", [])
    home_team_name = "Unknown"
    away_team_name = "Unknown"
    
    if len(participants) >= 2:
        home_team_data = next((p for p in participants if p.get("meta", {}).get("location") == "home"), None)
        away_team_data = next((p for p in participants if p.get("meta", {}).get("location") == "away"), None)
        
        if home_team_data:
            home_team_name = home_team_data.get("name", "Unknown")
        if away_team_data:
            away_team_name = away_team_data.get("name", "Unknown")
    
    skipped_info = {
        "fixture_id": fixture_data.get("id"),
        "home_team": home_team_name,
        "away_team": away_team_name,
        "league_id": fixture_data.get("league_id"),
        "commence_time": fixture_data.get("starting_at"),
        "reason": reason,
        "timestamp": timezone.now().isoformat()
    }
    
    skipped_fixtures.append(skipped_info)
    logger.warning(f"⚠️  SKIPPED FIXTURE: {reason} - {home_team_name} vs {away_team_name} (ID: {fixture_data.get('id')})")

def make_api_request(endpoint: str, params: Dict = None) -> Optional[Dict]:
    """
    Make a request to the SportMonks API with retry logic and rate limiting.
    
    Args:
        endpoint: API endpoint path (after base URL)
        params: Query parameters for the request
        
    Returns:
        JSON response data or None if all retries failed
    """
    token = get_api_token()
    url = f"{SPORTMONKS_BASE_URL}/{endpoint}"
    
    # Debug logging
    logger.debug(f"API Token: {token[:10]}...{token[-5:]}")
    logger.debug(f"Request URL: {url}")
    
    headers = {
        "Authorization": token,
        "Accept": "application/json"
    }
    
    # Add default parameters if not provided
    if params is None:
        params = {}
    
    logger.debug(f"Request params: {params}")
    
    for attempt in range(SPORTMONKS_MAX_RETRIES):
        try:
            # Rate limiting
            if attempt > 0:
                time.sleep(SPORTMONKS_RETRY_DELAY)
            
            logger.debug(f"Making API request to {url} (attempt {attempt+1})")
            response = requests.get(url, headers=headers, params=params)
            
            # Log response details
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {response.headers}")
            
            if response.status_code != 200:
                logger.debug(f"Response content: {response.text[:500]}")
            
            # Handle 404 errors gracefully
            if response.status_code == 404:
                logger.warning(f"Resource not found (404) for endpoint: {endpoint}")
                return None
            
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API error
            if "error" in data:
                logger.error(f"API Error: {data['error']['message']}")
                return None
                
            return data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Resource not found (404) for endpoint: {endpoint}")
                return None
            logger.error(f"HTTP error (attempt {attempt + 1}/{SPORTMONKS_MAX_RETRIES}): {e}")
            if attempt == SPORTMONKS_MAX_RETRIES - 1:
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed (attempt {attempt + 1}/{SPORTMONKS_MAX_RETRIES}): {e}")
            if attempt == SPORTMONKS_MAX_RETRIES - 1:
                return None
            
        # Rate limiting
        time.sleep(1 / SPORTMONKS_RATE_LIMIT)
    
    return None

def fetch_leagues() -> List[Dict]:
    """
    Fetch Romanian leagues from SportMonks API.
    
    Returns:
        List of league data dictionaries
    """
    logger.info("Fetching leagues from SportMonks API")
    
    # Simple request with minimal parameters
    response = make_api_request("leagues")
    
    if not response or "data" not in response:
        logger.error("Failed to fetch leagues")
        return []
    
    leagues = response["data"]
    logger.info(f"Fetched {len(leagues)} leagues")
    
    return leagues

def fetch_fixtures_for_league(league_id: int, days_range: int = 7) -> List[Dict]:
    """
    Fetch fixtures for a specific league within a date range.
    
    Args:
        league_id: SportMonks league ID
        days_range: Number of days to fetch fixtures for (before and after today)
        
    Returns:
        List of fixture data dictionaries
    """
    logger.info(f"Fetching fixtures for league ID {league_id}")
    
    # Include additional data with the fixtures
    params = {
        "leagues": league_id,
        "include": "participants;venue;scores",
    }
    
    response = make_api_request("fixtures", params)
    
    if not response or "data" not in response:
        logger.error(f"Failed to fetch fixtures for league ID {league_id}")
        return []
    
    fixtures = response["data"]
    logger.info(f"Fetched {len(fixtures)} fixtures for league ID {league_id}")
    
    return fixtures

def fetch_live_fixtures() -> List[Dict]:
    """
    Fetch currently live fixtures for Romanian leagues.
    
    Returns:
        List of live fixture data dictionaries
    """
    logger.info("Fetching live fixtures")
    
    params = {
        "include": "scores;participants;venue;lineups;events;state;statistics.type;injuries;metadata",
        "filter[status]": "LIVE"  # Updated filter format for live matches
    }
    
    response = make_api_request("livescores", params)
    
    if not response or "data" not in response:
        logger.error("Failed to fetch live fixtures")
        return []
    
    all_fixtures = response["data"]
    
    # Filter for Romanian leagues
    romanian_fixtures = [
        fixture for fixture in all_fixtures 
        if fixture.get("league_id") in ROMANIAN_LEAGUE_IDS.values()
    ]
    
    logger.info(f"Fetched {len(romanian_fixtures)} live Romanian fixtures")
    
    return romanian_fixtures

def get_or_create_league(league_data: Dict) -> Tuple[League, bool]:
    """
    Get or create a League object from SportMonks league data.
    
    Args:
        league_data: League data from SportMonks API
        
    Returns:
        Tuple of (League object, created flag)
    """
    try:
        league_name = league_data.get("name", "Unknown League")
        country = league_data.get("country", {}).get("name", "Romania")
        
        league, created = League.objects.get_or_create(
            name_en=league_name,
            defaults={
                "name_ro": league_name,  # Use English name as fallback
                "country": country,
                "api_id": league_data.get("id")
            }
        )
        
        # Update API reference if missing
        if not league.api_id:
            league.api_id = league_data.get("id")
            league.save()
            
        return league, created
    
    except Exception as e:
        logger.error(f"Error creating league: {e}")
        return None, False

def get_or_create_team(team_data: Dict) -> Tuple[Team, bool]:
    """
    Enhanced team creation with strict validation - NO DUMMY DATA ALLOWED.
    
    Args:
        team_data: Team data from SportMonks API
        
    Returns:
        Tuple of (Team object, created flag) or (None, False) if invalid
    """
    try:
        # STRICT VALIDATION - NO DUMMY DATA
        team_name = team_data.get("name", "").strip()
        
        # Reject empty or missing names
        if not team_name or team_name == "":
            logger.error(f"Team data missing name: {team_data}")
            return None, False
            
        # Reject dummy/placeholder names
        dummy_patterns = [
            'home team', 'away team', 'team a', 'team b', 
            'unknown team', 'test team', 'mock team', 'demo team',
            'placeholder', 'tbd', 'to be determined'
        ]
        
        team_name_lower = team_name.lower()
        for pattern in dummy_patterns:
            if pattern in team_name_lower:
                logger.error(f"🚫 REJECTED dummy team name: '{team_name}'")
                return None, False
        
        # Reject names that are too short (likely dummy)
        if len(team_name) < 3:
            logger.error(f"🚫 REJECTED team name too short: '{team_name}'")
            return None, False
            
        # Reject names with numbers only (likely auto-generated)
        if team_name.replace(' ', '').isdigit():
            logger.error(f"🚫 REJECTED team name is numbers only: '{team_name}'")
            return None, False
        
        # Ensure we have a valid SportMonks team ID
        team_id = team_data.get("id")
        if not team_id:
            logger.error(f"🚫 REJECTED team data missing ID: {team_data}")
            return None, False
            
        team_slug = team_name.lower().replace(" ", "-").replace(".", "")
        
        # Create/get team with validated data
        team, created = Team.objects.get_or_create(
            name_en=team_name,
            defaults={
                "name_ro": team_name,  # Use English name as fallback
                "slug": team_slug,
                "api_id": str(team_id)
            }
        )
        
        # Update API reference if missing
        if not team.api_id and team_id:
            team.api_id = str(team_id)
            team.save()
            
        logger.info(f"✅ Valid team created/found: {team_name} (SportMonks ID: {team_id})")
        return team, created
    
    except Exception as e:
        logger.error(f"Error creating team: {e}")
        return None, False

def parse_fixture_datetime(fixture_data: Dict) -> datetime:
    """
    Parse fixture datetime from SportMonks API data.
    
    Args:
        fixture_data: Fixture data from SportMonks API
        
    Returns:
        Timezone-aware datetime object
    """
    try:
        # New SportMonks date format is a string like "2006-03-25 16:00:00"
        dt_str = fixture_data.get("starting_at")
        
        if not dt_str:
            raise ValueError("No valid datetime found in fixture data")
            
        # Parse the datetime string (if no timezone, assume UTC)
        if '+' in dt_str or 'Z' in dt_str:
            # Already has timezone
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        else:
            # No timezone, assume UTC
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            # Make it timezone aware
            dt = timezone.make_aware(dt)
            
        return dt
    
    except Exception as e:
        logger.error(f"Error parsing fixture datetime: {e}")
        # Return a fallback date (30 days from now)
        return timezone.now() + timedelta(days=30)

def get_fixture_status(fixture_data: Dict) -> str:
    """
    Get fixture status code from SportMonks API data.
    
    Args:
        fixture_data: Fixture data from SportMonks API
        
    Returns:
        Status code (e.g., "NS", "FT", "HT", etc.)
    """
    # Map SportMonks state codes to our status codes
    state_map = {
        1: "NS",     # Not started
        2: "1H",     # First half
        3: "HT",     # Halftime
        4: "2H",     # Second half
        5: "ET",     # Extra time
        6: "BT",     # Break time
        7: "PEN",    # Penalties
        8: "FT",     # Full time
        9: "AET",    # After extra time
        10: "APEN",  # After penalties
        11: "LIVE",  # Live (generic)
        12: "CANC",  # Cancelled
        13: "TBA",   # Time to be announced
        14: "WO",    # Walkover
        15: "ABAND", # Abandoned
        16: "SUSP",  # Suspended
        17: "INT",   # Interrupted
        18: "POSTP", # Postponed
        19: "AWARDED" # Awarded
    }
    
    state_id = fixture_data.get("state_id")
    
    if state_id is None:
        return "NS"  # Default to not started
        
    return state_map.get(state_id, "NS")

def process_fixture_data(fixture_data: Dict) -> Optional[Dict]:
    """
    Enhanced fixture processing with strict team validation - NO DUMMY DATA.
    
    Args:
        fixture_data: Fixture data from SportMonks API
        
    Returns:
        Dictionary compatible with Match model or None if invalid
    """
    try:
        fixture_id = fixture_data.get("id")
        
        # Extract league data
        league_id = fixture_data.get("league_id")
        league_data = {"id": league_id, "name": fixture_data.get("league", {}).get("name", "Unknown League")}
        
        # Get or create league
        league, _ = get_or_create_league(league_data)
        if not league:
            logger.error(f"🚫 SKIPPED - Failed to get or create league for fixture {fixture_id}")
            return None
            
        # Extract team data
        participants = fixture_data.get("participants", [])
        if len(participants) < 2:
            logger.error(f"🚫 SKIPPED - Fixture {fixture_id} doesn't have enough participants")
            return None
            
        # Find home and away teams
        home_team_data = next((p for p in participants if p.get("meta", {}).get("location") == "home"), None)
        away_team_data = next((p for p in participants if p.get("meta", {}).get("location") == "away"), None)
        
        if not home_team_data or not away_team_data:
            logger.error(f"🚫 SKIPPED - Couldn't determine home/away teams for fixture {fixture_id}")
            return None
            
        # STRICT TEAM VALIDATION - Use enhanced team creation
        home_team, _ = get_or_create_team(home_team_data)
        away_team, _ = get_or_create_team(away_team_data)
        
        # REJECT fixture if either team is invalid
        if not home_team or not away_team:
            logger.error(f"🚫 SKIPPED - Invalid teams for fixture {fixture_id} - REJECTING FIXTURE")
            # Log the skipped fixture for debugging
            log_skipped_fixture(fixture_data, "Invalid team data")
            return None
            
        # Extract fixture datetime
        kickoff = parse_fixture_datetime(fixture_data)
        
        # Extract status
        status = get_fixture_status(fixture_data)
        
        # Extract venue
        venue = fixture_data.get("venue", {}).get("name", "")
        
        # Extract scores
        scores = fixture_data.get("scores", [])
        home_score = None
        away_score = None
        
        for score in scores:
            if score.get("description") == "CURRENT" or score.get("description") == "FULLTIME":
                for participant in participants:
                    if participant.get("id") == score.get("participant_id"):
                        if participant.get("meta", {}).get("location") == "home":
                            home_score = score.get("score", {}).get("goals", 0)
                        elif participant.get("meta", {}).get("location") == "away":
                            away_score = score.get("score", {}).get("goals", 0)
                
        # Prepare match data for database
        match_data = {
            "league": league,
            "home_team": home_team,
            "away_team": away_team,
            "kickoff": kickoff,
            "status": status,
            "api_ref": str(fixture_data.get("id")),
            "home_score": home_score,
            "away_score": away_score,
            "venue": venue
        }
        
        # Prepare metadata
        metadata = {
            "sportmonks_id": fixture_data.get("id"),
            "league_id": fixture_data.get("league_id"),
            "season_id": fixture_data.get("season_id"),
            "round_id": fixture_data.get("round_id"),
            "stage_id": fixture_data.get("stage_id"),
            "venue_id": fixture_data.get("venue_id"),
            "raw_scores": scores,
            "raw_participants": participants,
        }
        
        if fixture_data.get("venue"):
            metadata["venue_data"] = fixture_data.get("venue")
        
        logger.info(f"✅ Valid fixture processed: {home_team.name_en} vs {away_team.name_en} (ID: {fixture_id})")
        
        return {
            "match_data": match_data,
            "metadata": metadata
        }
        
    except Exception as e:
        logger.exception(f"🚫 SKIPPED - Error processing fixture data: {e}")
        return None

def store_match_metadata(match: Match, metadata: Dict) -> bool:
    """
    Store match metadata from SportMonks API.
    
    Args:
        match: Match object to store metadata for
        metadata: Metadata dictionary
        
    Returns:
        Success flag
    """
    try:
        # Get or create MatchMetadata object
        match_metadata, created = MatchMetadata.objects.get_or_create(
            match=match,
            defaults={"data": metadata}
        )
        
        # Update if exists
        if not created:
            match_metadata.data = metadata
            match_metadata.updated_at = timezone.now()
            match_metadata.save()
            
        return True
        
    except Exception as e:
        logger.error(f"Error storing metadata for match {match.id}: {e}")
        return False

def fetch_team_injuries(team_id: int) -> List[Dict]:
    """
    Fetch injuries for a specific team from SportMonks API.
    
    Args:
        team_id: SportMonks team ID
        
    Returns:
        List of injury data dictionaries
    """
    logger.info(f"Fetching injuries for team ID {team_id}")
    
    params = {
        "include": "player;team",
    }
    
    response = make_api_request(f"teams/{team_id}/injuries", params)
    
    if not response:
        logger.warning(f"Skipping team ID {team_id} – injuries not found (404)")
        return []
    
    if "data" not in response:
        logger.error(f"Failed to fetch injuries for team ID {team_id} - invalid response format")
        return []
    
    injuries = response["data"]
    logger.info(f"Fetched {len(injuries)} injuries for team ID {team_id}")
    
    return injuries

def fetch_team_stats(team_id: int) -> Optional[Dict]:
    """
    Fetch statistics for a specific team from SportMonks API.
    
    Args:
        team_id: SportMonks team ID
        
    Returns:
        Team statistics dictionary or None if failed
    """
    logger.info(f"Fetching stats for team ID {team_id}")
    
    params = {
        "include": "season;league"
    }
    
    response = make_api_request(f"teams/{team_id}/stats", params)
    
    if not response:
        logger.warning(f"Skipping team ID {team_id} – stats not found (404)")
        return None
    
    if "data" not in response:
        logger.error(f"Failed to fetch stats for team ID {team_id} - invalid response format")
        return None
    
    stats = response["data"]
    logger.info(f"Fetched stats for team ID {team_id}")
    
    return stats

def fetch_team_players(team_id: int) -> List[Dict]:
    """
    Fetch player data for a specific team from SportMonks API.
    
    Args:
        team_id: SportMonks team ID
        
    Returns:
        List of player data dictionaries
    """
    logger.info(f"Fetching players for team ID {team_id}")
    
    params = {
        "include": "player;position"
    }
    
    response = make_api_request(f"players/squad/{team_id}", params)
    
    if not response:
        logger.warning(f"Skipping team ID {team_id} – players not found (404)")
        return []
    
    if "data" not in response:
        logger.error(f"Failed to fetch players for team ID {team_id} - invalid response format")
        return []
    
    players = response["data"]
    logger.info(f"Fetched {len(players)} players for team ID {team_id}")
    
    return players

def enrich_match_data(match: Match) -> bool:
    """
    Enrich a match with additional data from SportMonks.
    
    Args:
        match: Match object to enrich
        
    Returns:
        Success flag
    """
    try:
        # Get existing metadata or create new
        metadata, created = MatchMetadata.objects.get_or_create(
            match=match,
            defaults={"data": {}}
        )
        
        current_data = metadata.data.copy()
        
        # Fetch home team ID
        home_team_id = None
        if match.home_team and match.home_team.api_id:
            try:
                home_team_id = int(match.home_team.api_id)
            except (ValueError, TypeError):
                logger.warning(f"Invalid home team API ID: {match.home_team.api_id}")
        
        # Fetch away team ID
        away_team_id = None
        if match.away_team and match.away_team.api_id:
            try:
                away_team_id = int(match.away_team.api_id)
            except (ValueError, TypeError):
                logger.warning(f"Invalid away team API ID: {match.away_team.api_id}")
        
        # Fetch home team injuries
        if home_team_id:
            home_injuries = fetch_team_injuries(home_team_id)
            if home_injuries:
                current_data["home_injuries"] = home_injuries
                # Count injured starters to update match field
                injured_starters = sum(1 for inj in home_injuries if inj.get("player", {}).get("is_starter", False))
                match.injured_starters_home = injured_starters
        
        # Fetch away team injuries
        if away_team_id:
            away_injuries = fetch_team_injuries(away_team_id)
            if away_injuries:
                current_data["away_injuries"] = away_injuries
                # Count injured starters to update match field
                injured_starters = sum(1 for inj in away_injuries if inj.get("player", {}).get("is_starter", False))
                match.injured_starters_away = injured_starters
        
        # Fetch home team stats
        if home_team_id:
            home_stats = fetch_team_stats(home_team_id)
            if home_stats:
                current_data["home_team_stats"] = home_stats
                # Extract relevant stats
                if "stats" in home_stats:
                    stats = home_stats["stats"]
                    match.avg_goals_home = stats.get("scored_avg", 0)
                    match.avg_cards_home = stats.get("yellowcards_avg", 0)
                    match.team_form_home = stats.get("form_value", 0)
        
        # Fetch away team stats
        if away_team_id:
            away_stats = fetch_team_stats(away_team_id)
            if away_stats:
                current_data["away_team_stats"] = away_stats
                # Extract relevant stats
                if "stats" in away_stats:
                    stats = away_stats["stats"]
                    match.avg_goals_away = stats.get("scored_avg", 0)
                    match.avg_cards_away = stats.get("yellowcards_avg", 0)
                    match.team_form_away = stats.get("form_value", 0)
        
        # Save metadata
        metadata.data = current_data
        metadata.updated_at = timezone.now()
        metadata.save()
        
        # Save match with updated fields
        match.save()
        
        logger.info(f"Successfully enriched match {match.id} with additional data")
        return True
        
    except Exception as e:
        logger.error(f"Error enriching match {match.id}: {e}")
        return False

def enrich_teams_demo_mode() -> int:
    """
    Enrich team data in demo mode using actual team IDs from the database.
    
    Returns:
        Number of teams processed
    """
    logger.info("Running team enrichment in demo mode...")
    
    # Get a few valid Team.api_id values from the database
    team_ids = list(Team.objects.filter(api_id__isnull=False).values_list("api_id", flat=True)[:5])
    
    if not team_ids:
        logger.warning("No teams with API IDs found in database for demo mode")
        return 0
    
    logger.info(f"Using team IDs for demo: {team_ids}")
    
    processed_count = 0
    
    for team_id in team_ids:
        try:
            # Convert to int if it's a string
            team_id_int = int(team_id)
            
            # Fetch team injuries (will handle 404s gracefully)
            injuries = fetch_team_injuries(team_id_int)
            logger.info(f"Team {team_id_int}: Found {len(injuries)} injuries")
            
            # Fetch team stats (will handle 404s gracefully)
            stats = fetch_team_stats(team_id_int)
            if stats:
                logger.info(f"Team {team_id_int}: Found stats")
            
            # Fetch team players (will handle 404s gracefully)
            players = fetch_team_players(team_id_int)
            logger.info(f"Team {team_id_int}: Found {len(players)} players")
            
            processed_count += 1
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid team ID {team_id}: {e}")
            continue
    
    logger.info(f"✅ Teams processed: {processed_count}")
    return processed_count

def fetch_and_store_fixtures(days_range: int = 7, league_ids: List[int] = None) -> Tuple[int, int, int]:
    """
    Fetch and store fixtures for Romanian leagues.
    
    Args:
        days_range: Number of days to fetch fixtures for (before and after today)
        league_ids: Optional list of league IDs to filter by
        
    Returns:
        Tuple of (created_count, updated_count, failed_count)
    """
    created_count = 0
    updated_count = 0
    failed_count = 0
    
    # First, test basic API connectivity by fetching leagues
    leagues = fetch_leagues()
    
    if not leagues:
        logger.error("Could not fetch any leagues. API connection failed.")
        return created_count, updated_count, failed_count
    
    logger.info(f"Successfully fetched {len(leagues)} leagues!")
    
    # Fetch fixtures for Romanian leagues
    all_fixtures = []
    
    # If specific league IDs are provided, use them instead of the default Romanian leagues
    target_leagues = {}
    if league_ids:
        # Convert league IDs to dict format for fetch_fixtures_for_league
        for league_id in league_ids:
            target_leagues[f"League ID {league_id}"] = league_id
    else:
        target_leagues = ROMANIAN_LEAGUE_IDS
    
    for league_name, league_id in target_leagues.items():
        logger.info(f"Fetching fixtures for {league_name} (ID: {league_id})")
        fixtures = fetch_fixtures_for_league(league_id, days_range)
        all_fixtures.extend(fixtures)
    
    logger.info(f"Total fixtures found: {len(all_fixtures)}")
    
    # Process the fetched fixtures
    for fixture_data in all_fixtures:
        processed_data = process_fixture_data(fixture_data)
        
        if not processed_data:
            logger.error(f"Failed to process fixture: {fixture_data.get('id')}")
            failed_count += 1
            continue
        
        match_data = processed_data['match_data']
        metadata = processed_data['metadata']
        
        try:
            # Create or update the match
            match, created = Match.objects.update_or_create(
                api_ref=match_data['api_ref'],
                defaults=match_data
            )
            
            # Store metadata
            store_match_metadata(match, metadata)
            
            # Enrich match with additional data
            enrich_match_data(match)
            
            if created:
                logger.info(f"Created new match: {match}")
                created_count += 1
            else:
                logger.info(f"Updated existing match: {match}")
                updated_count += 1
                
        except Exception as e:
            logger.error(f"Error storing fixture: {e}")
            failed_count += 1
    
    logger.info(f"Fetch and store complete: {created_count} created, {updated_count} updated, {failed_count} failed")
    
    # Save skipped fixtures log if any
    global skipped_fixtures
    if skipped_fixtures:
        with open("skipped_fixtures_missing_teams.json", "w") as f:
            import json
            json.dump({
                "total_skipped": len(skipped_fixtures),
                "timestamp": timezone.now().isoformat(),
                "skipped_fixtures": skipped_fixtures
            }, f, indent=2)
        logger.warning(f"📄 {len(skipped_fixtures)} fixtures skipped - logged to skipped_fixtures_missing_teams.json")
        # Reset for next run
        skipped_fixtures = []
    
    return created_count, updated_count, failed_count 