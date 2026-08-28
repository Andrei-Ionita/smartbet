"""Publication and settlement for homepage and named-strategy selections.

This record deliberately does not reuse ``PublishedClaim``. Gems are the rare,
strictly-qualified claim tier. Homepage and strategy selections are broader
public selections whose value is accountability: once displayed, they stay in
Results and are graded at the frozen price and market.
"""

import logging
from datetime import timedelta, timezone as dt_timezone

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.models import (
    FixtureResultObservation,
    GemFeedCache,
    PublicSelection,
    PublicSelectionResult,
    StrategyLabExperiment,
    StrategyLabObservation,
    StrategyLabSettlement,
)
from core.services import market_evaluation, strategy_lab

logger = logging.getLogger(__name__)

HOMEPAGE_LIMIT = 5
STRATEGY_LIMIT = 5
MINIMUM_LEAD = timedelta(hours=1)
MAXIMUM_PRICE_AGE = timedelta(hours=24)


def _aware(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = parse_datetime(value.replace('Z', '+00:00'))
    if value is None:
        return None
    if timezone.is_naive(value):
        return timezone.make_aware(value, dt_timezone.utc)
    return value


def _valid_publication_times(kickoff, captured, now):
    return bool(
        kickoff and captured
        and kickoff >= now + MINIMUM_LEAD
        and captured <= now + timedelta(minutes=5)
        and now - captured <= MAXIMUM_PRICE_AGE
    )


def _create_selection(**fields):
    """Race-safe insert; one category/source/fixture can publish only once."""
    existing = PublicSelection.objects.filter(
        category=fields['category'],
        source_key=fields['source_key'],
        fixture_id=fields['fixture_id'],
    ).first()
    if existing is not None:
        return existing, False
    try:
        with transaction.atomic():
            return PublicSelection.objects.create(**fields), True
    except IntegrityError:
        existing = PublicSelection.objects.filter(
            category=fields['category'],
            source_key=fields['source_key'],
            fixture_id=fields['fixture_id'],
        ).first()
        if existing is None:
            raise
        return existing, False


def publish_homepage_selections(now=None, limit=HOMEPAGE_LIMIT):
    """Fill the rolling homepage with up to five frozen upcoming selections."""
    now = now or timezone.now()
    active = PublicSelection.objects.filter(
        category=PublicSelection.CATEGORY_HOMEPAGE,
        kickoff__gt=now,
    ).count()
    available = max(0, int(limit) - active)
    if available == 0:
        return {'published': 0, 'active': active, 'invalid': 0}

    cache = GemFeedCache.objects.filter(key=GemFeedCache.CACHE_KEY).first()
    if cache is None:
        return {'published': 0, 'active': active, 'invalid': 0}

    payload = cache.payload or {}
    board = payload.get('decision_board') or {}
    lanes = [
        (PublicSelection.REASON_VALUE, board.get('price_watchlist') or []),
        (PublicSelection.REASON_STRONG, board.get('strong_signals') or []),
    ]
    existing_fixtures = set(
        PublicSelection.objects.filter(
            category=PublicSelection.CATEGORY_HOMEPAGE,
        ).values_list('fixture_id', flat=True)
    )
    published = invalid = 0

    for reason, candidates in lanes:
        for item in candidates:
            if published >= available:
                break
            try:
                fixture_id = int(item['fixture_id'])
                kickoff = _aware(item.get('kickoff'))
                provenance = item.get('odds_provenance') or {}
                captured = _aware(provenance.get('odds_captured_at'))
                odds = float(item.get('verified_price'))
                if fixture_id in existing_fixtures:
                    continue
                if odds <= 1.0 or not _valid_publication_times(kickoff, captured, now):
                    invalid += 1
                    continue

                _, created = _create_selection(
                    category=PublicSelection.CATEGORY_HOMEPAGE,
                    source_key='homepage',
                    source_version=cache.ranking_version or '',
                    source_ref=(
                        f'homepage:{cache.generated_at.isoformat()}:{fixture_id}'
                    ),
                    reason_code=reason,
                    fixture_id=fixture_id,
                    home_team=str(item.get('home_team') or '')[:100],
                    away_team=str(item.get('away_team') or '')[:100],
                    league=str(item.get('league') or '')[:100],
                    kickoff=kickoff,
                    market_type='1x2',
                    predicted_outcome=str(item.get('leading_selection') or '')[:120],
                    model_score=float(item.get('signal_strength') or 0),
                    odds=odds,
                    bookmaker=str(
                        provenance.get('odds_bookmaker_name')
                        or item.get('bookmaker') or ''
                    )[:64],
                    bookmaker_count=max(1, int(
                        provenance.get('odds_bookmaker_count')
                        or item.get('bookmakers_checked') or 1
                    )),
                    odds_captured_at=captured,
                    published_at=now,
                )
                if created:
                    published += 1
                    existing_fixtures.add(fixture_id)
            except (KeyError, TypeError, ValueError):
                invalid += 1
        if published >= available:
            break

    return {'published': published, 'active': active + published, 'invalid': invalid}


def _matching_strategy_observation(report, fit):
    experiment = StrategyLabExperiment.objects.filter(
        strategy_key=report['strategy_key'],
        version=report['version'],
    ).first()
    if experiment is None:
        return None
    query = experiment.observations.filter(
        evidence_phase=StrategyLabObservation.PHASE_FORWARD,
        fixture_id=fit['fixture_id'],
        side=fit['side'],
        label=fit['selection'],
    )
    if fit.get('line') is None:
        query = query.filter(handicap__isnull=True)
    else:
        query = query.filter(handicap=fit['line'])
    return query.order_by('-observed_at').first()


def publish_strategy_selections(now=None, limit=STRATEGY_LIMIT):
    """Freeze the up-to-five public fits for every registered strategy."""
    now = now or timezone.now()
    published = invalid = already = 0

    for definition in strategy_lab.STRATEGY_DEFINITIONS:
        strategy_key = definition['strategy_key']
        active = PublicSelection.objects.filter(
            category=PublicSelection.CATEGORY_STRATEGY,
            source_key=strategy_key,
            kickoff__gt=now,
        ).count()
        available = max(0, int(limit) - active)
        if available == 0:
            continue
        report = strategy_lab.build_public_current_fits(strategy_key, limit=limit)
        if not report:
            continue
        published_for_strategy = 0
        for fit in report['fits']:
            if published_for_strategy >= available:
                break
            observation = _matching_strategy_observation(report, fit)
            if observation is None:
                invalid += 1
                continue
            if not _valid_publication_times(
                observation.kickoff, observation.odds_captured_at, now,
            ):
                invalid += 1
                continue

            _, created = _create_selection(
                category=PublicSelection.CATEGORY_STRATEGY,
                source_key=report['strategy_key'],
                source_version=report['version'],
                source_ref=f'strategy:{observation.observation_id}',
                reason_code=PublicSelection.REASON_STRATEGY,
                source_strategy_observation=observation,
                fixture_id=observation.fixture_id,
                home_team=observation.home_team,
                away_team=observation.away_team,
                league=observation.league,
                league_id=observation.league_id,
                kickoff=observation.kickoff,
                market_type=observation.market,
                predicted_outcome=observation.label,
                side=observation.side,
                line=observation.handicap,
                model_score=observation.model_mass,
                odds=observation.odds,
                bookmaker=observation.bookmaker,
                bookmaker_count=observation.bookmaker_count,
                odds_captured_at=observation.odds_captured_at,
                published_at=now,
            )
            if created:
                published += 1
                published_for_strategy += 1
            else:
                already += 1

    return {'published': published, 'already': already, 'invalid': invalid}


def publish_current_selections(now=None):
    now = now or timezone.now()
    return {
        'homepage': publish_homepage_selections(now=now),
        'strategies': publish_strategy_selections(now=now),
    }


STRATEGY_STATUS_MAP = {
    StrategyLabSettlement.OUTCOME_FULL_WIN: PublicSelectionResult.STATUS_WON,
    StrategyLabSettlement.OUTCOME_HALF_WIN: PublicSelectionResult.STATUS_HALF_WON,
    StrategyLabSettlement.OUTCOME_PUSH: PublicSelectionResult.STATUS_PUSH,
    StrategyLabSettlement.OUTCOME_HALF_LOSS: PublicSelectionResult.STATUS_HALF_LOST,
    StrategyLabSettlement.OUTCOME_FULL_LOSS: PublicSelectionResult.STATUS_LOST,
}


def _latest_result(fixture_id):
    return (
        FixtureResultObservation.objects
        .filter(fixture_id=fixture_id)
        .order_by('-result_version', '-captured_at')
        .first()
    )


def _settlement_for(selection):
    result = _latest_result(selection.fixture_id)
    if result is None:
        return None
    if result.provider_status in FixtureResultObservation.STATUS_VOIDLIKE:
        return {
            'status': PublicSelectionResult.STATUS_CANCELLED,
            'unit_profit': 0.0,
            'result': result,
        }
    if not result.is_scoreable or not result.confirmed:
        return None

    observation = selection.source_strategy_observation
    if observation is not None:
        # The public row is its own immutable promise. Strategy Lab freezes the
        # closest qualifying observation at its registered horizon, which is
        # not necessarily the newer observation displayed on the strategy
        # page. Waiting for a settlement attached to that exact observation
        # left otherwise gradeable public rows pending forever. Grade the
        # frozen public terms directly against the same confirmed result.
        lab = (
            observation.settlements.filter(result=result)
            .order_by('-settled_at').first()
        )
        if lab is not None:
            return {
                'status': STRATEGY_STATUS_MAP[lab.outcome],
                'unit_profit': lab.unit_profit,
                'result': result,
            }
        profit = strategy_lab.profit_for_frozen_selection(
            market=selection.market_type,
            side=selection.side,
            line=selection.line,
            odds=selection.odds,
            result=result,
        )
        if profit is None:
            return None
        return {
            'status': STRATEGY_STATUS_MAP[
                strategy_lab.outcome_for(profit, selection.odds)
            ],
            'unit_profit': profit,
            'result': result,
        }

    won = market_evaluation.evaluate_prediction(
        market_type=selection.market_type,
        predicted_outcome=selection.predicted_outcome,
        home_score=result.home_score,
        away_score=result.away_score,
        fixture_status=result.provider_status,
    )
    if won is None:
        return None
    return {
        'status': (
            PublicSelectionResult.STATUS_WON
            if won else PublicSelectionResult.STATUS_LOST
        ),
        'unit_profit': selection.odds - 1 if won else -1.0,
        'result': result,
    }


def settle_public_selections(now=None):
    """Settle every unresolved selection from confirmed provider evidence."""
    now = now or timezone.now()
    settled = pending = 0
    rows = PublicSelection.objects.filter(result__isnull=True).select_related(
        'source_strategy_observation',
    )
    for selection in rows:
        derived = _settlement_for(selection)
        if derived is None:
            pending += 1
            continue
        result = derived['result']
        try:
            PublicSelectionResult.objects.create(
                selection=selection,
                status=derived['status'],
                unit_profit=derived['unit_profit'],
                actual_score_home=result.home_score,
                actual_score_away=result.away_score,
                settled_at=now,
                result_source=result.provider,
                result_reference=f'fixture-result:{result.result_id}',
            )
            settled += 1
        except IntegrityError:
            pass
    return {'settled': settled, 'pending': pending}


def serialize_selection(selection):
    result = getattr(selection, 'result', None)
    integrity_ok = selection.verify_integrity()
    return {
        'selection_id': str(selection.selection_id),
        'receipt_url': f'/results/selection/{selection.selection_id}',
        'category': selection.category,
        'source_key': selection.source_key,
        'source_version': selection.source_version,
        'reason_code': selection.reason_code,
        'fixture_id': selection.fixture_id,
        'home_team': selection.home_team,
        'away_team': selection.away_team,
        'league': selection.league,
        'kickoff': selection.kickoff.isoformat(),
        'market_type': selection.market_type,
        'predicted_outcome': selection.predicted_outcome,
        'line': selection.line,
        'model_score': selection.model_score,
        'odds': selection.odds,
        'bookmaker': selection.bookmaker or None,
        'bookmaker_count': selection.bookmaker_count,
        'odds_captured_at': selection.odds_captured_at.isoformat(),
        'published_at': selection.published_at.isoformat(),
        'selection_hash': selection.selection_hash,
        'integrity_ok': integrity_ok,
        'status': result.status if result else PublicSelectionResult.STATUS_PENDING,
        'unit_profit': result.unit_profit if result else None,
        'profit_at_10': round(result.unit_profit * 10, 2) if result else None,
        'actual_score_home': result.actual_score_home if result else None,
        'actual_score_away': result.actual_score_away if result else None,
        'settled_at': result.settled_at.isoformat() if result else None,
        'counts_towards_record': bool(
            integrity_ok and result and result.status not in {
                PublicSelectionResult.STATUS_VOID,
                PublicSelectionResult.STATUS_CANCELLED,
            }
        ),
    }


def public_rows(category='', source_key='', state='', fixture_id=None):
    rows = PublicSelection.objects.select_related('result').all()
    if category:
        rows = rows.filter(category=category)
    if source_key:
        rows = rows.filter(source_key=source_key)
    if fixture_id is not None:
        rows = rows.filter(fixture_id=fixture_id)
    if state == 'pending':
        rows = rows.filter(result__isnull=True)
    elif state == 'settled':
        rows = rows.filter(result__isnull=False)
    return [serialize_selection(row) for row in rows]
