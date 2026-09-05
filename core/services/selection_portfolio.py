"""One publication path for market discovery, homepage and their forward record.

All reads use stored pre-match evidence. Only the scheduler publishes; GETs
never select, reprice or insert. A homepage appearance reuses a market receipt.
"""
import math
from collections import Counter, defaultdict
from datetime import timedelta
from functools import lru_cache

from django.db import transaction
from django.utils import timezone

from core.models import (
    FixtureContextObservation, FixtureResultObservation, GemFeedCache, HomepageSelectionAppearance,
    PublicSelection, SelectionBoard, SignalObservation, StrategyLabObservation,
)
from core.services import public_selections, strategy_lab
from core.services.integrity import canonical_sha256

VERSION = 'market-portfolio-v5'
POLICY = {
    'version': VERSION, 'per_market': 5, 'homepage': 5,
    'minimum_lead_hours': 1, 'maximum_lead_hours': 72,
    'maximum_quote_age_hours': 2, 'minimum_books': 3,
    'maximum_price_spread': 0.20,
    'minimum_model_ev': 0.03, 'maximum_model_ev': 0.50,
    'minimum_odds': 1.30, 'maximum_odds': 12,
    'correct_score_maximum_odds': 30,
    'specialist_minimum_mass': 0.975,
    'specialist_ev_stress': 0.10,
    'minimum_calibration_sample': 30,
    'calibration_maximum_model_weight': 0.5,
    'calibration_prior_strength': 50, 'calibration_lower_bound_z': 1.28,
    'calibration_start': '2026-08-26T00:00:00+00:00',
    'ranking': 'conservative_return_then_price_coverage_then_kickoff',
    'research_requires_positive_model_ev': True,
    'research_may_have_negative_conservative_ev': True,
}
POLICY_HASH = canonical_sha256(POLICY)

# Markets without a deterministic captured-result contract stay visible in the
# coverage list, with an explicit reason. They cannot quietly enter a record.
MARKETS = {
    '1x2': ('Match result', 'Rezultat final', 'match-result'),
    'btts': ('Both teams to score', 'Ambele echipe marchează', 'both-teams-to-score'),
    'over_under_1.5': ('Goals 1.5', 'Goluri 1,5', 'total-goals-1-5'),
    'over_under_2.5': ('Goals 2.5', 'Goluri 2,5', 'total-goals-2-5'),
    'over_under_3.5': ('Goals 3.5', 'Goluri 3,5', 'total-goals-3-5'),
    'double_chance': ('Double chance', 'Șansă dublă', 'double-chance'),
    'correct_score': ('Correct score', 'Scor corect', 'correct-score'),
    'half_time_result': ('Half-time result', 'Rezultat la pauză', 'half-time-result'),
    'half_time_full_time': ('Half-time / full-time', 'Pauză / final', 'half-time-full-time'),
    'asian_handicap': ('Asian handicap', 'Handicap asiatic', 'asian-handicap'),
    'asian_goal_line': ('Asian goal lines', 'Total asiatic', 'asian-goal-lines'),
    'team_total_goals': ('Team goals', 'Golurile echipei', 'team-total-goals'),
}
UNAVAILABLE = {
    'first_team_to_score': 'first_goal_result_contract_missing',
    'corners': 'model_and_result_contract_missing',
    'cards': 'model_and_result_contract_missing',
    'player_props': 'model_and_result_contract_missing',
}
SPECIALISTS = {'asian_handicap', 'asian_goal_line', 'team_total_goals'}
DIRECT_PRICE_IDS = {
    '1x2': {1}, 'btts': {14}, 'double_chance': {2}, 'correct_score': {57},
    'half_time_result': {31}, 'half_time_full_time': {29},
    'over_under_1.5': {7, 80}, 'over_under_2.5': {7, 80}, 'over_under_3.5': {7, 80},
}


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


