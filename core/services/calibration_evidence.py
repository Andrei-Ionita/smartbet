"""Public, reproducible calibration evidence derived from append-only rows.

This module never writes to the database and never changes a recommendation.
It turns SignalObservation vectors and confirmed FixtureResultObservation rows
into one pre-match decision per fixture/market.  Keeping the selection rule here
gives the public API, tests and future offline research one shared denominator.
"""

import math
from collections import Counter, defaultdict

from core.models import FixtureResultObservation, SignalObservation
from core.services import market_outcomes


EVALUATION_HORIZON_HOURS = 1.0
MIN_PUBLIC_FIXTURES = 30
MIN_PUBLIC_BIN_FORECASTS = 10
CALIBRATION_MARKETS = ('1x2', 'btts', 'over_under_2.5')
SUPPORTED_MARKETS = CALIBRATION_MARKETS + ('double_chance',)
MARKET_OUTCOMES = {
    '1x2': ('home', 'draw', 'away'),
    'btts': ('yes', 'no'),
    'over_under_2.5': ('over', 'under'),
    'double_chance': ('1x', 'x2', '12'),
}
MARKET_LABELS = {
    '1x2': 'Match result',
    'btts': 'Both teams to score',
    'over_under_2.5': 'Over / under 2.5',
    'double_chance': 'Double chance',
}
BIN_EDGES = tuple(i / 10 for i in range(11))
VECTOR_SUM_TOLERANCE = 0.025


def _round(value, places=4):
    return None if value is None else round(value, places)


def _valid_vector(market, vector):
    expected = MARKET_OUTCOMES.get(market)
    if not expected or not isinstance(vector, dict):
        return None
    try:
        parsed = {outcome: float(vector[outcome]) for outcome in expected}
    except (KeyError, TypeError, ValueError):
        return None
    if any(not math.isfinite(p) or p < 0 or p > 1 for p in parsed.values()):
        return None
    expected_sum = 2.0 if market == 'double_chance' else 1.0
    if abs(sum(parsed.values()) - expected_sum) > VECTOR_SUM_TOLERANCE:
        return None
    # Small provider rounding errors are normal. Re-normalising the complete
    # vector is explicit here and the original values remain immutable in DB.
    # Double-chance probabilities are dependent marginals whose sum is two, so
    # preserve that target rather than pretending they form a distribution.
    total = sum(parsed.values())
    return {outcome: (p / total) * expected_sum for outcome, p in parsed.items()}


def _latest_results(fixture_ids):
    """Return the latest result version, including provisional corrections."""
    latest = {}
    if not fixture_ids:
        return latest
    rows = (
        FixtureResultObservation.objects
        .filter(fixture_id__in=fixture_ids)
        .order_by('fixture_id', '-result_version', '-captured_at')
    )
    for row in rows:
        latest.setdefault(row.fixture_id, row)
    return latest


