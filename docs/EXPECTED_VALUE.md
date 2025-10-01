# Expected Value (EV) Calculation in SmartBet

This document explains how Expected Value (EV) is calculated and used in the SmartBet application.

## What is Expected Value?

Expected Value (EV) is a mathematical concept used in betting to determine whether a bet offers positive value in the long run. It is calculated using the formula:

```
EV = (Model Probability * Bookmaker Odds) - 1
```

- **Positive EV**: When EV > 0, it indicates a potentially profitable bet in the long run
- **Zero EV**: When EV = 0, it indicates a fair bet (breakeven)
- **Negative EV**: When EV < 0, it indicates an unprofitable bet that should be avoided

## Implementation Details

We've integrated EV calculation into the SmartBet prediction system:

1. **Database**: Added an `expected_value` field to the `MatchScoreModel` model in `core/models.py`
2. **Calculation**: Implemented in `predictor/scoring_model.py` as part of the match scoring pipeline
3. **Presentation**: Added EV badges in output and classifications for bets:
   - EV > 0.05: "VALUE BET ✅"
   - EV < 0: "AVOID ❌"
   - 0 ≤ EV ≤ 0.05: "FAIR ⚖️"

### EV Calculation Flow

1. The model generates a probability for each match outcome (home win, draw, or away win)
2. This probability is compared against the bookmaker's odds for the same outcome
3. EV is calculated using the formula above
4. The resulting EV is stored in the database and used for filtering/ranking bets

## Usage in SmartBet

EV is used in SmartBet to:

1. **Prioritize Bets**: Higher EV bets are prioritized in recommendations
2. **Filter Bad Bets**: Negative EV bets can be excluded from recommendations
3. **Value Indication**: Provide users with insight into potential value of a bet

## Example Scenarios

1. **Positive EV (Value Bet)**:
   - Model probability: 50%
   - Bookmaker odds: 3.00
   - EV = (0.5 * 3.00) - 1 = 0.5 (50% expected profit)

2. **Fair Bet**:
   - Model probability: 33%
   - Bookmaker odds: 3.03
   - EV = (0.33 * 3.03) - 1 = 0 (breakeven)

3. **Negative EV (Avoid)**:
   - Model probability: 60%
   - Bookmaker odds: 1.5
   - EV = (0.6 * 1.5) - 1 = -0.1 (10% expected loss)

## Command for Testing EV

You can run the `demo_ev_calculation` command to see EV calculation in action:

```bash
python manage.py demo_ev_calculation --count 3
```

This will create test matches with different odds scenarios and show how EV is calculated for each.

## Next Steps

- Add frontend display of EV with appropriate badges/colors
- Incorporate EV into the ranking algorithm for the suggestion engine
- Add EV filters in the UI to allow users to set minimum EV thresholds
- Implement proper EV values in the data sent to the frontend API 