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
import os
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

# ── Price freshness AT PUBLICATION ──────────────────────────────────────────
# `snapshot_timestamp_problems` already rejects a price that is stale RELATIVE
# TO ITS PREDICTION. That check cannot see this failure: a six-day-old price
# paired with a six-day-old prediction is internally coherent, passes every
# gate, and still gets published today as "verified".
#
# It happened. On 2026-08-08 half the live commitments carried prices older
# than 12h at publication, one of them 150.7 hours — six days. A reviewer
# asked the right question: does that price prove a bettor could actually have
# taken it? No. And since the public record's whole purpose is a future ROI
# that means something, a price nobody could get makes the eventual number
# fiction.
#
# So freshness is measured against PUBLICATION TIME, which is the moment we
# assert the price. Tunable, because the honest threshold is an empirical
# question — but a ceiling exists, and it fails closed.
MAX_PRICE_AGE_AT_PUBLICATION = timedelta(
    hours=float(os.environ.get('MAX_PRICE_AGE_HOURS', '12'))
)


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
# A claim's identity is its SOURCE SNAPSHOT — the immutable prediction state it
# was frozen from. Publishing is idempotent per snapshot:
#
#   * a non-superseded claim already exists for that snapshot -> return it
#   * the latest-state PredictionLog has since changed        -> irrelevant; the
#     claim was frozen from the snapshot, not the mutable row
#
# Every claim also carries its own immutable `claim_id` UUID, the stable public
# identifier.
def _existing_claim_for_snapshot(snapshot):
    return (
        PublishedClaim.objects
        .filter(snapshot=snapshot)
        .filter(superseded_by__isnull=True)
        .order_by('-published_at')
        .first()
    )


def check_snapshot_publication_eligibility(snapshot, now=None):
    """Machine-readable reasons this snapshot may NOT be published. Pure."""
    now = now or timezone.now()
    problems = []

    if not snapshot.is_recommended:
        problems.append('not_recommended')
    if snapshot.is_audit_excluded:
        problems.append('audit_excluded')
    if snapshot.pricing_integrity_status != PredictionLog.PRICING_VERIFIED:
        problems.append(f'pricing_not_verified:{snapshot.pricing_integrity_status}')
    if snapshot.odds is None:
        problems.append('no_odds')

    missing = public_universe.missing_provenance_fields(
        snapshot.odds_provenance, snapshot.market_type
    )
    if missing:
        problems.append('incomplete_provenance:' + ','.join(missing))

    # Timestamp coherence, per the documented capture sequence.
    for problem in public_universe.snapshot_timestamp_problems(snapshot):
        problems.append(problem)

    # A claim asserts foresight, so publication must precede kickoff.
    if snapshot.kickoff is None:
        problems.append('no_kickoff')
    elif snapshot.kickoff <= now:
        problems.append('fixture_already_started')

    # A snapshot replaced by a correction must not be published.
    if snapshot.is_superseded:
        problems.append('snapshot_superseded')

    # The price must not have been captured after we publish it.
    if snapshot.odds_captured_at and snapshot.odds_captured_at > now:
        problems.append('odds_captured_after_publication')

    # ...nor long before it. See MAX_PRICE_AGE_AT_PUBLICATION.
    if snapshot.odds_captured_at:
        age = now - snapshot.odds_captured_at
        if age > MAX_PRICE_AGE_AT_PUBLICATION:
            problems.append(
                f'stale_price_at_publication:{age.total_seconds() / 3600:.1f}h')

    return problems


def price_age_hours_at_publication(claim):
    """How old the recorded price was when the claim was published.

    Published so a reader never has to subtract two timestamps to discover
    that a quoted price was days old — which is exactly what a reviewer had
    to do on 2026-08-08.
    """
    if not claim.odds_captured_at or not claim.published_at:
        return None
    return round(
        (claim.published_at - claim.odds_captured_at).total_seconds() / 3600, 1)


@transaction.atomic
def publish_prediction_claim(snapshot_id, published_by=None, now=None):
    """Freeze an immutable PredictionSnapshot into a public claim.

    The snapshot is the AUTHORITATIVE input: every claim field is copied from it,
    never from the mutable PredictionLog. Idempotent per snapshot.
    """
    from core.models import PredictionSnapshot

    now = now or timezone.now()

    try:
        # `of=('self',)` is REQUIRED: select_related on the nullable
        # `prediction` FK produces a LEFT OUTER JOIN, and Postgres refuses
        # "FOR UPDATE cannot be applied to the nullable side of an outer join".
        # SQLite ignores this, so only a real Postgres run catches it.
        snapshot = (
            PredictionSnapshot.objects.select_for_update(of=('self',))
            .select_related('prediction').get(pk=snapshot_id)
        )
    except (PredictionSnapshot.DoesNotExist, ValueError, TypeError):
        raise PublicationError('snapshot_not_found', str(snapshot_id))

    existing = _existing_claim_for_snapshot(snapshot)
    if existing is not None:
        logger.info('Claim already published for snapshot %s -> %s',
                    snapshot_id, existing.claim_id)
        return existing

    # A snapshot that has been tampered with in the database must never become a
    # published claim.
    if not snapshot.verify_integrity():
        raise PublicationError('snapshot_integrity_failed', str(snapshot_id))

    problems = check_snapshot_publication_eligibility(snapshot, now=now)
    if problems:
        raise PublicationError('ineligible', '; '.join(problems))

    if snapshot.prediction_id is None:
        raise PublicationError(
            'no_latest_state_row',
            'settlement needs a PredictionLog to read third-party results from',
        )

    claim = PublishedClaim(
        snapshot=snapshot,
        prediction=snapshot.prediction,
        fixture_id=snapshot.fixture_id,
        home_team=snapshot.home_team,
        away_team=snapshot.away_team,
        league=snapshot.league,
        league_id=snapshot.league_id,
        kickoff=snapshot.kickoff,
        market_type=snapshot.market_type,
        predicted_outcome=snapshot.predicted_outcome,
        confidence=snapshot.confidence,
        odds=snapshot.odds,
        odds_provenance=dict(snapshot.odds_provenance or {}),
        odds_captured_at=snapshot.odds_captured_at,
        # The RUN's generation time, from the snapshot — not the fixture's
        # first-seen time on the mutable row.
        prediction_generated_at=snapshot.prediction_generated_at,
        published_at=now,
        model_version=snapshot.model_version,
        prediction_run_id=snapshot.prediction_run_id,
        pricing_integrity_status=snapshot.pricing_integrity_status,
    )
    try:
        claim.save()
    except IntegrityError as exc:
        raced = _existing_claim_for_snapshot(snapshot)
        if raced is not None:
            return raced
        raise PublicationError('integrity_error', str(exc))

    logger.info('Published claim %s from snapshot %s by %s',
                claim.claim_id, snapshot_id,
                getattr(published_by, 'username', 'system'))
    return claim


