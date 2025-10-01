"""
Command to create a test match for testing the scoring system.
"""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Match, Team, League, OddsSnapshot

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Create a test match for scoring'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Days in the future for the test match (default: 1)'
        )
        
    def handle(self, *args, **options):
        days_ahead = options['days']
        now = timezone.now()
        kickoff_time = now + timedelta(days=days_ahead)
        
        # Create teams if needed
        home_team, home_created = Team.objects.get_or_create(
            name_ro="Test Home Team",
            defaults={
                'name_en': "Test Home Team",
                'slug': "test-home-team"
            }
        )
        
        away_team, away_created = Team.objects.get_or_create(
            name_ro="Test Away Team",
            defaults={
                'name_en': "Test Away Team",
                'slug': "test-away-team"
            }
        )
        
        if home_created:
            self.stdout.write(f"Created home team: {home_team}")
        if away_created:
            self.stdout.write(f"Created away team: {away_team}")
        
        # Create league if needed
        league, league_created = League.objects.get_or_create(
            name_ro="Test League",
            defaults={
                'name_en': "Test League",
                'country': "Romania"
            }
        )
        
        if league_created:
            self.stdout.write(f"Created league: {league}")
        
        # Create match with a unique API ref based on timestamp
        api_ref = f"test_match_{int(now.timestamp())}"
        match = Match.objects.create(
            league=league,
            home_team=home_team,
            away_team=away_team,
            kickoff=kickoff_time,
            status="NS",  # Not Started
            api_ref=api_ref
        )
        
        self.stdout.write(self.style.SUCCESS(f"Created test match: {match} (ID: {match.id}, API Ref: {api_ref})"))
        
        # Add odds
        odds = OddsSnapshot.objects.create(
            match=match,
            bookmaker="Bet365",
            odds_home=1.5,
            odds_draw=3.5,
            odds_away=5.5,
            fetched_at=now
        )
        
        self.stdout.write(self.style.SUCCESS(f"Added odds for match: Home={odds.odds_home}, Draw={odds.odds_draw}, Away={odds.odds_away}"))
        
        # Suggest command to generate scores
        self.stdout.write("\nTo generate scores for this match, run:")
        self.stdout.write(f"python manage.py generate_match_scores --verbose") 