"""
Command to test the match score generation pipeline.
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Match, MatchScoreModel
from predictor.scoring_model import generate_match_scores, store_match_scores

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test the match score generation pipeline'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=5,
            help='Number of matches to process (default: 5)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )
        
    def handle(self, *args, **options):
        limit = options['limit']
        verbose = options['verbose']
        
        # Find upcoming matches with odds
        upcoming_matches = Match.objects.filter(
            kickoff__gte=timezone.now(),
            odds_snapshots__isnull=False
        ).distinct()[:limit]
        
        self.stdout.write(f"Found {upcoming_matches.count()} upcoming matches with odds")
        
        if not upcoming_matches.exists():
            self.stdout.write(self.style.WARNING("No upcoming matches with odds found"))
            self.stdout.write("Creating a test match...")
            
            # Use create_test_match command logic to create a test match
            from django.core.management import call_command
            call_command('create_test_match', days=1)
            
            # Retry finding matches
            upcoming_matches = Match.objects.filter(
                kickoff__gte=timezone.now(),
                odds_snapshots__isnull=False
            ).distinct()[:limit]
            
            if not upcoming_matches.exists():
                self.stdout.write(self.style.ERROR("Still no matches available after creating a test match"))
                return
        
        # Generate scores
        self.stdout.write(f"Generating scores for {upcoming_matches.count()} matches")
        scores = generate_match_scores(list(upcoming_matches))
        
        # Print results before saving
        self.stdout.write("\n=== Generated Scores ===")
        for score in scores:
            match = next((m for m in upcoming_matches if m.api_ref == score.fixture_id or str(m.id) == score.fixture_id), None)
            if match:
                self.stdout.write(f"{match} | Home: {score.home_team_score:.2f} | Away: {score.away_team_score:.2f} | Confidence: {score.confidence_level}")
            else:
                self.stdout.write(f"Match not found for fixture ID: {score.fixture_id}")
        
        # Save to DB
        try:
            store_match_scores(scores)
            self.stdout.write(self.style.SUCCESS(f"Successfully stored {len(scores)} match scores"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error storing match scores: {e}"))
            return
        
        # Verify storage
        self.stdout.write("\n=== Stored Scores ===")
        for score in MatchScoreModel.objects.order_by("-generated_at")[:limit]:
            self.stdout.write(f"{score.match} → {score.predicted_outcome} | Home: {score.home_team_score:.2f} | Away: {score.away_team_score:.2f} | Confidence: {score.confidence_level}") 