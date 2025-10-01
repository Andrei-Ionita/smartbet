"""
Command to generate match scores for upcoming matches and store them in the database.

This command fetches all upcoming matches with odds and generates prediction scores,
then stores those scores in the database.
"""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import IntegrityError

from core.models import Match, MatchScoreModel
from predictor.scoring_model import generate_match_scores, store_match_scores

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate and store prediction scores for upcoming matches'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days ahead to generate scores for (default: 7)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration of scores even if they already exist'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about the scores being generated'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Calculate scores but do not store them in the database'
        )
        parser.add_argument(
            '--source',
            type=str,
            default='basic_model_v1',
            help='Source identifier for the generated scores (default: basic_model_v1)'
        )
        parser.add_argument(
            '--include-past',
            action='store_true',
            help='Include past matches (useful for testing with historical data)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit the number of matches to process (0 = no limit)'
        )
        
    def handle(self, *args, **options):
        days_ahead = options['days']
        force = options['force']
        verbose = options['verbose']
        dry_run = options['dry_run']
        source = options['source']
        include_past = options['include_past']
        limit = options['limit']
        
        # Calculate the time range for upcoming matches
        now = timezone.now()
        end_date = now + timedelta(days=days_ahead)
        
        self.stdout.write(f"Generating match scores for fixtures between {now.date()} and {end_date.date()}")
        
        # Get upcoming matches
        if include_past:
            self.stdout.write(self.style.WARNING("Including past matches for testing purposes"))
            # Get all matches, with a starting date 30 days in the past
            past_date = now - timedelta(days=30)
            matches_query = Match.objects.filter(
                kickoff__gte=past_date
            )
        else:
            # Get only upcoming matches
            matches_query = Match.objects.filter(
                kickoff__gte=now,
                kickoff__lte=end_date
            )
            
        # Apply limit if specified
        if limit > 0:
            matches_query = matches_query[:limit]
            
        upcoming_matches = matches_query
        
        if verbose:
            time_range = "in the next 30 days" if include_past else f"in the next {days_ahead} days"
            self.stdout.write(f"Found {upcoming_matches.count()} matches {time_range}")
        
        # Filter out matches that already have scores, unless force is True
        if not force:
            matches_with_scores = MatchScoreModel.objects.filter(
                match__in=upcoming_matches
            ).values_list('match_id', flat=True)
            
            upcoming_matches = upcoming_matches.exclude(id__in=matches_with_scores)
            if verbose:
                self.stdout.write(f"After filtering out matches with existing scores: {upcoming_matches.count()} matches")
        
        if not upcoming_matches.exists():
            self.stdout.write(self.style.WARNING("No matches found that need scores generated"))
            
            # Special case for demo/testing - if there are no matches at all, create a mock match
            if Match.objects.count() == 0 and include_past:
                self.stdout.write(self.style.WARNING("No matches found in the database. Creating a mock match for testing."))
                
                # Import models needed for creating a mock match
                from core.models import Team, League
                
                # Create teams if needed
                home_team, _ = Team.objects.get_or_create(
                    name_ro="Test Home Team",
                    name_en="Test Home Team",
                    slug="test-home-team"
                )
                
                away_team, _ = Team.objects.get_or_create(
                    name_ro="Test Away Team",
                    name_en="Test Away Team",
                    slug="test-away-team"
                )
                
                # Create league if needed
                league, _ = League.objects.get_or_create(
                    name_ro="Test League",
                    name_en="Test League",
                    country="Romania"
                )
                
                # Create match
                match = Match.objects.create(
                    league=league,
                    home_team=home_team,
                    away_team=away_team,
                    kickoff=now + timedelta(days=1),
                    status="NS",
                    api_ref="test_match_123"
                )
                
                # Create odds
                from core.models import OddsSnapshot
                OddsSnapshot.objects.create(
                    match=match,
                    bookmaker="Bet365",
                    odds_home=1.5,
                    odds_draw=3.5,
                    odds_away=5.5,
                    fetched_at=now
                )
                
                self.stdout.write(self.style.SUCCESS(f"Created mock match: {match}"))
                upcoming_matches = Match.objects.filter(id=match.id)
            else:
                return
        
        # Filter matches to only include those with odds
        matches_with_odds = []
        for match in upcoming_matches:
            if match.odds_snapshots.exists():
                matches_with_odds.append(match)
            elif verbose:
                self.stdout.write(f"Skipping match {match.id} ({match}) - no odds")
        
        if verbose:
            self.stdout.write(f"Found {len(matches_with_odds)} matches with odds")
        
        if not matches_with_odds:
            self.stdout.write(self.style.WARNING("No matches with odds found"))
            return
        
        # Generate scores for the matches
        self.stdout.write(f"Generating scores for {len(matches_with_odds)} matches")
        scores = generate_match_scores(matches_with_odds)
        
        if verbose:
            for i, score in enumerate(scores):
                self.stdout.write(f"\nScore {i+1}:")
                match = next((m for m in matches_with_odds if m.api_ref == score.fixture_id or str(m.id) == score.fixture_id), None)
                if match:
                    self.stdout.write(f"  Match: {match.home_team} vs {match.away_team} ({match.kickoff})")
                self.stdout.write(f"  Fixture ID: {score.fixture_id}")
                self.stdout.write(f"  Home Score: {score.home_team_score}")
                self.stdout.write(f"  Away Score: {score.away_team_score}")
                self.stdout.write(f"  Confidence: {score.confidence_level}")
        
        # Store the scores in the database
        if not dry_run:
            self.stdout.write(f"Storing {len(scores)} scores in the database")
            try:
                store_match_scores(scores)
                self.stdout.write(self.style.SUCCESS(f"Successfully stored {len(scores)} scores in the database"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error storing scores: {e}"))
        else:
            self.stdout.write(self.style.WARNING("Dry run - scores not stored in the database"))
            if verbose:
                self.stdout.write(f"Would have stored {len(scores)} scores")
        
        # Print summary
        self.stdout.write("\nSummary:")
        self.stdout.write(f"  - {upcoming_matches.count()} matches in selected time period")
        self.stdout.write(f"  - {len(matches_with_odds)} matches with odds")
        self.stdout.write(f"  - {len(scores)} scores generated")
        if not dry_run:
            self.stdout.write(f"  - {len(scores)} scores stored in the database") 