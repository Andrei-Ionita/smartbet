"""
Append-only capture of provider signal evidence.

Reads the internal evidence feed (server-to-server, shared secret) and writes
one SignalObservation per fixture-market-outcome candidate plus one compact
FixtureContextObservation whenever the pre-match context changes. It performs
no ranking and publishes nothing.

Idempotency is content-derived, exactly like the prediction run id: the hash
covers the provider values and the price for that one candidate, so replaying a
payload inserts nothing. A genuinely new observation — a moved price, a fresh
provider value, a later capture time — hashes differently and appends.
"""
import logging
import os
import uuid

import requests
from django.utils import timezone

from core.models import FixtureContextObservation, SignalObservation
from core.services.integrity import canonical_sha256, norm_dt, norm_num

logger = logging.getLogger(__name__)

# The sweep fetches fixtures for ~30 leagues plus batched team form for Variant
# B, so it legitimately takes minutes on a cold cache. 60s was too tight and
# timed out the stage on 2026-08-05. Safe to be generous: this stage runs last,
# is fully isolated, and a slow evidence sweep cannot delay settlement.
REQUEST_TIMEOUT = 240


def _as_aware(value):
    if not value:
        return None
    parsed = value
    if isinstance(value, str):
        from django.utils.dateparse import parse_datetime
        parsed = parse_datetime(value.replace(' ', 'T')) if 'T' not in value \
            else parse_datetime(value)
        if parsed is None:
            return None
    if timezone.is_naive(parsed):
        from datetime import timezone as dt_timezone
        parsed = timezone.make_aware(parsed, dt_timezone.utc)
    return parsed


def observation_hash(candidate):
    """Deterministic identity for one observed candidate.

    Covers the provider values and the price VALUE. Deliberately excludes both
    `observed_at` and `odds_captured_at`:

      * `observed_at` would make every retry look new.
      * `odds_captured_at` advances whenever the provider re-stamps an
        unchanged quote. Including it is what makes PredictionSnapshot append
        four rows an hour for fixtures whose prices never moved — at ~10
        candidates per fixture across four markets, the same mistake here would
        write tens of thousands of near-identical rows a day.

    What remains is the semantics we actually want: a row appears when the
    probability or the price genuinely CHANGES, which is exactly the signal
    closing-line value is measured from.
    """
    return canonical_sha256({
        'v': 2,
        'fixture_id': candidate.get('fixture_id'),
        'market': candidate.get('market'),
        'outcome': candidate.get('outcome'),
        'provider': candidate.get('provider'),
        'provider_type_id': candidate.get('provider_type_id'),
        'raw_probability': norm_num(candidate.get('raw_probability')),
        'normalized_probability': norm_num(candidate.get('normalized_probability')),
        'vector': {k: norm_num(v) for k, v in (candidate.get('raw_vector') or {}).items()},
        'odds': norm_num(candidate.get('odds')),
        'price_status': candidate.get('price_status'),
        # Variant B belongs to the identity: the same provider probability under
        # a changed form multiplier is a genuinely different heuristic state.
        'adjusted_score': norm_num(candidate.get('adjusted_score')),
        'form_multiplier': norm_num(candidate.get('form_multiplier')),
        # A changed predictability rating, active value flag or fair odd is a
        # genuinely new pre-match state even when the raw outcome probability
        # and bookmaker quote did not move.
        'provider_context': candidate.get('provider_context') or {},
    })


def context_hash(context):
    """Content identity for a fixture-context snapshot.

    Capture time is excluded intentionally. A new row means the pre-match facts
    changed, not merely that the scheduler ran again.
    """
    return canonical_sha256({
        'v': 1,
        'fixture_id': context.get('fixture_id'),
        'fixture_predictable': context.get('fixture_predictable'),
        'lineup_status': context.get('lineup_status'),
        'home_formation': context.get('home_formation') or '',
        'away_formation': context.get('away_formation') or '',
        'home_form': context.get('home_form') or '',
        'away_form': context.get('away_form') or '',
        'sidelined': context.get('sidelined') or [],
        'lineups': context.get('lineups') or [],
        'referees': context.get('referees') or [],
        'venue': context.get('venue'),
        'neutral_venue': context.get('neutral_venue'),
        'data_availability': context.get('data_availability') or {},
    })


