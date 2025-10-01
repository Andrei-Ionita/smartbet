"""
Command to test the score generation and storage pipeline using mock data.
This avoids database schema issues by not querying actual match data.
"""

import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from django.core.management.base import BaseCommand
from django.utils import timezone

from predictor.scoring_model import MatchScore, store_match_scores

logger = logging.getLogger(__name__)

# Create mock classes for testing
@dataclass
class MockTeam:
    id: int
    name: str
    
    def __str__(self):
        return self.name

@dataclass
class MockMatch:
    id: int
    home_team: MockTeam
    away_team: MockTeam
    api_ref: str
    
    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"

class Command(BaseCommand):
    help = 'Test the match score storage pipeline using mock data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=3,
            help='Number of mock scores to generate (default: 3)'
        )
        
    def handle(self, *args, **options):
        count = options['count']
        
        self.stdout.write(self.style.NOTICE(f"Testing match score storage with {count} mock scores"))
        
        # Generate mock match scores
        scores = self._generate_mock_scores(count)
        
        # Print generated scores
        self.stdout.write(self.style.NOTICE("\nGenerated mock scores:"))
        for i, score in enumerate(scores):
            self.stdout.write(f"{i+1}. Fixture ID: {score.fixture_id}")
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
        try:
            store_match_scores(scores)
            self.stdout.write(self.style.SUCCESS("\nTest completed successfully!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\nError storing scores: {e}"))
    
    def _generate_mock_scores(self, count):
        """Generate mock match scores for testing."""
        now = datetime.now()
        scores = []
        
        for i in range(count):
            # Alternate between home win, away win, and draw
            scenario = i % 3
            
            if scenario == 0:  # Home win
                home_score = 0.7
                away_score = 0.3
                confidence = "high"
            elif scenario == 1:  # Away win
                home_score = 0.3
                away_score = 0.7
                confidence = "high"
            else:  # Draw
                home_score = 0.5
                away_score = 0.5
                confidence = "medium"
            
            score = MatchScore(
                fixture_id=f"test_match_{i+1}",
                home_team_score=home_score,
                away_team_score=away_score,
                confidence_level=confidence,
                source="mock_test_model",
                generated_at=now
            )
            
            scores.append(score)
            
        return scores 