@lru_cache(maxsize=128)
def calibration_pairs(market, outcome, as_of):
    """One decision per fixture; only results actually available at as_of."""
    signals = SignalObservation.objects.filter(
        market=market, outcome=outcome, vector_complete=True,
        observed_at__gte=POLICY['calibration_start'], observed_at__lt=as_of,
        kickoff__lt=as_of, hours_to_kickoff__gte=1,
    ).only('fixture_id', 'normalized_probability', 'observed_at', 'kickoff', 'hours_to_kickoff').order_by('fixture_id', 'hours_to_kickoff', '-observed_at')
    chosen = {}
    for signal in signals.iterator():
        if signal.observed_at <= signal.kickoff - timedelta(hours=1):
            chosen.setdefault(signal.fixture_id, signal)
    results = {}
    # Select latest known version BEFORE checking finality. A newer correction
    # that retracts a final must not resurrect an older scoreable result.
    for result in FixtureResultObservation.objects.filter(
        fixture_id__in=chosen, captured_at__lt=as_of,
    ).order_by('fixture_id', '-result_version', '-captured_at'):
        results.setdefault(result.fixture_id, result)
    pairs = []
    for fixture_id, signal in chosen.items():
        result = results.get(fixture_id)
        if result is None or not result.confirmed or not result.is_scoreable:
            continue
        profit = strategy_lab.profit_for_frozen_selection(
            market=market, side=outcome, line=None, odds=2, result=result,
        )
        if profit is not None:
            pairs.append((signal.normalized_probability, int(profit > 0)))
    return tuple(pairs)


def probability_context(signal, as_of):
    if signal.market == 'double_chance':
        # DC outcomes overlap. Derive their baseline from the same fixture's
        # complete 1X2 book instead of treating the three DC odds as exclusive.
        vector = getattr(signal, '_portfolio_x12_vector', None)
        baseline = None if vector else SignalObservation.objects.filter(
            fixture_id=signal.fixture_id, market='1x2', outcome='home',
            observed_at__lte=as_of, odds_captured_at__lte=as_of,
            odds_captured_at__gte=as_of - timedelta(hours=2),
            price_vector_complete=True, provenance_complete=True,
        ).order_by('-observed_at').first()
        if baseline is None and not vector:
            return None
        vector = vector or baseline.market_price_vector
        try:
            implied = {key: 1 / float(vector[key]['odds'] if isinstance(vector[key], dict) else vector[key])
                       for key in ('home', 'draw', 'away')}
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            return None
        if any(not math.isfinite(p) or not 0 < p < 1 for p in implied.values()):
            return None
        legs = {'1x': ('home', 'draw'), 'x2': ('draw', 'away'), '12': ('home', 'away')}
        if signal.outcome not in legs:
            return None
        market = sum(implied[k] for k in legs[signal.outcome]) / sum(implied.values())
    else:
        if set(signal.raw_vector or {}) - set(signal.market_price_vector or {}):
            return None
        market = strategy_lab._signal_market_probability(signal)
    if market is None:
        return None
    pairs = [(p, actual) for p, actual in calibration_pairs(signal.market, signal.outcome, as_of)
             if _finite(p) and abs(p - signal.normalized_probability) <= .10]
    count = len(pairs)
    empirical = (sum(actual for _, actual in pairs) + 2) / (count + 4)
    weight = min(POLICY['calibration_maximum_model_weight'], count / 200)
    estimate = (1 - weight) * market + weight * empirical
    uncertainty = max(.02, POLICY['calibration_lower_bound_z'] * math.sqrt(
        estimate * (1 - estimate) / (count + POLICY['calibration_prior_strength'])))
    return {'market_probability': market, 'conservative_probability': max(0, estimate - uncertainty),
            'calibration_observations': count}


def _context_summary(context):
    if context is None:
        return {'lineups': 'unavailable', 'observed_at': None, 'form_available': False,
                'absences_available': False, 'absence_count': None}
    availability = context.data_availability or {}
    return {
        'lineups': context.lineup_status,
        'observed_at': context.observed_at.isoformat(),
        'form_available': bool(context.home_form and context.away_form),
        'home_form': context.home_form or None, 'away_form': context.away_form or None,
        'absences_available': bool(availability.get('sidelined') or context.sidelined),
        'absence_count': len(context.sidelined) if context.sidelined else None,
        'neutral_venue': context.neutral_venue,
    }


