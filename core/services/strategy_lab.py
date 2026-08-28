"""Versioned, append-only strategy research with honest promotion gates.

Retrospective backtests may reject a hypothesis, but never validate it.
Forward observations are frozen at a pre-registered horizon and are the only
evidence allowed to make a strategy eligible for public review. Every
experiment chooses at most one bet per fixture, preventing correlated outcomes,
alternative lines and repeated sweeps from manufacturing a large sample.
Nothing in this module publishes a Gem automatically.
"""
import math
from collections import Counter, defaultdict
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from core.models import (
    FixtureResultObservation,
    SignalObservation,
    StrategyLabExperiment,
    StrategyLabObservation,
    StrategyLabSettlement,
)
from core.services.integrity import canonical_sha256, norm_dt, norm_num


COMMON_VALUE_RULES = {
    'expected_return_lower_gt': 0.03,
    'minimum_model_mass': 0.95,
    'maximum_model_mass': 1.05,
    'minimum_bookmakers': 2,
    'minimum_odds': 1.50,
    'maximum_odds': 4.00,
    'maximum_quote_age_hours': 24,
    'require_complete_vector': True,
    'require_complete_price_vector': True,
    'staking': 'flat_one_unit',
    'result_basis': 'confirmed_90_minute_score',
    'settlement_supported': True,
    'maximum_forward_drawdown_units': 20,
}


def _direct_definition(key, name, market, **rule_overrides):
    rules = {**COMMON_VALUE_RULES, **rule_overrides}
    return {
        'strategy_key': key,
        'version': 'v2',
        'name': name,
        'market': market,
        'source': 'signal_observation',
        'decision_horizon_hours': 1.0,
        'minimum_settled_for_review': 100,
        'rules': rules,
    }


ASIAN_HANDICAP_V2 = {
    'strategy_key': 'asian-handicap-score-distribution',
    'version': 'v2',
    'name': 'Asian Handicap — score-distribution value',
    'market': 'asian_handicap',
    'source': 'specialist_candidate',
    'decision_horizon_hours': 1.0,
    'minimum_settled_for_review': 100,
    'rules': {
        'expected_return_lower_gt': 0.02,
        'minimum_model_mass': 0.95,
        'maximum_model_mass': 1.05,
        'minimum_bookmakers': 2,
        'minimum_odds': 1.50,
        'maximum_odds': 3.50,
        'maximum_quote_age_hours': 24,
        'require_complete_vector': True,
        'require_complete_price_vector': False,
        'result_basis': 'confirmed_90_minute_score',
        'settlement_supported': True,
        'staking': 'flat_one_unit',
        'quarter_line_settlement': 'split_equal_stake',
        'maximum_forward_drawdown_units': 20,
    },
}

ASIAN_GOAL_LINE_V2 = {
    **ASIAN_HANDICAP_V2,
    'strategy_key': 'asian-goal-line-score-distribution',
    'name': 'Asian goal line — score-distribution value',
    'market': 'asian_goal_line',
    'rules': {
        **ASIAN_HANDICAP_V2['rules'],
        'result_basis': 'confirmed_90_minute_total_goals',
        'quarter_line_settlement': 'split_equal_stake',
    },
}

TEAM_TOTAL_V2 = {
    **ASIAN_HANDICAP_V2,
    'strategy_key': 'team-total-score-distribution',
    'name': 'Team total goals — bounded score-distribution value',
    'market': 'team_total_goals',
    'rules': {
        **ASIAN_HANDICAP_V2['rules'],
        'result_basis': 'confirmed_team_90_minute_goals',
        'maximum_odds': 5.00,
    },
}


STRATEGY_DEFINITIONS = (
    ASIAN_HANDICAP_V2,
    ASIAN_GOAL_LINE_V2,
    TEAM_TOTAL_V2,
    _direct_definition(
        'full-time-result-value', 'Full-time result — model/price value', '1x2',
    ),
    _direct_definition(
        'both-teams-score-value', 'Both teams to score — model/price value', 'btts',
        maximum_odds=3.50,
    ),
    _direct_definition(
        'total-goals-1-5-value', 'Total goals 1.5 — model/price value',
        'over_under_1.5', minimum_odds=1.35, maximum_odds=3.50,
    ),
    _direct_definition(
        'total-goals-2-5-value', 'Total goals 2.5 — model/price value',
        'over_under_2.5', maximum_odds=3.50,
    ),
    _direct_definition(
        'total-goals-3-5-value', 'Total goals 3.5 — model/price value',
        'over_under_3.5', maximum_odds=4.00,
    ),
    _direct_definition(
        'double-chance-value', 'Double chance — model/price value',
        'double_chance', minimum_model_mass=1.90, maximum_model_mass=2.10,
        minimum_odds=1.25, maximum_odds=2.50,
    ),
    _direct_definition(
        'half-time-result-value', 'Half-time result — model/price value',
        'half_time_result', result_basis='confirmed_half_time_score',
    ),
    _direct_definition(
        'half-time-full-time-value', 'Half-time/full-time — model/price value',
        'half_time_full_time', result_basis='confirmed_half_time_and_90_minute_score',
        minimum_odds=2.00, maximum_odds=12.00,
    ),
    _direct_definition(
        'correct-score-value', 'Correct score — model/price value',
        'correct_score', expected_return_lower_gt=0.05,
        minimum_odds=4.00, maximum_odds=30.00,
        require_complete_price_vector=False,
    ),
)

DEFINITION_BY_KEY = {
    (definition['strategy_key'], definition['version']): definition
    for definition in STRATEGY_DEFINITIONS
}
DEFINITION_BY_MARKET = {
    definition['market']: definition
    for definition in STRATEGY_DEFINITIONS
    if definition.get('source') == 'signal_observation'
}

