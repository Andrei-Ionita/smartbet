"""
The one authoritative schema and write path for recommendation ingest.

Split out of `core.api_views.log_recommendations` so that:

* the HTTP boundary can enforce HMAC authentication without the scheduler —
  which ingests in-process — having to forge a signed request;
* validation happens in exactly one place, before anything is written.

Selection logic is NOT here and is not changed by this module. The Phase 2
defensive filters, normalisation, snapshot recording and pricing-integrity
classification below are carried over verbatim from the original view.
"""
import hashlib
import json
import logging

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import datetime, timedelta

from core.models import PredictionLog, PredictionSnapshot
from core.services import public_universe, snapshot_recording

logger = logging.getLogger(__name__)

# ── Abuse limits ────────────────────────────────────────────────────────────
# A legitimate run sends the engine's top ~10 picks; 27 leagues could in
# principle justify more, so the cap is generous but finite. Without it a
# single request could pin the worker and the database.
MAX_BATCH_SIZE = 200
MAX_BODY_BYTES = 2 * 1024 * 1024

# Markets the model actually produces. An unknown market cannot be graded, so
# it must never be stored.
ALLOWED_MARKET_TYPES = {'1x2', 'btts', 'over_under_2.5', 'double_chance'}

# Odds must be a real decimal price. <= 1 implies a guaranteed or negative
# return and is always either a bug or an attack.
MIN_ODDS = 1.01
MAX_ODDS = 1000.0

# A price captured long before the run cannot be the price the model saw.
MAX_ODDS_AGE = timedelta(hours=48)


class ValidationError(Exception):
    """Payload rejected. `errors` is a list of row-level, non-leaking messages."""

    def __init__(self, errors):
        super().__init__('; '.join(errors[:5]))
        self.errors = errors


def _as_aware(value):
    if value is None:
        return None
    if isinstance(value, str):
        parsed = parse_datetime(value.replace('Z', '+00:00'))
        if parsed is None:
            return None
        value = parsed
    if isinstance(value, datetime) and timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.utc)
    return value if isinstance(value, datetime) else None


def validate_batch(recommendations, *, now=None):
    """Validate a whole batch. Raises ValidationError; never writes.

    Transactional by design: a batch is accepted or rejected as a unit, so a
    malformed row cannot leave a half-written run behind. Errors are indexed by
    row and name only the field at fault — no payload echo, no internals.
    """
    now = now or timezone.now()
    errors = []

    if not isinstance(recommendations, list):
        raise ValidationError(['recommendations must be a list'])
    if not recommendations:
        raise ValidationError(['recommendations must not be empty'])
    if len(recommendations) > MAX_BATCH_SIZE:
        raise ValidationError([f'batch exceeds the maximum of {MAX_BATCH_SIZE} rows'])

    seen = set()
    for i, rec in enumerate(recommendations):
        def bad(msg):
            errors.append(f'row {i}: {msg}')

        if not isinstance(rec, dict):
            bad('must be an object')
            continue

        fixture_id = rec.get('fixture_id')
        if not isinstance(fixture_id, int) or fixture_id <= 0:
            bad('fixture_id must be a positive integer')
            continue

        best_market = rec.get('best_market')
        if best_market is not None and not isinstance(best_market, dict):
            bad('best_market must be an object')
            continue
        best_market = best_market or {}

        market_type = best_market.get('type', '1x2')
        if market_type not in ALLOWED_MARKET_TYPES:
            bad('unknown market_type')
            continue

        predicted = rec.get('predicted_outcome')
        if not isinstance(predicted, str) or not predicted.strip():
            bad('predicted_outcome is required')
            continue

        # One row per (fixture, market, outcome) per batch. Duplicates inside a
        # single run are always a caller bug.
        key = (fixture_id, market_type, predicted.strip().capitalize())
        if key in seen:
            bad('duplicate fixture/market/outcome within the batch')
            continue
        seen.add(key)

        for field in ('home_team', 'away_team', 'league'):
            value = rec.get(field)
            if not isinstance(value, str) or not value.strip():
                bad(f'{field} is required')
            elif len(value) > 100:
                bad(f'{field} exceeds 100 characters')

        kickoff = _as_aware(rec.get('kickoff'))
        if kickoff is None:
            bad('kickoff must be an ISO-8601 datetime')
        elif kickoff <= now:
            # A prediction recorded after kickoff is not a prediction. This is
            # the single most important check here: it is what stops a
            # backdated pick being presented as foresight.
            bad('kickoff is in the past — a prediction cannot postdate the match')

        odds = rec.get('odds')
        if odds is None:
            odds = best_market.get('odds')
        if not isinstance(odds, (int, float)) or isinstance(odds, bool):
            bad('odds must be a number')
        elif not (MIN_ODDS <= float(odds) <= MAX_ODDS):
            bad('odds outside the acceptable range')

        confidence = rec.get('confidence')
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            bad('confidence must be a number')
        elif not (0 <= float(confidence) <= 100):
            bad('confidence outside 0-100')

        provenance = rec.get('odds_provenance') or best_market.get('odds_provenance')
        if not isinstance(provenance, dict) or not provenance:
            bad('odds_provenance is required')
        else:
            missing = public_universe.missing_provenance_fields(provenance, market_type)
            if missing:
                bad('odds_provenance incomplete')
            captured = snapshot_recording.parse_odds_captured_at(provenance)
            if captured is None:
                bad('odds_provenance.odds_captured_at is required')
            elif captured > now + timedelta(minutes=5):
                bad('odds_captured_at is in the future')
            elif now - captured > MAX_ODDS_AGE:
                bad('odds_captured_at is too old to be this run\'s price')

    if errors:
        raise ValidationError(errors)


