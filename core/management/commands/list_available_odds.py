import os
import time
import requests
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from dotenv import load_dotenv
from pathlib import Path

# Set up environment for API key
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)
API_KEY = os.getenv('API_FOOTBALL_KEY')

class Command(BaseCommand):
    help = 'Lists available odds for fixtures in Romanian Liga 1 over the past and next 7 days'

    API_HOST = 'v3.football.api-sports.io'
    API_ENDPOINT_ODDS = f'https://{API_HOST}/odds'
    LEAGUE_ID = 283  # Romanian Liga 1
    TARGET_BOOKMAKER = "Bet365"
    TARGET_MARKET = "Match Winner"
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to look back and forward from today'
        )
        parser.add_argument(
            '--league',
            type=int,
            default=283,
            help='League ID to check (default: 283 for Romanian Liga 1)'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed odds information'
        )

    def handle(self, *args, **options):
        days_range = options['days']
        league_id = options['league']
        detailed = options['detailed']
        
        self.LEAGUE_ID = league_id
        
        if not API_KEY:
            self.stderr.write(self.style.ERROR(
                f"API_FOOTBALL_KEY not found in environment variables or in .env file (expected at {dotenv_path}).\n"
                "Please ensure your .env file is in the project root (same level as manage.py) and contains API_FOOTBALL_KEY."
            ))
            return
            
        self.stdout.write(self.style.SUCCESS(f"API Key loaded. Checking odds for League ID {self.LEAGUE_ID} over {days_range*2+1} days..."))
        
        # Headers for API requests
        headers = {
            "x-apisports-key": API_KEY
        }
        
        # Generate date range (last 7 days to next 7 days)
        today = datetime.today().date()
        date_range = [today + timedelta(days=i) for i in range(-days_range, days_range + 1)]
        
        total_fixtures = 0
        fixtures_with_odds = 0
        fixtures_with_bet365 = 0
        fixtures_with_match_winner = 0
        fixtures_with_complete_odds = 0
        
        # Loop through each date
        for date in date_range:
            date_str = date.strftime('%Y-%m-%d')
            self.stdout.write(f"\nChecking fixtures for date: {date_str}")
            
            # Fetch fixtures for this date and league
            params = {
                'league': self.LEAGUE_ID,
                'date': date_str
            }
            
            try:
                # First, get fixtures for this date
                fixtures_response = requests.get(
                    f"https://{self.API_HOST}/fixtures", 
                    headers=headers, 
                    params=params, 
                    timeout=30
                )
                fixtures_data = fixtures_response.json()
                
                if fixtures_response.status_code != 200:
                    self.stderr.write(self.style.ERROR(f"API error: {fixtures_data.get('message', 'Unknown error')}"))
                    continue
                
                fixtures_list = fixtures_data.get('response', [])
                if not fixtures_list:
                    self.stdout.write(f"  No fixtures found for {date_str}")
                    continue
                
                self.stdout.write(f"  Found {len(fixtures_list)} fixtures for {date_str}")
                total_fixtures += len(fixtures_list)
                
                # Process each fixture
                for fixture in fixtures_list:
                    fixture_id = fixture['fixture']['id']
                    home_team = fixture['teams']['home']['name']
                    away_team = fixture['teams']['away']['name']
                    
                    self.stdout.write(f"\n  Checking odds for Fixture {fixture_id}: {home_team} vs {away_team}")
                    
                    # Fetch odds for this fixture
                    odds_params = {'fixture': fixture_id}
                    
                    # Throttle API requests
                    time.sleep(1)
                    
                    odds_response = requests.get(
                        self.API_ENDPOINT_ODDS, 
                        headers=headers, 
                        params=odds_params, 
                        timeout=30
                    )
                    odds_data = odds_response.json()
                    
                    if odds_response.status_code != 200:
                        self.stderr.write(self.style.ERROR(f"    API error: {odds_data.get('message', 'Unknown error')}"))
                        continue
                    
                    # Check if odds are available
                    odds_list = odds_data.get('response', [])
                    if not odds_list:
                        self.stdout.write(self.style.WARNING(f"    [✗] Fixture {fixture_id} - {home_team} vs {away_team}"))
                        self.stdout.write(self.style.WARNING(f"    No odds available"))
                        continue
                    
                    fixtures_with_odds += 1
                    
                    # Process odds data
                    fixture_odds = odds_list[0]
                    bookmakers = fixture_odds.get('bookmakers', [])
                    
                    # Check for Bet365
                    has_bet365 = False
                    has_match_winner = False
                    odds_home = None
                    odds_draw = None
                    odds_away = None
                    
                    for bookmaker in bookmakers:
                        if bookmaker.get('name') == self.TARGET_BOOKMAKER:
                            has_bet365 = True
                            fixtures_with_bet365 += 1
                            
                            # Check for Match Winner market
                            for bet in bookmaker.get('bets', []):
                                if bet.get('name') == self.TARGET_MARKET:
                                    has_match_winner = True
                                    fixtures_with_match_winner += 1
                                    
                                    # Extract odds
                                    for value in bet.get('values', []):
                                        if value.get('value') == 'Home':
                                            odds_home = value.get('odd')
                                        elif value.get('value') == 'Draw':
                                            odds_draw = value.get('odd')
                                        elif value.get('value') == 'Away':
                                            odds_away = value.get('odd')
                                    
                                    break
                            break
                    
                    # Output results for this fixture
                    status = "✓" if has_bet365 and has_match_winner else "✗"
                    
                    self.stdout.write(self.style.SUCCESS(f"    [{status}] Fixture {fixture_id} - {home_team} vs {away_team}"))
                    self.stdout.write(f"    Bet365: {'Yes' if has_bet365 else 'No'}")
                    
                    if has_bet365:
                        self.stdout.write(f"    Match Winner: {'Yes' if has_match_winner else 'No'}")
                        
                        if has_match_winner and odds_home and odds_draw and odds_away:
                            fixtures_with_complete_odds += 1
                            self.stdout.write(f"    Odds: H={odds_home} D={odds_draw} A={odds_away}")
                            
                            if detailed:
                                # Show all available bookmakers
                                self.stdout.write(f"    Available bookmakers ({len(bookmakers)}):")
                                bookmaker_names = [b.get('name') for b in bookmakers]
                                self.stdout.write(f"    {', '.join(bookmaker_names)}")
                                
                                # Show all available markets for Bet365
                                for bookmaker in bookmakers:
                                    if bookmaker.get('name') == self.TARGET_BOOKMAKER:
                                        bets = bookmaker.get('bets', [])
                                        self.stdout.write(f"    Bet365 markets ({len(bets)}):")
                                        market_names = [b.get('name') for b in bets]
                                        self.stdout.write(f"    {', '.join(market_names)}")
                                        break
            
            except requests.exceptions.RequestException as e:
                self.stderr.write(self.style.ERROR(f"Network error: {str(e)}"))
                continue
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Unexpected error: {str(e)}"))
                continue
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f"\n=== SUMMARY ==="))
        self.stdout.write(f"Total fixtures processed: {total_fixtures}")
        self.stdout.write(f"Fixtures with any odds data: {fixtures_with_odds} ({self._percentage(fixtures_with_odds, total_fixtures)}%)")
        self.stdout.write(f"Fixtures with {self.TARGET_BOOKMAKER}: {fixtures_with_bet365} ({self._percentage(fixtures_with_bet365, total_fixtures)}%)")
        self.stdout.write(f"Fixtures with {self.TARGET_BOOKMAKER}/{self.TARGET_MARKET}: {fixtures_with_match_winner} ({self._percentage(fixtures_with_match_winner, total_fixtures)}%)")
        self.stdout.write(f"Fixtures with complete H/D/A odds: {fixtures_with_complete_odds} ({self._percentage(fixtures_with_complete_odds, total_fixtures)}%)")
    
    def _percentage(self, part, whole):
        return round((part / whole * 100) if whole else 0, 1) 