def candidate_from_observation(row, now, context=None):
    """Return a qualified research candidate plus a single rejection code.

    Qualification establishes a priceable, settleable research hypothesis.
    Conservative EV and sample size determine its evidence label; raw EV is
    never represented as demonstrated profitability.
    """
    if row.market not in MARKETS:
        return None, 'unsupported_market'
    if row.evidence_phase != StrategyLabObservation.PHASE_FORWARD:
        return None, 'retrospective'
    hours = (row.kickoff - now).total_seconds() / 3600
    age = (now - row.odds_captured_at).total_seconds() / 3600
    if not POLICY['minimum_lead_hours'] <= hours <= POLICY['maximum_lead_hours']:
        return None, 'kickoff_window'
    if row.observed_at > now or age < 0 or age > POLICY['maximum_quote_age_hours']:
        return None, 'stale_price'
    maximum_odds = POLICY['correct_score_maximum_odds'] if row.market == 'correct_score' else POLICY['maximum_odds']
    if not _finite(row.odds) or not POLICY['minimum_odds'] <= row.odds <= maximum_odds:
        return None, 'odds_range'
    if row.bookmaker_count < POLICY['minimum_books']:
        return None, 'bookmaker_coverage'
    if not all(_finite(n) and n > 1 for n in (row.price_min, row.price_max)):
        return None, 'invalid_price_range'
    spread = (row.price_max - row.price_min) / row.price_min
    if spread < 0 or spread > POLICY['maximum_price_spread']:
        return None, 'price_disagreement'
    if context is not None and context.fixture_predictable is False:
        return None, 'fixture_unpredictable'

    probability = market_probability = conservative_probability = None
    calibration_count = 0
    if row.market in SPECIALISTS:
        if (row.source_signal_id is not None or not _finite(row.handicap)
                or not _finite(row.model_mass) or not POLICY['specialist_minimum_mass'] <= row.model_mass <= 1.001
                or row.market_id not in {
                    'asian_handicap': {6, 104}, 'asian_goal_line': {7, 105},
                    'team_total_goals': {86},
                }[row.market]):
            return None, 'specialist_evidence'
        # Quarter lines include refunds and split stakes: EV cannot be inverted
        # into a win probability using (EV+1)/odds.
        model_ev = row.expected_return_lower
        conservative_ev = model_ev - POLICY['specialist_ev_stress']
        method = 'score_distribution_stress'
    else:
        signal = row.source_signal
        if (signal is None or not signal.vector_complete or not signal.price_vector_complete
                or not signal.provenance_complete or signal.price_status != 'verified'):
            return None, 'incomplete_evidence'
        provenance = row.price_provenance or {}
        if (provenance.get('odds_market_id') not in DIRECT_PRICE_IDS[row.market]
                or provenance.get('odds_fixture_id', row.fixture_id) != row.fixture_id):
            return None, 'wrong_price_market'
        if row.market.startswith('over_under_') and provenance.get('odds_line') != float(row.market.rsplit('_', 1)[-1]):
            return None, 'wrong_price_line'
        if signal.fixture_id != row.fixture_id or signal.market != row.market or signal.outcome != row.side:
            return None, 'inconsistent_selection'
        expected_mass = 2 if row.market == 'double_chance' else 1
        vector = signal.raw_vector or {}
        if (not vector or any(not _finite(p) or not 0 <= p <= 1 for p in vector.values())
                or abs(sum(vector.values()) - expected_mass) > 0.02
                or signal.outcome not in vector):
            return None, 'incomplete_probability_vector'
        probability = signal.normalized_probability
        if not _finite(probability) or not 0 < probability < 1:
            return None, 'invalid_probability'
        if abs(vector[signal.outcome] - probability) > 0.001:
            return None, 'inconsistent_probability'
        model_ev = probability * row.odds - 1
        calibrated = probability_context(signal, now)
        if calibrated:
            market_probability = calibrated['market_probability']
            conservative_probability = calibrated['conservative_probability']
            conservative_ev = conservative_probability * row.odds - 1
            calibration_count = calibrated['calibration_observations']
            method = 'market_shrunk_calibration'
        else:
            # Without a defensible market baseline we cannot compare EV across
            # markets. Missing inputs never receive a favourable fallback.
            return None, 'market_baseline_missing'
    if not _finite(model_ev) or not _finite(conservative_ev):
        return None, 'invalid_ev'
    if model_ev < POLICY['minimum_model_ev']:
        return None, 'model_edge_too_small'
    if model_ev > POLICY['maximum_model_ev']:
        return None, 'model_edge_outlier'

    evidence = {
        'source_observation': str(row.observation_id),
        'source_hash': row.source_payload_hash,
        'quote_evidence': row.price_provenance,
        'quote_evidence_hash': getattr(row, '_current_quote_hash', row.source_payload_hash),
        'model_probability': probability, 'market_probability': market_probability,
        'conservative_probability': conservative_probability,
        'model_ev': model_ev, 'conservative_ev': conservative_ev,
        'calibration_count': calibration_count, 'probability_method': method,
        'score_coverage': row.model_mass if row.market in SPECIALISTS else None,
        'price_spread': spread, 'context': _context_summary(context),
        'evidence_label': 'price_edge' if (
            calibration_count >= POLICY['minimum_calibration_sample'] and conservative_ev > 0
        ) else 'research',
    }
    return {'observation': row, 'evidence': evidence}, None


