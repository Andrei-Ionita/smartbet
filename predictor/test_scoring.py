"""
Test script for demonstrating the scoring model functionality.

To run this script: python manage.py shell < predictor/test_scoring.py
"""

import sys
import logging
from django.utils import timezone
from datetime import timedelta

from core.models import Match, OddsSnapshot
from predictor.scoring_model import generate_match_scores

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_scoring_model():
    """Run a test of the scoring model on recent matches."""
    # Get recent matches from the last 7 days that have odds
    recent_date = timezone.now() - timedelta(days=7)
    
    # Find matches with odds snapshots
    matches_with_odds = Match.objects.filter(
        oddsnapshot__isnull=False,
        kickoff__gte=recent_date
    ).distinct()
    
    logger.info(f"Found {matches_with_odds.count()} recent matches with odds")
    
    # Generate scores
    match_scores = generate_match_scores(list(matches_with_odds))
    
    logger.info(f"Generated {len(match_scores)} match scores")
    
    # Display results
    print("\n=== SMARTBET SCORING RESULTS ===")
    print(f"Analyzed {len(match_scores)} matches\n")
    
    for score in match_scores:
        print(f"Match: {score.match.home_team} vs {score.match.away_team}")
        print(f"Kickoff: {score.match.kickoff}")
        print(f"Score: {score.score:.2f} (Confidence: {score.confidence_level.value})")
        print(f"Prediction: {score.predicted_outcome.value.title()} ({score.recommended_bet})")
        print(f"Source: {score.source}\n")
    
    # Calculate some stats
    if match_scores:
        avg_score = sum(s.score for s in match_scores) / len(match_scores)
        print(f"Average match score: {avg_score:.2f}")
        
        # Group by outcome
        outcomes = {}
        for s in match_scores:
            outcome = s.predicted_outcome.value
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
        
        print("\nPredicted outcomes distribution:")
        for outcome, count in outcomes.items():
            print(f"  {outcome.title()}: {count} ({count/len(match_scores)*100:.1f}%)")
    
    return match_scores

# Run the test if executed directly
if __name__ == "__main__":
    print("Running scoring model test...")
    try:
        scores = test_scoring_model()
        print(f"\nTest completed successfully with {len(scores)} scored matches")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1) 