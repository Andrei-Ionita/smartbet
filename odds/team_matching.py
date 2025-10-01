"""
Team name matching utilities for linking OddsAPI data to SportMonks fixtures.
Handles fuzzy matching, aliases, and normalization to ensure odds are properly matched.
"""

import re
import json
import logging
from typing import Dict, List, Optional, Tuple
from difflib import get_close_matches, SequenceMatcher
from datetime import datetime, timedelta
from django.utils import timezone

from core.models import Match

logger = logging.getLogger(__name__)

# Team aliases for common variations
TEAM_ALIASES = {
    # Premier League
    "brighton": "brighton and hove albion",
    "brighton & hove albion": "brighton and hove albion",
    "liverpool": "liverpool fc",
    "manchester united": "man utd",
    "man utd": "manchester united", 
    "manchester city": "man city",
    "man city": "manchester city",
    "tottenham": "tottenham hotspur",
    "spurs": "tottenham hotspur",
    "chelsea": "chelsea fc",
    "arsenal": "arsenal fc",
    "west ham": "west ham united",
    "newcastle": "newcastle united",
    "leicester": "leicester city",
    "crystal palace": "crystal palace fc",
    "wolves": "wolverhampton wanderers",
    "wolverhampton": "wolverhampton wanderers",
    "sheffield united": "sheffield utd",
    "sheffield utd": "sheffield united",
    "nottingham forest": "nottm forest",
    "nottm forest": "nottingham forest",
    
    # La Liga
    "barcelona": "fc barcelona",
    "fc barcelona": "barcelona",
    "real madrid": "real madrid cf",
    "atletico madrid": "atletico de madrid",
    "athletic bilbao": "athletic club",
    "athletic club": "athletic bilbao",
    "real sociedad": "real sociedad de futbol",
    "valencia": "valencia cf",
    "sevilla": "sevilla fc",
    "villarreal": "villarreal cf",
    "real betis": "real betis balompie",
    "celta vigo": "rc celta",
    "rc celta": "celta vigo",
    
    # Bundesliga
    "bayern munich": "fc bayern munich",
    "fc bayern munich": "bayern munich",
    "borussia dortmund": "bvb dortmund",
    "bvb dortmund": "borussia dortmund",
    "bayer leverkusen": "bayer 04 leverkusen",
    "rb leipzig": "rasenballsport leipzig",
    "eintracht frankfurt": "frankfurt",
    "frankfurt": "eintracht frankfurt",
    "borussia monchengladbach": "borussia mgladbach",
    "borussia mgladbach": "borussia monchengladbach",
    
    # Serie A
    "juventus": "juventus fc",
    "ac milan": "milan",
    "milan": "ac milan",
    "inter": "inter milan",
    "inter milan": "internazionale",
    "internazionale": "inter milan",
    "napoli": "ssc napoli",
    "ssc napoli": "napoli",
    "roma": "as roma",
    "as roma": "roma",
    "lazio": "ss lazio",
    "ss lazio": "lazio",
    "atalanta": "atalanta bc",
    "fiorentina": "acf fiorentina",
    
    # Ligue 1
    "psg": "paris saint germain",
    "paris saint germain": "psg",
    "paris sg": "paris saint germain",
    "marseille": "olympique marseille",
    "olympique marseille": "marseille",
    "lyon": "olympique lyonnais",
    "olympique lyonnais": "lyon",
    "saint etienne": "as saint etienne",
    "as saint etienne": "saint etienne",
    
    # Romanian Liga 1
    "fcsb": "steaua bucuresti",
    "steaua bucuresti": "fcsb",
    "steaua": "fcsb",
    "cfr cluj": "cfr 1907 cluj",
    "rapid bucuresti": "fc rapid bucuresti",
    "fc rapid bucuresti": "rapid bucuresti",
    "dinamo bucuresti": "fc dinamo bucuresti",
    "fc dinamo bucuresti": "dinamo bucuresti",
    "universitatea craiova": "cs universitatea craiova",
    "cs universitatea craiova": "universitatea craiova",
    "sepsi": "sepsi osk",
    "sepsi osk": "sepsi",
    "uta arad": "fc uta arad",
    "fc uta arad": "uta arad",
    "petrolul ploiesti": "fc petrolul ploiesti",
    "fc petrolul ploiesti": "petrolul ploiesti",
}

