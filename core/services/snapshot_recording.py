"""
Recording immutable prediction snapshots.

Every genuinely new model run appends a snapshot per (fixture, market, outcome),
INCLUDING for fixtures already in the pool. The latest-state `PredictionLog` row
is then updated as a convenience view.

    Prediction run -> immutable PredictionSnapshot -> update latest-state
                                                     PredictionLog

Nothing here ever rewrites a snapshot. A retried run is idempotent because the
uniqueness key includes `prediction_run_id`.
"""
import logging

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import timezone as dt_timezone

from core.models import PredictionSnapshot
from core.services import public_universe

logger = logging.getLogger(__name__)


def parse_odds_captured_at(provenance):
    """Capture timestamp from provenance, as an aware datetime or None."""
    raw = (provenance or {}).get('odds_captured_at')
    if not raw:
        return None
    parsed = parse_datetime(str(raw).replace(' ', 'T', 1))
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, dt_timezone.utc)
    return parsed


@transaction.atomic
def record_snapshot(
    *, prediction_run_id, prediction, fixture_id, home_team, away_team, league,
    league_id, kickoff, market_type, predicted_outcome, confidence,
    expected_value=None, is_recommended=False, model_version=None, odds=None,
    odds_provenance=None, prediction_generated_at=None, is_audit_excluded=False,
):
    """Append one snapshot for this run, or return the existing one.

    `prediction_generated_at` is the RUN's generation time — deliberately NOT
    `PredictionLog.prediction_logged_at`, which is the fixture's first-seen time
    and would pair an old timestamp with a freshly captured price.
    """
    generated = prediction_generated_at or timezone.now()

    existing = PredictionSnapshot.objects.filter(
        prediction_run_id=prediction_run_id,
        fixture_id=fixture_id,
        market_type=market_type,
        predicted_outcome=predicted_outcome,
    ).first()
    if existing is not None:
        return existing, False

    snapshot = PredictionSnapshot(
        prediction_run_id=prediction_run_id,
        prediction=prediction,
        fixture_id=fixture_id,
        home_team=home_team,
        away_team=away_team,
        league=league,
        league_id=league_id,
        kickoff=kickoff,
        market_type=market_type,
        predicted_outcome=predicted_outcome,
        confidence=confidence,
        expected_value=expected_value,
        is_recommended=is_recommended,
        model_version=model_version,
        odds=odds,
        odds_provenance=dict(odds_provenance) if odds_provenance else None,
        odds_captured_at=parse_odds_captured_at(odds_provenance),
        prediction_generated_at=generated,
        is_audit_excluded=is_audit_excluded,
    )
    # Classification needs snapshot_created_at, which auto_now_add only sets on
    # insert. Provide the value the DB is about to write so the status is right
    # first time; save() then recomputes the hash over the final field set.
    snapshot.snapshot_created_at = generated
    snapshot.pricing_integrity_status = public_universe.classify_snapshot(snapshot)

    try:
        snapshot.save()
    except IntegrityError:
        # Lost a race with a concurrent retry of the same run.
        raced = PredictionSnapshot.objects.filter(
            prediction_run_id=prediction_run_id,
            fixture_id=fixture_id,
            market_type=market_type,
            predicted_outcome=predicted_outcome,
        ).first()
        if raced is not None:
            return raced, False
        raise

    logger.info(
        'Snapshot %s recorded for fixture %s (%s/%s) run %s status=%s',
        snapshot.snapshot_id, fixture_id, market_type, predicted_outcome,
        prediction_run_id, snapshot.pricing_integrity_status,
    )
    return snapshot, True
