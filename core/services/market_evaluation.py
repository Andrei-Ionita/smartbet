"""
THE single implementation of market grading.

Pure: given a bet (market + selection) and a fixture's third-party result,
return whether that bet won. It holds no reference to any model instance, so
the same rules serve two different callers with two different sources of truth:

  * `PredictionLog.calculate_performance` grades the LATEST prediction, using
    the row's current market and outcome;
  * claim settlement grades a PUBLISHED CLAIM, using the market and outcome
    FROZEN in that claim.

That distinction is the whole point. Before this module existed, settlement read
`PredictionLog.was_correct`, which is graded against the row's CURRENT pick — so
a pipeline re-run that changed a fixture's market or selection would have
settled a published claim against a bet it never made.

The score and fixture status are third-party facts about the match and are
correctly read from the live row; only the BET must come from the claim.
"""

# Fixture statuses that mean no bet can stand.
CANCELLED_MATCH_STATUSES = {'CANC', 'CANCELLED', 'WO'}
VOID_MATCH_STATUSES = {'POSTP', 'ABAN', 'SUSP', 'DELETED', 'INT'}

OUTCOME_HOME = 'home'
OUTCOME_DRAW = 'draw'
OUTCOME_AWAY = 'away'


def actual_1x2(home_score, away_score, fallback=None):
    """The match result implied by the score, or `fallback` when unknown."""
    if home_score is None or away_score is None:
        return (fallback or '').lower() or None
    if home_score > away_score:
        return OUTCOME_HOME
    if away_score > home_score:
        return OUTCOME_AWAY
    return OUTCOME_DRAW


def is_void_status(fixture_status):
    return (fixture_status or '').upper() in VOID_MATCH_STATUSES


def is_cancelled_status(fixture_status):
    return (fixture_status or '').upper() in CANCELLED_MATCH_STATUSES


def evaluate_prediction(market_type, predicted_outcome, home_score, away_score,
                        fixture_status=None, actual_outcome=None):
    """Did this bet win?

    Returns True (won), False (lost), or None (cannot be determined — no
    usable result, or a void/cancelled fixture).

    Deliberately takes plain values, never a model instance, so a caller cannot
    accidentally grade against a mutable row.
    """
    if is_void_status(fixture_status) or is_cancelled_status(fixture_status):
        return None
    if not predicted_outcome:
        return None

    market_type = market_type or '1x2'
    predicted = str(predicted_outcome).lower().strip()
    result_1x2 = actual_1x2(home_score, away_score, fallback=actual_outcome)
    have_scores = home_score is not None and away_score is not None

    if market_type == 'btts':
        if not have_scores:
            return None
        both_scored = home_score > 0 and away_score > 0
        predicted_yes = 'yes' in predicted
        return predicted_yes == both_scored

    if market_type in {
            'over_under_1.5', 'over_under_2.5', 'over_under_3.5'}:
        if not have_scores:
            return None
        try:
            line = float(market_type.rsplit('_', 1)[-1])
        except (ValueError, IndexError):
            return None
        is_over = (home_score + away_score) > line
        predicted_over = 'over' in predicted
        return predicted_over == is_over

    if market_type == 'correct_score':
        if not have_scores:
            return None
        expected = predicted.replace(':', '-').replace(' ', '')
        return expected == f'{home_score}-{away_score}'

    if market_type == 'double_chance':
        if not result_1x2:
            return None
        if '1x' in predicted or ('home' in predicted and 'draw' in predicted):
            return result_1x2 in (OUTCOME_HOME, OUTCOME_DRAW)
        if 'x2' in predicted or ('draw' in predicted and 'away' in predicted):
            return result_1x2 in (OUTCOME_DRAW, OUTCOME_AWAY)
        if '12' in predicted:
            return result_1x2 in (OUTCOME_HOME, OUTCOME_AWAY)
        return None

    # Only the explicit match-result market may use 1X2 grading. Silently
    # treating a new market as 1X2 would corrupt the immutable performance
    # record, so unknown markets remain unscored until a grader is registered.
    if market_type != '1x2':
        return None
    if not result_1x2:
        return None
    return predicted == result_1x2