def normalize_name(name: str) -> str:
    """
    Normalize team name for better matching.
    
    Args:
        name: Raw team name
        
    Returns:
        Normalized team name for comparison
    """
    if not name:
        return ""
    
    # Convert to lowercase
    name = name.lower().strip()
    
    # Apply aliases first
    if name in TEAM_ALIASES:
        name = TEAM_ALIASES[name]
    
    # Remove common suffixes and prefixes
    name = re.sub(r'\s+fc$', '', name)  # remove trailing 'fc'
    name = re.sub(r'^fc\s+', '', name)  # remove leading 'fc'
    name = re.sub(r'\s+cf$', '', name)  # remove trailing 'cf'
    name = re.sub(r'^cf\s+', '', name)  # remove leading 'cf'
    name = re.sub(r'\s+sc$', '', name)  # remove trailing 'sc'
    name = re.sub(r'^sc\s+', '', name)  # remove leading 'sc'
    name = re.sub(r'\s+bc$', '', name)  # remove trailing 'bc'
    name = re.sub(r'^bc\s+', '', name)  # remove leading 'bc'
    name = re.sub(r'\s+united$', '', name)  # remove trailing 'united'
    name = re.sub(r'\s+city$', '', name)  # remove trailing 'city'
    
    # Remove punctuation and normalize spaces
    name = re.sub(r'[^\w\s]', '', name)  # remove punctuation
    name = re.sub(r'\s+', ' ', name)     # normalize multiple spaces
    name = name.strip()
    
    return name

def get_name_variations(name: str) -> List[str]:
    """
    Get all possible variations of a team name for matching.
    
    Args:
        name: Original team name
        
    Returns:
        List of name variations to try for matching
    """
    variations = [name]
    
    # Add normalized version
    normalized = normalize_name(name)
    if normalized not in variations:
        variations.append(normalized)
    
    # Add alias if available
    lower_name = name.lower().strip()
    if lower_name in TEAM_ALIASES:
        alias = TEAM_ALIASES[lower_name]
        if alias not in variations:
            variations.append(alias)
            # Also add normalized alias
            normalized_alias = normalize_name(alias)
            if normalized_alias not in variations:
                variations.append(normalized_alias)
    
    # Remove empty strings
    variations = [v for v in variations if v]
    
    return variations

def fuzzy_match(a: str, b: str, cutoff: float = 0.85) -> bool:
    """
    Enhanced fuzzy matching with cutoff ≥ 0.85 as specified.
    
    Args:
        a: First string to compare
        b: Second string to compare  
        cutoff: Minimum similarity ratio (default 0.85)
        
    Returns:
        True if strings match with similarity >= cutoff
    """
    if not a or not b:
        return False
        
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio() >= cutoff

def match_teams(oddsapi_home: str, oddsapi_away: str, fixtures: List[Match]) -> Optional[Match]:
    """
    Find matching fixture using fuzzy matching with team name normalization.
    
    Args:
        oddsapi_home: Home team name from OddsAPI
        oddsapi_away: Away team name from OddsAPI
        fixtures: List of potential matching fixtures
        
    Returns:
        Matching fixture or None if no good match found
    """
    # Get all variations for OddsAPI team names
    home_variations = get_name_variations(oddsapi_home)
    away_variations = get_name_variations(oddsapi_away)
    
    logger.debug(f"Matching teams: {oddsapi_home} vs {oddsapi_away}")
    logger.debug(f"Home variations: {home_variations}")
    logger.debug(f"Away variations: {away_variations}")
    
    for fixture in fixtures:
        # Get all variations for fixture team names (both EN and RO)
        fixture_home_variations = []
        fixture_away_variations = []
        
        # English names
        if fixture.home_team.name_en:
            fixture_home_variations.extend(get_name_variations(fixture.home_team.name_en))
        if fixture.away_team.name_en:
            fixture_away_variations.extend(get_name_variations(fixture.away_team.name_en))
            
        # Romanian names
        if fixture.home_team.name_ro:
            fixture_home_variations.extend(get_name_variations(fixture.home_team.name_ro))
        if fixture.away_team.name_ro:
            fixture_away_variations.extend(get_name_variations(fixture.away_team.name_ro))
        
        # Remove duplicates
        fixture_home_variations = list(set(fixture_home_variations))
        fixture_away_variations = list(set(fixture_away_variations))
        
        # Try exact matches first
        for home_var in home_variations:
            for away_var in away_variations:
                if (home_var in fixture_home_variations and 
                    away_var in fixture_away_variations):
                    logger.info(f"✅ Exact match found: {fixture} ('{home_var}' vs '{away_var}')")
                    return fixture
        
        # Try fuzzy matching with high confidence (0.8+)
        for home_var in home_variations:
            home_matches = get_close_matches(home_var, fixture_home_variations, 
                                           n=1, cutoff=0.8)
            if home_matches:
                for away_var in away_variations:
                    away_matches = get_close_matches(away_var, fixture_away_variations, 
                                                   n=1, cutoff=0.8)
                    if away_matches:
                        logger.info(f"✅ Fuzzy match found: {fixture} "
                                  f"('{home_var}' -> '{home_matches[0]}', "
                                  f"'{away_var}' -> '{away_matches[0]}')")
                        return fixture
    
    logger.warning(f"❌ No match found for: {oddsapi_home} vs {oddsapi_away}")
    return None