# "All markets" must never be interpreted as "pretend every market is
# testable". Blockers remain visible in the private report until their evidence
# prerequisites exist.
BLOCKED_STRATEGIES = (
    {
        'strategy_key': 'first-team-to-score-value',
        'name': 'First team to score',
        'status': 'blocked',
        'reason': 'Result evidence stores scores, not the ordered goal-event timeline.',
        'required_evidence': 'timestamped goal events with cancellations and VAR corrections',
    },
    {
        'strategy_key': 'cards-corners-player-props',
        'name': 'Cards, corners and player props',
        'status': 'blocked',
        'reason': 'Prices exist for some fixtures, but no matching probability vectors are captured.',
        'required_evidence': 'versioned pre-match distributions and exact event/stat settlement data',
    },
    {
        'strategy_key': 'context-filtered-variants',
        'name': 'Lineup, availability, form and league-qualified variants',
        'status': 'collecting_inputs',
        'reason': 'Filters must be pre-registered after a base strategy has enough data.',
        'required_evidence': 'forward base-strategy sample plus stable context coverage',
    },
)


def _aware(value):
    if not value:
        return None
    if isinstance(value, str):
        from django.utils.dateparse import parse_datetime
        value = parse_datetime(value.replace(' ', 'T'))
    if value is None:
        return None
    if timezone.is_naive(value):
        from datetime import timezone as dt_timezone
        value = timezone.make_aware(value, dt_timezone.utc)
    return value


def _rules_hash(definition):
    return canonical_sha256({
        'strategy_key': definition['strategy_key'],
        'version': definition['version'],
        'market': definition['market'],
        'source': definition.get('source'),
        'decision_horizon_hours': definition['decision_horizon_hours'],
        'rules': definition['rules'],
    })


def ensure_experiment(definition=None):
    """Return one registered experiment, refusing silent rule changes."""
    definition = definition or ASIAN_HANDICAP_V2
    digest = _rules_hash(definition)
    experiment, created = StrategyLabExperiment.objects.get_or_create(
        strategy_key=definition['strategy_key'],
        version=definition['version'],
        defaults={
            'name': definition['name'],
            'market': definition['market'],
            'status': StrategyLabExperiment.STATUS_SHADOW,
            'decision_horizon_hours': definition['decision_horizon_hours'],
            'rules': definition['rules'],
            'rules_hash': digest,
            'minimum_settled_for_review': definition['minimum_settled_for_review'],
        },
    )
    if not created and experiment.rules_hash != digest:
        raise RuntimeError(
            f"strategy {definition['strategy_key']} {definition['version']} "
            'already exists with different rules; create a new version'
        )
    return experiment


def ensure_all_experiments():
    return [ensure_experiment(definition) for definition in STRATEGY_DEFINITIONS]


def observation_hash(candidate, experiment):
    """Semantic specialist-candidate identity; timestamps cannot inflate it."""
    provenance = candidate.get('price_provenance') or {}
    return canonical_sha256({
        'v': 2,
        'rules_hash': experiment.rules_hash,
        'fixture_id': candidate.get('fixture_id'),
        'kickoff': norm_dt(_aware(candidate.get('kickoff'))),
        'market_id': candidate.get('market_id'),
        'side': candidate.get('side'),
        'handicap': norm_num(candidate.get('handicap')),
        'odds': norm_num(candidate.get('odds')),
        'bookmaker': candidate.get('bookmaker'),
        'bookmaker_count': candidate.get('bookmaker_count'),
        'price_min': norm_num(candidate.get('price_min')),
        'price_max': norm_num(candidate.get('price_max')),
        'model_mass': norm_num(candidate.get('model_mass')),
        'expected_return_lower': norm_num(candidate.get('expected_return_lower')),
        'expected_return_upper': norm_num(candidate.get('expected_return_upper')),
        'price_source': {
            'market_id': provenance.get('market_id'),
            'bookmaker_id': provenance.get('bookmaker_id'),
            'bookmaker_name': provenance.get('bookmaker_name'),
            'selection_policy': provenance.get('selection_policy'),
        },
    })