def derive_run_id(recommendations) -> str:
    """A run identity derived from the calculation itself.

    Deliberately content-addressed rather than random, so the two halves of the
    run-identity contract both hold:

    * **A retry of the same run is idempotent.** Re-ingesting the identical
      payload yields the same run id, so the snapshot uniqueness key
      ``(run_id, fixture_id, market_type, predicted_outcome)`` matches the
      existing rows and nothing is appended twice.
    * **A genuinely new run gets a new identity.** Any difference — a changed
      price, a new fixture, a fresh ``odds_captured_at`` — changes the digest,
      so real subsequent runs still produce distinct immutable snapshots.

    ``sort_keys`` so dict ordering can never split one run into two.
    """
    canonical = json.dumps(recommendations, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:32]


@transaction.atomic
def ingest_recommendations(recommendations, *, prediction_run_id=None, validate=True):
    """Persist one prediction run. Returns the same payload shape as before.

    Wrapped in a transaction so a failure part-way cannot leave a run with
    snapshots but no rows (or the reverse).
    """
    if validate:
        validate_batch(recommendations)

    prediction_run_id = prediction_run_id or derive_run_id(recommendations)
    run_generated_at = timezone.now()

    logged_count = updated_count = snapshots_created = 0
    skipped_blacklist = skipped_outcome = skipped_high_ev = skipped_watchlist = 0

    from core.api_views import (
        PHASE_2A_BLACKLISTED_LEAGUES,
        PHASE_2A_BLOCKED_OUTCOMES,
        PHASE_2B_MAX_EV,
        PHASE_2C_WATCHLIST_LEAGUES,
    )

    for rec in recommendations:
        fixture_id = rec.get('fixture_id')
        if not fixture_id:
            continue

        # Phase 2a/2b/2c defensive filters — unchanged.
        if rec.get('league') in PHASE_2A_BLACKLISTED_LEAGUES:
            skipped_blacklist += 1
            continue
        predicted_lower = (rec.get('predicted_outcome') or '').lower()
        if any(needle in predicted_lower for needle in PHASE_2A_BLOCKED_OUTCOMES):
            skipped_outcome += 1
            continue
        incoming_ev = rec.get('expected_value') or rec.get('ev')
        normalized_ev = None
        if incoming_ev is not None:
            normalized_ev = incoming_ev / 100.0 if abs(incoming_ev) > 1 else incoming_ev
            if normalized_ev > PHASE_2B_MAX_EV:
                skipped_high_ev += 1
                continue
        watch = PHASE_2C_WATCHLIST_LEAGUES.get(rec.get('league'))
        if watch is not None:
            incoming_conf = rec.get('confidence') or 0
            normalized_conf = incoming_conf / 100.0 if incoming_conf > 1 else incoming_conf
            effective_ev = normalized_ev if normalized_ev is not None else 0
            if normalized_conf < watch['min_confidence'] or effective_ev < watch['min_ev']:
                skipped_watchlist += 1
                continue

        kickoff = _as_aware(rec.get('kickoff')) or timezone.now()

        probabilities = rec.get('probabilities', {}) or {}
        prob_home = probabilities.get('home', 0) or 0
        prob_draw = probabilities.get('draw', 0) or 0
        prob_away = probabilities.get('away', 0) or 0

        confidence = rec.get('confidence', 0)
        if confidence > 1:
            confidence = confidence / 100

        expected_value = rec.get('expected_value') or rec.get('ev')
        if expected_value is not None and expected_value > 1:
            expected_value = expected_value / 100

        if prob_home > 1:
            prob_home = prob_home / 100
        if prob_draw > 1:
            prob_draw = prob_draw / 100
        if prob_away > 1:
            prob_away = prob_away / 100

        odds_data = rec.get('odds_data', {}) or {}
        predicted_outcome = rec.get('predicted_outcome', 'Home').capitalize()

        best_market = rec.get('best_market') or {}
        bet_odds = rec.get('odds') or best_market.get('odds')
        odds_provenance = (
            rec.get('odds_provenance') or best_market.get('odds_provenance') or None
        )
        raw_ev = best_market.get('original_ev')
        if raw_ev is not None and abs(raw_ev) > 1:
            raw_ev = raw_ev / 100.0

        existing = PredictionLog.objects.filter(fixture_id=fixture_id).first()

        prediction_data = {
            'home_team': rec.get('home_team', 'Unknown'),
            'away_team': rec.get('away_team', 'Unknown'),
            'league': rec.get('league', 'Unknown'),
            'league_id': None,
            'kickoff': kickoff,
            'predicted_outcome': predicted_outcome,
            'confidence': confidence,
            'probability_home': prob_home,
            'probability_draw': prob_draw,
            'probability_away': prob_away,
            'odds_home': odds_data.get('home'),
            'odds_draw': odds_data.get('draw'),
            'odds_away': odds_data.get('away'),
            'odds': bet_odds,
            'bookmaker': best_market.get('bookmaker') or odds_data.get('bookmaker'),
            'expected_value': expected_value,
            'raw_expected_value': raw_ev,
            'model_count': (rec.get('ensemble_info', {}) or {}).get('model_count', 0),
            'consensus': (rec.get('ensemble_info', {}) or {}).get('consensus'),
            'variance': (rec.get('ensemble_info', {}) or {}).get('variance'),
            'ensemble_strategy': (rec.get('ensemble_info', {}) or {}).get(
                'strategy', 'consensus_ensemble'
            ),
            'recommendation_score': rec.get('revenue_vs_risk_score'),
            'is_recommended': True,
            'market_type': best_market.get('type', '1x2'),
            'market_type_id': (
                best_market.get('type_id')
                or (rec.get('debug_info', {}) or {}).get('market_type_id')
            ),
            'market_score': best_market.get('market_score'),
            'odds_provenance': odds_provenance,
            'prediction_run_id': prediction_run_id,
        }

        snapshot_row, snapshot_is_new = snapshot_recording.record_snapshot(
            prediction_run_id=prediction_run_id,
            prediction=existing,
            fixture_id=fixture_id,
            home_team=prediction_data.get('home_team'),
            away_team=prediction_data.get('away_team'),
            league=prediction_data.get('league'),
            league_id=prediction_data.get('league_id'),
            kickoff=prediction_data.get('kickoff'),
            market_type=prediction_data.get('market_type'),
            predicted_outcome=prediction_data.get('predicted_outcome'),
            confidence=prediction_data.get('confidence'),
            expected_value=prediction_data.get('expected_value'),
            is_recommended=True,
            model_version=prediction_data.get('ensemble_strategy'),
            odds=bet_odds,
            odds_provenance=odds_provenance,
            prediction_generated_at=run_generated_at,
        )
        if snapshot_is_new:
            snapshots_created += 1

        if existing:
            for key, value in prediction_data.items():
                setattr(existing, key, value)
            existing.is_recommended = True
            existing.pricing_integrity_status = public_universe.status_for(
                odds_provenance,
                existing.prediction_logged_at,
                existing.is_audit_excluded,
                bet_odds,
                prediction_data.get('market_type'),
            )
            existing.save()
            updated_count += 1
        else:
            prediction_data['pricing_integrity_status'] = public_universe.status_for(
                odds_provenance, timezone.now(), False, bet_odds,
                prediction_data.get('market_type'),
            )
            created_row = PredictionLog.objects.create(
                fixture_id=fixture_id, **prediction_data
            )
            logged_count += 1
            if snapshot_row is not None and snapshot_row.prediction_id is None:
                PredictionSnapshot.objects.filter(
                    pk=snapshot_row.snapshot_id
                ).update(prediction=created_row)

    return {
        'success': True,
        'logged_count': logged_count,
        'updated_count': updated_count,
        'prediction_run_id': prediction_run_id,
        'snapshots_created': snapshots_created,
        'skipped_blacklist': skipped_blacklist,
        'skipped_outcome': skipped_outcome,
        'skipped_high_ev': skipped_high_ev,
        'skipped_watchlist': skipped_watchlist,
        'total': logged_count + updated_count,
        'message': (
            f'Logged {logged_count} new, updated {updated_count} existing; '
            f'skipped {skipped_blacklist} blacklist + {skipped_outcome} blocked-outcome '
            f'+ {skipped_high_ev} high-EV + {skipped_watchlist} watchlist recs'
        ),
    }