def rank(candidate):
    row, evidence = candidate['observation'], candidate['evidence']
    return (-evidence['conservative_ev'], -row.bookmaker_count,
            evidence['price_spread'], row.kickoff, row.fixture_id, row.market, row.side, row.handicap or 0)


def refresh_quote(row, fresh, now):
    """Refresh an in-memory projection from the current signed-in worker feed.

    The archived observation is never updated. The immutable board will retain
    the complete current quote evidence used to freeze a new public selection.
    """
    observed = public_selections._aware(fresh.get('observed_at'))
    kickoff = public_selections._aware(fresh.get('kickoff'))
    if (not observed or observed > now or now - observed > timedelta(hours=3)
            or kickoff != row.kickoff or fresh.get('odds') != row.odds):
        return False
    if row.source_signal_id:
        signal = row.source_signal
        if (fresh.get('fixture_id') != row.fixture_id or fresh.get('market') != row.market
                or fresh.get('outcome') != row.side
                or fresh.get('raw_vector') != signal.raw_vector
                or fresh.get('normalized_probability') != signal.normalized_probability):
            return False
        captured = public_selections._aware(fresh.get('odds_captured_at'))
        provenance = fresh.get('odds_provenance') or {}
        signal.market_price_vector = fresh.get('market_price_vector')
        signal.price_vector_complete = bool(fresh.get('price_vector_complete'))
        signal.vector_complete = bool(fresh.get('vector_complete'))
        signal.price_status = fresh.get('price_status')
        signal.provenance_complete = bool(provenance)
        row.price_min = provenance.get('odds_min', 0)
        row.price_max = provenance.get('odds_max', 0)
        row.bookmaker_count = int(provenance.get('odds_bookmaker_count') or 0)
        row.bookmaker = fresh.get('bookmaker') or ''
        if (fresh.get('provider_context') or {}).get('fixture_predictable') is False:
            return False
    else:
        if strategy_lab.observation_hash(fresh, row.experiment) != row.source_payload_hash:
            return False
        captured = public_selections._aware(fresh.get('captured_at'))
        provenance = fresh.get('price_provenance') or {}
    if captured is None:
        return False
    row.odds_captured_at = captured
    row.price_provenance = provenance
    row._current_quote_hash = canonical_sha256(fresh)
    return True


def choose_boards(candidates):
    """One side/line per fixture in each market; no forced market diversity."""
    boards = {market: [] for market in MARKETS}
    seen = defaultdict(set)
    for candidate in sorted(candidates, key=rank):
        row = candidate['observation']
        if row.fixture_id in seen[row.market] or len(boards[row.market]) >= POLICY['per_market']:
            continue
        boards[row.market].append(candidate)
        seen[row.market].add(row.fixture_id)
    return boards


def _freeze(candidate, now):
    row = candidate['observation']
    return public_selections._create_selection(
        category=PublicSelection.CATEGORY_STRATEGY,
        source_key=f'{VERSION}:{row.market}', source_version=POLICY_HASH,
        source_ref=f'{VERSION}:{row.market}:{row.fixture_id}',
        reason_code=PublicSelection.REASON_VALUE if candidate['evidence']['evidence_label'] == 'price_edge' else PublicSelection.REASON_STRATEGY,
        source_strategy_observation=row,
        fixture_id=row.fixture_id, home_team=row.home_team, away_team=row.away_team,
        league=row.league, league_id=row.league_id, kickoff=row.kickoff,
        market_type=row.market, predicted_outcome=row.label, side=row.side,
        line=row.handicap, model_score=candidate['evidence']['model_probability'],
        odds=row.odds, bookmaker=row.bookmaker, bookmaker_count=row.bookmaker_count,
        odds_captured_at=row.odds_captured_at, published_at=now,
    )