def capture(payload, ingestion_run_id):
    """Append bounded score-distribution candidates from specialist markets."""
    candidates = payload.get('strategy_candidates') or []
    written = skipped = invalid = post_kickoff = 0
    allowed = {
        'asian_handicap': ({'home', 'away'}, {6, 104}),
        'asian_goal_line': ({'over', 'under'}, {7, 105}),
        'team_total_goals': (
            {'home_over', 'home_under', 'away_over', 'away_under'}, {86},
        ),
    }

    for candidate in candidates:
        definition = DEFINITION_BY_KEY.get((
            candidate.get('strategy_key'), candidate.get('strategy_version'),
        ))
        if not definition or definition.get('source') != 'specialist_candidate':
            invalid += 1
            continue
        experiment = ensure_experiment(definition)
        allowed_sides, allowed_markets = allowed.get(
            definition['market'], (set(), set()),
        )
        kickoff = _aware(candidate.get('kickoff'))
        observed_at = _aware(candidate.get('observed_at')) or timezone.now()
        captured_at = _aware(candidate.get('captured_at'))
        required = (
            candidate.get('fixture_id'), candidate.get('side'),
            candidate.get('handicap'), candidate.get('odds'), captured_at,
        )
        if (kickoff is None or any(value is None for value in required)
                or candidate.get('side') not in allowed_sides
                or candidate.get('market_id') not in allowed_markets
                or float(candidate.get('odds') or 0) <= 1):
            invalid += 1
            continue
        hours = (kickoff - observed_at).total_seconds() / 3600.0
        if hours < 0:
            post_kickoff += 1
        digest = observation_hash(candidate, experiment)
        if StrategyLabObservation.objects.filter(source_payload_hash=digest).exists():
            skipped += 1
            continue
        StrategyLabObservation.objects.create(
            experiment=experiment,
            evidence_phase=StrategyLabObservation.PHASE_FORWARD,
            ingestion_run_id=ingestion_run_id,
            source_payload_hash=digest,
            fixture_id=candidate['fixture_id'],
            home_team=(candidate.get('home_team') or '')[:100],
            away_team=(candidate.get('away_team') or '')[:100],
            league=(candidate.get('league') or '')[:100],
            league_id=candidate.get('league_id'),
            kickoff=kickoff,
            observed_at=observed_at,
            hours_to_kickoff=hours,
            market=definition['market'][:40],
            market_id=candidate.get('market_id'),
            side=candidate['side'][:32],
            handicap=float(candidate['handicap']),
            label=(candidate.get('label') or '')[:120],
            selection_payload={
                'model_mass': candidate.get('model_mass'),
                'line': candidate.get('handicap'),
                'side': candidate.get('side'),
                'edge_bounds': [candidate.get('expected_return_lower'),
                                candidate.get('expected_return_upper')],
            },
            odds=float(candidate['odds']),
            bookmaker=(candidate.get('bookmaker') or '')[:64],
            bookmaker_count=max(0, int(candidate.get('bookmaker_count') or 0)),
            price_min=float(candidate.get('price_min') or candidate['odds']),
            price_max=float(candidate.get('price_max') or candidate['odds']),
            odds_captured_at=captured_at,
            price_provenance=candidate.get('price_provenance') or {},
            model_mass=float(candidate.get('model_mass') or 0),
            expected_return_lower=float(candidate.get('expected_return_lower') or 0),
            expected_return_upper=float(candidate.get('expected_return_upper') or 0),
            robust_positive_edge=bool(candidate.get('robust_positive_edge')),
            calculation_version=(candidate.get('calculation_version') or '')[:80],
        )
        written += 1

    return {
        'strategy_candidates': len(candidates),
        'strategy_written': written,
        'strategy_skipped_duplicate': skipped,
        'strategy_invalid': invalid,
        'strategy_post_kickoff': post_kickoff,
    }


def _provenance_number(provenance, key, default):
    try:
        value = provenance.get(key)
        return float(value) if value is not None else default
    except (TypeError, ValueError, AttributeError):
        return default


def capture_signal_observations(signals, *, phase, ingestion_run_id=None):
    """Materialise direct model-vs-price hypotheses from immutable signals.

    ``phase`` is mandatory. A backfill caller cannot accidentally label old
    evidence as forward validation.
    """
    if phase not in dict(StrategyLabObservation.PHASE_CHOICES):
        raise ValueError('phase must be retrospective or forward')
    ensure_all_experiments()
    written = skipped = unsupported = invalid = 0

    for signal in signals:
        definition = DEFINITION_BY_MARKET.get(signal.market)
        if not definition:
            unsupported += 1
            continue
        experiment = ensure_experiment(definition)
        probability = signal.normalized_probability
        if (signal.odds is None or signal.odds <= 1 or probability is None
                or probability < 0 or probability > 1
                or signal.odds_captured_at is None):
            invalid += 1
            continue

        provenance = signal.odds_provenance or {}
        bookmaker_count = int(_provenance_number(
            provenance, 'odds_bookmaker_count', 1,
        ))
        price_min = _provenance_number(provenance, 'odds_min', signal.odds)
        price_max = _provenance_number(provenance, 'odds_max', signal.odds)
        expected_return = probability * signal.odds - 1
        digest = canonical_sha256({
            'v': 1,
            'rules_hash': experiment.rules_hash,
            'signal_hash': signal.source_payload_hash,
            'phase': phase,
        })
        if StrategyLabObservation.objects.filter(source_payload_hash=digest).exists():
            skipped += 1
            continue

        StrategyLabObservation.objects.create(
            experiment=experiment,
            source_signal=signal,
            evidence_phase=phase,
            ingestion_run_id=(ingestion_run_id or signal.ingestion_run_id)[:64],
            source_payload_hash=digest,
            fixture_id=signal.fixture_id,
            home_team=signal.home_team,
            away_team=signal.away_team,
            league=signal.league,
            league_id=signal.league_id,
            kickoff=signal.kickoff,
            observed_at=signal.observed_at,
            hours_to_kickoff=signal.hours_to_kickoff,
            market=signal.market,
            market_id=provenance.get('odds_market_id'),
            side=signal.outcome[:32],
            handicap=None,
            label=signal.outcome.replace('_', ' ')[:120],
            selection_payload={
                'normalized_probability': probability,
                'raw_vector': signal.raw_vector,
                'vector_complete': signal.vector_complete,
                'price_vector_complete': signal.price_vector_complete,
                'pipeline_version': signal.pipeline_version,
            },
            odds=signal.odds,
            bookmaker=signal.bookmaker,
            bookmaker_count=max(0, bookmaker_count),
            price_min=price_min,
            price_max=price_max,
            odds_captured_at=signal.odds_captured_at,
            price_provenance=provenance,
            model_mass=signal.vector_sum,
            expected_return_lower=expected_return,
            expected_return_upper=expected_return,
            robust_positive_edge=expected_return > definition['rules']['expected_return_lower_gt'],
            calculation_version=signal.calculation_version,
        )
        written += 1

    return {
        'signal_strategy_written': written,
        'signal_strategy_skipped_duplicate': skipped,
        'signal_strategy_unsupported': unsupported,
        'signal_strategy_invalid': invalid,
    }


