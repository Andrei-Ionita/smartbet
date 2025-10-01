"""
Command to test the score generation and storage pipeline.
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Match
from predictor.scoring_model import generate_match_scores, store_match_scores

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test the match score generation and storage pipeline'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=5,
            help='Number of matches to process (default: 5)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update of existing scores'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days ahead to look for matches (default: 7)'
        )
        
    def handle(self, *args, **options):
        limit = options['limit']
        force = options['force']
        days_ahead = options['days']
        
        self.stdout.write(self.style.NOTICE(f"Testing match score generation and storage pipeline"))
        self.stdout.write(f"Looking for matches in the next {days_ahead} days, limit: {limit}")
        
        # Find upcoming matches with odds
        from_date = timezone.now()
        to_date = from_date + timezone.timedelta(days=days_ahead)
        
        matches = Match.objects.filter(
            kickoff__gte=from_date,
            kickoff__lte=to_date,
            odds_snapshots__isnull=False
        ).distinct()[:limit]
        
        self.stdout.write(f"Found {matches.count()} upcoming matches with odds")
        
        if not matches.exists():
            self.stdout.write(self.style.WARNING("No upcoming matches with odds found. Creating a test match..."))
            
            # Create a test match if none exists
            from django.core.management import call_command
            call_command('create_test_match', days=1)
            
            # Try again
            matches = Match.objects.filter(
                kickoff__gte=from_date,
                odds_snapshots__isnull=False
            ).distinct()[:limit]
            
            if not matches.exists():
                self.stdout.write(self.style.ERROR("Still no matches available for testing"))
                return
        
        # Display matches to process
        self.stdout.write(self.style.NOTICE("\nMatches to process:"))
        for i, match in enumerate(matches):
            odds = match.odds_snapshots.order_by('-fetched_at').first()
            odds_str = f" (Odds: H={odds.odds_home}, D={odds.odds_draw}, A={odds.odds_away})" if odds else ""
            self.stdout.write(f"{i+1}. {match}{odds_str}")
        
        # Generate scores
        self.stdout.write(self.style.NOTICE("\nGenerating scores..."))
        scores = generate_match_scores(matches)
        
        if not scores:
            self.stdout.write(self.style.ERROR("No scores were generated!"))
            return
            
        # Print generated scores
        self.stdout.write(self.style.NOTICE("\nGenerated scores:"))
        for i, score in enumerate(scores):
            match = next((m for m in matches if m.api_ref == score.fixture_id or str(m.id) == score.fixture_id), None)
            match_str = str(match) if match else f"Unknown match ({score.fixture_id})"
            
            self.stdout.write(f"{i+1}. {match_str}")
            self.stdout.write(f"   Home Score: {score.home_team_score:.2f}")
            self.stdout.write(f"   Away Score: {score.away_team_score:.2f}")
            self.stdout.write(f"   Confidence: {score.confidence_level}")
            
            # Determine outcome
            if score.home_team_score > score.away_team_score:
                outcome = "HOME WIN"
            elif score.away_team_score > score.home_team_score:
                outcome = "AWAY WIN"
            else:
                outcome = "DRAW"
            self.stdout.write(f"   Predicted Outcome: {outcome}")
        
        # Store scores
        self.stdout.write(self.style.NOTICE("\nStoring scores in database..."))
        store_match_scores(scores)
        
        self.stdout.write(self.style.SUCCESS("\nTest completed successfully!")) 