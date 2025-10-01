"""
Command to generate and store match scores for all upcoming matches with valid odds.
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q

from core.models import Match, OddsSnapshot
from predictor.scoring_model import generate_match_scores, store_match_scores

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate and store match scores for all upcoming matches with valid odds'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days ahead to look for matches (default: 7)'
        )
        
    def handle(self, *args, **options):
        days_ahead = options['days']
        
        self.stdout.write(self.style.NOTICE(f"Generating scores for upcoming matches with odds"))
        self.stdout.write(f"Looking for matches in the next {days_ahead} days")
        
        # Find upcoming matches with valid odds
        from_date = timezone.now()
        to_date = from_date + timezone.timedelta(days=days_ahead)
        
        matches = Match.objects.filter(
            status="NS",  # Not Started
            kickoff__gte=from_date,
            kickoff__lte=to_date,
            odds_snapshots__bookmaker="Bet365",
            odds_snapshots__odds_home__isnull=False,
            odds_snapshots__odds_draw__isnull=False,
            odds_snapshots__odds_away__isnull=False
        ).distinct()
        
        total_matches = matches.count()
        
        if total_matches == 0:
            self.stdout.write(self.style.WARNING("No upcoming matches with valid odds found"))
            return
        
        self.stdout.write(self.style.SUCCESS(f"Found {total_matches} upcoming matches with valid odds"))
        
        # Display matches to process
        self.stdout.write(self.style.NOTICE("\nMatches to process:"))
        for i, match in enumerate(matches):
            odds = match.odds_snapshots.filter(bookmaker="Bet365").order_by('-fetched_at').first()
            odds_str = f" (Odds: H={odds.odds_home}, D={odds.odds_draw}, A={odds.odds_away})" if odds else ""
            self.stdout.write(f"{i+1}. {match}{odds_str} [{match.kickoff.strftime('%Y-%m-%d %H:%M')}]")
        
        # Process each match individually to handle errors gracefully
        scores_stored = 0
        matches_skipped = 0
        
        for match in matches:
            try:
                self.stdout.write(f"Processing: {match}")
                
                # Generate scores for this match
                match_scores = generate_match_scores([match])
                
                if not match_scores:
                    self.stdout.write(self.style.WARNING(f"No scores generated for {match} - skipping"))
                    matches_skipped += 1
                    continue
                
                # Store the scores
                store_match_scores(match_scores)
                scores_stored += len(match_scores)
                
                self.stdout.write(self.style.SUCCESS(f"Successfully scored {match}"))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing match {match}: {e}"))
                logger.error(f"Error processing match {match.id}: {e}")
                matches_skipped += 1
        
        # Print summary
        self.stdout.write(self.style.NOTICE("\n=== Score Generation Summary ==="))
        self.stdout.write(f"Total matches processed: {total_matches}")
        self.stdout.write(f"Scores stored: {scores_stored}")
        
        if matches_skipped > 0:
            self.stdout.write(self.style.WARNING(f"Matches skipped due to errors: {matches_skipped}"))
        else:
            self.stdout.write(self.style.SUCCESS("All matches processed successfully")) 