def collect_decisions(horizon_hours=EVALUATION_HORIZON_HOURS):
    """Choose one reproducible probability vector per fixture and market.

    The chosen row is the closest complete valid vector to kickoff that still
    existed at least ``horizon_hours`` beforehand.  Multiple outcome rows and
    repeated hourly sweeps therefore never inflate the decision count.
    """
    rows = list(
        SignalObservation.objects
        .filter(market__in=SUPPORTED_MARKETS)
        .only(
            'observation_id', 'fixture_id', 'home_team', 'away_team', 'league',
            'league_id', 'kickoff', 'observed_at', 'hours_to_kickoff', 'market',
            'provider', 'provider_model_version', 'raw_vector', 'vector_complete',
            'market_price_vector', 'price_vector_complete', 'pipeline_version',
            'calculation_version',
        )
        .order_by('fixture_id', 'market', 'hours_to_kickoff', '-observed_at')
    )

    universe = set()
    candidates = {}
    reasons = defaultdict(set)
    for row in rows:
        key = (row.fixture_id, row.market)
        universe.add(key)
        if row.hours_to_kickoff < horizon_hours:
            reasons[key].add('inside_evaluation_horizon')
            continue
        if not row.vector_complete:
            reasons[key].add('incomplete_probability_vector')
            continue
        vector = _valid_vector(row.market, row.raw_vector)
        if vector is None:
            reasons[key].add('invalid_probability_vector')
            continue
        # Ordered nearest-to-cutoff first. Do not replace the selected row with
        # an older observation from the same fixture/market.
        if key not in candidates:
            candidates[key] = (row, vector)

    results = _latest_results({fixture_id for fixture_id, _ in universe})
    decisions = []
    exclusion_counts = Counter()

    for key in sorted(universe):
        selected = candidates.get(key)
        if selected is None:
            group_reasons = reasons.get(key, set())
            if 'incomplete_probability_vector' in group_reasons:
                reason = 'incomplete_probability_vector'
            elif 'invalid_probability_vector' in group_reasons:
                reason = 'invalid_probability_vector'
            else:
                reason = 'inside_evaluation_horizon'
            exclusion_counts[reason] += 1
            continue

        row, vector = selected
        result = results.get(row.fixture_id)
        state = 'pending_result'
        result_payload = None
        if result is not None:
            result_payload = {
                'result_id': str(result.result_id),
                'version': result.result_version,
                'provider_status': result.provider_status,
                'home_score': result.home_score,
                'away_score': result.away_score,
                'confirmed': result.confirmed,
                'scoreable': result.is_scoreable,
                'captured_at': result.captured_at.isoformat(),
            }
            if not result.is_scoreable:
                state = 'unscoreable_result'
            elif not result.confirmed:
                state = 'awaiting_confirmation'
            else:
                state = 'evaluated'

        actual_vector = None
        actual_outcome = None
        brier = log_loss = None
        predicted_outcome = max(vector, key=vector.get)
        correct = None
        if state == 'evaluated':
            actual_vector = market_outcomes.outcome_vector(
                row.market, result.home_score, result.away_score,
            )
            if row.market == 'double_chance':
                winners = [outcome for outcome, won in actual_vector.items() if won]
                actual_outcome = ' + '.join(winners)
                correct = bool(actual_vector[predicted_outcome])
                # The three legs are dependent marginals, not one multiclass
                # probability distribution. Keep them visible in the archive
                # but out of Brier/log-loss calibration summaries.
            else:
                actual_outcome = max(actual_vector, key=actual_vector.get)
                brier = sum(
                    (vector[outcome] - actual_vector[outcome]) ** 2
                    for outcome in MARKET_OUTCOMES[row.market]
                )
                true_probability = max(vector[actual_outcome], 1e-12)
                log_loss = -math.log(true_probability)
                correct = predicted_outcome == actual_outcome

        decisions.append({
            'fixture_id': row.fixture_id,
            'fixture': f'{row.home_team} vs {row.away_team}',
            'home_team': row.home_team,
            'away_team': row.away_team,
            'league': row.league,
            'league_id': row.league_id,
            'kickoff': row.kickoff,
            'market': row.market,
            'market_label': MARKET_LABELS[row.market],
            'observation_id': str(row.observation_id),
            'observed_at': row.observed_at,
            'hours_to_kickoff': row.hours_to_kickoff,
            'provider': row.provider,
            'provider_model_version': row.provider_model_version,
            'pipeline_version': row.pipeline_version,
            'calculation_version': row.calculation_version,
            'probabilities': vector,
            'predicted_outcome': predicted_outcome,
            'actual_outcome': actual_outcome,
            'correct': correct,
            'brier_score': brier,
            'log_loss': log_loss,
            'price_vector': row.market_price_vector,
            'price_vector_complete': row.price_vector_complete,
            'state': state,
            'result': result_payload,
        })

    decisions.sort(key=lambda row: (row['kickoff'], row['fixture_id'], row['market']), reverse=True)
    return decisions, {
        'fixture_market_universe': len(universe),
        'eligible_decisions': len(decisions),
        'excluded_before_evaluation': dict(exclusion_counts),
    }


def _mean(values):
    return sum(values) / len(values) if values else None


def _wilson_interval(successes, count, z=1.96):
    if count <= 0:
        return None
    rate = successes / count
    denominator = 1 + (z * z / count)
    centre = (rate + z * z / (2 * count)) / denominator
    margin = z * math.sqrt((rate * (1 - rate) / count) + z * z / (4 * count * count)) / denominator
    return [_round(max(0, centre - margin)), _round(min(1, centre + margin))]


def _market_implied_vector(decision):
    if not decision['price_vector_complete'] or not isinstance(decision['price_vector'], dict):
        return None
    implied = {}
    try:
        for outcome in MARKET_OUTCOMES[decision['market']]:
            entry = decision['price_vector'][outcome]
            odds = float(entry.get('odds') if isinstance(entry, dict) else entry)
            if not math.isfinite(odds) or odds <= 1:
                return None
            implied[outcome] = 1 / odds
    except (KeyError, TypeError, ValueError):
        return None
    total = sum(implied.values())
    return {outcome: value / total for outcome, value in implied.items()}


def _evidence_level(fixture_count):
    if fixture_count < MIN_PUBLIC_FIXTURES:
        return 'collecting'
    if fixture_count < 100:
        return 'early'
    if fixture_count < 300:
        return 'developing'
    return 'substantial'


