"""Publication and settlement for homepage and named-strategy selections.

This record deliberately does not reuse ``PublishedClaim``. Gems are the rare,
strictly-qualified claim tier. Homepage and strategy selections are broader
public selections whose value is accountability: once displayed, they stay in
Results and are graded at the frozen price and market.
"""

import logging
from collections import defaultdict
from datetime import timedelta, timezone as dt_timezone

from django.db import IntegrityError, transaction
from django.db.models import Count
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.models import (
    FixtureResultObservation,
    GemFeedCache,
    PublicSelection,
    PublicSelectionClosingPrice,
    PublicSelectionResult,
    SignalObservation,
    StrategyLabExperiment,
    StrategyLabObservation,
    StrategyLabSettlement,
)
from core.services import market_evaluation, strategy_lab

logger = logging.getLogger(__name__)

HOMEPAGE_LIMIT = 5
STRATEGY_LIMIT = 5
MINIMUM_LEAD = timedelta(hours=1)
MAXIMUM_PRICE_AGE = timedelta(hours=2)

SCORED_STATUSES = {
    PublicSelectionResult.STATUS_WON,
    PublicSelectionResult.STATUS_HALF_WON,
    PublicSelectionResult.STATUS_PUSH,
    PublicSelectionResult.STATUS_HALF_LOST,
    PublicSelectionResult.STATUS_LOST,
}


def _sample_band(count):
    if count < 30:
        return 'very_early'
    if count < 100:
        return 'early'
    if count < 300:
        return 'developing'
    return 'maturing'


