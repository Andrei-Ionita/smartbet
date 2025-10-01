import os
import requests
from datetime import date, timedelta, datetime as dt_datetime
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction
from dotenv import load_dotenv

# Assuming your models are in 'core.models'
# Ensure your project is in PYTHONPATH or use relative imports if appropriate
# from ....core.models import Match, Team, League # Example for deeper structures
# For a typical Django app structure, this should work:
from core.models import Match, Team, League

load_dotenv()
API_FOOTBALL_KEY = os.environ.get('API_FOOTBALL_KEY')

class Command(BaseCommand):
    help = 'Fetches match fixtures from API-FOOTBALL for a specified period and updates the database.'

    API_HOST = 'v3.football.api-sports.io'
    API_ENDPOINT_FIXTURES = f'https://{API_HOST}/fixtures'
    LEAGUE_ID = 283  # Romanian Liga I
    SEASON = 2022    # Target season for historical data

    def handle(self, *args, **options):
        api_key = API_FOOTBALL_KEY # Use the globally loaded key
        if not api_key:
            # Attempt to load again if not found, or if run in a context where global load didn't happen
            load_dotenv() 
            api_key = os.environ.get('API_FOOTBALL_KEY')
            if not api_key:
                raise CommandError("API_FOOTBALL_KEY environment variable not set.")

        from_date_str = '2022-08-01'
        to_date_str = '2022-08-15'
        
        params = {
            'league': str(self.LEAGUE_ID),
            'season': str(self.SEASON),
            'from': from_date_str,
            'to': to_date_str
        }
        
        headers = {
            'x-rapidapi-key': api_key,
            'x-rapidapi-host': self.API_HOST
        }

        self.stdout.write(f"Fetching fixtures from {params['from']} to {params['to']} for league {self.LEAGUE_ID}, season {self.SEASON}...")

        try:
            response = requests.get(self.API_ENDPOINT_FIXTURES, headers=headers, params=params, timeout=30)
            response.raise_for_status()  # Raise an exception for HTTP errors
        except requests.exceptions.RequestException as e:
            raise CommandError(f"API request failed: {e}")

        response_data = response.json()

        if not response_data.get('response'):
            self.stdout.write(self.style.WARNING("No fixtures found in API response for the given period."))
            if response_data.get('errors'):
                 self.stderr.write(f"API Errors: {response_data.get('errors')}")
            return

        fixtures_data = response_data['response']
        
        first_league = League.objects.first()
        if not first_league:
            raise CommandError("No leagues found in the database. Please add at least one league (e.g., Romanian Liga I) first.")
        self.stdout.write(f"Using league: {first_league.name_ro} (ID: {first_league.id}) for all fetched matches.")

        inserted_count = 0
        updated_count = 0

        with transaction.atomic():
            for item in fixtures_data:
                fixture_details = item.get('fixture', {})
                teams_details = item.get('teams', {})
                
                api_ref = str(fixture_details.get('id'))
                kickoff_str = fixture_details.get('date')
                status_short = fixture_details.get('status', {}).get('short')

                raw_home_team_name = teams_details.get('home', {}).get('name')
                raw_away_team_name = teams_details.get('away', {}).get('name')

                if not all([api_ref, kickoff_str, status_short, raw_home_team_name, raw_away_team_name]):
                    self.stderr.write(f"Skipping fixture with API ref {api_ref} due to missing essential data.")
                    continue
                
                try:
                    # API dates are typically ISO8601 with timezone
                    kickoff_datetime = dt_datetime.fromisoformat(kickoff_str)
                except ValueError:
                    self.stderr.write(f"Could not parse kickoff date '{kickoff_str}' for fixture {api_ref}. Skipping.")
                    continue

                home_team_slug = raw_home_team_name.lower().replace(' ', '-')
                away_team_slug = raw_away_team_name.lower().replace(' ', '-')

                home_team, home_created = Team.objects.get_or_create(
                    slug=home_team_slug,
                    defaults={'name_ro': raw_home_team_name, 'name_en': raw_home_team_name}
                )
                if home_created:
                    self.stdout.write(f"Created new team: {raw_home_team_name} (slug: {home_team_slug})")

                away_team, away_created = Team.objects.get_or_create(
                    slug=away_team_slug,
                    defaults={'name_ro': raw_away_team_name, 'name_en': raw_away_team_name}
                )
                if away_created:
                    self.stdout.write(f"Created new team: {raw_away_team_name} (slug: {away_team_slug})")
                
                match_defaults = {
                    'league': first_league,
                    'home_team': home_team,
                    'away_team': away_team,
                    'kickoff': kickoff_datetime,
                    'status': status_short,
                }
                
                match, created = Match.objects.update_or_create(
                    api_ref=api_ref,
                    defaults=match_defaults
                )
                
                if created:
                    inserted_count += 1
                else:
                    updated_count += 1
            
        self.stdout.write(self.style.SUCCESS(f"Successfully processed fixtures. Inserted: {inserted_count}, Updated: {updated_count} matches.")) 