def eligible_snapshots_for_prediction(prediction, now=None):
    """Publishable snapshots for a latest-state row, newest first."""
    from core.models import PredictionSnapshot

    out = []
    for snap in (PredictionSnapshot.objects.filter(prediction=prediction)
                 .order_by('-prediction_generated_at')):
        if not check_snapshot_publication_eligibility(snap, now=now):
            out.append(snap)
    return out


def publish_for_prediction(prediction_id, published_by=None, now=None):
    """COMPATIBILITY wrapper. Resolves to ONE unambiguous eligible snapshot.

    Refuses when several candidates exist — the founder must choose the exact
    snapshot rather than have "latest" silently picked for them.
    """
    try:
        prediction = PredictionLog.objects.get(pk=prediction_id)
    except PredictionLog.DoesNotExist:
        raise PublicationError('prediction_not_found', str(prediction_id))

    candidates = eligible_snapshots_for_prediction(prediction, now=now)
    if not candidates:
        raise PublicationError(
            'no_eligible_snapshot',
            'no immutable snapshot for this prediction is publishable',
        )
    if len(candidates) > 1:
        raise PublicationError(
            'ambiguous_snapshot',
            'several eligible snapshots exist: '
            + ', '.join(str(c.snapshot_id) for c in candidates)
            + ' — publish one explicitly',
        )
    return publish_prediction_claim(
        candidates[0].snapshot_id, published_by=published_by, now=now
    )


# ── Settlement ──────────────────────────────────────────────────────────────
# Valid transitions are PENDING (no result row) -> WON | LOST | VOID | CANCELLED.
# There is no path back to PENDING and no path between terminal states.
#
# CRITICAL: a published claim is graded against the market and selection FROZEN
# IN THE CLAIM — never against the live PredictionLog row's current pick. Only
# the SCORE and FIXTURE STATUS come from the live row, because those are
# third-party facts about the match rather than statements we made.
#
# Reading `prediction.was_correct` here would be a correctness bug: that field is
# graded against whatever the row currently predicts, so a pipeline re-run that
# changed a fixture's market or selection would settle a published claim against
# a bet it never made.


def derive_settlement(claim_or_prediction):
    """Settlement status for a claim, or None while it cannot be determined.

    Accepts a PublishedClaim (preferred) or, for the latest-state view, a
    PredictionLog. With a claim, the BET is taken from the claim's frozen
    fields and only the RESULT from the linked prediction.
    """
    from core.models import PublishedClaim as _Claim
    from core.services import market_evaluation

    if isinstance(claim_or_prediction, _Claim):
        claim = claim_or_prediction
        # Always re-read the source: settlement must reflect CURRENT third-party
        # fixture data, and a cached FK can be stale.
        prediction = PredictionLog.objects.get(pk=claim.prediction_id)
        market_type = claim.market_type              # FROZEN
        predicted_outcome = claim.predicted_outcome  # FROZEN
    else:
        prediction = claim_or_prediction
        market_type = prediction.market_type
        predicted_outcome = prediction.predicted_outcome

    status = (prediction.match_status or '').upper()
    if market_evaluation.is_cancelled_status(status):
        return PublishedClaim.STATUS_CANCELLED
    if market_evaluation.is_void_status(status):
        return PublishedClaim.STATUS_VOID

    won = market_evaluation.evaluate_prediction(
        market_type=market_type,
        predicted_outcome=predicted_outcome,
        home_score=prediction.actual_score_home,
        away_score=prediction.actual_score_away,
        fixture_status=prediction.match_status,
        actual_outcome=prediction.actual_outcome,
    )
    if won is None:
        return None
    return PublishedClaim.STATUS_WON if won else PublishedClaim.STATUS_LOST


@transaction.atomic
def settle_published_claim(claim, status=None, now=None):
    """Record settlement for a claim, once.

    Idempotent for an identical status; raises SettlementError on a
    contradictory one. Never touches any claim field.
    """
    now = now or timezone.now()
    # Re-read the source for the SCORE; the BET comes from the claim itself.
    prediction = PredictionLog.objects.get(pk=claim.prediction_id)
    status = status or derive_settlement(claim)

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