def _capture_contexts(payload, run_id):
    written = skipped = invalid = post_kickoff = 0
    contexts = payload.get('fixture_contexts') or []

    for context in contexts:
        kickoff = _as_aware(context.get('kickoff'))
        observed_at = _as_aware(context.get('observed_at')) or timezone.now()
        if kickoff is None or not context.get('fixture_id'):
            invalid += 1
            continue

        hours = (kickoff - observed_at).total_seconds() / 3600.0
        if hours < 0:
            post_kickoff += 1

        digest = context_hash(context)
        if FixtureContextObservation.objects.filter(
            source_payload_hash=digest,
        ).exists():
            skipped += 1
            continue

        sidelined = context.get('sidelined') or []
        home_id = context.get('home_team_id')
        away_id = context.get('away_team_id')
        try:
            FixtureContextObservation.objects.create(
                observation_id=uuid.uuid4(),
                ingestion_run_id=run_id,
                source_payload_hash=digest,
                fixture_id=context['fixture_id'],
                home_team=(context.get('home_team') or '')[:100],
                away_team=(context.get('away_team') or '')[:100],
                league=(context.get('league') or '')[:100],
                league_id=context.get('league_id'),
                kickoff=kickoff,
                observed_at=observed_at,
                hours_to_kickoff=hours,
                fixture_predictable=context.get('fixture_predictable'),
                lineup_status=(context.get('lineup_status') or 'unavailable')[:24],
                home_formation=(context.get('home_formation') or '')[:32],
                away_formation=(context.get('away_formation') or '')[:32],
                home_form=(context.get('home_form') or '')[:20],
                away_form=(context.get('away_form') or '')[:20],
                home_sidelined_count=sum(
                    1 for row in sidelined
                    if row.get('participant_id') == home_id
                ),
                away_sidelined_count=sum(
                    1 for row in sidelined
                    if row.get('participant_id') == away_id
                ),
                sidelined=sidelined,
                lineups=context.get('lineups') or [],
                referees=context.get('referees') or [],
                venue=context.get('venue'),
                neutral_venue=context.get('neutral_venue'),
                data_availability=context.get('data_availability') or {},
                provider=(context.get('provider') or 'sportmonks')[:32],
                calculation_version=(
                    context.get('calculation_version') or ''
                )[:80],
            )
            written += 1
        except Exception:
            logger.exception('failed to append context for fixture %s',
                             context.get('fixture_id'))
            invalid += 1

    return {
        'contexts': len(contexts),
        'context_written': written,
        'context_skipped_duplicate': skipped,
        'context_invalid': invalid,
        'context_post_kickoff': post_kickoff,
    }