def _market_summary(market, decisions):
    fixture_count = len(decisions)
    enough = fixture_count >= MIN_PUBLIC_FIXTURES
    provider_brier = _mean([d['brier_score'] for d in decisions])
    provider_log_loss = _mean([d['log_loss'] for d in decisions])
    accuracy = _mean([1.0 if d['correct'] else 0.0 for d in decisions])

    uniform = {outcome: 1 / len(MARKET_OUTCOMES[market]) for outcome in MARKET_OUTCOMES[market]}
    uniform_brier = _mean([
        sum((uniform[o] - (1 if o == d['actual_outcome'] else 0)) ** 2 for o in uniform)
        for d in decisions
    ])
    uniform_log_loss = math.log(len(uniform)) if decisions else None

    market_rows = []
    for decision in decisions:
        vector = _market_implied_vector(decision)
        if vector is None:
            continue
        actual = decision['actual_outcome']
        market_rows.append({
            'brier': sum((p - (1 if outcome == actual else 0)) ** 2
                         for outcome, p in vector.items()),
            'log_loss': -math.log(max(vector[actual], 1e-12)),
        })

    components = []
    for decision in decisions:
        actual = decision['actual_outcome']
        components.extend(
            (probability, 1 if outcome == actual else 0, decision['fixture_id'])
            for outcome, probability in decision['probabilities'].items()
        )

    bins = []
    ece = 0.0
    for index, low in enumerate(BIN_EDGES[:-1]):
        high = BIN_EDGES[index + 1]
        members = [row for row in components if low <= row[0] <= high if (index == 9 or row[0] < high)]
        if not members:
            continue
        mean_forecast = _mean([row[0] for row in members])
        successes = sum(row[1] for row in members)
        observed = successes / len(members)
        ece += (len(members) / len(components)) * abs(observed - mean_forecast)
        distinct_fixtures = len({row[2] for row in members})
        publish_bin = (
            len(members) >= MIN_PUBLIC_BIN_FORECASTS
            and distinct_fixtures >= MIN_PUBLIC_BIN_FORECASTS
        )
        bins.append({
            'lower': low,
            'upper': high,
            'forecast_count': len(members),
            'fixture_count': distinct_fixtures,
            'mean_forecast': _round(mean_forecast),
            'observed_frequency': _round(observed) if publish_bin else None,
            'gap': _round(observed - mean_forecast) if publish_bin else None,
            'wilson_95': _wilson_interval(successes, len(members)) if publish_bin else None,
            'status': 'visible' if publish_bin else 'collecting',
        })

    def guarded(value):
        return _round(value) if enough else None

    market_count = len(market_rows)
    market_enough = market_count >= MIN_PUBLIC_FIXTURES
    return {
        'market': market,
        'label': MARKET_LABELS[market],
        'fixture_count': fixture_count,
        'evidence_level': _evidence_level(fixture_count),
        'minimum_for_metrics': MIN_PUBLIC_FIXTURES,
        'metrics_visible': enough,
        'provider': {
            'brier_score': guarded(provider_brier),
            'log_loss': guarded(provider_log_loss),
            'top_choice_accuracy': guarded(accuracy),
            'expected_calibration_error': guarded(ece),
        },
        'uniform_baseline': {
            'brier_score': guarded(uniform_brier),
            'log_loss': guarded(uniform_log_loss),
        },
        'market_baseline': {
            'fixture_count': market_count,
            'metrics_visible': market_enough,
            'brier_score': _round(_mean([r['brier'] for r in market_rows])) if market_enough else None,
            'log_loss': _round(_mean([r['log_loss'] for r in market_rows])) if market_enough else None,
        },
        'calibration_bins': bins,
    }


def build_report(horizon_hours=EVALUATION_HORIZON_HOURS):
    decisions, coverage = collect_decisions(horizon_hours=horizon_hours)
    state_counts = Counter(row['state'] for row in decisions)
    evaluated = [
        row for row in decisions
        if row['state'] == 'evaluated' and row['market'] in CALIBRATION_MARKETS
    ]
    by_market = defaultdict(list)
    for row in evaluated:
        by_market[row['market']].append(row)

    fixture_count = len({row['fixture_id'] for row in evaluated})
    coverage.update({
        'evaluated_market_decisions': len(evaluated),
        'evaluated_fixtures': fixture_count,
        'decision_states': dict(state_counts),
    })
    return {
        'methodology_version': 'calibration-evidence-v1',
        'evaluation_horizon_hours': horizon_hours,
        'minimum_public_fixtures': MIN_PUBLIC_FIXTURES,
        'minimum_public_bin_forecasts': MIN_PUBLIC_BIN_FORECASTS,
        'coverage': coverage,
        'markets': [
            _market_summary(market, by_market.get(market, []))
            for market in CALIBRATION_MARKETS
        ],
        'notes': [
            'One fixture-market decision is selected at the fixed pre-kickoff horizon; repeated observations and outcome rows do not increase the sample.',
            'Only complete provider probability vectors paired with confirmed, scoreable full-time results are evaluated.',
            'Metrics stay hidden below the stated minimum, but the archive remains available so the evidence can be independently recomputed.',
            'Markets from the same fixture share one scoreline and are not independent observations.',
            'Double-chance vectors remain in the archive but are excluded from calibration aggregates because their three legs are deterministically dependent.',
            'These are probability-quality diagnostics, not evidence of betting profitability.',
        ],
    }


def serialize_decision(decision):
    """JSON-safe public representation of a chosen decision."""
    return {
        **decision,
        'kickoff': decision['kickoff'].isoformat(),
        'observed_at': decision['observed_at'].isoformat(),
        'hours_to_kickoff': _round(decision['hours_to_kickoff'], 2),
        'probabilities': {key: _round(value) for key, value in decision['probabilities'].items()},
        'brier_score': _round(decision['brier_score']),
        'log_loss': _round(decision['log_loss']),
    }
