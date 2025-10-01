import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Match
from predictor.scoring_model import generate_match_scores, store_match_scores

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate betting recommendations using the scoring model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=3,
            help='Days ahead to generate recommendations for (default: 3)'
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=0.3,
            help='Minimum score threshold for recommendations (default: 0.3)'
        )
        parser.add_argument(
            '--league',
            type=str,
            default=None,
            help='Filter by league name (e.g. "Superliga")'
        )
        parser.add_argument(
            '--save',
            action='store_true',
            help='Save the scores to the database'
        )

    def handle(self, *args, **options):
        days_ahead = options['days']
        score_threshold = options['threshold']
        league_filter = options['league']
        save_to_db = options['save']
        
        # Calculate date range
        today = timezone.now()
        end_date = today + timedelta(days=days_ahead)
        
        self.stdout.write(f"Generating betting recommendations for {today.date()} to {end_date.date()}")
        
        # Build the query
        query = Match.objects.filter(
            kickoff__gte=today,
            kickoff__lte=end_date
        )
        
        # Apply league filter if provided
        if league_filter:
            query = query.filter(league_name__icontains=league_filter)
            self.stdout.write(f"Filtering by league: {league_filter}")
        
        # Get upcoming matches
        upcoming_matches = list(query)
        self.stdout.write(f"Found {len(upcoming_matches)} upcoming matches")
        
        if not upcoming_matches:
            self.stdout.write(self.style.WARNING("No upcoming matches found in the specified date range"))
            return
            
        # Generate scores
        match_scores = generate_match_scores(upcoming_matches)
        
        if not match_scores:
            self.stdout.write(self.style.WARNING("No scores could be generated. Are there odds available for these matches?"))
            return
            
        # Store scores in the database if requested
        if save_to_db:
            try:
                store_match_scores(match_scores)
                self.stdout.write(self.style.SUCCESS(f"Successfully saved {len(match_scores)} match scores to the database"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error storing match scores: {e}"))
            
        # Filter by threshold and sort by score
        filtered_scores = [s for s in match_scores if s.score >= score_threshold]
        filtered_scores.sort(key=lambda x: x.score, reverse=True)
        
        # Display results
        self.stdout.write(self.style.SUCCESS(f"\n=== SMARTBET RECOMMENDATIONS ({len(filtered_scores)}) ==="))
        
        for i, score in enumerate(filtered_scores, 1):
            self.stdout.write(f"\n{i}. {score.match.home_team} vs {score.match.away_team}")
            self.stdout.write(f"   Kickoff: {score.match.kickoff}")
            self.stdout.write(f"   Score: {score.score:.2f} ({score.confidence_level.value.upper()})")
            self.stdout.write(self.style.SUCCESS(f"   Bet: {score.predicted_outcome.value.upper()} ({score.recommended_bet})"))
            
        # Display summary stats
        if filtered_scores:
            avg_score = sum(s.score for s in filtered_scores) / len(filtered_scores)
            self.stdout.write(f"\nAverage recommendation score: {avg_score:.2f}")
            
            # Outcome distribution
            outcomes = {}
            for s in filtered_scores:
                outcome = s.predicted_outcome.value
                outcomes[outcome] = outcomes.get(outcome, 0) + 1
                
            self.stdout.write("\nRecommendation distribution:")
            for outcome, count in outcomes.items():
                percentage = (count / len(filtered_scores)) * 100
                self.stdout.write(f"  {outcome.upper()}: {count} ({percentage:.1f}%)")
                
        else:
            self.stdout.write(self.style.WARNING(f"\nNo recommendations meet the minimum threshold of {score_threshold}")) 