# SmartBet Predictor Module

This module contains the prediction and scoring logic for the SmartBet system, which analyzes football matches and generates betting recommendations.

## Components

- `scoring_model.py`: Contains the core scoring and recommendation logic
- `test_scoring.py`: Test script to demonstrate the scoring model functionality

## Using the Scoring Model

### Basic Usage

```python
from core.models import Match
from predictor.scoring_model import generate_match_scores

# Get matches to score
matches = Match.objects.filter(kickoff__gte=timezone.now())

# Generate scores
match_scores = generate_match_scores(list(matches))

# Display a recommendation
for score in match_scores:
    print(f"Match: {score.match.home_team} vs {score.match.away_team}")
    print(f"Recommendation: {score.predicted_outcome.value.title()} ({score.recommended_bet})")
    print(f"Confidence: {score.confidence_level.value}")
```

### Running the Test Script

To test the scoring model on recent matches:

```bash
python manage.py shell < predictor/test_scoring.py
```

## Implementation Details

### Scoring Logic

The scoring model version 1 uses a basic rule-based heuristic:

1. Retrieves the latest bookmaker odds for each match
2. Inverts the odds to create a basic probability-based score (lower odds = higher probability = higher score)
3. Normalizes the score to a 0-1 range
4. Assigns a confidence level based on the score
5. Determines the predicted outcome based on which option has the lowest odds
6. Generates a recommendation string

### MatchScore Data Model

The `MatchScore` class contains:

- `match`: The Match object being scored
- `odds_snapshot`: The OddsSnapshot used for scoring
- `score`: A float value from 0-1 (higher is better)
- `confidence_level`: Enum indicating LOW/MEDIUM/HIGH/VERY_HIGH confidence
- `predicted_outcome`: Enum indicating HOME_WIN/DRAW/AWAY_WIN
- `recommended_bet`: A string describing the recommended bet
- `generated_at`: Timestamp when the score was generated
- `source`: Identifier for the model version ("basic_model_v1")

## Future Improvements

Future versions of the scoring model will implement:

1. Machine learning-based predictions
2. Historical performance analysis
3. Team strength metrics
4. League-specific adjustments
5. Performance tracking and feedback loops 