def _selection_explanation(selection):
    """Plain-language context derived only from frozen selection metadata."""
    if selection.source_key.startswith('market-portfolio-'):
        return {
            'title': 'Market selection',
            'why_selected': 'The model estimated a positive return at the checked price. This selection passed the registered data, price and settlement checks for its market.',
            'evidence': f'{selection.predicted_outcome} at {selection.odds:.2f}; {selection.bookmaker_count} bookmakers checked. These terms were recorded before kickoff.',
            'risk': 'The model estimate is under evaluation. A positive model EV can still have a negative conservative estimate, and neither guarantees a profit.',
        }
    plural = 's' if selection.bookmaker_count != 1 else ''
    if selection.reason_code == PublicSelection.REASON_VALUE:
        return {
            'title': 'Potential value',
            'why_selected': (
                'The price model and the recorded market price supported the '
                'same outcome with enough disagreement to merit investigation.'
            ),
            'evidence': (
                f'{selection.bookmaker_count} bookmaker price{plural} checked; '
                'selection and price frozen before kickoff.'
            ),
            'risk': (
                'A model-market disagreement is not proof that the model is '
                'right. Prices and team information can change after publication.'
            ),
        }
    if selection.reason_code == PublicSelection.REASON_STRATEGY:
        definition = next((
            item for item in strategy_lab.STRATEGY_DEFINITIONS
            if item['strategy_key'] == selection.source_key
        ), None)
        name = definition['name'] if definition else selection.source_key.replace('-', ' ')
        return {
            'title': 'Strategy match',
            'why_selected': (
                f'This fixture passed the frozen rules for {name} '
                f'({selection.source_version or "recorded version"}).'
            ),
            'evidence': (
                f'{selection.predicted_outcome} at {selection.odds:.2f}, checked '
                f'across {selection.bookmaker_count} bookmaker{plural}.'
            ),
            'risk': (
                'This is an experimental strategy with a developing sample. '
                'A rule match is not a guarantee or an instruction to bet.'
            ),
        }
    signal = (
        f'Signal score {selection.model_score:.2f}; '
        if selection.model_score is not None else ''
    )
    return {
        'title': 'Strong model signal',
        'why_selected': (
            'The model separated this outcome clearly from its alternatives '
            'and the recorded market supplied a usable reference price.'
        ),
        'evidence': (
            f'{signal}{selection.bookmaker_count} bookmaker price{plural} checked.'
        ),
        'risk': (
            'Signal strength is not a calibrated win probability and does not '
            'by itself establish that the recorded odds offered value.'
        ),
    }


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
    """Freeze the v4 multi-market portfolio before kickoff for validation.

    Public history remains a presentation decision. Recording both potential-
    value and strong-signal lanes here is what lets the new engine establish an
    honest forward record instead of optimizing against completed fixtures.
    """
    now = now or timezone.now()
    active = PublicSelection.objects.filter(
        category=PublicSelection.CATEGORY_HOMEPAGE,
        source_key='portfolio-v4',
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
            source_key='portfolio-v4',
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
                    source_key='portfolio-v4',
                    source_version=(
                        f"portfolio-v4:{cache.ranking_version or 'unversioned'}"
                    )[:128],
                    source_ref=(
                        f'portfolio-v4:{cache.generated_at.isoformat()}:{fixture_id}'
                    ),
                    reason_code=reason,
                    fixture_id=fixture_id,
                    home_team=str(item.get('home_team') or '')[:100],
                    away_team=str(item.get('away_team') or '')[:100],
                    league=str(item.get('league') or '')[:100],
                    kickoff=kickoff,
                    market_type=str(item.get('market_type') or '1x2')[:40],
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

            probability_context = (
                observation.selection_payload or {}
            ).get('probability_context') or {}
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
                model_score=probability_context.get('conservative_probability'),
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
    from core.services.selection_portfolio import publish_portfolio
    return {'portfolio': publish_portfolio(now=now)}


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


def _closing_candidate(selection):
    observation = selection.source_strategy_observation
    if observation is not None:
        query = StrategyLabObservation.objects.filter(
            experiment=observation.experiment,
            fixture_id=selection.fixture_id,
            side=selection.side,
            evidence_phase=observation.evidence_phase,
            hours_to_kickoff__gte=0,
            odds_captured_at__lte=selection.kickoff,
        )
        query = query.filter(
            handicap__isnull=True,
        ) if selection.line is None else query.filter(handicap=selection.line)
        row = query.order_by('hours_to_kickoff', '-observed_at').first()
        if row is None or row.odds <= 1:
            return None
        return {
            'odds': row.odds,
            'bookmaker': row.bookmaker,
            'bookmaker_count': row.bookmaker_count,
            'captured_at': row.odds_captured_at,
            'source_ref': f'strategy-observation:{row.observation_id}',
        }

    outcome = selection.side or selection.predicted_outcome.strip().lower().replace(' ', '_')
    row = (
        SignalObservation.objects
        .filter(
            fixture_id=selection.fixture_id,
            market=selection.market_type,
            outcome=outcome,
            price_status='verified',
            provenance_complete=True,
            odds__gt=1,
            odds_captured_at__lte=selection.kickoff,
            hours_to_kickoff__gte=0,
        )
        .order_by('hours_to_kickoff', '-observed_at')
        .first()
    )
    if row is None:
        return None
    provenance = row.odds_provenance or {}
    return {
        'odds': row.odds,
        'bookmaker': row.bookmaker,
        'bookmaker_count': max(1, int(
            provenance.get('odds_bookmaker_count') or 1
        )),
        'captured_at': row.odds_captured_at,
        'source_ref': f'signal-observation:{row.observation_id}',
    }


def capture_closing_prices(now=None):
    """Freeze the closest stored verified quote after kickoff becomes known."""
    now = now or timezone.now()
    captured = unavailable = 0
    rows = PublicSelection.objects.filter(
        kickoff__lte=now,
        closing_price__isnull=True,
    ).select_related(
        'source_strategy_observation',
        'source_strategy_observation__experiment',
    )
    for selection in rows:
        candidate = _closing_candidate(selection)
        if candidate is None:
            unavailable += 1
            continue
        try:
            PublicSelectionClosingPrice.objects.create(
                selection=selection,
                odds=candidate['odds'],
                bookmaker=candidate['bookmaker'],
                bookmaker_count=candidate['bookmaker_count'],
                odds_captured_at=candidate['captured_at'],
                recorded_at=now,
                source_ref=candidate['source_ref'],
                closing_line_value=selection.odds / candidate['odds'] - 1,
            )
            captured += 1
        except IntegrityError:
            pass
    return {'captured': captured, 'unavailable': unavailable}


def settle_public_selections(now=None):
    """Settle every unresolved selection from confirmed provider evidence."""
    now = now or timezone.now()
    closing = capture_closing_prices(now=now)
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
    return {'settled': settled, 'pending': pending, 'closing_prices': closing}


def serialize_selection(selection):
    result = getattr(selection, 'result', None)
    integrity_ok = selection.verify_integrity()
    try:
        closing = selection.closing_price
    except PublicSelectionClosingPrice.DoesNotExist:
        closing = None
    return {
        'selection_id': str(selection.selection_id),
        'receipt_url': f'/results/selection/{selection.selection_id}',
        'category': selection.category,
        'source_key': selection.source_key,
        'source_version': selection.source_version,
        'reason_code': selection.reason_code,
        'explanation': _selection_explanation(selection),
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
        'closing_price': ({
            'odds': closing.odds,
            'bookmaker': closing.bookmaker or None,
            'bookmaker_count': closing.bookmaker_count,
            'odds_captured_at': closing.odds_captured_at.isoformat(),
            'closing_line_value_percent': round(
                closing.closing_line_value * 100, 2,
            ),
            'evidence_hash': closing.evidence_hash,
        } if closing else None),
        'counts_towards_record': bool(
            integrity_ok and result and result.status not in {
                PublicSelectionResult.STATUS_VOID,
                PublicSelectionResult.STATUS_CANCELLED,
            }
        ),
    }


def summarize_rows(rows):
    """Canonical flat-stake performance summary for serialized ledger rows."""
    statuses = (
        PublicSelectionResult.STATUS_PENDING,
        PublicSelectionResult.STATUS_WON,
        PublicSelectionResult.STATUS_HALF_WON,
        PublicSelectionResult.STATUS_PUSH,
        PublicSelectionResult.STATUS_HALF_LOST,
        PublicSelectionResult.STATUS_LOST,
        PublicSelectionResult.STATUS_VOID,
        PublicSelectionResult.STATUS_CANCELLED,
    )
    valid_rows = [row for row in rows if row['integrity_ok']]
    status_counts = {
        status: sum(1 for row in valid_rows if row['status'] == status)
        for status in statuses
    }
    scored = [
        row for row in rows
        if row['integrity_ok'] and row['status'] in SCORED_STATUSES
    ]
    profit_units = round(sum(float(row['unit_profit'] or 0) for row in scored), 4)
    success_units = (
        status_counts[PublicSelectionResult.STATUS_WON]
        + 0.5 * status_counts[PublicSelectionResult.STATUS_HALF_WON]
    )
    accuracy_denominator = (
        success_units
        + status_counts[PublicSelectionResult.STATUS_LOST]
        + 0.5 * status_counts[PublicSelectionResult.STATUS_HALF_LOST]
    )
    return {
        'published': len(rows),
        'pending': status_counts[PublicSelectionResult.STATUS_PENDING],
        'settled': len(scored),
        'won': status_counts[PublicSelectionResult.STATUS_WON],
        'half_won': status_counts[PublicSelectionResult.STATUS_HALF_WON],
        'push': status_counts[PublicSelectionResult.STATUS_PUSH],
        'half_lost': status_counts[PublicSelectionResult.STATUS_HALF_LOST],
        'lost': status_counts[PublicSelectionResult.STATUS_LOST],
        'void_or_cancelled': (
            status_counts[PublicSelectionResult.STATUS_VOID]
            + status_counts[PublicSelectionResult.STATUS_CANCELLED]
        ),
        'integrity_excluded': sum(1 for row in rows if not row['integrity_ok']),
        'profit_units': profit_units,
        'profit_at_10': round(profit_units * 10, 2),
        'roi_percent': round(profit_units / len(scored) * 100, 2) if scored else None,
        'win_rate': round(
            success_units / accuracy_denominator * 100, 2,
        ) if accuracy_denominator else None,
        'average_odds': round(
            sum(float(row['odds']) for row in scored) / len(scored), 3,
        ) if scored else None,
        'sample_band': _sample_band(len(scored)),
    }


def _odds_band(odds):
    value = float(odds)
    if value < 1.50:
        return '1.01–1.49'
    if value < 2.00:
        return '1.50–1.99'
    if value < 3.00:
        return '2.00–2.99'
    return '3.00+'


def performance_report(rows):
    """One public source for totals and non-prescriptive diagnostics."""
    dimensions = {
        'by_category': lambda row: row['category'],
        'by_strategy': lambda row: (
            row['source_key']
            if row['category'] == PublicSelection.CATEGORY_STRATEGY else None
        ),
        'by_strategy_version': lambda row: (
            f"{row['source_key']}:{row['source_version'] or 'unversioned'}"
            if row['category'] == PublicSelection.CATEGORY_STRATEGY else None
        ),
        'by_market': lambda row: row['market_type'],
        'by_reason': lambda row: row['reason_code'],
        'by_odds_band': lambda row: _odds_band(row['odds']),
        'by_league': lambda row: row['league'] or 'Unknown league',
    }
    report = {'overall': summarize_rows(rows)}
    for name, key_fn in dimensions.items():
        groups = defaultdict(list)
        for row in rows:
            key = key_fn(row)
            if key:
                groups[str(key)].append(row)
        cohorts = [
            {'key': key, **summarize_rows(group)}
            for key, group in groups.items()
        ]
        report[name] = sorted(
            cohorts,
            key=lambda item: (-item['settled'], -item['published'], item['key']),
        )
    return report


def audit_ledger():
    """Re-grade the immutable ledger and report structural discrepancies."""
    issues = []
    duplicate_groups = PublicSelection.objects.values(
        'category', 'source_key', 'fixture_id',
    ).annotate(row_count=Count('selection_id')).filter(row_count__gt=1)
    for group in duplicate_groups:
        issues.append({
            'selection_id': None,
            'code': 'duplicate_category_source_fixture',
            'category': group['category'],
            'source_key': group['source_key'],
            'fixture_id': group['fixture_id'],
        })
    rows = PublicSelection.objects.select_related(
        'result', 'source_strategy_observation',
    ).all()
    for selection in rows:
        selection_id = str(selection.selection_id)
        if not selection.verify_integrity():
            issues.append({'selection_id': selection_id, 'code': 'hash_mismatch'})
        if selection.published_at > selection.kickoff - MINIMUM_LEAD:
            issues.append({
                'selection_id': selection_id,
                'code': 'insufficient_pre_kickoff_lead',
            })
        if selection.odds_captured_at > selection.published_at + timedelta(minutes=5):
            issues.append({
                'selection_id': selection_id,
                'code': 'price_captured_after_publication',
            })
        if selection.odds <= 1:
            issues.append({'selection_id': selection_id, 'code': 'invalid_odds'})
        stored = getattr(selection, 'result', None)
        derived = _settlement_for(selection)
        if stored is not None and derived is None:
            issues.append({
                'selection_id': selection_id,
                'code': 'settlement_has_no_confirmed_evidence',
            })
        elif stored is not None and derived is not None:
            if stored.status != derived['status']:
                issues.append({
                    'selection_id': selection_id,
                    'code': 'settlement_status_mismatch',
                })
            if abs(float(stored.unit_profit) - float(derived['unit_profit'])) > 0.0001:
                issues.append({
                    'selection_id': selection_id,
                    'code': 'settlement_profit_mismatch',
                })
            expected_reference = f"fixture-result:{derived['result'].result_id}"
            if stored.result_reference != expected_reference:
                issues.append({
                    'selection_id': selection_id,
                    'code': 'result_reference_mismatch',
                })
            if (
                stored.actual_score_home != derived['result'].home_score
                or stored.actual_score_away != derived['result'].away_score
            ):
                issues.append({
                    'selection_id': selection_id,
                    'code': 'result_score_mismatch',
                })
            if stored.result_source != derived['result'].provider:
                issues.append({
                    'selection_id': selection_id,
                    'code': 'result_source_mismatch',
                })
    counts = defaultdict(int)
    for issue in issues:
        counts[issue['code']] += 1
    affected = {item['selection_id'] for item in issues if item['selection_id']}
    return {
        'checked': len(rows),
        'passed': len(rows) - len(affected),
        'issue_count': len(issues),
        'issues_by_code': dict(sorted(counts.items())),
        'issues': issues,
    }


def public_rows(category='', source_key='', state='', fixture_id=None):
    rows = PublicSelection.objects.select_related('result', 'closing_price').all()
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
