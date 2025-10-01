from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
import time
import os
import sys
import json
import requests
from datetime import datetime
import csv
import logging
from django.conf import settings

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from core.models import League, Team, Match
from django.utils.text import slugify

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LEAGUE_CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'league_config.json')
SPORTMONKS_TOKEN = os.getenv('SPORTMONKS_API_TOKEN')

# --- API CLIENT ---
class APIClient:
    """A robust API client with rate limiting, retries, and logging."""
    def __init__(self, api_name, rate_limit_per_min, command):
        self.api_name = api_name
        self.requests_made = 0
        self.start_time = time.time()
        self.rate_limit_delay = 60.0 / rate_limit_per_min
        self.command = command

    def get(self, url, params=None, retries=3, backoff_factor=0.5):
        """Perform a GET request with retry logic."""
        if params is None:
            params = {}
        
        # Rate limiting
        self._enforce_rate_limit()

        for attempt in range(retries):
            try:
                response = requests.get(url, params=params, timeout=30)
                self.requests_made += 1
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    self.command.stdout.write(self.command.style.WARNING("  Rate limit exceeded. Waiting 60 seconds..."))
                    time.sleep(60)
                    continue # Retry the request
                else:
                    self.command.stdout.write(self.command.style.ERROR(f"  🚨 [{self.api_name}] API Error (Attempt {attempt + 1}/{retries}): {response.status_code} for {url}"))
                    self.command.stdout.write(f"     Response: {response.text[:200]}")
            except requests.exceptions.RequestException as e:
                self.command.stdout.write(self.command.style.ERROR(f"  🚨 [{self.api_name}] Request Failed (Attempt {attempt + 1}/{retries}): {e}"))

            time.sleep(backoff_factor * (2 ** attempt))
        
        self.command.stdout.write(self.command.style.ERROR(f"  🔥 [{self.api_name}] All retries failed for {url}"))
        return None

    def _enforce_rate_limit(self):
        """Enforce rate limiting to avoid API bans."""
        elapsed_time = time.time() - self.start_time
        if elapsed_time < 60:
            if self.requests_made >= 115: # Stay just under 120
                sleep_time = 60 - elapsed_time
                self.command.stdout.write(self.command.style.SUCCESS(f"  ⏳ [SportMonks] Rate limit approaching. Sleeping for {sleep_time:.2f}s..."))
                time.sleep(sleep_time)
                self.start_time = time.time()
                self.requests_made = 0
        else:
            self.start_time = time.time()
            self.requests_made = 0