def qualifies(observation):
    rules = observation.experiment.rules
    payload = observation.selection_payload or {}
    complete_vector = payload.get('vector_complete', True)
    complete_prices = payload.get('price_vector_complete', True)
    if observation.source_signal is not None:
        price_provenance_ready = (
            observation.source_signal.price_status == 'verified'
            and observation.source_signal.provenance_complete
        )
    else:
        price_provenance_ready = bool(
            observation.bookmaker
            and (observation.price_provenance or {}).get('selection_policy')
        )
    quote_age = (
        observation.observed_at - observation.odds_captured_at
    ).total_seconds() / 3600.0
    return (
        price_provenance_ready
        and
        observation.robust_positive_edge
        and observation.expected_return_lower > rules['expected_return_lower_gt']
        and rules['minimum_model_mass'] <= observation.model_mass <= rules['maximum_model_mass']
        and observation.bookmaker_count >= rules['minimum_bookmakers']
        and rules['minimum_odds'] <= observation.odds <= rules['maximum_odds']
        and -1 <= quote_age <= rules.get('maximum_quote_age_hours', 24)
        and (not rules.get('require_complete_vector') or complete_vector)
        and (not rules.get('require_complete_price_vector') or complete_prices)
    )


def choose_decisions(experiment=None, *, phase=None):
    """Freeze the closest eligible state outside the horizon, one bet/fixture."""
    experiment = experiment or ensure_experiment(ASIAN_HANDICAP_V2)
    rows = StrategyLabObservation.objects.filter(
        experiment=experiment,
        hours_to_kickoff__gte=experiment.decision_horizon_hours,
    )
    if phase:
        rows = rows.filter(evidence_phase=phase)
    rows = rows.order_by(
        'fixture_id', 'side', 'handicap', 'hours_to_kickoff', '-observed_at',
    )
    frozen_lines = {}
    for row in rows:
        key = (row.fixture_id, row.side, row.handicap)
        frozen_lines.setdefault(key, row)

    by_fixture = defaultdict(list)
    for row in frozen_lines.values():
        if qualifies(row):
            by_fixture[row.fixture_id].append(row)

    decisions = []
    for fixture_rows in by_fixture.values():
        fixture_rows.sort(key=lambda row: (
            -row.expected_return_lower,
            -row.bookmaker_count,
            abs(row.handicap or 0),
            row.side,
        ))
        decisions.append(fixture_rows[0])
    return decisions


def _handicap_legs(line):
    quarter = round(float(line) * 4) / 4
    doubled = abs(quarter * 2)
    if abs(doubled - round(doubled)) < 1e-9:
        return [quarter]
    return [quarter - .25, quarter + .25]


def unit_profit(side, handicap, odds, home_score, away_score):
    difference = home_score - away_score
    if side == 'away':
        difference *= -1
    profits = []
    for leg in _handicap_legs(handicap):
        adjusted = difference + leg
        profits.append(odds - 1 if adjusted > 0 else (-1 if adjusted < 0 else 0))
    return sum(profits) / len(profits)


def total_unit_profit(side, line, odds, goals):
    """Settle Asian whole/half/quarter totals as equal split stakes."""
    direction = side.rsplit('_', 1)[-1]
    profits = []
    for leg in _handicap_legs(line):
        difference = goals - leg if direction == 'over' else leg - goals
        profits.append(odds - 1 if difference > 0 else (-1 if difference < 0 else 0))
    return sum(profits) / len(profits)


def outcome_for(profit, odds):
    if math.isclose(profit, odds - 1, abs_tol=1e-9):
        return StrategyLabSettlement.OUTCOME_FULL_WIN
    if profit > 0:
        return StrategyLabSettlement.OUTCOME_HALF_WIN
    if math.isclose(profit, 0, abs_tol=1e-9):
        return StrategyLabSettlement.OUTCOME_PUSH
    if profit > -1:
        return StrategyLabSettlement.OUTCOME_HALF_LOSS
    return StrategyLabSettlement.OUTCOME_FULL_LOSS


def _score_by_description(raw_scores, descriptions):
    by_desc = {}
    for entry in raw_scores or []:
        desc = str(entry.get('description') or '').upper().replace(' ', '_')
        score = entry.get('score') or {}
        participant = score.get('participant')
        goals = score.get('goals')
        if participant in ('home', 'away') and isinstance(goals, int):
            by_desc.setdefault(desc, {})[participant] = goals
    for description in descriptions:
        score = by_desc.get(description)
        if score and 'home' in score and 'away' in score:
            return score['home'], score['away']
    return None


def _winner(home_score, away_score):
    return 'home' if home_score > away_score else ('away' if away_score > home_score else 'draw')


def _direct_win(observation, result):
    market = observation.market
    side = observation.side.lower()
    home, away = result.home_score, result.away_score
    total = home + away
    if market == '1x2':
        return side == _winner(home, away)
    if market == 'btts':
        return side == ('yes' if home > 0 and away > 0 else 'no')
    if market.startswith('over_under_'):
        line = float(market.rsplit('_', 1)[1])
        actual = 'over' if total > line else 'under'
        return side == actual
    if market == 'double_chance':
        winner = _winner(home, away)
        return winner in {
            '1x': ('home', 'draw'), 'x2': ('draw', 'away'), '12': ('home', 'away'),
        }.get(side, ())
    if market == 'correct_score':
        return side == f'{home}-{away}'
    if market in ('half_time_result', 'half_time_full_time'):
        half = _score_by_description(
            result.raw_scores,
            ('1ST_HALF', 'FIRST_HALF', 'HALFTIME', 'HALF_TIME', 'HT'),
        )
        if half is None:
            return None
        half_winner = _winner(*half)
        if market == 'half_time_result':
            return side == half_winner
        return side == f'{half_winner}_{_winner(home, away)}'
    return None


