"""
Pure derivation of market outcomes from a full-time score.

No database, no provider, no side effects — a score in, outcome vectors out, so
it is exhaustively testable and cannot drift from whatever the caller believes.

DOUBLE CHANCE IS NOT THREE INDEPENDENT EVENTS
---------------------------------------------
1X, X2 and 12 each cover two of the three mutually exclusive match results, so
exactly TWO of the three legs win on every played fixture, always. Their sum is
2 by construction, not 1, and they are deterministically dependent: knowing the
1X2 result fixes all three legs with no freedom left. Scoring them as three
independent Bernoulli trials would treat one match result as three observations
and report an effective sample size roughly triple the truth.
"""

MARKETS = ('1x2', 'btts', 'over_under_2.5', 'double_chance')

# Which double-chance legs win for each 1X2 result. Read across: a home win
# makes 1X and 12 winners and X2 a loser.
DOUBLE_CHANCE_TRUTH = {
    'home': {'1x': True, 'x2': False, '12': True},
    'draw': {'1x': True, 'x2': True, '12': False},
    'away': {'1x': False, 'x2': True, '12': True},
}


def result_1x2(home_score, away_score):
    if home_score > away_score:
        return 'home'
    if home_score < away_score:
        return 'away'
    return 'draw'


def derive_outcomes(home_score, away_score):
    """Return the winning outcome of every supported market.

    Raises ValueError on a score that is not a pair of non-negative integers —
    a missing or malformed score must never silently produce 'draw'.
    """
    for value in (home_score, away_score):
        if value is None or isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f'score must be an integer, got {value!r}')
        if value < 0:
            raise ValueError(f'score cannot be negative, got {value!r}')

    total = home_score + away_score
    winner = result_1x2(home_score, away_score)

    return {
        '1x2': winner,
        'btts': 'yes' if (home_score > 0 and away_score > 0) else 'no',
        # 2.5 is a half-goal line, so it cannot push: 3+ is over, 0-2 is under.
        'over_under_2.5': 'over' if total >= 3 else 'under',
        # The COMPLETE leg vector, never one selected leg.
        'double_chance': dict(DOUBLE_CHANCE_TRUTH[winner]),
    }


def outcome_vector(market, home_score, away_score):
    """One-hot (or multi-hot for double chance) truth vector for a market.

    Keys match the outcome names SignalObservation stores, so a probability
    vector and this vector can be scored component-wise without a lookup table.
    """
    outcomes = derive_outcomes(home_score, away_score)

    if market == '1x2':
        winner = outcomes['1x2']
        return {name: 1 if name == winner else 0 for name in ('home', 'draw', 'away')}
    if market == 'btts':
        winner = outcomes['btts']
        return {name: 1 if name == winner else 0 for name in ('yes', 'no')}
    if market == 'over_under_2.5':
        winner = outcomes['over_under_2.5']
        return {name: 1 if name == winner else 0 for name in ('over', 'under')}
    if market == 'double_chance':
        legs = outcomes['double_chance']
        return {name: 1 if legs[name] else 0 for name in ('1x', 'x2', '12')}
    raise ValueError(f'unsupported market {market!r}')


def independent_component_count(market):
    """How many free binary choices a market really contains.

    Used to keep effective sample size honest. A 1X2 vector is three numbers but
    one multiclass decision; a double-chance vector is three legs but still one
    underlying match result with zero additional freedom.
    """
    return {
        '1x2': 1,            # one multiclass decision over three outcomes
        'btts': 1,           # one binary decision
        'over_under_2.5': 1,
        'double_chance': 0,  # fully determined by the 1x2 result — adds nothing
    }[market]
