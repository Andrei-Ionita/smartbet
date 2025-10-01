"""
Django management command to generate demo data for testing.
"""

import random
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Match, Team, League, OddsSnapshot, MatchMetadata

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate demo data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--matches',
            type=int,
            default=20,
            help='Number of matches to generate',
        )

    def handle(self, *args, **options):
        num_matches = options.get('matches')
        self.stdout.write(f"Generating {num_matches} demo matches...")
        
        # Create a league if none exists
        league, created = League.objects.get_or_create(
            name_en="Demo League",
            defaults={
                'name_ro': "Demo Liga",
                'country': "Romania",
                'api_id': 999,
                'slug': "demo-league"
            }
        )
        if created:
            self.stdout.write(f"Created league: {league}")
        
        # Create teams if they don't exist
        teams = []
        for i in range(1, 11):
            team, created = Team.objects.get_or_create(
                name_en=f"Demo Team {i}",
                defaults={
                    'name_ro': f"Demo Echipa {i}",
                    'slug': f"demo-team-{i}",
                    'api_id': 1000 + i
                }
            )
            if created:
                self.stdout.write(f"Created team: {team}")
            teams.append(team)
        
        # Generate matches
        matches_created = 0
        
        for i in range(num_matches):
            # Select random teams
            home_team = random.choice(teams)
            away_team = random.choice([t for t in teams if t != home_team])
            
            # Generate random date in the past
            days_ago = random.randint(1, 60)
            kickoff = timezone.now() - timedelta(days=days_ago)
            
            # Set the match as completed
            status = 'FT'
            
            # Generate random scores
            home_score = random.randint(0, 4)
            away_score = random.randint(0, 3)
            
            # Create the match
            match, created = Match.objects.get_or_create(
                home_team=home_team,
                away_team=away_team,
                kickoff=kickoff,
                defaults={
                    'league': league,
                    'status': status,
                    'home_score': home_score,
                    'away_score': away_score,
                    'api_ref': f"demo-{i}",
                    'venue': "Demo Stadium",
                    'avg_goals_home': 1.5 + random.random(),
                    'avg_goals_away': 1.2 + random.random(),
                    'avg_cards_home': 1.8 + random.random(),
                    'avg_cards_away': 2.1 + random.random(),
                    'team_form_home': 7.0 + 5 * random.random(),
                    'team_form_away': 6.0 + 5 * random.random(),
                    'injured_starters_home': random.randint(0, 3),
                    'injured_starters_away': random.randint(0, 3)
                }
            )
            
            if created:
                matches_created += 1
                
                # Create odds snapshot
                home_odds = 1.8 + random.random()
                draw_odds = 3.0 + random.random()
                away_odds = 3.5 + random.random()
                
                # Opening odds slightly different from current
                opening_odds_home = home_odds * (0.95 + 0.1 * random.random())
                opening_odds_draw = draw_odds * (0.95 + 0.1 * random.random())
                opening_odds_away = away_odds * (0.95 + 0.1 * random.random())
                
                # Closing odds same as current for this demo
                closing_odds_home = home_odds
                closing_odds_draw = draw_odds
                closing_odds_away = away_odds
                
                OddsSnapshot.objects.create(
                    match=match,
                    bookmaker="Demo Bookmaker",
                    odds_home=home_odds,
                    odds_draw=draw_odds,
                    odds_away=away_odds,
                    opening_odds_home=opening_odds_home,
                    opening_odds_draw=opening_odds_draw,
                    opening_odds_away=opening_odds_away,
                    closing_odds_home=closing_odds_home,
                    closing_odds_draw=closing_odds_draw,
                    closing_odds_away=closing_odds_away,
                    fetched_at=kickoff - timedelta(hours=1)
                )
                
                # Generate metadata
                metadata = {
                    "demo_data": True,
                    "home_injuries": [
                        {"player": {"name": "Player 1", "is_starter": True if match.injured_starters_home > 0 else False}},
                        {"player": {"name": "Player 2", "is_starter": True if match.injured_starters_home > 1 else False}}
                    ],
                    "away_injuries": [
                        {"player": {"name": "Player A", "is_starter": True if match.injured_starters_away > 0 else False}},
                        {"player": {"name": "Player B", "is_starter": True if match.injured_starters_away > 1 else False}}
                    ]
                }
                
                MatchMetadata.objects.create(
                    match=match,
                    data=metadata
                )
        
        self.stdout.write(self.style.SUCCESS(f"Successfully created {matches_created} demo matches"))
        self.stdout.write("You can now run:")
        self.stdout.write("  python manage.py generate_training_data")
        self.stdout.write("  python manage.py train_smartbet_model") 