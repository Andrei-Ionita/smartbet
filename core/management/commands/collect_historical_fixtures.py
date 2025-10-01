from django.core.management.base import BaseCommand
from rich.console import Console
import os
import requests
import time
import csv
from datetime import datetime

console = Console()

LEAGUE_CONFIG = {
    'Premier League': {'country': 'England', 'id': 8},
    'La Liga': {'country': 'Spain', 'id': 564},
    'Serie A': {'country': 'Italy', 'id': 384},
    'Bundesliga': {'country': 'Germany', 'id': 82},
    'Ligue 1': {'country': 'France', 'id': 301},
    'Liga I': {'country': 'Romania', 'id': 271}
}

def load_env_vars():
    """Load environment variables from .env file"""
    env_vars = {}
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except FileNotFoundError:
        console.print("[bold red].env file not found[/bold red]")
    return env_vars

class Command(BaseCommand):
    help = 'Fetches historical fixture data from SportMonks API for specified leagues and seasons.'

    def handle(self, *args, **options):
        env_vars = load_env_vars()
        api_token = env_vars.get('SPORTMONKS_API_TOKEN')
        
        if not api_token:
            console.print("[bold red]SPORTMONKS_API_TOKEN not found in .env file.[/bold red]")
            return

        base_url = "https://api.sportmonks.com/v3/football"
        all_fixtures_data = []

        for league_name, config in LEAGUE_CONFIG.items():
            league_id = config['id']
            console.print(f"[bold cyan]Fetching seasons for {league_name} (ID: {league_id})...[/bold cyan]")
            
            seasons_url = f"{base_url}/seasons?api_token={api_token}&league_id={league_id}&per_page=50"
            try:
                seasons_response = requests.get(seasons_url)
                seasons_response.raise_for_status()
                seasons = seasons_response.json().get('data', [])
            except requests.exceptions.RequestException as e:
                console.print(f"[bold red]Error fetching seasons for {league_name}: {e}[/bold red]")
                continue

            target_seasons = [
                s for s in seasons 
                if not s.get('is_current') and s.get('starting_at') and 
                '2021' <= s.get('starting_at', '')[:4] <= '2024'
            ]
            
            console.print(f"Found {len(target_seasons)} target seasons for {league_name} between 2021-2024.")

            for season in target_seasons:
                season_id = season['id']
                season_name = season['name']
                console.print(f"  [green]Fetching fixtures for season: {season_name} (ID: {season_id})[/green]")
                
                page = 1
                fixtures_fetched_count = 0
                
                while True:
                    fixtures_url = (
                        f"{base_url}/fixtures"
                        f"?api_token={api_token}"
                        f"&season_id={season_id}"
                        f"&include=scores;participants"
                        f"&per_page=50"
                        f"&page={page}"
                    )
                    
                    try:
                        time.sleep(0.6) # Rate limiting
                        fixtures_response = requests.get(fixtures_url)
                        fixtures_response.raise_for_status()
                        response_data = fixtures_response.json()
                        fixtures = response_data.get('data', [])

                        if not fixtures:
                            console.print(f"    No more fixtures found for season {season_name} on page {page}.")
                            break
                        
                        fixtures_fetched_count += len(fixtures)

                        for fixture in fixtures:
                            home_team = next((p for p in fixture.get('participants', []) if p.get('meta', {}).get('location') == 'home'), {})
                            away_team = next((p for p in fixture.get('participants', []) if p.get('meta', {}).get('location') == 'away'), {})
                            
                            home_goals, away_goals = None, None
                            for score_item in fixture.get('scores', []):
                                if score_item.get('description') == 'CURRENT':
                                    participant = score_item.get('score', {}).get('participant')
                                    goals = score_item.get('score', {}).get('goals')
                                    if participant == 'home':
                                        home_goals = goals
                                    elif participant == 'away':
                                        away_goals = goals

                            outcome = None
                            if home_goals is not None and away_goals is not None:
                                if home_goals > away_goals:
                                    outcome = 'home'
                                elif home_goals < away_goals:
                                    outcome = 'away'
                                else:
                                    outcome = 'draw'

                            fixture_data = {
                                'fixture_id': fixture.get('id'),
                                'league_id': fixture.get('league_id'),
                                'season_id': fixture.get('season_id'),
                                'home_team_id': home_team.get('id'),
                                'home_team_name': home_team.get('name'),
                                'away_team_id': away_team.get('id'),
                                'away_team_name': away_team.get('name'),
                                'kickoff': fixture.get('starting_at'),
                                'home_score': home_goals,
                                'away_score': away_goals,
                                'outcome': outcome
                            }
                            all_fixtures_data.append(fixture_data)
                        
                        pagination = response_data.get('pagination', {})
                        if not pagination.get('has_more'):
                            break
                            
                        page += 1

                    except requests.exceptions.RequestException as e:
                        console.print(f"[bold red]    API Error fetching fixtures for season {season_name}: {e}[/bold red]")
                        break

                console.print(f"  [bold green]SUCCESS:[/bold green] Fetched {fixtures_fetched_count} fixtures for season {season_name}.")

        output_filename = 'historical_fixtures.csv'
        if all_fixtures_data:
            console.print(f"\n[bold yellow]Writing {len(all_fixtures_data)} total fixtures to {output_filename}...[/bold yellow]")
            with open(output_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=all_fixtures_data[0].keys())
                writer.writeheader()
                writer.writerows(all_fixtures_data)
            console.print("[bold blue]Data collection complete.[/bold blue]")
        else:
            console.print("[bold red]No fixtures were collected.[/bold red]") 