def profit_for_frozen_selection(*, market, side, line, odds, result):
    """Grade immutable market terms against one confirmed 90-minute result.

    Public selections and Strategy Lab decisions are separate ledgers.  A
    displayed public selection must therefore be settled from the exact market,
    side, line and price that were frozen when it was published — not from
    whichever StrategyLabObservation later became the experiment's canonical
    one-hour decision.
    """
    if market == 'asian_handicap':
        if line is None:
            return None
        return unit_profit(
            side, line, odds,
            result.home_score, result.away_score,
        )
    if market == 'asian_goal_line':
        if line is None:
            return None
        return total_unit_profit(
            side, line, odds,
            result.home_score + result.away_score,
        )
    if market == 'team_total_goals':
        if line is None:
            return None
        team = side.split('_', 1)[0]
        goals = result.home_score if team == 'home' else result.away_score
        return total_unit_profit(
            side, line, odds, goals,
        )

    # _direct_win deliberately reads only these plain settlement fields.  The
    # adapter prevents any mutable model or experimental qualification state
    # from entering the calculation.
    class FrozenTerms:
        pass

    terms = FrozenTerms()
    terms.market = market
    terms.side = side
    won = _direct_win(terms, result)
    if won is None:
        return None
    return odds - 1 if won else -1


def _profit_for(observation, result):
    return profit_for_frozen_selection(
        market=observation.market,
        side=observation.side,
        line=observation.handicap,
        odds=observation.odds,
        result=result,
    )


def _settle_one(experiment):
    decisions = choose_decisions(experiment)
    fixture_ids = {row.fixture_id for row in decisions}
    latest = {}
    for result in (
        FixtureResultObservation.objects
        .filter(fixture_id__in=fixture_ids)
        .order_by('fixture_id', '-result_version', '-captured_at')
    ):
        latest.setdefault(result.fixture_id, result)

    written = skipped = awaiting_result = ungradable = 0
    for decision in decisions:
        result = latest.get(decision.fixture_id)
        if not result or not result.confirmed or not result.is_scoreable:
            awaiting_result += 1
            continue
        if StrategyLabSettlement.objects.filter(observation=decision, result=result).exists():
            skipped += 1
            continue
        profit = _profit_for(decision, result)
        if profit is None:
            ungradable += 1
            continue
        digest = canonical_sha256({
            'v': 2,
            'observation': str(decision.observation_id),
            'result': str(result.result_id),
            'result_version': result.result_version,
            'home_score': result.home_score,
            'away_score': result.away_score,
            'unit_profit': norm_num(profit),
        })
        StrategyLabSettlement.objects.create(
            observation=decision,
            result=result,
            result_version=result.result_version,
            home_score=result.home_score,
            away_score=result.away_score,
            outcome=outcome_for(profit, decision.odds),
            unit_profit=profit,
            settlement_hash=digest,
        )
        written += 1
    return {
        'decisions': len(decisions), 'written': written, 'skipped': skipped,
        'awaiting_result': awaiting_result, 'ungradable': ungradable,
    }


def settle(experiment=None):
    """Settle one or every registered experiment against confirmed results."""
    experiments = [experiment] if experiment else ensure_all_experiments()
    totals = Counter()
    per_experiment = {}
    for item in experiments:
        summary = _settle_one(item)
        per_experiment[f'{item.strategy_key}:{item.version}'] = summary
        totals.update(summary)
    return {**dict(totals), 'experiments': per_experiment}


def _maximum_drawdown(settlements):
    balance = peak = drawdown = 0.0
    for row in settlements:
        balance += row.unit_profit
        peak = max(peak, balance)
        drawdown = max(drawdown, peak - balance)
    return drawdown


def _mean_ci(values, z=2.87):
    """Family-wise 95% interval for mean ROI across the registered family.

    2.87 is the two-sided Bonferroni critical value for roughly twelve
    simultaneous hypotheses. It is deliberately stricter than a standalone
    1.96 interval so adding markets cannot make a lucky strategy look proven.
    """
    count = len(values)
    if count < 2:
        return None
    mean = sum(values) / count
    variance = sum((value - mean) ** 2 for value in values) / (count - 1)
    margin = z * math.sqrt(variance / count)
    return [round(mean - margin, 4), round(mean + margin, 4)]


def _latest_settlements(decisions):
    decision_ids = {row.observation_id for row in decisions}
    latest = {}
    for row in (
        StrategyLabSettlement.objects
        .filter(observation_id__in=decision_ids)
        .select_related('observation')
        .order_by('observation_id', '-result_version', '-settled_at')
    ):
        latest.setdefault(row.observation_id, row)
    return sorted(latest.values(), key=lambda row: row.observation.kickoff)


def _closing_line_value(experiment, decisions):
    values = []
    for decision in decisions:
        close = (
            StrategyLabObservation.objects
            .filter(
                experiment=experiment,
                fixture_id=decision.fixture_id,
                side=decision.side,
                handicap=decision.handicap,
                evidence_phase=decision.evidence_phase,
                hours_to_kickoff__gte=0,
            )
            .order_by('hours_to_kickoff', '-observed_at')
            .first()
        )
        if close and close.odds > 1:
            values.append(decision.odds / close.odds - 1)
    return values


