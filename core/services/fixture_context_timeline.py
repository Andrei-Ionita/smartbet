"""Public, read-only timeline built from append-only pre-match evidence."""

from collections import defaultdict

from core.models import FixtureContextObservation, SignalObservation


MAX_EVENTS = 30


def _iso(value):
    return value.isoformat() if value else None


def _event(row, code, category, data=None):
    return {
        'code': code,
        'category': category,
        'observed_at': _iso(row.observed_at),
        'hours_to_kickoff': round(row.hours_to_kickoff, 2),
        'data': data or {},
    }


def _venue_name(value):
    return (value or {}).get('name') or ''


def _public_venue(value):
    if not value:
        return None
    return {
        key: value.get(key)
        for key in ('id', 'name', 'city_name', 'capacity')
        if value.get(key) is not None
    }


def _current(row):
    if not row:
        return None
    return {
        'observed_at': _iso(row.observed_at),
        'hours_to_kickoff': round(row.hours_to_kickoff, 2),
        'fixture_predictable': row.fixture_predictable,
        'lineup_status': row.lineup_status,
        'home_formation': row.home_formation or None,
        'away_formation': row.away_formation or None,
        'home_form': row.home_form or None,
        'away_form': row.away_form or None,
        'home_sidelined_count': row.home_sidelined_count,
        'away_sidelined_count': row.away_sidelined_count,
        'venue': _public_venue(row.venue),
        'neutral_venue': row.neutral_venue,
        'data_availability': row.data_availability or {},
    }


def _context_events(rows):
    if not rows:
        return []
    events = [_event(rows[0], 'context_capture_started', 'availability')]
    for previous, current in zip(rows, rows[1:]):
        if previous.fixture_predictable != current.fixture_predictable:
            events.append(_event(current, 'predictability_changed', 'context', {
                'from': previous.fixture_predictable,
                'to': current.fixture_predictable,
            }))
        if previous.lineup_status != current.lineup_status:
            events.append(_event(current, 'lineup_status_changed', 'lineup', {
                'from': previous.lineup_status,
                'to': current.lineup_status,
                'player_count': len(current.lineups or []),
            }))
        old_formation = [previous.home_formation or None, previous.away_formation or None]
        new_formation = [current.home_formation or None, current.away_formation or None]
        if old_formation != new_formation:
            events.append(_event(current, 'formation_changed', 'lineup', {
                'from': old_formation,
                'to': new_formation,
            }))
        old_absences = [previous.home_sidelined_count, previous.away_sidelined_count]
        new_absences = [current.home_sidelined_count, current.away_sidelined_count]
        if old_absences != new_absences:
            events.append(_event(current, 'sidelined_count_changed', 'squad', {
                'from': old_absences,
                'to': new_absences,
            }))
        old_form = [previous.home_form or None, previous.away_form or None]
        new_form = [current.home_form or None, current.away_form or None]
        if old_form != new_form:
            events.append(_event(current, 'form_changed', 'form', {
                'from': old_form,
                'to': new_form,
            }))
        if _venue_name(previous.venue) != _venue_name(current.venue):
            events.append(_event(current, 'venue_changed', 'context', {
                'from': _venue_name(previous.venue) or None,
                'to': _venue_name(current.venue) or None,
            }))
        if previous.neutral_venue != current.neutral_venue:
            events.append(_event(current, 'neutral_venue_changed', 'context', {
                'from': previous.neutral_venue,
                'to': current.neutral_venue,
            }))
    return events


def _signal_events(rows):
    by_market = defaultdict(list)
    for row in rows:
        by_market[row.market].append(row)

    events = []
    for market, market_rows in by_market.items():
        for previous, current in zip(market_rows, market_rows[1:]):
            base = {'market': market}
            if previous.outcome != current.outcome:
                events.append(_event(current, 'model_leader_changed', 'model', {
                    **base,
                    'from': previous.outcome,
                    'to': current.outcome,
                    'probability': current.normalized_probability,
                }))
            elif abs(previous.normalized_probability - current.normalized_probability) >= 0.005:
                events.append(_event(current, 'model_probability_changed', 'model', {
                    **base,
                    'outcome': current.outcome,
                    'from': previous.normalized_probability,
                    'to': current.normalized_probability,
                }))

            old_odds = previous.odds if previous.price_status == 'verified' else None
            new_odds = current.odds if current.price_status == 'verified' else None
            if old_odds != new_odds and (
                old_odds is None or new_odds is None or abs(old_odds - new_odds) >= 0.01
            ):
                events.append(_event(current, 'verified_price_changed', 'price', {
                    **base,
                    'outcome': current.outcome,
                    'from': old_odds,
                    'to': new_odds,
                    'bookmaker': current.bookmaker or None,
                }))
    return events


def build_timeline(fixture_id):
    contexts = list(
        FixtureContextObservation.objects
        .filter(fixture_id=fixture_id, hours_to_kickoff__gte=0)
        .order_by('observed_at', 'created_at')
    )
    selected_signals = list(
        SignalObservation.objects
        .filter(
            fixture_id=fixture_id,
            hours_to_kickoff__gte=0,
            is_selected_outcome=True,
        )
        .order_by('observed_at', 'created_at')
    )

    events = _context_events(contexts) + _signal_events(selected_signals)
    events.sort(key=lambda row: row['observed_at'] or '', reverse=True)
    latest = contexts[-1] if contexts else None

    return {
        'fixture_id': fixture_id,
        'source': 'append_only_pre_match_observations',
        'methodology_version': 'fixture-context-v1',
        'snapshot_count': len(contexts),
        'signal_snapshot_count': len(selected_signals),
        'first_observed_at': _iso(contexts[0].observed_at) if contexts else None,
        'last_observed_at': _iso(latest.observed_at) if latest else None,
        'current': _current(latest),
        'events': events[:MAX_EVENTS],
        'limitations': [
            'Context is shown only when it was observed before kickoff.',
            'Available does not mean confirmed; predicted and confirmed lineup states remain distinct.',
            'A context change is evidence, not proof that it caused a price or model movement.',
        ],
    }
