"""
THE only supported way to create or settle a public claim.

Both the manual staff workflow and the future gem selector call these functions.
The selector's job is to *choose* a candidate; it must never duplicate
eligibility checks, snapshot creation, hash generation, immutability
enforcement, or permission logic:

    candidate = select_best_gem(...)
    claim = publish_prediction_claim(candidate.prediction_id, published_by=user)

Background: docs/audit/gem-selector-diagnostics-2026-07-29.md
"""
import logging
from datetime import timedelta
from datetime import timezone as dt_timezone

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import PredictionLog, PublishedClaim, PublishedClaimResult
from core.services import public_universe

logger = logging.getLogger(__name__)

# Prices are captured in the same pipeline run that generates the prediction, so
# a small clock/ordering skew is expected; anything beyond this is incoherent.
_CAPTURE_SLACK = timedelta(hours=6)


class PublicationError(Exception):
    """Publication refused. `reason` is a stable machine-readable code."""

    def __init__(self, reason, detail=''):
        self.reason = reason
        self.detail = detail
        super().__init__(f'{reason}: {detail}' if detail else reason)


class SettlementError(Exception):
    """Settlement refused (e.g. a contradictory result)."""

    def __init__(self, reason, detail=''):
        self.reason = reason
        self.detail = detail
        super().__init__(f'{reason}: {detail}' if detail else reason)


# ── Uniqueness / claim identity ─────────────────────────────────────────────
# A claim's identity is its SOURCE PREDICTION, not its fixture. `PredictionLog`
# is unique per fixture today, but the product is expected to support several
# markets per fixture later, so keying on fixture_id would wrongly block a second
# legitimate claim. Publishing is therefore idempotent per
# (source prediction, market_type, predicted_outcome):
#
#   * an existing, non-superseded claim for that triple  -> return it unchanged
#   * the source has since changed                       -> still return the
#     original; never rewrite or replace it (use claim.correct() to record a
#     correction as a NEW superseding claim)
#
# Every claim also carries its own immutable `claim_id` UUID, which is the stable
# public identifier.
def _existing_claim(prediction, market_type, predicted_outcome):
    return (
        PublishedClaim.objects
        .filter(
            prediction=prediction,
            market_type=market_type,
            predicted_outcome=predicted_outcome,
        )
        .filter(superseded_by__isnull=True)
        .order_by('-published_at')
        .first()
    )


def check_publication_eligibility(prediction, now=None):
    """Return a list of machine-readable reasons this may NOT be published.

    Empty list means eligible. Pure — performs no writes.
    """
    now = now or timezone.now()
    problems = []

    if not prediction.is_recommended:
        problems.append('not_recommended')
    if prediction.is_audit_excluded:
        problems.append('audit_excluded')
    if prediction.pricing_integrity_status != PredictionLog.PRICING_VERIFIED:
        problems.append(f'pricing_not_verified:{prediction.pricing_integrity_status}')
    if prediction.odds is None:
        problems.append('no_odds')

    missing = public_universe.missing_provenance_fields(
        prediction.odds_provenance, prediction.market_type
    )
    if missing:
        problems.append('incomplete_provenance:' + ','.join(missing))

    # A claim asserts foresight, so publication must precede kickoff.
    if prediction.kickoff is None:
        problems.append('no_kickoff')
    elif prediction.kickoff <= now:
        problems.append('fixture_already_started')

    # The prediction must have been generated before its own kickoff, and the
    # price must have been captured no later than publication.
    generated = prediction.prediction_logged_at
    if generated and prediction.kickoff and generated > prediction.kickoff:
        problems.append('prediction_generated_after_kickoff')

    captured_at = _odds_captured_at(prediction)
    if captured_at and prediction.kickoff and captured_at > prediction.kickoff:
        problems.append('odds_captured_after_kickoff')
    if captured_at and generated and captured_at < generated - _CAPTURE_SLACK:
        # A price captured materially BEFORE the prediction was generated means
        # the two do not describe the same moment.
        problems.append('odds_captured_before_prediction')

    return problems


def _odds_captured_at(prediction):
    """Parse the capture timestamp out of provenance, if present."""
    prov = prediction.odds_provenance or {}
    raw = prov.get('odds_captured_at')
    if not raw:
        return None
    from django.utils.dateparse import parse_datetime

    parsed = parse_datetime(str(raw).replace(' ', 'T', 1))
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, dt_timezone.utc)
    return parsed