@transaction.atomic
def publish_portfolio(now=None):
    now = now or timezone.now()
    # The scheduler already owns the expensive scan. Lock its cache row to
    # serialize publication and reject old evidence following a failed scan.
    cache = GemFeedCache.objects.select_for_update().filter(key='portfolio_input').first()
    if cache is None or now - cache.generated_at > timedelta(hours=3) or cache.generated_at > now:
        return {'published': 0, 'status': 'scan_unavailable'}
    previous_board = SelectionBoard.objects.filter(version=VERSION).first()
    if previous_board and previous_board.payload.get('policy_hash') != POLICY_HASH:
        raise ValueError('Portfolio rules changed: register a new version before publication')
    calibration_pairs.cache_clear()
    from core.services.evidence_capture import observation_hash
    inputs = cache.payload or {}
    direct_inputs = {observation_hash(c): c for c in inputs.get('candidates', [])}
    current_x12 = {}
    for c in inputs.get('candidates', []):
        captured = public_selections._aware(c.get('odds_captured_at'))
        if (c.get('market') == '1x2' and c.get('outcome') == 'home'
                and c.get('price_vector_complete') and c.get('odds_provenance')
                and captured and now - timedelta(hours=2) <= captured <= now):
            current_x12[c.get('fixture_id')] = c.get('market_price_vector')
    specialist_inputs = {}
    for c in inputs.get('strategy_candidates', []):
        specialist_inputs[(c.get('fixture_id'), c.get('market_id'), c.get('side'), c.get('handicap'))] = c
    observations = StrategyLabObservation.objects.filter(
        evidence_phase=StrategyLabObservation.PHASE_FORWARD,
        kickoff__gte=now + timedelta(hours=1), kickoff__lte=now + timedelta(hours=72),
        observed_at__lte=now,
    ).select_related('source_signal', 'experiment').order_by('-observed_at', '-pk')
    latest = {}
    for row in observations.iterator():
        # Multiple experiments may refer to the same signal; evaluate each
        # current fixture/market/side/line once, independent of old promotions.
        latest.setdefault((row.fixture_id, row.market, row.side, row.handicap), row)
    contexts = {}
    for context in FixtureContextObservation.objects.filter(
        fixture_id__in={row.fixture_id for row in latest.values()}, observed_at__lte=now,
    ).order_by('-observed_at'):
        contexts.setdefault(context.fixture_id, context)
    previous = { (s.fixture_id, s.market_type): s for s in PublicSelection.objects.filter(
        source_key__startswith=f'{VERSION}:', kickoff__gt=now,
    ) }
    candidates, reasons = [], Counter()
    evaluated = Counter()
    for row in latest.values():
        evaluated[row.market] += 1
        fresh = direct_inputs.get(row.source_signal.source_payload_hash) if row.source_signal_id else specialist_inputs.get((row.fixture_id, row.market_id, row.side, row.handicap))
        try:
            quote_ready = bool(fresh and refresh_quote(row, fresh, now))
        except (TypeError, ValueError, KeyError, OverflowError):
            quote_ready = False
        if not quote_ready:
            reasons['missing_current_evidence'] += 1
            continue
        if row.source_signal_id:
            row.source_signal._portfolio_x12_vector = current_x12.get(row.fixture_id)
        candidate, reason = candidate_from_observation(row, now, contexts.get(row.fixture_id))
        if candidate is None:
            reasons[reason] += 1
            continue
        frozen = previous.get((row.fixture_id, row.market))
        if frozen and (frozen.side != row.side or frozen.line != row.handicap or frozen.source_version != POLICY_HASH):
            reasons['already_published_other_terms'] += 1
            continue
        candidates.append(candidate)
    boards = choose_boards(candidates)
    published, cards = 0, {}
    market_ids = {}
    ranked = []
    for market, pool in boards.items():
        market_ids[market] = []
        for candidate in pool:
            selection, created = _freeze(candidate, now)
            published += int(created)
            selection_id = str(selection.selection_id)
            # The record always shows original odds; current evidence may
            # refresh only in this new immutable board snapshot.
            cards[selection_id] = {
                'selection_id': selection_id, 'evidence': candidate['evidence'],
                'current_odds': candidate['observation'].odds,
                'current_bookmaker_count': candidate['observation'].bookmaker_count,
                'current_price_at': candidate['observation'].odds_captured_at.isoformat(),
            }
            candidate['selection_id'] = selection_id
            market_ids[market].append(selection_id)
            ranked.append(candidate)
    previous_home = dict(HomepageSelectionAppearance.objects.filter(version=VERSION).values_list('fixture_id', 'selection_id'))
    homepage, seen = [], set()
    for candidate in sorted(ranked, key=rank):
        fixture_id = candidate['observation'].fixture_id
        identity = candidate['selection_id']
        if fixture_id in seen or (fixture_id in previous_home and str(previous_home[fixture_id]) != identity):
            continue
        homepage.append(identity)
        seen.add(fixture_id)
        if len(homepage) == POLICY['homepage']:
            break
    payload = {
        'policy': POLICY, 'policy_hash': POLICY_HASH, 'cards': cards,
        'markets': market_ids, 'homepage': homepage,
        'scan': {'fixtures_scanned': inputs.get('fixtures_seen', 0),
                 'fixtures_evaluated': len({r.fixture_id for r in latest.values()}),
                 'candidates_evaluated': len(latest), 'eligible_candidates': len(candidates),
                 'published_on_board': len(cards), 'market_candidates': dict(evaluated),
                 'rejections': dict(reasons), 'scan_at': cache.generated_at.isoformat()},
    }
    digest = canonical_sha256({'version': VERSION, 'at': now.isoformat(), 'payload': payload})
    board, _ = SelectionBoard.objects.get_or_create(evidence_hash=digest, defaults={
        'version': VERSION, 'generated_at': now, 'payload': payload,
    })
    for selection_id in homepage:
        selection = PublicSelection.objects.get(pk=selection_id)
        HomepageSelectionAppearance.objects.get_or_create(
            version=VERSION, fixture_id=selection.fixture_id,
            defaults={'selection': selection, 'board': board, 'published_at': now},
        )
    return {'published': published, 'status': 'ok', 'markets': len(cards), 'homepage': len(homepage)}


