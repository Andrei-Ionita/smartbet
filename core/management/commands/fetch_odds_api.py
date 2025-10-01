import os
from dotenv import load_dotenv
from pathlib import Path

# Keep other necessary imports below the .env loading logic
import requests 
import logging
import time 
import json # For pretty printing JSON if needed for debugging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, IntegrityError
from django.utils import timezone
from datetime import datetime, timedelta

from core.models import Match, OddsSnapshot

# Explicitly resolve .env from the project root directory
# fetch_odds_api.py is typically in: project_root/app_name/management/commands/script.py
# Path(__file__).resolve() is this script.
# .parent -> commands/
# .parent.parent -> management/
# .parent.parent.parent -> app_name/ (e.g., 'core')
# .parent.parent.parent.parent -> project_root/ (where manage.py and .env are)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent 
dotenv_path = BASE_DIR / ".env"

# Debug print for the path being checked
print(f">>> [fetch_odds_api.py] Looking for .env at: {dotenv_path}")

# load_dotenv will return True if it found and loaded a .env file, False otherwise.
loaded_dotenv_status = load_dotenv(dotenv_path=dotenv_path)
print(f">>> [fetch_odds_api.py] .env loaded: {loaded_dotenv_status}")

# Read the API key from environment variables AFTER attempting to load .env
API_SPORTS_KEY_FROM_ENV = os.getenv("API_FOOTBALL_KEY") 
print(f">>> [fetch_odds_api.py] API_FOOTBALL_KEY from env: {API_SPORTS_KEY_FROM_ENV if API_SPORTS_KEY_FROM_ENV else 'NOT FOUND'}")

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetches odds from API-FOOTBALL (api-sports.io) for stored matches, with enhanced debugging.'

    API_HOST = 'v3.football.api-sports.io'
    API_ENDPOINT_ODDS = f'https://{API_HOST}/odds'
    API_ENDPOINT_LEAGUES = f'https://{API_HOST}/leagues'
    TARGET_BOOKMAKER_NAME = "Bet365" 
    MATCH_WINNER_BET_NAME = "Match Winner"
    FALLBACK_SEASON = 2023  # Fallback if auto-detection fails
    LEAGUE_ID = 283  # Romanian Liga 1

    THROTTLE_SECONDS = 1  # Throttle API requests to 1 per second 
    MAX_RETRIES_RATE_LIMIT = 2
    RETRY_WAIT_SECONDS_RATE_LIMIT = 30

    def add_arguments(self, parser):
        # Optional argument to enable verbose logging of raw API responses
        parser.add_argument(
            '--log-raw-response',
            action='store_true',
            help='Log the full raw JSON response from the API for debugging.',
        )
        parser.add_argument(
            '--season',
            type=int,
            default=None,
            help='Override the automatically detected season',
        )
        parser.add_argument(
            '--auto-season',
            action='store_true',
            help='Automatically detect the season based on current date',
        )
        parser.add_argument(
            '--diagnostic',
            action='store_true',
            help='Show detailed diagnostic information about season detection and API calls',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key_error_occurred_session = False
        self.headers_logged_this_session = False # Flag to log headers only once
        self.season = None

    def get_available_seasons(self, headers, diagnostic=False):
        """
        Helper method to discover available seasons for the configured league ID
        and determine which season is active for today's date
        """
        if diagnostic:
            self.stdout.write(self.style.WARNING(f"\n🔍 Checking available seasons for League ID {self.LEAGUE_ID}..."))
        else:
            self.stdout.write(f"Checking available seasons for League ID {self.LEAGUE_ID}...")
        
        params = {
            'id': self.LEAGUE_ID
        }
        
        try:
            response = requests.get(
                self.API_ENDPOINT_LEAGUES,
                headers=headers,
                params=params,
                timeout=30
            )
            data = response.json()
            
            if response.status_code != 200:
                self.stderr.write(self.style.ERROR(f"API error: {data.get('message', 'Unknown error')}"))
                return [], None, None
            
            if not data.get('response'):
                self.stdout.write(self.style.WARNING(f"No league data found for ID {self.LEAGUE_ID}"))
                return [], None, None
            
            seasons = []
            league_data = data.get('response', [])[0] if data.get('response') else None
            
            if not league_data:
                return [], None, None
                
            # Extract league info
            league_name = league_data.get('league', {}).get('name', 'Unknown')
            country = league_data.get('country', {}).get('name', 'Unknown')
            
            if diagnostic:
                self.stdout.write(self.style.SUCCESS(f"📋 League info: {league_name} ({country})"))
            
            # Extract available seasons
            seasons_data = league_data.get('seasons', [])
            
            if not seasons_data:
                self.stdout.write(self.style.WARNING(f"No seasons data found for league {league_name}"))
                return [], None, None
            
            # Print seasons information
            if diagnostic:
                self.stdout.write(self.style.SUCCESS("Available seasons:"))
            
            current_season = None
            active_season_for_today = None
            today = datetime.today().date()
            
            for season in seasons_data:
                year = season.get('year')
                current = season.get('current', False)
                start_date_str = season.get('start')
                end_date_str = season.get('end')
                
                try:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                    
                    # Check if today's date falls within this season's range
                    is_active_today = start_date <= today <= end_date
                    
                    if is_active_today:
                        active_season_for_today = year
                        active_emoji = "✅"
                    else:
                        active_emoji = "  "
                        
                    if diagnostic:
                        status = "CURRENT" if current else "     "
                        today_status = "TODAY" if is_active_today else "     "
                        self.stdout.write(f"  [{status}] [{today_status}] {year}: {start_date_str} → {end_date_str}")
                except (ValueError, TypeError):
                    if diagnostic:
                        self.stdout.write(f"  Error parsing dates for season {year}: {start_date_str} → {end_date_str}")
                
                seasons.append(year)
                if current:
                    current_season = year
            
            # Detailed diagnostic logging
            if diagnostic:
                if current_season:
                    self.stdout.write(self.style.SUCCESS(f"\n🏆 API-marked current season: {current_season}"))
                
                if active_season_for_today:
                    self.stdout.write(self.style.SUCCESS(f"📅 Season active for today's date ({today}): {active_season_for_today}"))
                else:
                    self.stdout.write(self.style.WARNING(f"⚠️ No season contains today's date ({today})!"))
            
            return seasons, current_season, active_season_for_today
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error fetching league info: {str(e)}"))
            if diagnostic:
                import traceback
                self.stderr.write(self.style.ERROR(f"Traceback: {traceback.format_exc()}"))
            return [], None, None

    def handle(self, *args, **options):
        log_raw_response = options['log_raw_response'] # Get value of the optional argument
        explicit_season = options['season']
        auto_season = options['auto_season']
        diagnostic = options['diagnostic']

        # API_SPORTS_KEY_FROM_ENV is loaded at the module level
        if not API_SPORTS_KEY_FROM_ENV:
            self.stderr.write(self.style.ERROR(
                f"API_FOOTBALL_KEY not found in environment variables or in .env file (expected at {dotenv_path}).\n"
                "Please ensure your .env file is in the project root (same level as manage.py) and contains: API_FOOTBALL_KEY=your_actual_key"
            ))
            self.api_key_error_occurred_session = True
            self.stdout.write(self.style.ERROR("\nNo odds data was ingested due to missing API key configuration."))
            return

        headers = {
            "x-apisports-key": API_SPORTS_KEY_FROM_ENV 
        }

        # Determine the appropriate season if auto-season is enabled or explicit season is provided
        if auto_season or explicit_season:
            if diagnostic:
                self.stdout.write(self.style.WARNING("\n📊 SEASON SELECTION PROCESS:"))
            
            if explicit_season:
                self.season = explicit_season
                if diagnostic:
                    self.stdout.write(f"  1. Using explicitly provided season: {self.season} (from --season parameter)")
            elif auto_season:
                # Get available seasons for auto-detection
                seasons, api_current_season, active_season_for_today = self.get_available_seasons(headers, diagnostic=diagnostic)
                
                # Determine which season to use based on priorities
                if active_season_for_today:
                    self.season = active_season_for_today
                    if diagnostic:
                        self.stdout.write(f"  1. Using season matching today's date: {self.season}")
                elif api_current_season:
                    self.season = api_current_season
                    if diagnostic:
                        self.stdout.write(f"  1. Using API-marked current season: {self.season}")
                else:
                    self.season = self.FALLBACK_SEASON
                    if diagnostic:
                        self.stdout.write(f"  1. Using fallback season: {self.season} (no better season detected)")
            
            # Log the final selected season
            if self.season:
                self.stdout.write(self.style.SUCCESS(f"🏆 Selected season: {self.season}"))
                if diagnostic:
                    if explicit_season:
                        self.stdout.write("   ↳ Reason: Explicitly provided via --season parameter")
                    elif self.season == active_season_for_today:
                        self.stdout.write(f"   ↳ Reason: This season's date range covers today ({datetime.today().date()})")
                    elif self.season == api_current_season:
                        self.stdout.write("   ↳ Reason: API reports this as the current season")
                    else:
                        self.stdout.write("   ↳ Reason: Fallback value, no better season detected")

        matches_to_fetch_for = Match.objects.filter(api_ref__isnull=False).exclude(api_ref__exact='')
        
        total_matches_to_process = matches_to_fetch_for.count()
        if total_matches_to_process == 0:
            self.stdout.write(self.style.WARNING("No matches with valid api_ref found to fetch odds for."))
            return

        self.stdout.write(f"Found {total_matches_to_process} matches with api_ref. Starting to fetch and process odds using API key from environment.")

        self.stdout.write(f"  Using API Host: {self.API_HOST}")
        if not self.headers_logged_this_session:
            # Censor the key slightly for logging if it's long, or log a placeholder
            # For debugging, it's often fine to see the start/end or length.
            # For production logs, avoid logging full keys.
            key_display = (API_SPORTS_KEY_FROM_ENV[:4] + "..." + API_SPORTS_KEY_FROM_ENV[-4:]) if API_SPORTS_KEY_FROM_ENV and len(API_SPORTS_KEY_FROM_ENV) > 8 else "KeyPresent (length < 8 or empty)"
            self.stdout.write(self.style.SUCCESS(f"  Using Headers for API calls (key partially masked): {{'x-apisports-key': '{key_display}'}}"))
            self.headers_logged_this_session = True

        successfully_inserted_count = 0
        api_calls_made_count = 0
        matches_skipped_existing_odds = 0
        matches_processed_with_target_odds_found = 0 # Count matches where we FOUND target odds
        total_rate_limit_retry_attempts = 0

        for match_idx, match_obj in enumerate(matches_to_fetch_for):
            if self.api_key_error_occurred_session: 
                self.stdout.write(self.style.WARNING("Halting further processing due to previous API key error."))
                break

            self.stdout.write(f"\n[{match_idx + 1}/{total_matches_to_process}] Processing Match ID: {match_obj.id} (API Ref: {match_obj.api_ref}) - {match_obj.home_team} vs {match_obj.away_team}")

            if OddsSnapshot.objects.filter(match=match_obj, bookmaker=self.TARGET_BOOKMAKER_NAME).exists():
                self.stdout.write(self.style.NOTICE(f"  Skipping Match ID {match_obj.id}: Odds from '{self.TARGET_BOOKMAKER_NAME}' already exist."))
                matches_skipped_existing_odds += 1
                continue

            current_match_retries_rate_limit = 0
            
            while current_match_retries_rate_limit <= self.MAX_RETRIES_RATE_LIMIT:
                if current_match_retries_rate_limit > 0:
                    self.stdout.write(self.style.WARNING(f"    Retrying API call for Match ID {match_obj.id} (Rate Limit Retry Attempt {current_match_retries_rate_limit}/{self.MAX_RETRIES_RATE_LIMIT}). Waiting {self.RETRY_WAIT_SECONDS_RATE_LIMIT}s..."))
                    time.sleep(self.RETRY_WAIT_SECONDS_RATE_LIMIT)
                
                if api_calls_made_count > 0: 
                    self.stdout.write(f"  Throttling: Waiting {self.THROTTLE_SECONDS}s before API call...")
                    time.sleep(self.THROTTLE_SECONDS)  # Always throttle API requests by 1 second
                
                self.stdout.write(f"  Attempting API call for Match ID {match_obj.id} (Overall Attempt for match: {current_match_retries_rate_limit + 1})")
                api_calls_made_count += 1
                params = {'fixture': match_obj.api_ref}
                
                # Add season parameter if available
                if self.season:
                    params['season'] = self.season
                    if diagnostic:
                        self.stdout.write(f"    Adding season={self.season} to API request params")
                
                odds_home, odds_draw, odds_away = None, None, None
                bet365_match_winner_found_this_attempt = False

                try:
                    response = requests.get(self.API_ENDPOINT_ODDS, headers=headers, params=params, timeout=30)
                    self.stdout.write(f"    API Call to: {response.url}")
                    self.stdout.write(f"    API Response Status: {response.status_code}")
                    
                    try:
                        response_data = response.json()
                        # 1. Log Raw Response Content (conditionally)
                        if log_raw_response:
                            self.stdout.write(f"    Raw API Response JSON:\n{json.dumps(response_data, indent=2)}")
                            # Alternatively, use logger.debug(f"Raw API Response JSON for {match_obj.api_ref}: {response_data}")
                    except json.JSONDecodeError:
                         self.stderr.write(self.style.ERROR(f"    Failed to decode JSON response for fixture {match_obj.api_ref}. Status: {response.status_code}, Content: {response.text[:500]}..."))
                         break # Cannot proceed without JSON

                    # NEW: Log the response data structure
                    self.stdout.write(f"    DEBUG: Response top-level keys: {list(response_data.keys())}")
                    
                    # NEW: Log number of entries in response field
                    response_array = response_data.get('response', [])
                    response_count = len(response_array)
                    self.stdout.write(f"    DEBUG: Response array contains {response_count} entries")
                    
                    # NEW: Log if response is empty
                    if response_count == 0:
                        self.stdout.write(self.style.WARNING(f"    DEBUG: Response array is empty for fixture {match_obj.api_ref}"))
                        if 'errors' in response_data:
                            self.stdout.write(f"    DEBUG: Response errors: {response_data.get('errors')}")
                        if 'results' in response_data:
                            self.stdout.write(f"    DEBUG: Response results count: {response_data.get('results')}")
                        if 'paging' in response_data:
                            self.stdout.write(f"    DEBUG: Response paging: {response_data.get('paging')}")

                    api_errors = response_data.get('errors')
                    token_error_message = None 
                    if isinstance(api_errors, dict) and api_errors.get('token'): 
                        token_error_message = api_errors.get('token')
                    elif isinstance(api_errors, (dict, list)) and ("key" in str(api_errors).lower() or "authentication" in str(api_errors).lower()): 
                        token_error_message = str(api_errors)

                    if token_error_message:
                        self.stderr.write(self.style.ERROR(f"API Key / Authentication Error: {token_error_message}"))
                        self.stderr.write(self.style.ERROR(f"  (Occurred on API call for fixture: {match_obj.api_ref})"))
                        self.stderr.write(self.style.ERROR(f"  Please ensure API_FOOTBALL_KEY in your .env file (expected at {dotenv_path}) is correct, active, and has access."))
                        self.api_key_error_occurred_session = True
                        self.stdout.write(self.style.ERROR("Command terminating due to API authentication error."))
                        return 

                    if response.status_code in [401, 403]: 
                        self.stderr.write(self.style.ERROR(f"HTTP {response.status_code} Authentication Error for fixture {match_obj.api_ref}: {response_data.get('message', response.text)}"))
                        self.stderr.write(self.style.ERROR(f"  Please check your API_FOOTBALL_KEY (expected in .env at {dotenv_path}) and subscription."))
                        self.api_key_error_occurred_session = True
                        self.stdout.write(self.style.ERROR("Command terminating due to HTTP Authentication error."))
                        return

                    if response.status_code == 429: 
                        self.stderr.write(self.style.WARNING(f"    HTTP 429 Rate limit detected for Match ID {match_obj.id}."))
                        current_match_retries_rate_limit += 1
                        total_rate_limit_retry_attempts += 1
                        if current_match_retries_rate_limit <= self.MAX_RETRIES_RATE_LIMIT:
                            continue 
                        else:
                            self.stderr.write(self.style.ERROR(f"    Max rate limit retries ({self.MAX_RETRIES_RATE_LIMIT}) reached for Match ID {match_obj.id}. Skipping this match."))
                            break 

                    response.raise_for_status()

                    api_response_list = response_data.get('response')
                    if not api_response_list or not isinstance(api_response_list, list):
                        self.stdout.write(self.style.WARNING(f"    API JSON contained no 'response' list or it was not a list for fixture {match_obj.api_ref}. Skipping odds processing."))
                        if response_data.get('results', 0) == 0:
                             self.stdout.write(self.style.NOTICE(f"    API indicated 0 results for this fixture."))
                        break 

                    if not api_response_list:
                         self.stdout.write(self.style.WARNING(f"    API 'response' list is empty for fixture {match_obj.api_ref}. No odds data available?"))
                         break 

                    fixture_odds_container = api_response_list[0] 
                    # NEW: Log keys in the response item
                    self.stdout.write(f"    DEBUG: First response item contains keys: {list(fixture_odds_container.keys())}")
                    
                    bookmakers_data = fixture_odds_container.get('bookmakers', [])
                    
                    # NEW: Log bookmakers count and names
                    self.stdout.write(f"    DEBUG: Found {len(bookmakers_data)} bookmakers in response")
                    if bookmakers_data:
                        bookmaker_names = [bk.get('name', 'unnamed') for bk in bookmakers_data]
                        self.stdout.write(f"    DEBUG: Bookmaker names in response: {bookmaker_names}")
                        # Check if our target bookmaker is present
                        if self.TARGET_BOOKMAKER_NAME not in bookmaker_names:
                            self.stdout.write(self.style.WARNING(f"    DEBUG: Target bookmaker '{self.TARGET_BOOKMAKER_NAME}' not found in response"))

                    if not bookmakers_data:
                        self.stdout.write(self.style.WARNING(f"    No 'bookmakers' data in API response for fixture {match_obj.api_ref}."))
                        break 

                    # Track if we find the target bookmaker
                    target_bookmaker_found = False
                    
                    for bookmaker_entry in bookmakers_data:
                        if bookmaker_entry.get('name') == self.TARGET_BOOKMAKER_NAME:
                            self.stdout.write(f"    Found bookmaker: {self.TARGET_BOOKMAKER_NAME}")
                            target_bookmaker_found = True
                            bets = bookmaker_entry.get('bets', [])
                            
                            # NEW: Log available bet types for this bookmaker
                            bet_types = [bet.get('name', 'unnamed') for bet in bets]
                            self.stdout.write(f"    DEBUG: Available bet types for {self.TARGET_BOOKMAKER_NAME}: {bet_types}")
                            
                            # Check if our target market is present
                            if self.MATCH_WINNER_BET_NAME not in bet_types:
                                self.stdout.write(self.style.WARNING(f"    DEBUG: Target market '{self.MATCH_WINNER_BET_NAME}' not found for bookmaker '{self.TARGET_BOOKMAKER_NAME}'"))
                            
                            for bet_type in bets:
                                if bet_type.get('name') == self.MATCH_WINNER_BET_NAME:
                                    self.stdout.write(self.style.SUCCESS(f"      Found '{self.MATCH_WINNER_BET_NAME}' market."))
                                    bet365_match_winner_found_this_attempt = True
                                    matches_processed_with_target_odds_found += 1
                                    odds_values = bet_type.get('values')
                                    
                                    # NEW: Log odds values structure
                                    self.stdout.write(f"      DEBUG: Odds values data structure: {odds_values}")
                                    
                                    # Track which outcome types were found
                                    found_outcomes = []
                                    
                                    for ov in odds_values:
                                        value_name = ov.get('value')
                                        found_outcomes.append(value_name)
                                        odd_val_str = ov.get('odd')
                                        try:
                                            odd_val = float(odd_val_str)
                                            if value_name == "Home": 
                                                odds_home = odd_val
                                                self.stdout.write(f"      DEBUG: Parsed Home odds: {odds_home}")
                                            elif value_name == "Draw": 
                                                odds_draw = odd_val
                                                self.stdout.write(f"      DEBUG: Parsed Draw odds: {odds_draw}")
                                            elif value_name == "Away": 
                                                odds_away = odd_val
                                                self.stdout.write(f"      DEBUG: Parsed Away odds: {odds_away}")
                                            else:
                                                self.stdout.write(f"      DEBUG: Unknown outcome type: '{value_name}' with odd value: {odd_val}")
                                        except (ValueError, TypeError):
                                            self.stderr.write(self.style.ERROR(f"      Could not parse odd value '{odd_val_str}' for '{value_name}'."))
                                    
                                    # NEW: Check if all required outcomes were found
                                    required_outcomes = ["Home", "Draw", "Away"]
                                    missing_outcomes = [outcome for outcome in required_outcomes if outcome not in found_outcomes]
                                    if missing_outcomes:
                                        self.stdout.write(self.style.WARNING(f"      DEBUG: Missing outcomes: {missing_outcomes}"))
                                        
                                    break 
                            if bet365_match_winner_found_this_attempt: break 
                    
                    # NEW: Log if bookmaker was not found
                    if not target_bookmaker_found:
                        self.stdout.write(self.style.WARNING(f"    DEBUG: Target bookmaker '{self.TARGET_BOOKMAKER_NAME}' not found in response"))
                    
                    if not bet365_match_winner_found_this_attempt:
                        self.stdout.write(self.style.NOTICE(f"    Odds for '{self.TARGET_BOOKMAKER_NAME}' / '{self.MATCH_WINNER_BET_NAME}' not found for Match ID {match_obj.id} in this API response."))
                        break 

                    # NEW: Log the final parsed values just before insertion
                    self.stdout.write(f"    DEBUG: Final parsed odds values - Home: {odds_home}, Draw: {odds_draw}, Away: {odds_away}")
                    
                    # NEW: Log warning if any values are missing
                    missing_values = []
                    if odds_home is None: missing_values.append("Home")
                    if odds_draw is None: missing_values.append("Draw")
                    if odds_away is None: missing_values.append("Away")
                    
                    if missing_values:
                        self.stdout.write(self.style.WARNING(f"    DEBUG: Missing odds values for: {missing_values}"))

                    if odds_home is not None and odds_draw is not None and odds_away is not None:
                        self.stdout.write(f"    Extracted Odds: Home={odds_home}, Draw={odds_draw}, Away={odds_away}")
                        # NEW: Log attempt to create OddsSnapshot
                        self.stdout.write(f"    DEBUG: Attempting to create OddsSnapshot in database")
                        try:
                            odds_snapshot = OddsSnapshot.objects.create(
                                match=match_obj, bookmaker=self.TARGET_BOOKMAKER_NAME,
                                odds_home=odds_home, odds_draw=odds_draw, odds_away=odds_away,
                                fetched_at=timezone.now()
                            )
                            successfully_inserted_count += 1
                            self.stdout.write(self.style.SUCCESS(f"      Successfully CREATED new OddsSnapshot for Match ID {match_obj.id}. Record ID: {odds_snapshot.id}"))
                        except Exception as creation_error:
                            # NEW: Log any error during insertion
                            self.stdout.write(self.style.ERROR(f"      DEBUG: Error creating OddsSnapshot: {str(creation_error)}"))
                    else:
                        self.stdout.write(self.style.WARNING(f"    Could not extract all three odds (H/D/A) for {self.TARGET_BOOKMAKER_NAME} for Match ID {match_obj.id} from found market."))
                    
                    break 

                except requests.exceptions.HTTPError as e: 
                    self.stderr.write(self.style.ERROR(f"    HTTP API error for fixture {match_obj.api_ref} (Attempt {current_match_retries_rate_limit + 1}): {e} - Response: {e.response.text if e.response else 'No response body'}"))
                    logger.error(f"HTTP API error for Match ID {match_obj.id}, fixture {match_obj.api_ref}, attempt {current_match_retries_rate_limit + 1}: {e}", exc_info=False)
                    break 
                except requests.exceptions.RequestException as e:
                    self.stderr.write(self.style.ERROR(f"    API Request (Connection/Timeout) failed for fixture {match_obj.api_ref} (Attempt {current_match_retries_rate_limit + 1}): {e}"))
                    logger.error(f"API Request failed for Match ID {match_obj.id}, fixture {match_obj.api_ref}, attempt {current_match_retries_rate_limit + 1}: {e}", exc_info=True)
                    current_match_retries_rate_limit +=1
                    if current_match_retries_rate_limit <= self.MAX_RETRIES_RATE_LIMIT:
                        continue 
                    else:
                        self.stderr.write(self.style.ERROR(f"    Max retries ({self.MAX_RETRIES_RATE_LIMIT}) reached for Match ID {match_obj.id} due to connection error. Skipping this match."))
                        break 
                except IntegrityError: 
                    self.stderr.write(self.style.WARNING(f"    OddsSnapshot for Match ID {match_obj.id} and bookmaker '{self.TARGET_BOOKMAKER_NAME}' already exists (IntegrityError). This should ideally be caught by the initial skip logic."))
                    matches_skipped_existing_odds +=1 
                    break 
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"    An unexpected error occurred for Match ID {match_obj.id} (Attempt {current_match_retries_rate_limit + 1}): {e}"))
                    logger.error(f"Unexpected error processing Match ID {match_obj.id}, attempt {current_match_retries_rate_limit + 1}: {e}", exc_info=True)
                    break 
            # End of retry while loop
        
        # Final Summary
        self.stdout.write(f"\n--- Odds Ingestion Final Summary ---")
        self.stdout.write(f"Total matches with api_ref considered: {total_matches_to_process}")
        self.stdout.write(f"Matches skipped (odds already existed): {matches_skipped_existing_odds}")
        self.stdout.write(f"Total API call attempts made: {api_calls_made_count}")
        self.stdout.write(f"Total retry attempts due to rate limits: {total_rate_limit_retry_attempts}")
        self.stdout.write(f"Matches where '{self.TARGET_BOOKMAKER_NAME}/{self.MATCH_WINNER_BET_NAME}' odds were found and processed: {matches_processed_with_target_odds_found}")
        self.stdout.write(self.style.SUCCESS(f"Successfully inserted new OddsSnapshots: {successfully_inserted_count}"))
        
        if self.season:
            self.stdout.write(f"Season used for API requests: {self.season}")
        
        if self.api_key_error_occurred_session and successfully_inserted_count == 0:
            self.stdout.write(self.style.ERROR(f"\nNo odds data was ingested due to an API authentication/token error. Please check your API_FOOTBALL_KEY in the .env file (expected at {dotenv_path})."))
        elif not self.api_key_error_occurred_session and total_matches_to_process > 0 and successfully_inserted_count == 0 and (total_matches_to_process - matches_skipped_existing_odds > 0) :
             self.stdout.write(self.style.WARNING("\nNo new odds data was ingested. This might be due to API responses not containing the target odds for the remaining matches, or other non-critical errors.")) 