@transaction.atomic
def publish_prediction_claim(prediction_id, published_by=None, now=None):
    """Freeze a verified prediction into an immutable public claim.

    Idempotent: publishing the same prediction twice returns the first claim.
    Raises PublicationError with a machine-readable `reason` when ineligible.
    """
    now = now or timezone.now()

    try:
        # Lock the source row so two concurrent publishes cannot both insert.
        prediction = (
            PredictionLog.objects.select_for_update().get(pk=prediction_id)
        )
    except PredictionLog.DoesNotExist:
        raise PublicationError('prediction_not_found', str(prediction_id))

    existing = _existing_claim(
        prediction, prediction.market_type, prediction.predicted_outcome
    )
    if existing is not None:
        # Never rewritten, even if the source has since changed.
        logger.info('Claim already published for prediction %s -> %s',
                    prediction_id, existing.claim_id)
        return existing

    problems = check_publication_eligibility(prediction, now=now)
    if problems:
        raise PublicationError('ineligible', '; '.join(problems))

    prov = prediction.odds_provenance or {}
    claim = PublishedClaim(
        prediction=prediction,
        fixture_id=prediction.fixture_id,
        home_team=prediction.home_team,
        away_team=prediction.away_team,
        league=prediction.league,
        league_id=prediction.league_id,
        kickoff=prediction.kickoff,
        market_type=prediction.market_type,
        predicted_outcome=prediction.predicted_outcome,
        confidence=prediction.confidence,
        odds=prediction.odds,
        # Snapshot, not a reference: the claim never reads mutable source fields
        # again at render time.
        odds_provenance=dict(prov),
        odds_captured_at=_odds_captured_at(prediction),
        prediction_generated_at=prediction.prediction_logged_at,
        published_at=now,
        model_version=prediction.ensemble_strategy,
        prediction_run_id=prediction.prediction_run_id,
        pricing_integrity_status=prediction.pricing_integrity_status,
    )
    try:
        claim.save()
    except IntegrityError as exc:
        # Lost a race, or an identical claim already exists (same hash).
        raced = _existing_claim(
            prediction, prediction.market_type, prediction.predicted_outcome
        )
        if raced is not None:
            return raced
        raise PublicationError('integrity_error', str(exc))

    logger.info('Published claim %s for prediction %s by %s',
                claim.claim_id, prediction_id,
                getattr(published_by, 'username', 'system'))
    return claim


# ── Settlement ──────────────────────────────────────────────────────────────
# Valid transitions are PENDING (no result row) -> WON | LOST | VOID | CANCELLED.
# There is no path back to PENDING and no path between terminal states: recording
# a different status for an already-settled claim is rejected, not applied.
VOID_MATCH_STATUSES = {'POSTP', 'ABAN', 'SUSP', 'DELETED', 'INT'}
CANCELLED_MATCH_STATUSES = {'CANC', 'CANCELLED', 'WO'}


def derive_settlement(prediction):
    """Settlement status implied by third-party fixture data, or None if pending."""
    status = (prediction.match_status or '').upper()
    if status in CANCELLED_MATCH_STATUSES:
        return PublishedClaim.STATUS_CANCELLED
    if status in VOID_MATCH_STATUSES:
        return PublishedClaim.STATUS_VOID
    if prediction.was_correct is None:
        return None
    return (PublishedClaim.STATUS_WON if prediction.was_correct
            else PublishedClaim.STATUS_LOST)


@transaction.atomic
def settle_published_claim(claim, status=None, now=None):
    """Record settlement for a claim, once.

    Idempotent for an identical status; raises SettlementError on a
    contradictory one. Never touches any claim field.
    """
    now = now or timezone.now()
    # Re-read the source: settlement must reflect CURRENT third-party fixture
    # data, and a cached FK on the passed claim instance can be stale.
    prediction = PredictionLog.objects.get(pk=claim.prediction_id)
    status = status or derive_settlement(prediction)

    if status is None:
        raise SettlementError('not_settled_yet', 'third-party result unavailable')
    if status == PublishedClaim.STATUS_PENDING:
        raise SettlementError('cannot_settle_to_pending')

    claim._state.fields_cache.pop('result', None)
    existing = getattr(claim, 'result', None)
    if existing is not None:
        if existing.status == status:
            return existing
        raise SettlementError(
            'contradictory_settlement',
            f'claim {claim.claim_id} already settled {existing.status}, '
            f'refusing to record {status}',
        )

    result = PublishedClaimResult(
        claim=claim,
        status=status,
        actual_score_home=prediction.actual_score_home,
        actual_score_away=prediction.actual_score_away,
        settled_at=now,
        result_source='sportmonks',
        result_reference=f'fixture:{prediction.fixture_id}:{prediction.match_status or ""}',
    )
    result.save()
    # Drop the reverse one-to-one cache so the caller's in-memory claim sees the
    # new settlement immediately (Django caches the "no result" lookup).
    claim._state.fields_cache.pop('result', None)
    logger.info('Settled claim %s as %s', claim.claim_id, status)
    return result
