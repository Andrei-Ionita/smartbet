"""
Test Django management command for the MatchScoreModel implementation.
This is a management command version of the test script that can be run directly.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count

from core.models import Match, MatchScoreModel, OddsSnapshot
from predictor.scoring_model import generate_match_scores, store_match_scores

class Command(BaseCommand):
    help = 'Test storing match scores in the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Test with all matches instead of just recent ones'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=5,
            help='Limit the number of matches to process'
        )

    def handle(self, *args, **options):
        use_all = options['all']
        limit = options['limit']
        
        # Find matches to test with
        if use_all:
            # Use all matches that have odds
            matches_with_odds = Match.objects.filter(
                odds_snapshots__isnull=False
            ).distinct()[:limit]
            self.stdout.write(f"Looking for any matches with odds (limit: {limit})")
        else:
            # Just use recent matches
            past_date = timezone.now() - timedelta(days=30)
            matches_with_odds = Match.objects.filter(
                kickoff__gte=past_date,
                odds_snapshots__isnull=False
            ).distinct()[:limit]
            self.stdout.write(f"Looking for matches in the last 30 days with odds (limit: {limit})")

        self.stdout.write(f"Found {matches_with_odds.count()} matches to test with")
        
        # If we found no matches, try a different approach
        if matches_with_odds.count() == 0:
            # Find any matches with odds
            matches_with_odds = Match.objects.filter(
                odds_snapshots__isnull=False
            ).distinct()[:limit]
            self.stdout.write(f"Second attempt - looking for any matches with odds: found {matches_with_odds.count()}")
            
            # If still no matches, just get some matches
            if matches_with_odds.count() == 0:
                matches_with_odds = Match.objects.all()[:limit]
                self.stdout.write(f"Final attempt - using any matches: found {matches_with_odds.count()}")
                
                # Create some dummy odds if needed
                for match in matches_with_odds:
                    if not OddsSnapshot.objects.filter(match=match).exists():
                        self.stdout.write(f"Creating dummy odds for match {match.id}")
                        OddsSnapshot.objects.create(
                            match=match,
                            bookmaker="Bet365",
                            odds_home=1.5,
                            odds_draw=3.5,
                            odds_away=5.5,
                            fetched_at=timezone.now()
                        )

        # If we have matches, generate scores
        if matches_with_odds:
            # Convert to list to avoid lazy evaluation
            matches_list = list(matches_with_odds)
            
            # Display the matches we're using
            self.stdout.write("\nMatches being used for testing:")
            for match in matches_list:
                self.stdout.write(f"  ID {match.id}: {match} (API Ref: {match.api_ref})")
                odds = OddsSnapshot.objects.filter(match=match).first()
                if odds:
                    self.stdout.write(f"    Has odds from {odds.bookmaker}: {odds.odds_home}/{odds.odds_draw}/{odds.odds_away}")
                else:
                    self.stdout.write(f"    No odds available")
            
            # Generate scores
            scores = generate_match_scores(matches_list)
            self.stdout.write(f"\nGenerated {len(scores)} scores")
            
            if scores:
                # Store the scores
                try:
                    store_match_scores(scores)
                    self.stdout.write(self.style.SUCCESS("Successfully stored match scores in the database"))
                    
                    # Verify the scores were stored
                    stored_scores = MatchScoreModel.objects.filter(
                        match__in=matches_list
                    ).values('predicted_outcome').annotate(
                        count=Count('predicted_outcome')
                    )
                    
                    self.stdout.write("\nStored scores by outcome:")
                    for outcome in stored_scores:
                        self.stdout.write(f"  {outcome['predicted_outcome']}: {outcome['count']}")
                        
                    self.stdout.write(f"\nTotal stored: {MatchScoreModel.objects.filter(match__in=matches_list).count()}")
                    
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Error storing scores: {e}"))
            else:
                self.stdout.write(self.style.WARNING("No scores were generated - are there odds for these matches?"))
        else:
            self.stdout.write(self.style.WARNING("No matches found to test with")) 