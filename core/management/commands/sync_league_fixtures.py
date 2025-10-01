from django.core.management.base import BaseCommand
from django.utils import timezone
import time
import os
import sys
import json
import requests
from datetime import datetime, timedelta

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from core.models import League, Team, Match, OddsSnapshot
from django.utils.text import slugify

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LEAGUE_CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'league_config.json')
ODDSAPI_KEY = os.getenv('ODDSAPI_KEY')

# --- API CLIENT ---
class APIClient:
    def __init__(self, api_name):
        self.api_name = api_name

    def get(self, url, params=None, retries=3, backoff_factor=0.5):
        if params is None:
            params = {}
        for attempt in range(retries):
            try:
                response = requests.get(url, params=params, timeout=20)
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"  🚨 [{self.api_name}] API Error (Attempt {attempt + 1}/{retries}): {response.status_code} for {url}")
            except requests.exceptions.RequestException as e:
                print(f"  🚨 [{self.api_name}] Request Failed (Attempt {attempt + 1}/{retries}): {e}")
            time.sleep(backoff_factor * (2 ** attempt))
        return None

oddsapi_client = APIClient("OddsAPI")

# --- MANAGEMENT COMMAND ---
class Command(BaseCommand):
    help = 'Syncs upcoming fixtures and odds from OddsAPI for supported leagues.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--live',
            action='store_true',
            help='Performs a live sync. Currently the default behavior.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting SmartBet Fixture Synchronization...'))
        self.stats = {
            "leagues_processed": 0,
            "fixtures_found": 0,
            "matches_created_or_updated": 0,
            "odds_snapshots_created": 0,
            "failed_lookups": 0
        }
        
        supported_leagues = self.load_league_config()
        if not supported_leagues:
            self.stdout.write(self.style.ERROR('Could not load league configuration. Aborting.'))
            return

        for league_config in supported_leagues:
            self.process_league(league_config)
            time.sleep(2) # Rate limit between processing leagues

        self.print_summary()

    def load_league_config(self):
        self.stdout.write("1. Loading league configuration...")
        try:
            with open(LEAGUE_CONFIG_PATH, 'r') as f:
                config = json.load(f)
            self.stdout.write(self.style.SUCCESS(f"  ✅ Loaded {len(config)} supported leagues."))
            return config
        except FileNotFoundError:
            return None

    def process_league(self, league_config):
        self.stdout.write(f"\n2. Processing League: {league_config['name_en']}")
        self.stats["leagues_processed"] += 1

        odds_data = self.fetch_odds_for_league(league_config['oddsapi_key'])
        if not odds_data:
            self.stdout.write(self.style.WARNING(f"  No odds data found for {league_config['name_en']}."))
            self.stats["failed_lookups"] += 1
            return
        
        self.stats["fixtures_found"] += len(odds_data)
        self.stdout.write(f"  Found {len(odds_data)} upcoming fixtures with odds.")

        league_obj, _ = League.objects.get_or_create(
            name_en=league_config['name_en'],
            defaults={
                'name_ro': league_config.get('name_ro', league_config['name_en']),
                'country': league_config.get('country', 'International')
            }
        )
        
        for game in odds_data:
            self.store_game_data(game, league_obj)

    def fetch_odds_for_league(self, oddsapi_league_key):
        params = {
            'apiKey': ODDSAPI_KEY,
            'regions': 'eu',
            'markets': 'h2h',
            'oddsFormat': 'decimal'
        }
        url = f"https://api.the-odds-api.com/v4/sports/{oddsapi_league_key}/odds"
        return oddsapi_client.get(url, params)

    def store_game_data(self, game_data, league_obj):
        home_team_name = game_data['home_team']
        away_team_name = game_data['away_team']

        home_team_obj, _ = Team.objects.get_or_create(
            name_en=home_team_name,
            defaults={'name_ro': home_team_name, 'slug': slugify(home_team_name)}
        )
        away_team_obj, _ = Team.objects.get_or_create(
            name_en=away_team_name,
            defaults={'name_ro': away_team_name, 'slug': slugify(away_team_name)}
        )

        try:
            kickoff_dt = datetime.fromisoformat(game_data['commence_time'].replace('Z', '+00:00'))
        except (ValueError, TypeError):
            kickoff_dt = timezone.now() + timedelta(days=1)

        match_obj, created = Match.objects.update_or_create(
            api_ref=game_data['id'],
            defaults={
                'league': league_obj,
                'home_team': home_team_obj,
                'away_team': away_team_obj,
                'kickoff': kickoff_dt,
                'status': 'NS',
            }
        )
        self.stats["matches_created_or_updated"] += 1

        # Store odds from the first available bookmaker
        bookmaker_data = game_data.get('bookmakers', [])[0] if game_data.get('bookmakers') else None
        if bookmaker_data:
            prices = bookmaker_data.get('markets', [{}])[0].get('outcomes', [])
            odds_home = next((p['price'] for p in prices if p['name'] == home_team_name), None)
            odds_draw = next((p['price'] for p in prices if p['name'] == 'Draw'), None)
            odds_away = next((p['price'] for p in prices if p['name'] == away_team_name), None)

            if all([odds_home, odds_draw, odds_away]):
                OddsSnapshot.objects.update_or_create(
                    match=match_obj,
                    bookmaker=bookmaker_data['title'],
                    defaults={
                        'odds_home': odds_home,
                        'odds_draw': odds_draw,
                        'odds_away': odds_away,
                        'fetched_at': timezone.now()
                    }
                )
                self.stats["odds_snapshots_created"] += 1
                self.stdout.write(self.style.SUCCESS(f"    ✅ Stored: {home_team_name} vs {away_team_name} with odds."))
            else:
                self.stdout.write(self.style.WARNING(f"    ⚠️ Missing h2h prices for {home_team_name} vs {away_team_name}."))
        else:
             self.stdout.write(self.style.WARNING(f"    ⚠️ No bookmaker odds found for {home_team_name} vs {away_team_name}."))


    def print_summary(self):
        self.stdout.write(self.style.SUCCESS('\n--- SYNC SUMMARY ---'))
        self.stdout.write(f"✅ Leagues Processed: {self.stats['leagues_processed']}")
        self.stdout.write(f"📅 Fixtures Found: {self.stats['fixtures_found']}")
        self.stdout.write(f"➕ Matches Created/Updated: {self.stats['matches_created_or_updated']}")
        self.stdout.write(f"💰 Odds Snapshots Created: {self.stats['odds_snapshots_created']}")
        
        if self.stats['fixtures_found'] > 0:
            odds_availability = (self.stats['odds_snapshots_created'] / self.stats['fixtures_found']) * 100
            self.stdout.write(f"  > Odds Availability: {odds_availability:.2f}%")

        self.stdout.write(f"🚨 Failed League Lookups: {self.stats['failed_lookups']}")
        self.stdout.write(self.style.SUCCESS('--- END SUMMARY ---')) 