def _phase_report(experiment, phase):
    decisions = choose_decisions(experiment, phase=phase)
    settled = _latest_settlements(decisions)
    profits = [row.unit_profit for row in settled]
    closing_values = _closing_line_value(experiment, decisions)
    count = len(settled)
    total = sum(profits)
    midpoint = count // 2
    earlier = profits[:midpoint]
    later = profits[midpoint:]
    return {
        'observations': experiment.observations.filter(evidence_phase=phase).count(),
        'decisions': len(decisions),
        'settled': count,
        'pending': len(decisions) - count,
        'outcomes': dict(Counter(row.outcome for row in settled)),
        'total_profit_units': round(total, 4),
        'flat_stake_roi': round(total / count, 4) if count else None,
        'roi_mean_familywise_95': _mean_ci(profits),
        'time_split_roi': {
            'earlier': round(sum(earlier) / len(earlier), 4) if earlier else None,
            'later': round(sum(later) / len(later), 4) if later else None,
        },
        'maximum_drawdown_units': round(_maximum_drawdown(settled), 4),
        'mean_closing_line_value': (
            round(sum(closing_values) / len(closing_values), 4)
            if closing_values else None
        ),
        'closing_line_samples': len(closing_values),
        'leagues': dict(Counter(row.observation.league for row in settled)),
    }


def _experiment_report(experiment):
    retrospective = _phase_report(
        experiment, StrategyLabObservation.PHASE_RETROSPECTIVE,
    )
    forward = _phase_report(experiment, StrategyLabObservation.PHASE_FORWARD)
    roi_interval = forward['roi_mean_familywise_95']
    time_split = forward['time_split_roi']
    rules = experiment.rules
    gates = {
            'settlement_supported': bool(rules.get('settlement_supported')),
            'minimum_forward_sample': (
                forward['settled'] >= experiment.minimum_settled_for_review
            ),
            'forward_roi_confidence_lower_positive': bool(
                roi_interval and roi_interval[0] > 0
            ),
            'positive_in_both_forward_time_halves': bool(
                time_split['earlier'] is not None and time_split['earlier'] > 0
                and time_split['later'] is not None and time_split['later'] > 0
            ),
            'positive_forward_mean_clv': (
                forward['mean_closing_line_value'] is not None
                and forward['mean_closing_line_value'] > 0
            ),
            'drawdown_within_limit': (
                forward['settled'] > 0
                and forward['maximum_drawdown_units']
                <= rules.get('maximum_forward_drawdown_units', 20)
            ),
            'manual_methodology_review_completed': experiment.status in (
                StrategyLabExperiment.STATUS_CANDIDATE,
                StrategyLabExperiment.STATUS_VALIDATED,
            ),
        }
    return {
        'strategy_key': experiment.strategy_key,
        'version': experiment.version,
        'name': experiment.name,
        'market': experiment.market,
        'status': experiment.status,
        'rules_hash': experiment.rules_hash,
        'decision_horizon_hours': experiment.decision_horizon_hours,
        'minimum_forward_settled_for_review': experiment.minimum_settled_for_review,
        'retrospective_backtest': retrospective,
        'forward_validation': forward,
        'promotion_gates': gates,
        'promotion_ready': all(gates.values()),
        'observations': retrospective['observations'] + forward['observations'],
        'decisions': retrospective['decisions'] + forward['decisions'],
        'settled': retrospective['settled'] + forward['settled'],
        'warnings': [
            'Retrospective results can reject this strategy but cannot validate it.',
            'At most one fixed-horizon decision per fixture enters performance.',
            'No strategy is promoted automatically; manual review remains mandatory.',
        ],
    }


def build_report():
    """Private lab report with backtest and forward evidence kept separate."""
    experiments = ensure_all_experiments()
    reports = [_experiment_report(experiment) for experiment in experiments]
    return {
        'lab_version': 'strategies-lab-v2',
        'generated_at': timezone.now().isoformat(),
        'experiments': reports,
        'blocked_or_queued': list(BLOCKED_STRATEGIES),
        'policy': {
            'retrospective_role': 'screen_and_reject_only',
            'promotion_evidence': 'forward_only',
            'decision_unit': 'maximum_one_bet_per_fixture_per_strategy',
            'automatic_publication': False,
        },
    }


def build_public_report():
    """Return an intentionally narrow, read-only view of lab progress.

    The public endpoint never registers experiments and never exposes rules,
    hashes, prices, candidate fixtures, league splits or operational detail.
    Missing experiments therefore render as ``not_started`` instead of being
    created by an anonymous GET request.
    """
    wanted = {
        (definition['strategy_key'], definition['version']): definition
        for definition in STRATEGY_DEFINITIONS
    }
    existing = {
        (experiment.strategy_key, experiment.version): experiment
        for experiment in StrategyLabExperiment.objects.filter(
            strategy_key__in=[key for key, _version in wanted],
            version__in=[version for _key, version in wanted],
        )
    }
    settled_by_experiment = {
        row['observation__experiment_id']: row['settled']
        for row in (
            StrategyLabSettlement.objects
            .filter(
                observation__experiment_id__in=[
                    experiment.experiment_id for experiment in existing.values()
                ],
                observation__evidence_phase=StrategyLabObservation.PHASE_FORWARD,
            )
            .values('observation__experiment_id')
            .annotate(settled=Count('observation_id', distinct=True))
        )
    }
    strategies = []
    for identity, definition in wanted.items():
        experiment = existing.get(identity)
        if experiment is None:
            strategies.append({
                'strategy_key': definition['strategy_key'],
                'version': definition['version'],
                'market': definition['market'],
                'evidence_status': 'not_started',
                'forward_settled': 0,
                'minimum_forward_settled_for_review': definition['minimum_settled_for_review'],
                'evidence_progress_percent': 0,
                'promotion_ready': False,
            })
            continue

        evidence = _public_evidence_status(
            experiment,
            settled=settled_by_experiment.get(experiment.experiment_id, 0),
        )
        settled = evidence['forward_settled']
        strategies.append({
            'strategy_key': experiment.strategy_key,
            'version': experiment.version,
            'market': experiment.market,
            'evidence_status': evidence['evidence_status'],
            'forward_settled': settled,
            'minimum_forward_settled_for_review': experiment.minimum_settled_for_review,
            'evidence_progress_percent': min(
                100,
                round(100 * settled / experiment.minimum_settled_for_review),
            ),
            # Candidate/validated are explicit reviewed lifecycle states. The
            # expensive research gates remain in the private lab report and
            # never need to be recomputed in a visitor request.
            'promotion_ready': experiment.status in (
                StrategyLabExperiment.STATUS_CANDIDATE,
                StrategyLabExperiment.STATUS_VALIDATED,
            ),
        })
    return {
        'lab_version': 'strategies-lab-v2',
        'generated_at': timezone.now().isoformat(),
        'strategies': strategies,
        'policy': {
            'retrospective_role': 'screen_and_reject_only',
            'promotion_evidence': 'forward_only',
            'automatic_publication': False,
        },
    }


