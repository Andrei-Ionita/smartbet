# Match Score Prediction Implementation

This document summarizes the implementation of the match score prediction system.

## Overview

We've implemented a complete scoring and recommendation system for football matches, including:

1. Data models for storing match scores and predictions
2. Functions for generating scores using rule-based heuristics
3. Storage mechanisms for persisting match scores to the database
4. Test scripts and commands for verifying functionality

## Components

### Models

- **MatchScoreModel**: A Django model in `core/models.py` that persists match scores with the following fields:
  - `match`: ForeignKey to Match
  - `fixture_id`: String identifier (indexed)
  - `home_team_score`: Float score for home team
  - `away_team_score`: Float score for away team
  - `confidence_level`: String representation of confidence
  - `source`: String identifier for the scoring model version
  - `generated_at`: Timestamp when the score was generated
  - `recommended_bet`: String description of the recommended bet
  - `predicted_outcome`: String representation of the predicted outcome

### Scoring Logic

- **MatchScore**: A dataclass in `predictor/scoring_model.py` that represents a match score with its predictions
- **BettingOutcome**: An enum defining possible match outcomes (HOME_WIN, DRAW, AWAY_WIN)
- **ConfidenceLevel**: An enum defining confidence levels (LOW, MEDIUM, HIGH, VERY_HIGH)
- **score_match()**: Function that calculates a score for a match based on odds
- **generate_match_scores()**: Function that generates scores for multiple matches
- **store_match_scores()**: Function that converts MatchScore objects to MatchScoreModel instances and stores them

### Management Commands

- **generate_betting_recommendations**: Command to generate and display betting recommendations
  - Added `--save` flag to store recommendations in the database
- **test_db_storage**: Test command to verify the database storage functionality

## Database Implementation

The database schema includes:
- Indexes on `fixture_id`, `generated_at`, and `predicted_outcome` fields
- Default ordering by `generated_at` (newest first)
- ForeignKey relationship to Match model

## How to Use

### Generating Match Scores

```python
from core.models import Match
from predictor.scoring_model import generate_match_scores, store_match_scores

# Get matches to score
matches = Match.objects.filter(kickoff__gte=timezone.now())

# Generate scores
match_scores = generate_match_scores(list(matches))

# Store scores in the database
store_match_scores(match_scores)
```

### Command Line Usage

Generate and display recommendations:
```
python manage.py generate_betting_recommendations
```

Generate, display, and save recommendations:
```
python manage.py generate_betting_recommendations --save
```

Test the database storage functionality:
```
python manage.py test_db_storage --all
```

## Next Steps

1. Enhance the scoring model with more sophisticated prediction algorithms
2. Add a way to track actual match outcomes and calculate success rates
3. Build a web interface to display match scores and recommendations
4. Implement batch processing for regular updates of match scores
5. Create an API endpoint for accessing match scores programmatically 