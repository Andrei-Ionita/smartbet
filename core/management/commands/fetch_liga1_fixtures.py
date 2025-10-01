import os
import time
import requests
import json
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from dotenv import load_dotenv
from pathlib import Path
import sys

from core.models import Match

# ⚠️ IMPORTANT: FREE API PLAN RESTRICTION
# The free plan for API-Football only allows accessing fixtures for a LIMITED DATE RANGE
# Typically this is TODAY and the NEXT 2 DAYS only (e.g., if today is 2025-05-11, 
# the allowed range is 2025-05-11 to 2025-05-13).
# Requests outside this range will return an error like:
# {'plan': 'Free plans do not have access to this date, try from 2025-05-11 to 2025-05-13'}

# Set up environment for API key
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)
API_KEY = os.getenv('API_FOOTBALL_KEY')

class Command(BaseCommand):
    help = 'Fetches fixtures for Romania Liga 1 (league ID 283) for today (free API plan limitation)'

    API_HOST = 'v3.football.api-sports.io'
    API_ENDPOINT_FIXTURES = f'https://{API_HOST}/fixtures'
    API_ENDPOINT_LEAGUES = f'https://{API_HOST}/leagues'
    LEAGUE_ID = 283  # Romanian Liga 1
    SEASON = None  # Will be auto-detected based on current date if not explicitly provided
    FALLBACK_SEASON = 2023  # Fallback if auto-detection fails
    LEAGUE_NAME = "Superliga"  # Hardcoded league name
    MAX_DAYS_AHEAD = 2  # Free API plan restriction - only today + 0 to +2 days allowed
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=0,
            help=f'Number of days ahead to fetch (default: 0 = today only)'
        )
        parser.add_argument(
            '--force-update',
            action='store_true',
            help='Force update of all fixtures even if they already exist'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=True,  # Changed to default True for diagnostic purposes
            help='Preview changes without writing to database (default: True)'
        )
        parser.add_argument(
            '--season',
            type=int,
            default=None,
            help='Override the automatically detected season'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed API response data'
        )
        parser.add_argument(
            '--check-seasons',
            action='store_true',
            help='Check available seasons for this league before fetching fixtures'
        )
        parser.add_argument(
            '--auto-season',
            action='store_true',
            help='Automatically try to find the current season if no fixtures are found'
        )
        parser.add_argument(
            '--no-dry-run',
            action='store_true',
            help='Actually write to database (disables dry-run mode)'
        )
        parser.add_argument(
            '--diagnostic',
            action='store_true',
            help='Show detailed diagnostic information about season detection and API calls'
        )

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

    def try_with_season(self, season, headers, date_range, options):
        """Try fetching fixtures with a specific season value"""
        previous_season = self.SEASON
        self.SEASON = season
        
        self.stdout.write(self.style.WARNING(f"\n🔄 Trying with season {self.SEASON}..."))
        
        fixtures = self.fetch_fixtures_for_date_range(date_range, headers, options)
        
        if fixtures:
            self.stdout.write(self.style.SUCCESS(f"✅ Successfully found fixtures with season {self.SEASON}!"))
            return fixtures, True
        else:
            self.stdout.write(self.style.WARNING(f"❌ No fixtures found with season {self.SEASON}"))
            self.SEASON = previous_season
            return None, False

    def fetch_fixtures_for_date_range(self, date_range, headers, options):
        """Fetch fixtures for the given date range and return them"""
        dry_run = options['dry_run']
        force_update = options['force_update']
        verbose = options['verbose']
        diagnostic = options.get('diagnostic', False)
        
        total_fixtures = 0
        fixtures_created = 0
        fixtures_updated = 0
        fixtures_skipped = 0
        api_calls = 0
        fixtures_per_day = {}
        all_fixtures = []
        
        # Loop through each date
        for date in date_range:
            date_str = date.strftime('%Y-%m-%d')
            self.stdout.write(f"\n📅 Fetching fixtures for date: {date_str}")
            
            # Fetch fixtures for this date and league
            params = {
                'league': self.LEAGUE_ID,
                'season': self.SEASON,
                'date': date_str
            }
            
            try:
                # Throttle API requests
                if api_calls > 0:
                    time.sleep(1)
                
                api_calls += 1
                
                # DIAGNOSTIC: Print the full URL with parameters
                full_url = f"{self.API_ENDPOINT_FIXTURES}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
                
                if diagnostic:
                    self.stdout.write(self.style.WARNING(f"  🔗 API URL: {full_url}"))
                    self.stdout.write(f"  🔑 Headers: {{'x-apisports-key': '{API_KEY[:4]}...{API_KEY[-4:]}'}} (masked)")
                
                fixtures_response = requests.get(
                    self.API_ENDPOINT_FIXTURES, 
                    headers=headers, 
                    params=params, 
                    timeout=30
                )
                self.stdout.write(f"  📶 API Response Status: {fixtures_response.status_code}")
                
                fixtures_data = fixtures_response.json()
                
                # DIAGNOSTIC: Print top-level keys from the API response
                if diagnostic:
                    self.stdout.write(self.style.WARNING(f"  📋 API Response Top-Level Keys: {list(fixtures_data.keys())}"))
                
                # If there are errors, print them
                if 'errors' in fixtures_data and fixtures_data['errors']:
                    self.stdout.write(self.style.ERROR(f"  ❌ API Errors: {fixtures_data['errors']}"))
                    
                    # Check for specific plan restriction error
                    plan_error = fixtures_data.get('errors', {}).get('plan')
                    if plan_error and 'Free plans do not have access to this date' in str(plan_error):
                        self.stdout.write(self.style.ERROR(
                            f"  ⛔ FREE PLAN RESTRICTION: {plan_error}\n"
                            f"  Skipping date {date_str} as it's outside the allowed range."
                        ))
                        fixtures_per_day[date_str] = 0
                        continue
                
                # Print pagination info if available
                if 'paging' in fixtures_data and diagnostic:
                    self.stdout.write(f"  📄 Paging: {fixtures_data['paging']}")
                
                # Print results count if available
                if 'results' in fixtures_data:
                    self.stdout.write(f"  🔢 API Reported Results Count: {fixtures_data['results']}")
                
                if fixtures_response.status_code != 200:
                    self.stderr.write(self.style.ERROR(f"API error: {fixtures_data.get('message', 'Unknown error')}"))
                    continue
                
                fixtures_list = fixtures_data.get('response', [])
                # DIAGNOSTIC: Print raw fixture list length
                self.stdout.write(self.style.WARNING(f"  📋 Raw fixture list length: {len(fixtures_list)}"))
                
                if not fixtures_list:
                    self.stdout.write(self.style.WARNING(f"  ⚠️ No fixtures found for {date_str}"))
                    fixtures_per_day[date_str] = 0
                    continue
                
                # Record fixtures per day for summary
                fixtures_per_day[date_str] = len(fixtures_list)
                all_fixtures.extend(fixtures_list)
                
                self.stdout.write(self.style.SUCCESS(f"  ✅ Found {len(fixtures_list)} fixtures for {date_str}"))
                total_fixtures += len(fixtures_list)
                
                # DIAGNOSTIC: Show the first fixture's structure if available
                if fixtures_list and verbose:
                    self.stdout.write(self.style.WARNING(f"  📋 First fixture structure:"))
                    self.stdout.write(json.dumps(fixtures_list[0], indent=2)[:500] + "... (truncated)")
                
                # Process each fixture - DIAGNOSTIC MODE - Just print details
                self.stdout.write(self.style.SUCCESS("\n  📊 FIXTURES FOUND:"))
                for fixture in fixtures_list:
                    fixture_id = fixture['fixture']['id']
                    home_team = fixture['teams']['home']['name']
                    away_team = fixture['teams']['away']['name']
                    
                    # Parse and format kickoff time
                    kickoff_utc = fixture['fixture']['date']
                    try:
                        kickoff = datetime.fromisoformat(kickoff_utc.replace('Z', '+00:00')).astimezone(timezone.get_current_timezone())
                        kickoff_str = kickoff.strftime('%Y-%m-%d %H:%M')
                    except:
                        kickoff_str = kickoff_utc
                    
                    status = fixture['fixture']['status']['short']
                    
                    # Print fixture details in the requested format
                    self.stdout.write(self.style.SUCCESS(f"  ▶ Match ID {fixture_id}: {home_team} vs {away_team} @ {kickoff_str} (status: {status})"))
                
                # If not in diagnostic mode, continue with DB operations
                if not dry_run:
                    for fixture in fixtures_list:
                        fixture_id = fixture['fixture']['id']
                        
                        # Extract required data
                        kickoff_utc = fixture['fixture']['date']
                        
                        try:
                            kickoff = datetime.fromisoformat(kickoff_utc.replace('Z', '+00:00')).astimezone(timezone.get_current_timezone())
                        except Exception as e:
                            self.stderr.write(self.style.ERROR(f"  ❌ Error parsing date '{kickoff_utc}': {str(e)}"))
                            # Try an alternate method
                            try:
                                kickoff = datetime.strptime(kickoff_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(timezone.get_current_timezone())
                                self.stdout.write(f"  ✅ Alternate date parsing successful: {kickoff}")
                            except Exception as e2:
                                self.stderr.write(self.style.ERROR(f"  ❌ Alternate parsing also failed: {str(e2)}"))
                                continue
                        
                        status = fixture['fixture']['status']['short']
                        
                        # Extract team names
                        home_team = fixture['teams']['home']['name']
                        away_team = fixture['teams']['away']['name']
                        
                        # Check if match already exists
                        match_exists = Match.objects.filter(api_ref=str(fixture_id)).exists()
                        
                        if match_exists and not force_update:
                            # Update only status if match exists
                            match = Match.objects.get(api_ref=str(fixture_id))
                            
                            # Check if any data needs updating
                            if match.status != status:
                                self.stdout.write(f"    Updating status: {match.status} -> {status}")
                                match.status = status
                                match.save(update_fields=['status'])
                                fixtures_updated += 1
                            else:
                                self.stdout.write(f"    Skipping - Match already exists with ID {match.id}")
                                fixtures_skipped += 1
                        else:
                            # Create new match or force update existing one
                            if match_exists:
                                match = Match.objects.get(api_ref=str(fixture_id))
                                action = "Updating"
                                fixtures_updated += 1
                            else:
                                match = Match(api_ref=str(fixture_id))
                                action = "Creating new"
                                fixtures_created += 1
                            
                            self.stdout.write(f"    {action} match: {home_team} vs {away_team}")
                            
                            match.home_team = home_team
                            match.away_team = away_team
                            match.kickoff = kickoff
                            match.status = status
                            match.league_name = self.LEAGUE_NAME
                            match.save()
            
            except requests.exceptions.RequestException as e:
                self.stderr.write(self.style.ERROR(f"Network error: {str(e)}"))
                continue
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Unexpected error: {str(e)}"))
                if diagnostic:
                    import traceback
                    self.stderr.write(self.style.ERROR(f"Traceback: {traceback.format_exc()}"))
                continue
                
        # Print fixtures per day
        self.stdout.write(self.style.SUCCESS("\n📋 SUMMARY OF FIXTURES:"))
        for date_str, count in fixtures_per_day.items():
            emoji = "✅" if count > 0 else "❌"
            self.stdout.write(f"{emoji} {date_str}: {count} fixtures")
            
        # Print summary
        if dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 DRY RUN MODE - No changes were made to the database"))
            self.stdout.write(f"Total API calls: {api_calls}")
            self.stdout.write(f"Total fixtures found: {total_fixtures}")
            
            if total_fixtures == 0:
                self.stdout.write(self.style.ERROR("\n❌ No fixtures were found for the specified dates and season."))
                self.stdout.write(self.style.ERROR("This could be because:"))
                self.stdout.write("  1. There are genuinely no matches scheduled for today")
                self.stdout.write("  2. The season value might be incorrect")
                self.stdout.write("  3. The API data might not be available yet")
                self.stdout.write("\nTry running with --check-seasons to see available seasons.")
            else:
                self.stdout.write(self.style.SUCCESS(f"\n✅ Successfully found {total_fixtures} fixtures for the specified date range."))
                self.stdout.write(self.style.SUCCESS("This confirms API access is working within free plan constraints."))
                self.stdout.write("\nIf you want to store these fixtures in the database, run without --dry-run:")
                self.stdout.write(f"python manage.py fetch_liga1_fixtures --days=0 --season={self.SEASON} --no-dry-run")
        else:
            self.stdout.write(f"\nFixtures created: {fixtures_created}")
            self.stdout.write(f"Fixtures updated: {fixtures_updated}")
            self.stdout.write(f"Fixtures skipped: {fixtures_skipped}")
            
        return all_fixtures

    def handle(self, *args, **options):
        days_ahead = options['days']
        force_update = options['force_update']
        dry_run = options['dry_run']
        verbose = options['verbose']
        check_seasons = options['check_seasons']
        auto_season = options['auto_season']
        diagnostic = options['diagnostic']
        explicit_season = options['season']
        
        # Override dry_run if --no-dry-run is provided
        if options['no_dry_run']:
            dry_run = False
            options['dry_run'] = False
        
        # Check if days_ahead exceeds the free plan limit
        if days_ahead > self.MAX_DAYS_AHEAD:
            self.stdout.write(self.style.WARNING(
                f"⚠️ WARNING: Free API plan only allows fetching fixtures for today + {self.MAX_DAYS_AHEAD} days ahead.\n"
                f"Automatically limiting requested range from {days_ahead} to {self.MAX_DAYS_AHEAD} days."
            ))
            days_ahead = self.MAX_DAYS_AHEAD
        
        if diagnostic:
            self.stdout.write(self.style.WARNING(f"🔍 DIAGNOSTIC MODE: Detailed information will be shown"))
            
        self.stdout.write(self.style.WARNING(f"🔍 Testing API fixture access for free plan"))
        
        if not API_KEY:
            self.stderr.write(self.style.ERROR(
                f"API_FOOTBALL_KEY not found in environment variables or in .env file (expected at {dotenv_path}).\n"
                "Please ensure your .env file is in the project root (same level as manage.py) and contains API_FOOTBALL_KEY."
            ))
            return
            
        self.stdout.write(self.style.SUCCESS(f"API Key loaded (masked): {API_KEY[:4]}...{API_KEY[-4:]}"))
        
        # Headers for API requests
        headers = {
            "x-apisports-key": API_KEY
        }
        
        # Get available seasons to auto-detect the appropriate one
        seasons, api_current_season, active_season_for_today = self.get_available_seasons(headers, diagnostic=diagnostic)
        
        # Determine which season to use based on priorities:
        # 1. Explicitly provided season (--season)
        # 2. Season that matches today's date 
        # 3. API-marked current season
        # 4. Fallback season
        
        # Start with detailed explanation about season selection
        if diagnostic:
            self.stdout.write(self.style.WARNING("\n📊 SEASON SELECTION PROCESS:"))
        
        if explicit_season:
            self.SEASON = explicit_season
            if diagnostic:
                self.stdout.write(f"  1. Using explicitly provided season: {self.SEASON} (from --season parameter)")
        elif active_season_for_today:
            self.SEASON = active_season_for_today
            if diagnostic:
                self.stdout.write(f"  1. Using season matching today's date: {self.SEASON}")
        elif api_current_season:
            self.SEASON = api_current_season
            if diagnostic:
                self.stdout.write(f"  1. Using API-marked current season: {self.SEASON}")
        else:
            self.SEASON = self.FALLBACK_SEASON
            if diagnostic:
                self.stdout.write(f"  1. Using fallback season: {self.SEASON} (no better season detected)")
        
        # Log the final selected season
        self.stdout.write(self.style.SUCCESS(f"🏆 Selected season: {self.SEASON}"))
        if diagnostic:
            if explicit_season:
                self.stdout.write("   ↳ Reason: Explicitly provided via --season parameter")
            elif self.SEASON == active_season_for_today:
                self.stdout.write(f"   ↳ Reason: This season's date range covers today ({datetime.today().date()})")
            elif self.SEASON == api_current_season:
                self.stdout.write("   ↳ Reason: API reports this as the current season")
            else:
                self.stdout.write("   ↳ Reason: Fallback value, no better season detected")
        
        self.stdout.write(self.style.SUCCESS(f"🏆 Fetching fixtures for League ID {self.LEAGUE_ID}, Season {self.SEASON} for today (free plan limit)..."))
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN: No database changes will be made"))
        
        # Generate date range for today only (0 days offset)
        today = datetime.today().date()
        date_range = [today + timedelta(days=i) for i in range(0, days_ahead + 1)]
        
        # Display the exact date range we're fetching
        if len(date_range) == 1:
            self.stdout.write(self.style.SUCCESS(f"📅 Date: Today ({date_range[0].strftime('%Y-%m-%d')})"))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"📅 Date range: {date_range[0].strftime('%Y-%m-%d')} to {date_range[-1].strftime('%Y-%m-%d')} "
                f"({len(date_range)} days)"
            ))
        
        # Update options with diagnostic flag
        options['diagnostic'] = diagnostic
        
        # Fetch fixtures with current season
        fixtures = self.fetch_fixtures_for_date_range(date_range, headers, options)
        
        # If no fixtures were found and auto_season is enabled, try to auto-discover the season
        if not fixtures and auto_season:
            self.stdout.write(self.style.WARNING(f"\n⚠️ No fixtures found with season {self.SEASON}. Trying other seasons..."))
            
            if diagnostic:
                self.stdout.write(self.style.WARNING("\n🔄 AUTO-SEASON FALLBACK PROCESS:"))
            
            # Try with recent seasons
            if seasons:
                # Sort seasons in descending order and try recent ones first
                seasons.sort(reverse=True)
                
                for season in seasons[:3]:  # Try up to 3 most recent seasons
                    if season != self.SEASON:
                        fixtures, success = self.try_with_season(season, headers, date_range, options)
                        if success:
                            self.stdout.write(self.style.SUCCESS(f"Found fixtures with alternative season: {season}"))
                            if diagnostic:
                                self.stdout.write(f"  Consider using --season={season} in future calls")
                            break
        
        # Final summary if no fixtures were found
        if not fixtures:
            self.stdout.write(self.style.ERROR(f"\n❌ No fixtures found for today with League ID {self.LEAGUE_ID}, Season {self.SEASON}"))
            self.stdout.write(self.style.WARNING("\n=== 🔍 TROUBLESHOOTING SUGGESTIONS ==="))
            self.stdout.write("1. Try different season values (use --check-seasons to see available seasons)")
            self.stdout.write(f"   Example: python manage.py fetch_liga1_fixtures --season=2022")
            self.stdout.write("2. Use --auto-season to automatically try to find the correct season")
            self.stdout.write("3. Verify league ID is correct (currently using 283 for Romanian Liga 1)")
            self.stdout.write("4. Check API key permissions and subscription status")
            self.stdout.write("5. There might genuinely be no fixtures scheduled for today")
        else:
            self.stdout.write(self.style.SUCCESS(f"\n✅ Successfully fetched fixtures for today with League ID {self.LEAGUE_ID}, Season {self.SEASON}"))
            self.stdout.write(self.style.SUCCESS("API access is working correctly within free plan constraints.")) 