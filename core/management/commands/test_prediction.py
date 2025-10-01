"""
Django management command to test the ML model prediction functionality.
"""

import logging
from django.core.management.base import BaseCommand

from predictor.ml_model import predict_outcome_probabilities

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test the ML model prediction functionality'

    def handle(self, *args, **options):
        self.stdout.write("Testing ML model prediction...")
        
        # Create a test match with sample features
        test_match = {
            'league_id': 999,
            'home_team_rating': 80,
            'away_team_rating': 75,
            'injured_home_starters': 1,
            'injured_away_starters': 2,
            'recent_form_diff': 5,
            'home_goals_avg': 1.8,
            'away_goals_avg': 1.2
        }
        
        # Create test odds
        test_odds = {
            'odds_home': 1.95,
            'odds_draw': 3.5,
            'odds_away': 4.2
        }
        
        # Run prediction
        self.stdout.write("Running prediction with test data...")
        probs = predict_outcome_probabilities(test_match, test_odds)
        
        # Display results
        self.stdout.write(self.style.SUCCESS("Prediction complete!"))
        self.stdout.write(f"Home win probability: {probs[0]:.4f}")
        self.stdout.write(f"Draw probability: {probs[1]:.4f}")
        self.stdout.write(f"Away win probability: {probs[2]:.4f}")
        
        # Determine most likely outcome
        max_prob = max(probs)
        if max_prob == probs[0]:
            outcome = "Home win"
        elif max_prob == probs[1]:
            outcome = "Draw"
        else:
            outcome = "Away win"
            
        self.stdout.write(f"Most likely outcome: {outcome} ({max_prob:.4f})") 