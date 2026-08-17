"""
Append-only capture of provider fixture results, for evidence evaluation.

The fixture universe is DISTINCT fixture_ids in SignalObservation — not
PredictionLog. That distinction is the whole point: PredictionLog holds only
fixtures that produced a recommendation, so using it would leave every observed
but unrecommended fixture permanently unscoreable, and BTTS and double chance
would stay uncalibratable exactly as before.

Fetched directly from the backend rather than through a new internal frontend
route: the scheduler already holds a provider token, so an extra hop would add
an authenticated surface for no gain.

This module never publishes, never settles and never writes to
SignalObservation.
"""
import logging
import os
import uuid

import requests
from django.utils import timezone

from core.models import (
    FixtureResultObservation, SignalObservation, StrategyLabObservation,
)
from core.services.integrity import canonical_sha256, norm_dt

logger = logging.getLogger(__name__)

BASE_URL = 'https://api.sportmonks.com/v3/football'
REQUEST_TIMEOUT = 30
BATCH_SIZE = 25  # provider multi-id endpoint; one request per 25 fixtures

# A final score is provisional until a second, later observation agrees with it.
CONFIRMATION_MIN_AGE_MINUTES = 30


def _token():
    token = os.environ.get('SPORTMONKS_API_TOKEN')
    if not token:
        raise RuntimeError('SPORTMONKS_API_TOKEN is not set')
    return token


def fixtures_needing_results(now=None, limit=500):
    """Observed fixtures past kickoff that still need a confirmed final result.

    Skips fixtures whose latest result observation is already a confirmed
    final — that is the governed stop-polling rule. Void-like states are also
    terminal: a cancelled match will not acquire a score later.
    """
    now = now or timezone.now()

    observed = set(
        SignalObservation.objects
        .filter(kickoff__lt=now)
        .values_list('fixture_id', flat=True)
        .distinct()
    )
    observed.update(
        StrategyLabObservation.objects
        .filter(kickoff__lt=now)
        .values_list('fixture_id', flat=True)
        .distinct()
    )
    if not observed:
        return []

    settled = set()
    latest = {}
    for row in (FixtureResultObservation.objects
                .filter(fixture_id__in=observed)
                .order_by('fixture_id', '-result_version', '-captured_at')):
        latest.setdefault(row.fixture_id, row)
    for fixture_id, row in latest.items():
        terminal_void = row.provider_status in FixtureResultObservation.STATUS_VOIDLIKE
        if (row.is_final and row.confirmed) or terminal_void:
            settled.add(fixture_id)

    return sorted(observed - settled)[:limit]


def fetch_results(fixture_ids):
    """Batch provider lookup. One request per BATCH_SIZE fixtures, never per row."""
    token = _token()
    out = []
    for start in range(0, len(fixture_ids), BATCH_SIZE):
        chunk = fixture_ids[start:start + BATCH_SIZE]
        url = (f"{BASE_URL}/fixtures/multi/{','.join(str(i) for i in chunk)}"
               f"?api_token={token}&include=participants;scores;league;state")
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            out.extend(response.json().get('data') or [])
        except Exception:
            logger.exception('result batch failed for %d fixtures', len(chunk))
    return out


def _pick_fulltime_score(fixture):
    """The 90-minute score, chosen explicitly rather than trusting a headline.

    SportMonks returns several score entries per fixture (current, half-time,
    2nd half, extra time). Ordinary football markets settle on the 90-minute
    result, so anything else must not be mistaken for it.
    """
    scores = fixture.get('scores') or []
    by_desc = {}
    for entry in scores:
        desc = (entry.get('description') or '').upper()
        score = entry.get('score') or {}
        participant = score.get('participant')
        goals = score.get('goals')
        if participant not in ('home', 'away') or goals is None:
            continue
        by_desc.setdefault(desc, {})[participant] = goals

    for desc in ('CURRENT', '2ND_HALF', 'FULLTIME', 'FT'):
        entry = by_desc.get(desc)
        if entry and 'home' in entry and 'away' in entry:
            return entry['home'], entry['away'], desc, scores
    return None, None, '', scores


def classify(provider_status, home_score, away_score):
    """(is_final, is_scoreable, reason). Never invents a result."""
    status = (provider_status or '').upper()
    model = FixtureResultObservation

    has_score = home_score is not None and away_score is not None

    if status in model.STATUS_VOIDLIKE:
        return False, False, f'void_like:{status.lower()}'
    if status in model.STATUS_NOT_STARTED:
        return False, False, 'not_started'
    if status in model.STATUS_IN_PLAY:
        return False, False, 'in_play'
    if status in model.STATUS_EXTRA_TIME:
        # A score exists, but it is not the 90-minute result these markets
        # settle on. Recorded, deliberately not scored.
        return True, False, 'extra_time_not_90min'
    if status in model.STATUS_ELIGIBLE_FINAL:
        if not has_score:
            return False, False, 'final_without_score'
        return True, True, ''
    return False, False, f'unknown_status:{status.lower()[:32]}'