def fetch_evidence(base_url=None, secret=None, days=5):
    """GET the internal feed. Fails closed when the secret is absent."""
    base_url = base_url or os.environ.get(
        'FRONTEND_URL', 'https://www.betglitch.com'
    ).rstrip('/')
    secret = secret if secret is not None else os.environ.get('INTERNAL_API_SECRET', '')
    if not secret:
        raise RuntimeError(
            'INTERNAL_API_SECRET is not set — refusing to call the evidence feed '
            'unauthenticated.'
        )

    response = requests.get(
        f'{base_url}/api/internal/evidence?days={days}',
        headers={'X-Internal-Auth': secret},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get('success'):
        raise RuntimeError(f"evidence feed returned failure: {payload.get('error')}")
    return payload


def capture(payload, ingestion_run_id=None):
    """Append observations. Returns a summary dict. Never updates a row."""
    candidates = payload.get('candidates') or []
    run_id = ingestion_run_id or canonical_sha256({
        'observed_at': payload.get('observed_at'),
        'count': len(candidates),
    })[:32]

    written = skipped = invalid = 0
    post_kickoff = 0

    for candidate in candidates:
        kickoff = _as_aware(candidate.get('kickoff'))
        observed_at = _as_aware(candidate.get('observed_at')) or timezone.now()
        if kickoff is None or candidate.get('normalized_probability') is None:
            invalid += 1
            continue

        hours = (kickoff - observed_at).total_seconds() / 3600.0
        if hours < 0:
            # Still recorded — the row is evidence that the sweep ran — but the
            # negative horizon is what excludes it from decision evaluation.
            post_kickoff += 1

        digest = observation_hash(candidate)
        if SignalObservation.objects.filter(source_payload_hash=digest).exists():
            skipped += 1
            continue

        vector = candidate.get('raw_vector') or {}
        try:
            SignalObservation.objects.create(
                observation_id=uuid.uuid4(),
                ingestion_run_id=run_id,
                source_payload_hash=digest,
                fixture_id=candidate['fixture_id'],
                home_team=candidate.get('home_team', '')[:100],
                away_team=candidate.get('away_team', '')[:100],
                league=(candidate.get('league') or '')[:100],
                league_id=candidate.get('league_id'),
                kickoff=kickoff,
                observed_at=observed_at,
                hours_to_kickoff=hours,
                market=candidate['market'],
                outcome=candidate['outcome'],
                provider=candidate.get('provider', 'sportmonks'),
                provider_type_id=candidate.get('provider_type_id'),
                provider_model_version=(candidate.get('provider_model_version') or '')[:64],
                provider_predicted_at=_as_aware(candidate.get('provider_predicted_at')),
                provider_context=candidate.get('provider_context') or {},
                raw_probability=candidate.get('raw_probability') or 0.0,
                normalized_probability=candidate['normalized_probability'],
                raw_vector=vector,
                vector_sum=candidate.get('vector_sum') or sum(vector.values()),
                vector_complete=bool(candidate.get('vector_complete')),
                price_status=(candidate.get('price_status') or '')[:24],
                odds=candidate.get('odds'),
                bookmaker=(candidate.get('bookmaker') or '')[:64],
                odds_captured_at=_as_aware(candidate.get('odds_captured_at')),
                odds_provenance=candidate.get('odds_provenance'),
                provenance_complete=bool(candidate.get('odds_provenance')),
                market_price_vector=candidate.get('market_price_vector'),
                price_vector_complete=bool(candidate.get('price_vector_complete')),
                is_selected_outcome=bool(candidate.get('is_selected_outcome')),
                probability_gap=candidate.get('probability_gap'),
                form_multiplier=candidate.get('form_multiplier'),
                form_inputs=candidate.get('form_inputs'),
                adjusted_score=candidate.get('adjusted_score'),
                cap_applied=bool(candidate.get('cap_applied')),
                market_score=candidate.get('market_score'),
                ranking_ev=candidate.get('ranking_ev'),
                variant_b_available=bool(candidate.get('variant_b_available')),
                variant_b_missing_reason=(
                    candidate.get('variant_b_missing_reason') or '')[:80],
                live_activation_state=(
                    candidate.get('live_activation_state') or '')[:16],
                selection_reason=(candidate.get('selection_reason') or '')[:120],
                pipeline_version=(candidate.get('pipeline_version') or '')[:80],
                calculation_version=(candidate.get('calculation_version') or '')[:80],
            )
            written += 1
        except Exception:
            logger.exception('failed to append observation for fixture %s',
                             candidate.get('fixture_id'))
            invalid += 1

    summary = {
        'ingestion_run_id': run_id,
        'candidates': len(candidates),
        'written': written,
        'skipped_duplicate': skipped,
        'invalid': invalid,
        'post_kickoff': post_kickoff,
        'fixtures': len({c.get('fixture_id') for c in candidates}),
    }
    summary.update(_capture_contexts(payload, run_id))
    return summary
