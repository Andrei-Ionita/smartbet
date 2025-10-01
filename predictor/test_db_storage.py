"""
Test Django management command for the MatchScoreModel implementation.
This is a management command version of the test script that can be run directly.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count

from core.models import Match, MatchScoreModel
from predictor.scoring_model import generate_match_scores, store_match_scores

class Command(BaseCommand):
    help = 'Test storing match scores in the database'

    def handle(self, *args, **options):
        # Find matches from the past to test with
        past_date = timezone.now() - timedelta(days=30)  # Look back 30 days
        matches = Match.objects.filter(kickoff__gte=past_date).order_by('-kickoff')[:5]

        self.stdout.write(f"Found {matches.count()} matches to test with")

        # If we have matches, generate scores
        if matches:
            # Generate scores
            scores = generate_match_scores(list(matches))
            self.stdout.write(f"Generated {len(scores)} scores")
            
            if scores:
                # Store the scores
                try:
                    store_match_scores(scores)
                    self.stdout.write(self.style.SUCCESS("Successfully stored match scores in the database"))
                    
                    # Verify the scores were stored
                    stored_scores = MatchScoreModel.objects.filter(
                        match__in=matches
                    ).values('predicted_outcome').annotate(
                        count=Count('predicted_outcome')
                    )
                    
                    self.stdout.write("\nStored scores by outcome:")
                    for outcome in stored_scores:
                        self.stdout.write(f"  {outcome['predicted_outcome']}: {outcome['count']}")
                        
                    self.stdout.write(f"\nTotal stored: {MatchScoreModel.objects.filter(match__in=matches).count()}")
                    
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Error storing scores: {e}"))
            else:
                self.stdout.write(self.style.WARNING("No scores were generated - are there odds for these matches?"))
        else:
            self.stdout.write(self.style.WARNING("No matches found to test with")) 