def find_matching_match_enhanced(api_match: Dict) -> Optional[Match]:
    """
    Enhanced version of find_matching_match with fuzzy team name matching.
    
    Args:
        api_match: Match data from OddsAPI
        
    Returns:
        Matching Match object or None if not found
    """
    try:
        # Try to find by API reference first (fastest)
        if api_match.get('id'):
            match = Match.objects.filter(api_ref=api_match['id']).first()
            if match:
                logger.info(f"✅ Found match by API ref: {match}")
                return match
        
        # Extract team names and kickoff time
        oddsapi_home = api_match['home_team']
        oddsapi_away = api_match['away_team']
        commence_time = api_match['commence_time']
        
        # Parse kickoff time
        if isinstance(commence_time, str):
            kickoff = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
            if kickoff.tzinfo is None:
                kickoff = timezone.make_aware(kickoff)
        else:
            kickoff = commence_time
            if kickoff.tzinfo is None:
                kickoff = timezone.make_aware(kickoff)
        
        # Look for matches within a 2-hour window
        window_start = kickoff - timedelta(hours=1)
        window_end = kickoff + timedelta(hours=1)
        
        # Get all matches within the time window
        time_window_matches = list(Match.objects.filter(
            kickoff__range=(window_start, window_end)
        ).select_related('home_team', 'away_team', 'league'))
        
        logger.debug(f"Found {len(time_window_matches)} matches in time window "
                    f"for {oddsapi_home} vs {oddsapi_away}")
        
        # Use enhanced fuzzy matching
        matched_fixture = match_teams(oddsapi_home, oddsapi_away, time_window_matches)
        
        if matched_fixture:
            logger.info(f"✅ Enhanced matching found: {matched_fixture}")
            return matched_fixture
        
        logger.warning(f"❌ No matching fixture found for: {oddsapi_home} vs {oddsapi_away} "
                      f"at {kickoff} (checked {len(time_window_matches)} fixtures)")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error in enhanced match finding: {e}")
        return None

def log_unmatched_odds(unmatched_events: List[Dict], filename: str = "unmatched_odds.json"):
    """
    Log unmatched odds events to a file for debugging.
    
    Args:
        unmatched_events: List of unmatched OddsAPI events
        filename: Output filename for unmatched events
    """
    if not unmatched_events:
        logger.info("✅ All odds events matched successfully!")
        return
    
    # Add timestamp to the data
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "total_unmatched": len(unmatched_events),
        "unmatched_events": unmatched_events
    }
    
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.warning(f"❌ {len(unmatched_events)} unmatched odds events logged to {filename}")
        
        # Log summary of unmatched teams for quick debugging
        teams_summary = set()
        for event in unmatched_events:
            teams_summary.add(f"{event['home_team']} vs {event['away_team']}")
        
        logger.warning("❌ Unmatched teams summary:")
        for teams in sorted(teams_summary):
            logger.warning(f"   - {teams}")
            
    except Exception as e:
        logger.error(f"❌ Failed to log unmatched odds: {e}")

def validate_team_matching() -> Dict[str, int]:
    """
    Validate team matching by testing against existing fixtures.
    Returns statistics about matching performance.
    
    Returns:
        Dictionary with matching statistics
    """
    from django.utils import timezone
    from datetime import timedelta
    
    # Get recent fixtures for testing
    recent_matches = Match.objects.filter(
        kickoff__gte=timezone.now() - timedelta(days=7)
    ).select_related('home_team', 'away_team')[:50]
    
    stats = {
        "total_tested": len(recent_matches),
        "exact_matches": 0,
        "fuzzy_matches": 0,
        "no_matches": 0
    }
    
    for match in recent_matches:
        # Simulate OddsAPI data format
        api_match = {
            'home_team': match.home_team.name_en,
            'away_team': match.away_team.name_en,
            'commence_time': match.kickoff.isoformat()
        }
        
        # Test matching
        found_match = find_matching_match_enhanced(api_match)
        
        if found_match and found_match.id == match.id:
            stats["exact_matches"] += 1
        elif found_match:
            stats["fuzzy_matches"] += 1
        else:
            stats["no_matches"] += 1
    
    logger.info(f"🧪 Team matching validation: {stats}")
    return stats 