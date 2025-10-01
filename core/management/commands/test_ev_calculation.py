"""
Command to test Expected Value calculation for match predictions.
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Match, MatchScoreModel
from predictor.scoring_model import generate_match_scores, store_match_scores

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test the Expected Value (EV) calculation for match predictions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=5,
            help='Number of upcoming matches to test with (default: 5)'
        )
        
    def handle(self, *args, **options):
        limit = options['limit']
        
        self.stdout.write(self.style.NOTICE(f"Running EV calculation test on up to {limit} upcoming matches"))
        
        # Find upcoming matches with odds
        upcoming_matches = Match.objects.filter(
            status='NS',
            kickoff__gte=timezone.now(),
            odds_snapshots__isnull=False
        ).distinct().order_by('kickoff')[:limit]
        
        if not upcoming_matches:
            self.stdout.write(self.style.WARNING("No upcoming matches with odds found"))
            return
        
        self.stdout.write(self.style.SUCCESS(f"Found {upcoming_matches.count()} upcoming matches with odds"))
        
        # Print the matches we'll be testing with
        self.stdout.write("\nMatches to test:")
        for i, match in enumerate(upcoming_matches, 1):
            bookmakers = list(match.odds_snapshots.values_list('bookmaker', flat=True).distinct())
            kickoff = match.kickoff.strftime("%Y-%m-%d %H:%M")
            self.stdout.write(f"{i}. {match} ({kickoff}) - Bookmakers: {', '.join(bookmakers)}")
        
        # Generate scores for these matches
        self.stdout.write(self.style.NOTICE("\nGenerating match scores with EV..."))
        scores = generate_match_scores(upcoming_matches)
        
        if not scores:
            self.stdout.write(self.style.ERROR("Failed to generate any scores!"))
            return
        
        # Display the results
        self.stdout.write(self.style.SUCCESS(f"\nGenerated {len(scores)} scores with EV calculations:"))
        self.stdout.write(f"{'Match':<40} {'Outcome':<10} {'Confidence':<10} {'Model Prob':<12} {'Odds':<8} {'EV':<8}")
        self.stdout.write("-" * 90)
        
        for score in scores:
            match = next((m for m in upcoming_matches if m.api_ref == score.fixture_id or str(m.id) == score.fixture_id), None)
            match_name = str(match) if match else f"Unknown match ({score.fixture_id})"
            
            # Determine outcome and associated odds
            if score.home_team_score > score.away_team_score:
                outcome = "HOME"
                model_prob = score.home_team_score
            elif score.away_team_score > score.home_team_score:
                outcome = "AWAY"
                model_prob = score.away_team_score
            else:
                outcome = "DRAW"
                model_prob = max(score.home_team_score, score.away_team_score)
            
            self.stdout.write(
                f"{match_name[:40]:<40} "
                f"{outcome:<10} "
                f"{score.confidence_level:<10} "
                f"{model_prob:.4f}     "
                f"{score.expected_value / model_prob + 1:.2f}    "
                f"{score.expected_value:.4f}"
            )
        
        # Store these scores
        self.stdout.write(self.style.NOTICE("\nStoring scores in database..."))
        store_match_scores(scores)
        
        # Check the stored scores
        stored_scores = MatchScoreModel.objects.filter(match__in=upcoming_matches).order_by('-generated_at')[:limit]
        self.stdout.write(self.style.SUCCESS(f"\nStored {stored_scores.count()} scores in database"))
        
        if stored_scores:
            self.stdout.write("\nScores in database:")
            for score in stored_scores:
                ev_description = ""
                if score.expected_value is not None:
                    if score.expected_value > 0.05:
                        ev_description = "VALUE BET"
                    elif score.expected_value < 0:
                        ev_description = "AVOID"
                    else:
                        ev_description = "FAIR"
                        
                self.stdout.write(
                    f"{score.match} - {score.predicted_outcome.upper()} "
                    f"(Confidence: {score.confidence_level}) "
                    f"EV: {score.expected_value:.4f} {ev_description}"
                )
        
        self.stdout.write(self.style.SUCCESS("\nEV calculation test completed successfully")) 