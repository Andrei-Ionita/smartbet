import os
import requests
import json
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from dotenv import load_dotenv
from pathlib import Path
import time
from rich.console import Console
from rich.table import Table

# Set up environment for API key
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)
API_KEY = os.getenv('API_FOOTBALL_KEY')

class Command(BaseCommand):
    help = 'Tests API access by fetching fixtures for today or a specific day offset'

    API_HOST = 'v3.football.api-sports.io'
    API_ENDPOINT_FIXTURES = f'https://{API_HOST}/fixtures'
    DEFAULT_LEAGUE_ID = 283  # Romanian Liga 1
    DEFAULT_SEASON = 2023  # Known good season to test with
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=0,
            help='Day offset from today (0=today, 1=tomorrow, 2=day after tomorrow)'
        )
        parser.add_argument(
            '--season',
            type=int,
            default=self.DEFAULT_SEASON,
            help=f'Season to use for testing (default: {self.DEFAULT_SEASON})'
        )
        parser.add_argument(
            '--league',
            type=int,
            default=self.DEFAULT_LEAGUE_ID,
            help=f'League ID to test (default: {self.DEFAULT_LEAGUE_ID} for Romanian Liga 1)'
        )
        parser.add_argument(
            '--raw-json',
            action='store_true',
            help='Display complete raw JSON response'
        )

    def handle(self, *args, **options):
        day_offset = options['days']
        season = options['season']
        league_id = options['league']
        show_raw = options['raw_json']
        
        # Calculate the target date based on the offset
        today = datetime.today().date()
        target_date = today + timedelta(days=day_offset)
        date_str = target_date.strftime('%Y-%m-%d')
        
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS(f"🔍 TESTING API FIXTURE ACCESS"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(f"📅 Date: {date_str} (Today{'+'+str(day_offset) if day_offset > 0 else ''})")
        self.stdout.write(f"🏆 League ID: {league_id}")
        self.stdout.write(f"🗓️ Season: {season}")
        
        # Check if API key is available
        if not API_KEY:
            self.stderr.write(self.style.ERROR(
                f"❌ API_FOOTBALL_KEY not found in environment variables or in .env file (expected at {dotenv_path}).\n"
                "Please ensure your .env file is in the project root (same level as manage.py) and contains API_FOOTBALL_KEY."
            ))
            return
        
        self.stdout.write(self.style.SUCCESS(f"✅ API Key found: {API_KEY[:4]}...{API_KEY[-4:]}"))
        
        # Set up API request
        headers = {
            "x-apisports-key": API_KEY
        }
        
        params = {
            "date": date_str,
            "league": league_id,
            "season": season
        }
        
        # Display the URL we're going to call
        url = f"{self.API_ENDPOINT_FIXTURES}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
        self.stdout.write(f"\n🔗 API URL: {url}")
        
        try:
            # Make the API request
            self.stdout.write("\nSending API request...")
            start_time = time.time()
            response = requests.get(
                self.API_ENDPOINT_FIXTURES,
                headers=headers,
                params=params,
                timeout=30
            )
            elapsed = time.time() - start_time
            
            # Check if the request was successful
            self.stdout.write(f"⏱️ Response time: {elapsed:.2f} seconds")
            self.stdout.write(f"📶 Status code: {response.status_code}")
            
            if response.status_code != 200:
                self.stderr.write(self.style.ERROR(f"❌ API error: {response.status_code} - {response.text}"))
                return
            
            # Parse the response
            data = response.json()
            
            # Print API errors if any
            if 'errors' in data and data['errors']:
                self.stderr.write(self.style.ERROR(f"❌ API errors:"))
                for error_key, error_msg in data['errors'].items():
                    self.stderr.write(self.style.ERROR(f"  - {error_key}: {error_msg}"))
                
                # Check specifically for plan restrictions
                if 'plan' in data['errors']:
                    plan_error = data['errors']['plan']
                    self.stderr.write(self.style.ERROR(f"\n⛔ FREE PLAN RESTRICTION: {plan_error}"))
                    if 'try from' in str(plan_error).lower():
                        self.stdout.write(self.style.WARNING(f"👉 This suggests you should try dates within the allowed range mentioned in the error."))
                    return
            
            # Display response metadata
            results_count = data.get('results', 0)
            self.stdout.write(f"\n📊 Results returned: {results_count}")
            
            # Print raw JSON if requested
            if show_raw:
                self.stdout.write(self.style.SUCCESS("\n📋 Raw API Response:"))
                self.stdout.write(json.dumps(data, indent=2))
            
            # Get the fixtures list
            fixtures = data.get('response', [])
            
            if not fixtures:
                self.stdout.write(self.style.WARNING(f"\n⚠️ No fixtures found for {date_str} with League ID {league_id} and Season {season}."))
                self.stdout.write(self.style.WARNING("This might be normal if there are genuinely no matches scheduled for this date."))
                return
            
            # Create a rich table for the fixtures
            console = Console()
            table = Table(show_header=True, header_style="bold")
            table.add_column("Fixture ID")
            table.add_column("Home Team")
            table.add_column("Away Team")
            table.add_column("Date/Time")
            table.add_column("Status")
            table.add_column("Venue")
            
            # Add fixtures to the table
            for fixture in fixtures:
                fixture_id = fixture['fixture']['id']
                home_team = fixture['teams']['home']['name']
                away_team = fixture['teams']['away']['name']
                match_date = fixture['fixture']['date']
                status = fixture['fixture']['status']['long']
                venue = fixture['fixture'].get('venue', {}).get('name', 'Unknown')
                
                table.add_row(
                    str(fixture_id),
                    home_team,
                    away_team,
                    match_date,
                    status,
                    venue
                )
            
            # Display the fixtures table
            self.stdout.write(self.style.SUCCESS(f"\n⚽ Fixtures for {date_str}:"))
            console.print(table)
            
            # Display a success summary
            self.stdout.write(self.style.SUCCESS(f"\n✅ SUCCESS: Found {len(fixtures)} fixtures for {date_str}"))
            self.stdout.write(self.style.SUCCESS(f"This confirms your API access is working correctly within the free tier constraints."))
            
            # Suggest next steps
            self.stdout.write(self.style.SUCCESS("\n🔧 Next steps:"))
            self.stdout.write("1. Try with different dates if needed")
            self.stdout.write(f"2. Run the main command: python manage.py fetch_liga1_fixtures --days=0 --season={season}")
            
        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f"❌ Error connecting to API: {str(e)}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Unexpected error: {str(e)}")) 