def read_portfolio(now=None):
    now = now or timezone.now()
    board = SelectionBoard.objects.filter(version=VERSION).first()
    payload = board.payload if board else {}
    valid_hash = board and board.evidence_hash == canonical_sha256({
        'version': board.version, 'at': board.generated_at.isoformat(), 'payload': payload,
    })
    stale = not valid_hash or board.generated_at > now or now - board.generated_at > timedelta(hours=2)
    raw_cards = payload.get('cards', {})
    selections = PublicSelection.objects.filter(pk__in=raw_cards).select_related('result', 'closing_price')
    cards = {}
    if not stale:
        for selection in selections:
            raw = raw_cards[str(selection.pk)]
            price_at = public_selections._aware(raw.get('current_price_at'))
            if (selection.kickoff <= now or not price_at or price_at > now
                    or now - price_at > timedelta(hours=POLICY['maximum_quote_age_hours'])):
                continue
            if not selection.verify_integrity():
                continue
            card = public_selections.serialize_selection(selection)
            cards[str(selection.pk)] = {**card, **raw}
    markets = [{
        'key': market, 'name': {'en': names[0], 'ro': names[1]},
        'strategy_url': f'/strategies/{names[2]}',
        'status': 'delayed' if stale else 'ready',
        'selections': [cards[i] for i in payload.get('markets', {}).get(market, []) if i in cards],
        'evaluated': payload.get('scan', {}).get('market_candidates', {}).get(market, 0),
    } for market, names in MARKETS.items()]
    return {'success': True, 'version': VERSION, 'policy_hash': POLICY_HASH,
            'generated_at': board.generated_at.isoformat() if board else None,
            'status': 'delayed' if stale else 'ready',
            'homepage': [cards[i] for i in payload.get('homepage', []) if i in cards],
            'markets': markets, 'unavailable_markets': UNAVAILABLE,
            'scan': payload.get('scan', {}), 'policy': POLICY}


def read_results():
    rows = [public_selections.serialize_selection(s) for s in PublicSelection.objects.filter(
        source_key__startswith=f'{VERSION}:',
    ).select_related('result', 'closing_price').order_by('-published_at')]
    homepage = set(str(pk) for pk in HomepageSelectionAppearance.objects.filter(version=VERSION).values_list('selection_id', flat=True))
    for row in rows:
        row['homepage'] = row['selection_id'] in homepage
    return {'success': True, 'version': VERSION, 'selections': rows,
            'performance': public_selections.performance_report(rows),
            'homepage_performance': public_selections.performance_report([r for r in rows if r['homepage']]),
            'policy': {'flat_stake_units': 1, 'homepage_is_subset': True,
                       'sample_review_threshold': 30, 'roi_is_realized_not_forecast': True}}
