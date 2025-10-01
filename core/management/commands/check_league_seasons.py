import os
import requests
from datetime import datetime
from django.core.management.base import BaseCommand
from dotenv import load_dotenv
from pathlib import Path
import time
from rich.console import Console
from rich.table import Table
import calendar

# Set up environment for API key
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)
API_KEY = os.getenv('API_FOOTBALL_KEY')

class Command(BaseCommand):
    help = 'Checks available seasons for Romania Liga 1 (league ID 283) to identify which covers May 2025'

    API_HOST = 'v3.football.api-sports.io'
    API_ENDPOINT_LEAGUES = f'https://{API_HOST}/leagues'
    TARGET_LEAGUE_ID = 283  # Romanian Liga 1
    TARGET_DATE = "2025-05-15"  # Date we're trying to find fixtures for
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--league',
            type=int,
            default=self.TARGET_LEAGUE_ID,
            help='League ID to check (default: 283 for Romanian Liga 1)'
        )
        parser.add_argument(
            '--date',
            type=str,
            default=self.TARGET_DATE,
            help='Target date to check season coverage for (format: YYYY-MM-DD)'
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Display raw JSON response'
        )

    def handle(self, *args, **options):
        league_id = options['league']
        target_date = options['date']
        show_json = options['json']
        
        # Try to parse the target date
        try:
            target_date_obj = datetime.strptime(target_date, "%Y-%m-%d")
            target_year = target_date_obj.year
            target_month = target_date_obj.month
            target_month_name = calendar.month_name[target_month]
        except ValueError:
            self.stderr.write(self.style.ERROR(f"Invalid date format: {target_date}. Please use YYYY-MM-DD."))
            return
        
        self.stdout.write(self.style.SUCCESS(f"🔍 Checking seasons available for League ID: {league_id}"))
        self.stdout.write(self.style.SUCCESS(f"📅 Target date: {target_date} ({target_month_name} {target_year})"))
        
        if not API_KEY:
            self.stderr.write(self.style.ERROR(
                f"API_FOOTBALL_KEY not found in environment variables or in .env file (expected at {dotenv_path}).\n"
                "Please ensure your .env file is in the project root (same level as manage.py) and contains API_FOOTBALL_KEY."
            ))
            return
        
        # Headers for API requests
        headers = {
            "x-apisports-key": API_KEY
        }
        
        # Parameters for the API request
        params = {
            'id': league_id
        }
        
        try:
            # Make the API request
            self.stdout.write("Fetching league information...")
            response = requests.get(
                self.API_ENDPOINT_LEAGUES,
                headers=headers,
                params=params,
                timeout=30
            )
            
            # Check if request was successful
            if response.status_code != 200:
                self.stderr.write(self.style.ERROR(f"API error: {response.status_code} - {response.text}"))
                return
            
            # Parse the response
            data = response.json()
            
            # Print raw JSON if requested
            if show_json:
                self.stdout.write(self.style.SUCCESS("Raw API Response:"))
                import json
                self.stdout.write(json.dumps(data, indent=2))
            
            # Check if we got any response data
            if not data.get('response'):
                self.stderr.write(self.style.ERROR(f"No data found for league ID {league_id}"))
                return
            
            # Extract the league information
            league_data = data['response'][0]
            league_name = league_data['league']['name']
            country = league_data['country']['name']
            
            self.stdout.write(self.style.SUCCESS(f"\n📊 League Information:"))
            self.stdout.write(f"  Name: {league_name}")
            self.stdout.write(f"  Country: {country}")
            self.stdout.write(f"  ID: {league_id}")
            
            # Extract and display the seasons information
            seasons = league_data.get('seasons', [])
            
            if not seasons:
                self.stdout.write(self.style.WARNING(f"No seasons data found for league {league_name}"))
                return
            
            # Use rich to create a nice table
            console = Console()
            table = Table(show_header=True, header_style="bold")
            table.add_column("Season ID", style="dim")
            table.add_column("Start Date")
            table.add_column("End Date")
            table.add_column("Coverage")
            table.add_column("Status")
            table.add_column(f"Covers {target_month_name} {target_year}")
            
            self.stdout.write(self.style.SUCCESS(f"\n🗓️ Available Seasons:"))
            seasons.sort(key=lambda x: x.get('year', 0), reverse=True)
            
            # Flag to track if we've found a season for our target date
            found_season_for_target = False
            
            for season in seasons:
                year = season.get('year')
                current = season.get('current', False)
                start_date = season.get('start')
                end_date = season.get('end')
                
                # Try to parse the dates
                try:
                    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
                    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                    
                    coverage = f"{start_date_obj.strftime('%b %Y')} → {end_date_obj.strftime('%b %Y')}"
                    
                    # Check if this season covers our target date
                    covers_target = start_date_obj <= target_date_obj <= end_date_obj
                    if covers_target:
                        found_season_for_target = True
                    
                    # Add a row to the table
                    status = "✅ CURRENT" if current else "PAST"
                    covers = "✓ YES" if covers_target else "✗ NO"
                    
                    table.add_row(
                        str(year),
                        start_date,
                        end_date,
                        coverage,
                        status,
                        covers
                    )
                    
                except ValueError:
                    # Handle date parsing errors
                    table.add_row(
                        str(year),
                        start_date or "Unknown",
                        end_date or "Unknown",
                        "Date parsing error",
                        "CURRENT" if current else "PAST",
                        "Unknown"
                    )
            
            # Display the table
            console.print(table)
            
            # Display a summary
            self.stdout.write("\n🔍 Summary:")
            if found_season_for_target:
                self.stdout.write(self.style.SUCCESS(f"✅ Found at least one season that covers {target_date} ({target_month_name} {target_year})"))
                appropriate_seasons = [s for s in seasons if 
                                     datetime.strptime(s.get('start'), "%Y-%m-%d") <= target_date_obj <= 
                                     datetime.strptime(s.get('end'), "%Y-%m-%d")]
                
                for season in appropriate_seasons:
                    self.stdout.write(self.style.SUCCESS(
                        f"  - Use season={season['year']} to fetch fixtures for {target_date} "
                        f"(Coverage: {season['start']} → {season['end']})"
                    ))
            else:
                self.stdout.write(self.style.ERROR(
                    f"❌ No season found that covers {target_date} ({target_month_name} {target_year}).\n"
                    f"This might indicate that fixture data for this period is not yet available in the API."
                ))
            
            # Show command to run
            self.stdout.write("\n🔧 Suggested command:")
            if found_season_for_target:
                self.stdout.write(
                    f"python manage.py fetch_liga1_fixtures --season={appropriate_seasons[0]['year']}"
                )
            else:
                self.stdout.write(
                    f"python manage.py fetch_liga1_fixtures --season={seasons[0]['year']} --check-seasons"
                )
                
        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f"Error connecting to API: {str(e)}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Unexpected error: {str(e)}")) 