def _public_evidence_status(experiment, *, settled=None):
    """Summarise reviewed public state without rebuilding the private lab.

    ``_experiment_report`` walks every historical observation, settlement and
    closing-price candidate. That belongs in offline research, not in a public
    request. Public pages need only the distinct forward-settled count and the
    experiment's explicit reviewed lifecycle state.
    """
    if settled is None:
        settled = (
            StrategyLabSettlement.objects
            .filter(
                observation__experiment=experiment,
                observation__evidence_phase=StrategyLabObservation.PHASE_FORWARD,
            )
            .values('observation_id')
            .distinct()
            .count()
        )
    if experiment.status == StrategyLabExperiment.STATUS_VALIDATED:
        status = 'validated'
    elif experiment.status == StrategyLabExperiment.STATUS_CANDIDATE:
        status = 'review_ready'
    elif settled:
        status = 'collecting_evidence'
    else:
        status = 'insufficient_evidence'
    return {
        'evidence_status': status,
        'forward_settled': settled,
        'minimum_forward_settled_for_review': experiment.minimum_settled_for_review,
    }


def _market_probability(observation):
    """Return the selected outcome's de-vigged market probability if valid."""
    signal = observation.source_signal
    if signal is None or not signal.price_vector_complete:
        return None
    vector = signal.market_price_vector
    if not isinstance(vector, dict) or observation.side not in vector:
        return None
    implied = {}
    try:
        for outcome, entry in vector.items():
            odds = float(entry.get('odds') if isinstance(entry, dict) else entry)
            if not math.isfinite(odds) or odds <= 1:
                return None
            implied[outcome] = 1 / odds
    except (TypeError, ValueError):
        return None
    total = sum(implied.values())
    if total <= 0:
        return None
    return implied[observation.side] / total


def _public_probability_summary(observation):
    """Expose probability context only where the stored evidence supports it."""
    payload = observation.selection_payload or {}
    probability = payload.get('normalized_probability')
    if probability is not None:
        try:
            probability = float(probability)
        except (TypeError, ValueError):
            probability = None
    if probability is not None and 0 < probability <= 1:
        market_probability = _market_probability(observation)
        return {
            'kind': 'point_estimate',
            'model_probability_percent': round(probability * 100, 1),
            'model_probability_low_percent': None,
            'model_probability_high_percent': None,
            'model_fair_odds': round(1 / probability, 2),
            'market_no_vig_probability_percent': (
                round(market_probability * 100, 1)
                if market_probability is not None else None
            ),
            'score_distribution_coverage_percent': None,
        }

    # Specialist markets calculate conservative lower/upper expected-return
    # bounds from the enumerated score distribution. Algebraically recovering
    # the probability bounds is safe; presenting either bound as an exact
    # probability would not be.
    try:
        low = (float(observation.expected_return_lower) + 1) / observation.odds
        high = (float(observation.expected_return_upper) + 1) / observation.odds
    except (TypeError, ValueError, ZeroDivisionError):
        low = high = None
    if low is not None:
        low = min(1.0, max(0.0, low))
        high = min(1.0, max(low, high))
    return {
        'kind': 'bounded_score_distribution',
        'model_probability_percent': None,
        'model_probability_low_percent': round(low * 100, 1) if low is not None else None,
        'model_probability_high_percent': round(high * 100, 1) if high is not None else None,
        'model_fair_odds': None,
        'market_no_vig_probability_percent': None,
        'score_distribution_coverage_percent': round(observation.model_mass * 100, 1),
    }


def _fit_rank(observation):
    """Deterministic internal ordering; scores are deliberately not public."""
    price_width = max(0.0, observation.price_max - observation.price_min)
    return (
        observation.expected_return_lower,
        observation.bookmaker_count,
        -price_width,
        observation.observed_at.timestamp(),
        -abs(observation.handicap or 0),
    )


