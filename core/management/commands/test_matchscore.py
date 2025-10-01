"""
Test command to verify that the MatchScore dataclass works correctly.

Run this command with:
python manage.py test_matchscore
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import Match, OddsSnapshot
from predictor.scoring_model import generate_match_scores

class Command(BaseCommand):
    help = 'Test the MatchScore dataclass in the scoring model'

    def handle(self, *args, **options):
        # Find a few recent matches to test with
        past_date = timezone.now() - timedelta(days=30)
        matches = Match.objects.all()[:3]  # Get any 3 matches

        self.stdout.write(f"Found {matches.count()} matches to test with")

        if matches:
            # Make sure there are odds for our test matches
            for match in matches:
                if not OddsSnapshot.objects.filter(match=match).exists():
                    self.stdout.write(f"Creating test odds for match {match.id}")
                    OddsSnapshot.objects.create(
                        match=match,
                        bookmaker="Bet365",
                        odds_home=1.5,
                        odds_draw=3.5,
                        odds_away=5.5,
                        fetched_at=timezone.now()
                    )

            # Generate match scores
            scores = generate_match_scores(list(matches))
            
            self.stdout.write(self.style.SUCCESS(f"Generated {len(scores)} match scores"))
            
            # Test accessing the attributes
            self.stdout.write("\nAccessing MatchScore attributes:")
            for idx, score in enumerate(scores):
                self.stdout.write(f"\nScore {idx+1}:")
                self.stdout.write(f"  fixture_id: {score.fixture_id}")
                self.stdout.write(f"  home_team_score: {score.home_team_score}")
                self.stdout.write(f"  away_team_score: {score.away_team_score}")
                self.stdout.write(f"  confidence_level: {score.confidence_level}")
                self.stdout.write(f"  source: {score.source}")
                self.stdout.write(f"  generated_at: {score.generated_at}")
                
                # Determine the likely outcome (for display only)
                if score.home_team_score > score.away_team_score:
                    predicted = "home"
                elif score.away_team_score > score.home_team_score:
                    predicted = "away"
                else:
                    predicted = "draw"
                self.stdout.write(f"  (Implied outcome: {predicted})")

            # Test the specific loop format mentioned in the request
            self.stdout.write("\nTesting with the requested loop format:")
            self.stdout.write("for s in scores:")
            self.stdout.write("    print(s.fixture_id, s.home_team_score, s.away_team_score, s.confidence_level)")
            self.stdout.write("\nOutput:")
            for s in scores:
                self.stdout.write(f"  {s.fixture_id} {s.home_team_score} {s.away_team_score} {s.confidence_level}")
        else:
            self.stdout.write(self.style.WARNING("No matches found to test with")) 