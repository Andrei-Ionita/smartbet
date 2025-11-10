# SportMonks Prediction System

## Overview

SmartBet uses **SportMonks' professional AI prediction models** via their Predictions API addon. We do **NOT** train our own machine learning models. Instead, we intelligently aggregate predictions from SportMonks' 3 expert models.

## How It Works

### 1. SportMonks Prediction Models

SportMonks provides access to 3 different AI models via their Predictions API:

- **Model 233**: First expert model
- **Model 237**: Second expert model
- **Model 238**: Third expert model

Each model independently predicts probabilities for:
- Home Win
- Draw
- Away Win

### 2. Fetching Predictions

We fetch predictions from SportMonks using their Fixtures API:

```python
# Example API call
url = "https://api.sportmonks.com/v3/football/fixtures/upcoming"
params = {
    'api_token': SPORTMONKS_TOKEN,
    'include': 'participants;league;predictions',  # Include predictions
    'filters': 'fixtureLeagues:8,564,384,82,301',  # Our supported leagues
}
```

Each fixture returns predictions from all 3 models:

```json
{
  "fixture_id": 12345,
  "name": "Manchester United vs Liverpool",
  "predictions": [
    {
      "type_id": 233,
      "predictions": {
        "home": 45.2,
        "draw": 28.1,
        "away": 26.7
      }
    },
    {
      "type_id": 237,
      "predictions": {
        "home": 48.3,
        "draw": 25.4,
        "away": 26.3
      }
    },
    {
      "type_id": 238,
      "predictions": {
        "home": 42.1,
        "draw": 30.2,
        "away": 27.7
      }
    }
  ]
}
```

### 3. Ensemble Aggregation

We combine the 3 model predictions using **consensus ensemble**:

#### Consensus Method

1. **Average Probabilities**: Calculate mean probability for each outcome across all 3 models
2. **Select Winner**: Choose outcome with highest average probability
3. **Calculate Confidence**: Use the winner's average probability as our confidence
4. **Track Consensus**: Measure how much the models agree (0-100%)
5. **Measure Variance**: Calculate standard deviation to detect disagreement

#### Example Calculation

For the fixture above:

```
Average Home: (45.2 + 48.3 + 42.1) / 3 = 45.2%
Average Draw: (28.1 + 25.4 + 30.2) / 3 = 27.9%
Average Away: (26.7 + 26.3 + 27.7) / 3 = 26.9%

Predicted Outcome: Home (highest average)
Confidence: 45.2%
Consensus: 87% (models mostly agree)
Variance: 3.1 (low disagreement)
```

### 4. Expected Value Calculation

After determining our prediction, we calculate Expected Value (EV):

```python
# Get best odds from The Odds API
odds_home = 2.20

# Calculate EV
EV = (win_probability × odds) - 1
EV = (0.452 × 2.20) - 1 = -0.006 = -0.6%
```

Positive EV = value bet
Negative EV = avoid

### 5. Quality Filtering

We only show predictions that meet quality thresholds:

- **Minimum Confidence**: 55%
- **Positive EV**: >0%
- **Reasonable Odds**: 1.3 - 5.0
- **Clear Winner**: >10% probability gap
- **Model Agreement**: Low variance preferred

### 6. Storing Predictions

Approved predictions are stored in `PredictionLog`:

```python
PredictionLog.objects.create(
    fixture_id=fixture_id,
    home_team="Manchester United",
    away_team="Liverpool",
    league="Premier League",
    kickoff=datetime(...),

    # Our aggregated prediction
    predicted_outcome="Home",
    confidence=0.452,

    # Individual outcome probabilities
    probability_home=0.452,
    probability_draw=0.279,
    probability_away=0.269,

    # Betting info
    odds_home=2.20,
    odds_draw=3.40,
    odds_away=3.10,
    expected_value=-0.006,

    # Ensemble metadata
    model_count=3,
    consensus=0.87,
    variance=3.1,
    ensemble_strategy="consensus_ensemble",

    # Timestamps (PROOF)
    prediction_logged_at=timezone.now(),  # Before match
    result_logged_at=None,  # After match completes
)
```