def build_public_current_fits(strategy_key, *, limit=5):
    """Return up to five fresh fixtures that pass one registered strategy.

    This is a read-only, allowlisted projection of forward observations. It
    never exposes private rules, internal scores or unqualified candidates.
    The scheduler freezes every displayed fit into the separate Strategy
    Results record before kickoff. One fixture can occupy at most one position
    on a strategy page.
    """
    limit = min(5, max(1, int(limit)))
    definition = next((
        item for item in STRATEGY_DEFINITIONS
        if item['strategy_key'] == strategy_key
    ), None)
    if definition is None:
        return None

    experiment = StrategyLabExperiment.objects.filter(
        strategy_key=definition['strategy_key'],
        version=definition['version'],
    ).first()
    now = timezone.now()
    if experiment is None:
        return {
            'strategy_key': definition['strategy_key'],
            'version': definition['version'],
            'market': definition['market'],
            'evidence_status': 'not_started',
            'generated_at': now.isoformat(),
            'eligible_fixture_count': 0,
            'fits': [],
            'policy': {
                'maximum_fits': 5,
                'empty_is_valid': True,
                'fit_is_public_pick': True,
                'fit_enters_strategy_results': True,
            },
        }

    maximum_age = experiment.rules.get('maximum_quote_age_hours', 24)
    rows = experiment.observations.filter(
        evidence_phase=StrategyLabObservation.PHASE_FORWARD,
        kickoff__gt=now,
        odds_captured_at__gte=now - timedelta(hours=maximum_age),
        odds_captured_at__lte=now + timedelta(minutes=5),
    ).select_related('experiment', 'source_signal').order_by(
        'fixture_id', 'side', 'handicap', '-observed_at',
    )

    # First freeze the latest state of each candidate line. If its newest state
    # no longer qualifies, an older, more flattering quote cannot resurface.
    latest_lines = {}
    for row in rows:
        identity = (row.fixture_id, row.side, row.handicap)
        latest_lines.setdefault(identity, row)

    by_fixture = defaultdict(list)
    for row in latest_lines.values():
        if qualifies(row):
            by_fixture[row.fixture_id].append(row)

    chosen = [max(fixture_rows, key=_fit_rank) for fixture_rows in by_fixture.values()]
    chosen.sort(key=lambda row: (_fit_rank(row), -row.kickoff.timestamp()), reverse=True)

    fits = []
    specialist = definition.get('source') == 'specialist_candidate'
    for rank, row in enumerate(chosen[:limit], start=1):
        probability = _public_probability_summary(row)
        fits.append({
            'rank': rank,
            'fixture_id': row.fixture_id,
            'home_team': row.home_team,
            'away_team': row.away_team,
            'league': row.league,
            'kickoff': row.kickoff.isoformat(),
            'market': row.market,
            'selection': row.label,
            'side': row.side,
            'line': row.handicap,
            'odds': round(row.odds, 2),
            'bookmaker': row.bookmaker,
            'bookmaker_count': row.bookmaker_count,
            'price_captured_at': row.odds_captured_at.isoformat(),
            'observed_at': row.observed_at.isoformat(),
            'break_even_probability_percent': round(100 / row.odds, 1),
            'probability': probability,
            'qualification': 'registered_rules_passed',
            'fit_reasons': [
                'fresh_verified_price',
                'multi_bookmaker_confirmation',
                ('exact_settlement_distribution' if specialist
                 else 'complete_model_and_price_vectors'),
                'conservative_value_threshold_passed',
            ],
            'caveats': [
                'price_can_move',
                'strategy_not_validated' if experiment.status != StrategyLabExperiment.STATUS_VALIDATED
                else 'strategy_evidence_still_not_a_guarantee',
                ('bounded_score_model' if specialist else 'model_estimate_not_calibrated'),
            ],
        })

    evidence = _public_evidence_status(experiment)
    return {
        'strategy_key': experiment.strategy_key,
        'version': experiment.version,
        'market': experiment.market,
        **evidence,
        'generated_at': now.isoformat(),
        'eligible_fixture_count': len(chosen),
        'fits': fits,
        'policy': {
            'maximum_fits': 5,
            'empty_is_valid': True,
            'fit_is_public_pick': True,
            'fit_enters_strategy_results': True,
            'one_fit_per_fixture': True,
            'prices_must_be_fresh_and_verified': True,
        },
    }


HOMEPAGE_STRATEGY_ORDER = (
    'asian-handicap-score-distribution',
    'total-goals-2-5-value',
    'full-time-result-value',
    'both-teams-score-value',
    'asian-goal-line-score-distribution',
    'team-total-score-distribution',
    'double-chance-value',
    'total-goals-1-5-value',
    'total-goals-3-5-value',
)


def build_public_strategy_highlights(*, limit=3):
    """Select a small, diverse homepage view of current research fits.

    Each strategy contributes at most its strongest current fit and each
    fixture can appear only once. The ordering deliberately alternates market
    families; fit scores from different registered strategies are not treated
    as directly comparable. This endpoint is only a projection of the same
    public research rows used on strategy pages and never publishes a Gem.
    """
    limit = min(3, max(1, int(limit)))
    highlights = []
    seen_fixtures = set()

    for strategy_key in HOMEPAGE_STRATEGY_ORDER:
        report = build_public_current_fits(strategy_key, limit=1)
        if not report or not report['fits']:
            continue
        fit = report['fits'][0]
        if fit['fixture_id'] in seen_fixtures:
            continue
        seen_fixtures.add(fit['fixture_id'])
        highlights.append({
            'strategy_key': report['strategy_key'],
            'version': report['version'],
            'market': report['market'],
            'evidence_status': report['evidence_status'],
            'generated_at': report['generated_at'],
            'fit': fit,
        })
        if len(highlights) == limit:
            break

    return {
        'generated_at': timezone.now().isoformat(),
        'highlights': highlights,
        'policy': {
            'maximum_highlights': 3,
            'one_fit_per_strategy': True,
            'one_fit_per_fixture': True,
            'fit_is_public_pick': False,
            'empty_is_valid': True,
        },
    }