def result_hash(fixture_id, provider_status, home_score, away_score, score_type):
    """Identity of one result BELIEF. Excludes capture time deliberately:
    re-observing the same final score must not append a new version."""
    return canonical_sha256({
        'v': 1,
        'fixture_id': fixture_id,
        'provider_status': (provider_status or '').upper(),
        'home_score': home_score,
        'away_score': away_score,
        'score_type': score_type,
    })


def capture(fixtures, ingestion_run_id=None, now=None):
    """Append result observations. Returns a summary. Never updates a row."""
    now = now or timezone.now()
    run_id = ingestion_run_id or canonical_sha256(
        {'at': norm_dt(now), 'n': len(fixtures)}
    )[:32]

    written = duplicate = corrections = confirmed_now = invalid = 0

    for fixture in fixtures:
        fixture_id = fixture.get('id')
        if fixture_id is None:
            invalid += 1
            continue

        state = fixture.get('state') or {}
        status = state.get('state') or state.get('short_name') or fixture.get('state_id') or ''
        home_score, away_score, score_type, raw_scores = _pick_fulltime_score(fixture)
        is_final, is_scoreable, reason = classify(status, home_score, away_score)

        digest = result_hash(fixture_id, status, home_score, away_score, score_type)
        existing = list(
            FixtureResultObservation.objects
            .filter(fixture_id=fixture_id).order_by('-result_version')
        )

        same_belief = next((r for r in existing if r.source_payload_hash == digest), None)
        if same_belief is not None:
            duplicate += 1
            # Re-observing an unconfirmed final, later, is what confirms it. The
            # confirmation is a NEW row, so the original belief is untouched.
            if (is_final and not same_belief.confirmed
                    and (now - same_belief.captured_at).total_seconds()
                    >= CONFIRMATION_MIN_AGE_MINUTES * 60
                    and not any(r.confirmed for r in existing)):
                FixtureResultObservation.objects.create(
                    result_id=uuid.uuid4(),
                    fixture_id=fixture_id,
                    home_team=same_belief.home_team, away_team=same_belief.away_team,
                    league=same_belief.league, league_id=same_belief.league_id,
                    kickoff=same_belief.kickoff,
                    provider=same_belief.provider, provider_status=status,
                    home_score=home_score, away_score=away_score,
                    score_type=score_type, raw_scores=raw_scores,
                    is_final=is_final, is_scoreable=is_scoreable,
                    ineligible_reason=reason, confirmed=True,
                    result_version=existing[0].result_version + 1,
                    supersedes=existing[0], is_correction=False,
                    captured_at=now, ingestion_run_id=run_id,
                    source_payload_hash=canonical_sha256(
                        {'confirm': digest, 'at': norm_dt(now)}
                    ),
                )
                confirmed_now += 1
            continue

        participants = fixture.get('participants') or []
        home = next((p for p in participants
                     if (p.get('meta') or {}).get('location') == 'home'), {})
        away = next((p for p in participants
                     if (p.get('meta') or {}).get('location') == 'away'), {})
        league = fixture.get('league') or {}

        kickoff = fixture.get('starting_at')
        if isinstance(kickoff, str):
            from django.utils.dateparse import parse_datetime
            kickoff = parse_datetime(kickoff.replace(' ', 'T'))
        if kickoff is None:
            obs = SignalObservation.objects.filter(fixture_id=fixture_id).first()
            kickoff = obs.kickoff if obs else now
        if timezone.is_naive(kickoff):
            from datetime import timezone as dt_tz
            kickoff = timezone.make_aware(kickoff, dt_tz.utc)

        is_correction = bool(existing) and any(
            r.is_final and (r.home_score, r.away_score) != (home_score, away_score)
            for r in existing
        )

        try:
            FixtureResultObservation.objects.create(
                result_id=uuid.uuid4(),
                fixture_id=fixture_id,
                home_team=(home.get('name') or '')[:100],
                away_team=(away.get('name') or '')[:100],
                league=(league.get('name') or '')[:100],
                league_id=league.get('id'),
                kickoff=kickoff,
                provider='sportmonks',
                provider_status=str(status)[:32],
                home_score=home_score, away_score=away_score,
                score_type=score_type[:24], raw_scores=raw_scores,
                is_final=is_final, is_scoreable=is_scoreable,
                ineligible_reason=reason[:64], confirmed=False,
                result_version=(existing[0].result_version + 1) if existing else 1,
                supersedes=existing[0] if existing else None,
                is_correction=is_correction,
                captured_at=now, ingestion_run_id=run_id,
                source_payload_hash=digest,
            )
            written += 1
            if is_correction:
                corrections += 1
        except Exception:
            logger.exception('failed to append result for fixture %s', fixture_id)
            invalid += 1

    return {
        'ingestion_run_id': run_id,
        'checked': len(fixtures),
        'written': written,
        'duplicate': duplicate,
        'confirmed': confirmed_now,
        'corrections': corrections,
        'invalid': invalid,
    }


def canonical_results():
    """fixture_id -> the currently authoritative result observation."""
    latest = {}
    for row in (FixtureResultObservation.objects
                .all().order_by('fixture_id', '-result_version', '-captured_at')):
        latest.setdefault(row.fixture_id, row)
    return latest