# --- MANAGEMENT COMMAND ---
class Command(BaseCommand):
    help = 'Collect historical football data from SportMonks API for ML training'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-year',
            type=int,
            default=2010,
            help='Start year for data collection (default: 2010)'
        )
        parser.add_argument(
            '--end-year', 
            type=int,
            default=2016,
            help='End year for data collection (default: 2016)'
        )
        parser.add_argument(
            '--limit-leagues',
            type=int,
            help='Limit to first N leagues for testing'
        )
        parser.add_argument(
            '--output-file',
            type=str,
            default='training_data.csv',
            help='Output CSV file name'
        )
        parser.add_argument(
            '--test-mode',
            action='store_true',
            help='Run in test mode with limited data'
        )

    def __init__(self):
        super().__init__()
        self.setup_logging()
        self.setup_api()
        self.collected_fixtures = set()
        self.total_fixtures = 0
        self.successful_fixtures = 0
        self.failed_requests = []

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('collect_training_data.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_api(self):
        """Setup API configuration"""
        # Try to get API token from environment or settings
        self.api_token = os.getenv('SPORTMONKS_API_TOKEN')
        if not self.api_token:
            try:
                self.api_token = settings.SPORTMONKS_API_TOKEN
            except AttributeError:
                raise CommandError("SPORTMONKS_API_TOKEN not found in environment or settings")
        
        self.base_url = "https://api.sportmonks.com/v3/football"
        self.rate_limit_delay = 0.6  # ~100 requests per minute to stay under 3000/hour
        
        # European Plan - Major League IDs
        self.target_leagues = {
            8: "Premier League",
            564: "La Liga", 
            384: "Serie A",
            82: "Bundesliga",
            301: "Ligue 1",
            271: "Danish Superliga",
            72: "Eredivisie",
            208: "Belgian Pro League",
            181: "Austrian Bundesliga",
            244: "Croatian 1. HNL",
            453: "Polish Ekstraklasa",
            462: "Portuguese Primeira Liga",
            573: "Swedish Allsvenskan",
            591: "Swiss Super League",
            600: "Turkish Super Lig",
            444: "Norwegian Eliteserien",
            501: "Scottish Premiership",
            609: "Ukrainian Premier League",
            486: "Russian Premier League"
        }

    def make_api_request(self, endpoint, params=None):
        """Make API request with error handling and rate limiting"""
        if params is None:
            params = {}
        
        params['api_token'] = self.api_token
        url = f"{self.base_url}/{endpoint}"
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                time.sleep(self.rate_limit_delay)
                response = requests.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limit
                    self.logger.warning(f"Rate limit hit, waiting 60 seconds...")
                    time.sleep(60)
                    continue
                else:
                    self.logger.error(f"API error {response.status_code} for {endpoint}: {response.text[:200]}")
                    
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request failed (attempt {attempt + 1}) for {endpoint}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))
        
        # Log failed request
        self.failed_requests.append({
            'endpoint': endpoint,
            'params': params,
            'timestamp': datetime.now().isoformat()
        })
        return None

    def get_seasons_for_league(self, league_id, start_year, end_year):
        """Get seasons for a league within year range"""
        self.logger.info(f"Getting seasons for league {league_id}")
        
        seasons = []
        page = 1
        
        while True:
            data = self.make_api_request('seasons', {
                'league_id': league_id,
                'per_page': 50,
                'page': page
            })
            
            if not data or 'data' not in data:
                break
                
            page_seasons = data['data']
            if not page_seasons:
                break
                
            # Filter seasons by year range
            for season in page_seasons:
                starting_at = season.get('starting_at', '')
                if starting_at and len(starting_at) >= 4:
                    year = int(starting_at[:4])
                    if start_year <= year <= end_year:
                        seasons.append(season)
            
            # Check pagination
            pagination = data.get('pagination', {})
            if not pagination.get('has_more', False):
                break
            page += 1
            
        self.logger.info(f"Found {len(seasons)} seasons for league {league_id}")
        return seasons

    def get_stages_for_season(self, season_id):
        """Get stages for a season using correct API v3 syntax"""
        data = self.make_api_request('stages', {'season_id': season_id})
        if data and 'data' in data:
            return data['data']
        return []

    def get_fixtures_for_season(self, season_id):
        """Get fixtures directly for a season - simpler approach"""
        fixtures = []
        page = 1
        
        while True:
            data = self.make_api_request('fixtures', {
                'season_id': season_id,
                'per_page': 100,
                'page': page
            })
            
            if not data or 'data' not in data:
                break
                
            page_fixtures = data['data']
            if not page_fixtures:
                break
                
            fixtures.extend(page_fixtures)
            
            # Check pagination
            pagination = data.get('pagination', {})
            if not pagination.get('has_more', False):
                break
            page += 1
            
        return fixtures

    def get_fixture_details(self, fixture_id):
        """Get detailed fixture information with includes"""
        includes = [
            'participants',
            'scores',
            'odds.bookmaker',
            'odds.market',
            'league',
            'season'
        ]
        
        data = self.make_api_request(f'fixtures/{fixture_id}', {
            'include': ','.join(includes)
        })
        
        if data and 'data' in data:
            return data['data']
        return None

    def extract_fixture_data(self, fixture):
        """Extract relevant data from fixture for CSV"""
        try:
            # Basic fixture info
            fixture_id = fixture.get('id')
            date = fixture.get('starting_at', '')
            name = fixture.get('name', '')
            
            # League and season info
            league_name = ''
            season_name = ''
            if 'league' in fixture:
                league_name = fixture['league'].get('name', '')
            if 'season' in fixture:
                season_name = fixture['season'].get('name', '')
            
            # Teams
            home_team = ''
            away_team = ''
            if 'participants' in fixture:
                for participant in fixture['participants']:
                    if participant.get('meta', {}).get('location') == 'home':
                        home_team = participant.get('name', '')
                    elif participant.get('meta', {}).get('location') == 'away':
                        away_team = participant.get('name', '')
            
            # Scores
            home_score = None
            away_score = None
            if 'scores' in fixture:
                for score in fixture['scores']:
                    if score.get('description') == 'CURRENT':
                        score_data = score.get('score', {})
                        if score_data.get('participant') == 'home':
                            home_score = score_data.get('goals')
                        elif score_data.get('participant') == 'away':
                            away_score = score_data.get('goals')
            
            # Odds (1X2 market)
            odds_home = None
            odds_draw = None
            odds_away = None
            
            if 'odds' in fixture:
                for odd in fixture['odds']:
                    market = odd.get('market', {})
                    if market.get('key') == 'fulltime_result':  # 1X2 market
                        bookmaker_odds = odd.get('bookmaker', {})
                        if bookmaker_odds.get('name'):  # Has bookmaker data
                            selections = odd.get('selections', [])
                            for selection in selections:
                                label = selection.get('label', '').lower()
                                if label == '1' or 'home' in label:
                                    odds_home = selection.get('odds')
                                elif label == 'x' or 'draw' in label:
                                    odds_draw = selection.get('odds')
                                elif label == '2' or 'away' in label:
                                    odds_away = selection.get('odds')
                            break  # Use first bookmaker found
            
            return {
                'fixture_id': fixture_id,
                'date': date,
                'name': name,
                'home_team': home_team,
                'away_team': away_team,
                'home_score': home_score,
                'away_score': away_score,
                'odds_home': odds_home,
                'odds_draw': odds_draw,
                'odds_away': odds_away,
                'league_name': league_name,
                'season_name': season_name
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting fixture data: {str(e)}")
            return None

    def save_to_csv(self, fixtures_data, output_file):
        """Save fixtures data to CSV"""
        if not fixtures_data:
            self.logger.warning("No data to save")
            return
            
        fieldnames = [
            'fixture_id', 'date', 'name', 'home_team', 'away_team',
            'home_score', 'away_score', 'odds_home', 'odds_draw', 'odds_away',
            'league_name', 'season_name'
        ]
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(fixtures_data)
            
        self.logger.info(f"Saved {len(fixtures_data)} fixtures to {output_file}")

    def handle(self, *args, **options):
        start_time = datetime.now()
        
        start_year = options['start_year']
        end_year = options['end_year']
        limit_leagues = options['limit_leagues']
        output_file = options['output_file']
        test_mode = options['test_mode']
        
        self.stdout.write(f"Starting data collection: {start_year}-{end_year}")
        
        # Warning about data availability
        if start_year >= 2018:
            self.stdout.write(
                self.style.WARNING(
                    f"WARNING: Requested years {start_year}-{end_year} may not have data available.\n"
                    f"Based on API analysis, historical data is only available for ~2005-2016.\n"
                    f"The script will attempt to collect data but may find limited results.\n"
                    f"Consider using --start-year 2010 --end-year 2016 for better results."
                )
            )
        
        # Select leagues to process
        leagues_to_process = dict(list(self.target_leagues.items())[:limit_leagues]) if limit_leagues else self.target_leagues
        
        self.stdout.write(f"Processing {len(leagues_to_process)} leagues")
        
        all_fixtures_data = []
        
        try:
            for league_id, league_name in leagues_to_process.items():
                self.stdout.write(f"\nProcessing {league_name} (ID: {league_id})")
                
                # Get seasons for this league
                seasons = self.get_seasons_for_league(league_id, start_year, end_year)
                
                if not seasons:
                    self.stdout.write(self.style.WARNING(f"No seasons found for {league_name} in {start_year}-{end_year}"))
                    continue
                
                for season in seasons:
                    season_id = season.get('id')
                    season_name = season.get('name', '')
                    
                    self.stdout.write(f"  Processing season: {season_name}")
                    
                    # Get fixtures directly for this season (simpler approach)
                    fixtures = self.get_fixtures_for_season(season_id)
                    
                    if not fixtures:
                        self.stdout.write(self.style.WARNING(f"No fixtures found for season {season_name}"))
                        continue
                    
                    self.stdout.write(f"    Found {len(fixtures)} fixtures")
                    
                    for fixture in fixtures:
                        fixture_id = fixture.get('id')
                        
                        # Skip if already collected
                        if fixture_id in self.collected_fixtures:
                            continue
                        
                        self.total_fixtures += 1
                        
                        # Get detailed fixture data
                        detailed_fixture = self.get_fixture_details(fixture_id)
                        
                        if detailed_fixture:
                            fixture_data = self.extract_fixture_data(detailed_fixture)
                            
                            if fixture_data:
                                all_fixtures_data.append(fixture_data)
                                self.collected_fixtures.add(fixture_id)
                                self.successful_fixtures += 1
                                
                                if self.successful_fixtures % 10 == 0:
                                    self.stdout.write(f"    Collected {self.successful_fixtures} fixtures")
                        
                        # Test mode limit
                        if test_mode and self.successful_fixtures >= 10:
                            self.stdout.write("Test mode: stopping at 10 fixtures")
                            break
                    
                    if test_mode and self.successful_fixtures >= 10:
                        break
                
                if test_mode and self.successful_fixtures >= 10:
                    break
            
            # Save collected data
            if all_fixtures_data:
                self.save_to_csv(all_fixtures_data, output_file)
            
            # Final statistics
            end_time = datetime.now()
            duration = end_time - start_time
            
            self.stdout.write(self.style.SUCCESS(f"\nCOLLECTION COMPLETE"))
            self.stdout.write(f"Duration: {duration}")
            self.stdout.write(f"Total fixtures processed: {self.total_fixtures}")
            self.stdout.write(f"Successful collections: {self.successful_fixtures}")
            self.stdout.write(f"Failed requests: {len(self.failed_requests)}")
            self.stdout.write(f"Output file: {output_file}")
            
            if self.failed_requests:
                # Save failed requests log
                with open('failed_requests.json', 'w') as f:
                    import json
                    json.dump(self.failed_requests, f, indent=2)
                self.stdout.write(f"Failed requests saved to: failed_requests.json")
            
            if self.successful_fixtures == 0:
                self.stdout.write(
                    self.style.ERROR(
                        f"\nNO DATA COLLECTED!\n"
                        f"This likely means no data is available for {start_year}-{end_year}.\n"
                        f"Try using --start-year 2010 --end-year 2016 instead."
                    )
                )
            
        except KeyboardInterrupt:
            self.stdout.write("\nCollection interrupted by user")
            if all_fixtures_data:
                self.save_to_csv(all_fixtures_data, f"partial_{output_file}")
                self.stdout.write(f"Partial data saved to partial_{output_file}")
        
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            raise CommandError(f"Collection failed: {str(e)}") 