### 7. Result Verification

After matches complete, we fetch results from SportMonks:

```python
# Update prediction with actual outcome
url = f"https://api.sportmonks.com/v3/football/fixtures/{fixture_id}"
response = requests.get(url, params={'include': 'scores'})

# Extract result
actual_home_score = 2
actual_away_score = 1
actual_outcome = "Home"

# Update prediction
prediction.actual_outcome = "Home"
prediction.was_correct = (actual_outcome == prediction.predicted_outcome)
prediction.result_logged_at = timezone.now()
prediction.save()
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│          SportMonks Predictions API                 │
│   (3 Expert AI Models: 233, 237, 238)              │
└─────────────────┬───────────────────────────────────┘
                  │
                  │ Fetch predictions for upcoming fixtures
                  │
         ┌────────▼────────┐
         │  Our Backend    │
         │   (Django)      │
         └────────┬────────┘
                  │
                  │ 1. Aggregate 3 models (consensus)
                  │ 2. Calculate EV with The Odds API
                  │ 3. Filter by quality thresholds
                  │ 4. Store in PredictionLog
                  │
         ┌────────▼────────┐
         │  Recommendations │
         │       API        │
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │  Frontend (UI)  │
         │  Top 10 Picks   │
         └─────────────────┘
```

## Why This Approach?

### Advantages

1. **Professional Models**: SportMonks trains models on massive datasets
2. **Always Up-to-Date**: Models retrained regularly by SportMonks
3. **No Training Overhead**: No need to collect training data or retrain
4. **Proven Performance**: SportMonks models are battle-tested
5. **Focus on Value**: We focus on aggregation, EV, and user experience
6. **Scalability**: Works across 27 leagues instantly

### What We Add

While we use SportMonks predictions, we add significant value:

1. **Intelligent Aggregation**: Consensus ensemble of 3 models
2. **Expected Value**: Calculate EV with real bookmaker odds
3. **Quality Filtering**: Only show high-quality predictions
4. **Risk Assessment**: Automatic risk warnings
5. **Bankroll Management**: Kelly Criterion stake sizing
6. **Transparency**: Public track record with timestamp proof
7. **User Experience**: Beautiful UI, explanations, insights

## Code Locations

### Prediction Fetching
- `test_sportmonks_api.py` - Test script for API exploration
- `core/views.py` - Fixture verification with SportMonks

### Prediction Storage
- `core/models.py` - `PredictionLog` model (lines ~200-400)
- `core/management/commands/log_predictions_batch.py` - Batch logging

### Recommendation Generation
- `core/api_views.py` - Main recommendations API
- `core/services/prediction_enhancer.py` - Quality scoring

### Result Updates
- `core/management/commands/update_results.py` - Fetch results from SportMonks
- `core/services/result_updater.py` - Result verification logic

## Environment Variables

```bash
# SportMonks API
SPORTMONKS_API_TOKEN=your_token_here

# The Odds API (for betting odds)
ODDS_API_KEY=your_key_here
```

## Supported Leagues

We support 27 European football leagues. The predictions come from SportMonks for:

- Premier League (England)
- La Liga (Spain)
- Serie A (Italy)
- Bundesliga (Germany)
- Ligue 1 (France)
- Champions League
- Europa League
- And 20 more leagues

## Future Enhancements

Potential improvements to the system:

1. **Model Weighting**: Weight models based on historical performance
2. **League-Specific Ensembles**: Different strategies per league
3. **Confidence Calibration**: Adjust confidence based on accuracy tracking
4. **Model Selection**: Only use models that agree (higher consensus)
5. **Time-Based Filtering**: Predictions closer to kickoff may be more accurate

## Summary

SmartBet is **NOT** a machine learning training platform. We are a **prediction aggregation and value betting platform** that:

1. Uses SportMonks' professional AI models
2. Intelligently combines their predictions
3. Calculates expected value with real odds
4. Provides professional bankroll management
5. Maintains complete transparency

This approach allows us to focus on what we do best: **helping users make smarter betting decisions** rather than competing with SportMonks' ML expertise.
