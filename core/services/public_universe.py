"""
THE single definition of the public verified universe.

Every public surface — dashboard metrics, proof cards, ROI simulation, league
statistics, methodology figures, the gem selector and every API endpoint — must
denominate on the querysets defined here. Nothing may re-implement a
"slightly different" filter; that divergence is exactly how the 2026-07-29
audit found the public ROI reading +10.61% while the defensible figure was
-4.90%.

Background: `docs/audit/gem-selector-diagnostics-2026-07-29.md`.
"""
import logging
import os
from datetime import timedelta
from datetime import timezone as dt_timezone

from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.models import PredictionLog

logger = logging.getLogger(__name__)

# ── Confidence gate ──────────────────────────────────────────────────────────
# The versioned frontend strategy owns market eligibility. This backend gate
# mirrors only its declared leading-outcome floor; it must not reintroduce the
# retired 0.60/market-specific tuning after the snapshot has been stamped.
PER_MARKET_CONF_THRESHOLDS = {}
DEFAULT_CONF_THRESHOLD = 0.55

# ── Pricing-integrity cutoff ────────────────────────────────────────────────
# The instant the deterministic odds selector went live. Predictions generated
# before this cannot have verifiable price provenance: the old pipeline chose
# odds by substring match across ~38 "2.5"-containing entries spanning seven
# markets, and SportMonks does not expose historical point-in-time odds, so the
# original prices are unrecoverable.
#
# This constant EXISTS TO ASSIGN STATUS, not to filter. All filtering keys on
# `pricing_integrity_status`, so individual rows can later be quarantined
# independently of their date.
#
# Configured by the PRICING_INTEGRITY_CUTOFF environment variable (ISO-8601,
# UTC) so the validated deployment timestamp can be set WITHOUT another code
# commit and redeploy. It stays centralised here — nothing else may read the
# environment variable directly.
#
# FAIL-SAFE: when unset, the cutoff is far-future, so every row classifies as
# legacy_unverified and nothing is published as verified. An unconfigured
# deployment therefore under-claims rather than over-claims.
_CUTOFF_UNSET_SENTINEL = '2999-01-01T00:00:00+00:00'


def _load_cutoff():
    raw = (os.environ.get('PRICING_INTEGRITY_CUTOFF') or '').strip()
    if not raw:
        logger.warning(
            'PRICING_INTEGRITY_CUTOFF is not set — no prediction can be marked '
            'pricing-verified. Set it to the validated deployment timestamp.'
        )
        raw = _CUTOFF_UNSET_SENTINEL
    parsed = parse_datetime(raw)
    if parsed is None:
        raise ImproperlyConfigured(
            f'PRICING_INTEGRITY_CUTOFF is not a valid ISO-8601 datetime: {raw!r}'
        )
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, dt_timezone.utc)
    return parsed


PRICING_INTEGRITY_CUTOFF = _load_cutoff()
CUTOFF_IS_CONFIGURED = bool((os.environ.get('PRICING_INTEGRITY_CUTOFF') or '').strip())

# The selection policy that counts as verified. Bump when the policy changes so
# older rows are not silently treated as produced by the current logic.
VERIFIED_ODDS_POLICIES = {'lower_median_v1'}

# A recorded quote is evidence only if it was still reasonably current when
# BetGlitch committed it. This is shared by publication and performance so a
# price cannot pass one surface and fail another.
MAX_PRICE_AGE_AT_PUBLICATION = timedelta(
    hours=float(os.environ.get('MAX_PRICE_AGE_HOURS', '12'))
)


def claim_price_age_hours(claim):
    """Age of the frozen price at publication, or None when unknowable."""
    if not claim.odds_captured_at or not claim.published_at:
        return None
    return round(
        (claim.published_at - claim.odds_captured_at).total_seconds() / 3600,
        1,
    )


def claim_has_fresh_price(claim):
    """True only when a claim's price existed and was at most the public cap."""
    if not claim.odds_captured_at or not claim.published_at:
        return False
    age = claim.published_at - claim.odds_captured_at
    return timedelta(0) <= age <= MAX_PRICE_AGE_AT_PUBLICATION


def confidence_filter() -> Q:
    """Per-market confidence gate as a Q object."""
    q = Q()
    for market, threshold in PER_MARKET_CONF_THRESHOLDS.items():
        q |= Q(market_type=market, confidence__gte=threshold)
    q |= (
        ~Q(market_type__in=PER_MARKET_CONF_THRESHOLDS.keys())
        & Q(confidence__gte=DEFAULT_CONF_THRESHOLD)
    )
    return q


def recommended_qs():
    """Recommended picks whose price we can stand behind, resolved or not.

    Excludes, in one place:
      * never-recommended predictions;
      * quarantined bad-data rows (`is_audit_excluded`);
      * legacy rows whose original odds cannot be verified;
      * rows missing or with invalid price provenance;
      * picks below the per-market confidence gate.
    """
    return (
        PredictionLog.objects.filter(
            is_recommended=True,
            is_audit_excluded=False,
            pricing_integrity_status=PredictionLog.PRICING_VERIFIED,
        )
        .exclude(match_status='archived')
        .filter(confidence_filter())
    )


def resolved_qs():
    """The public universe for every settled metric (accuracy, ROI, cells)."""
    return recommended_qs().filter(actual_outcome__isnull=False)


def priced_qs():
    """Resolved rows that also carry a settled P/L — the ROI denominator."""
    return resolved_qs().filter(profit_loss_10__isnull=False)


def pending_qs():
    """Verified picks not yet settled — candidates for publication."""
    return recommended_qs().filter(
        actual_outcome__isnull=True, kickoff__gt=timezone.now()
    )


# ── THE public performance universe ─────────────────────────────────────────
# Every headline public statistic — accuracy, ROI, P/L, by-market, by-league,
# homepage figures, transparency dashboard, monitoring — denominates on THIS.
#
# It is built from PublishedClaim, not PredictionLog, because PredictionLog
# rows were mutable across pipeline re-runs. Grading was always correct, but we
# cannot prove a stored predicted_outcome is identical to the one generated at
# its timestamp. Only a published claim carries that guarantee.
#
# A claim counts only when ALL hold:
#   * the claim exists and is not superseded by a correction;
#   * its integrity hash still matches its stored fields (not tampered);
#   * its price provenance is complete;
#   * it is not quarantined / audit-excluded;
#   * (for settled metrics) its result is resolved.
def _claim_base():
    from core.models import PublishedClaim

    return (
        PublishedClaim.objects
        .filter(pricing_integrity_status=PredictionLog.PRICING_VERIFIED)
        .exclude(prediction__is_audit_excluded=True)
        .exclude(superseded_by__isnull=False)   # a correction replaced it
        .select_related('prediction', 'result')
    )


def verified_claims():
    """Published claims eligible for public statistics.

    Integrity and provenance are validated in Python — a SHA-256 over the
    stored fields cannot be expressed in SQL. Tampered or incomplete claims are
    EXCLUDED rather than silently counted.
    """
    out = []
    for claim in _claim_base():
        if not claim.verify_integrity():
            logger.error(
                'PublishedClaim %s failed integrity verification — excluded '
                'from public statistics.', claim.claim_id
            )
            continue
        if missing_provenance_fields(claim.odds_provenance, claim.market_type):
            continue
        if not claim_has_fresh_price(claim):
            logger.warning(
                'PublishedClaim %s used a missing or stale price — visible but '
                'excluded from public statistics.', claim.claim_id
            )
            continue
        out.append(claim)
    return out


def resolved_claims():
    """Verified claims with a recorded WON/LOST settlement.

    Settlement is read from the separate PublishedClaimResult row — never
    derived from the mutable prediction — so a claim counts only once its result
    has been explicitly recorded.

    VOID/CANCELLED POLICY: a voided or cancelled fixture is excluded from BOTH
    the numerator and the denominator of every public figure (win rate, ROI,
    accuracy). No stake was ever settled, so counting it either way would
    misstate the record. Such claims remain publicly visible with their own
    status; they simply do not score.

    PENDING claims (no result recorded) are likewise excluded.
    """
    return [c for c in verified_claims() if c.is_resolved]


def claim_profit_loss(claim, stake=10.0):
    """Flat-stake P/L for a settled claim, computed from the CLAIM's price.

    Deliberately not `prediction.profit_loss_10`: that was derived from the
    mutable row's odds. Public money figures must use the published price and
    the recorded settlement.
    """
    from core.models import PublishedClaim

    if not claim.is_resolved or not claim.odds:
        return None
    won = claim.result_status == PublishedClaim.STATUS_WON
    return stake * (claim.odds - 1) if won else -stake


# ── Provenance completeness ─────────────────────────────────────────────────
# A row may only be marked verified when the recorded price can be audited end
# to end: which market priced it, at which line, for which outcome, from which
# bookmaker, and when. Anything short of that is an explicit non-verified
# state — never silent acceptance.
REQUIRED_PROVENANCE_FIELDS = (
    'odds',
    'odds_market_id',
    'odds_market_description',
    'odds_label',
    'odds_bookmaker_id',
    'odds_bookmaker_name',
    'odds_captured_at',
    'odds_selection_policy',
)

# Product markets whose price is meaningless without an exact line, and the
# line each one requires. Mirrors MARKET_SPECS in oddsSelection.ts.
MARKETS_REQUIRING_LINE = {'over_under_2.5': 2.5}


def missing_provenance_fields(provenance, market_type=None):
    """THE authoritative completeness check. Returns a list of problems.

    Empty list means the provenance is complete and usable. Used by both
    `status_for` (new records) and `classify_row` (existing records) so the two
    can never drift apart.
    """
    if not isinstance(provenance, dict):
        return ['provenance_absent']

    problems = [
        field for field in REQUIRED_PROVENANCE_FIELDS
        if provenance.get(field) in (None, '')
    ]

    policy = provenance.get('odds_selection_policy')
    if policy is not None and policy not in VERIFIED_ODDS_POLICIES:
        problems.append('unrecognised_selection_policy')

    required_line = MARKETS_REQUIRING_LINE.get(market_type)
    if required_line is not None:
        try:
            if float(provenance.get('odds_line')) != required_line:
                problems.append('wrong_or_missing_line')
        except (TypeError, ValueError):
            problems.append('wrong_or_missing_line')

    return problems


def status_for(provenance, logged_at, is_audit_excluded, odds, market_type=None) -> str:
    """Integrity status for a set of raw values. Pure — performs no writes.

    Used both when writing new predictions and when classifying existing rows,
    so the two can never drift apart.
    """
    if is_audit_excluded:
        return PredictionLog.PRICING_AUDIT_EXCLUDED

    if logged_at is not None and logged_at < PRICING_INTEGRITY_CUTOFF:
        return PredictionLog.PRICING_LEGACY_UNVERIFIED

    if odds is None:
        return PredictionLog.PRICING_MISSING_PROVENANCE

    if missing_provenance_fields(provenance, market_type):
        return PredictionLog.PRICING_MISSING_PROVENANCE

    return PredictionLog.PRICING_VERIFIED


def classify_row(pred: PredictionLog) -> str:
    """Integrity status a stored row should carry. Pure — performs no writes."""
    return status_for(
        pred.odds_provenance,
        pred.prediction_logged_at,
        pred.is_audit_excluded,
        pred.odds,
        pred.market_type,
    )

# ── Snapshot timestamp coherence ────────────────────────────────────────────
# THE DOCUMENTED CAPTURE SEQUENCE.
#
# The recommendation pipeline fetches fixtures WITH their odds in a single
# SportMonks request, then computes model output from the same response. So the
# real order is:
#
#   odds_captured_at   (the bookmaker's own last-update time — necessarily
#                       BEFORE our fetch)
#     <=  prediction_generated_at   (when that run produced the prediction)
#     <=  snapshot_created_at       (when we recorded it)
#     <   publication time
#     <   kickoff
#
# We deliberately do NOT require `prediction_generated_at <= odds_captured_at`:
# a price legitimately exists before we read it. What we DO enforce is that no
# timestamp implies a price or prediction existed earlier than it actually did,
# and that the price is not stale relative to the prediction it is paired with —
# the exact defect that made pre-cutoff rows unpublishable (an old prediction
# timestamp beside a freshly captured price).
MAX_ODDS_AGE_FOR_VERIFIED = timedelta(hours=72)
# Small tolerance for clock skew between the odds feed and our own clock.
_CLOCK_SKEW = timedelta(minutes=10)


def snapshot_timestamp_problems(snapshot):
    """Machine-readable timestamp-coherence failures. Pure."""
    problems = []
    generated = snapshot.prediction_generated_at
    captured = snapshot.odds_captured_at
    created = snapshot.snapshot_created_at
    kickoff = snapshot.kickoff

    if generated is None:
        return ['no_prediction_generated_at']

    # Nothing may claim to predate its own recording.
    if created is not None and generated > created + _CLOCK_SKEW:
        problems.append('prediction_generated_after_snapshot_created')
    if created is not None and captured is not None and captured > created + _CLOCK_SKEW:
        problems.append('odds_captured_after_snapshot_created')

    # A price paired with a prediction must belong to the same run window.
    if captured is not None:
        if captured > generated + _CLOCK_SKEW:
            problems.append('odds_captured_after_prediction')
        elif generated - captured > MAX_ODDS_AGE_FOR_VERIFIED:
            # This is the pre-cutoff defect: old prediction, fresh price — or
            # equally, fresh prediction paired with a long-stale price.
            problems.append('odds_stale_relative_to_prediction')

    if kickoff is not None:
        if generated >= kickoff:
            problems.append('prediction_generated_after_kickoff')
        if captured is not None and captured >= kickoff:
            problems.append('odds_captured_after_kickoff')

    return problems


def classify_snapshot(snapshot):
    """Pricing-integrity status a snapshot should carry. Pure — no writes.

    A snapshot is `verified` only when it was generated after the clean cutoff,
    carries complete provenance, is not quarantined, and its timestamps are
    coherent (see the documented capture sequence above).
    """
    if snapshot.is_audit_excluded:
        return PredictionLog.PRICING_AUDIT_EXCLUDED

    generated = snapshot.prediction_generated_at
    if generated is None or generated < PRICING_INTEGRITY_CUTOFF:
        return PredictionLog.PRICING_LEGACY_UNVERIFIED

    if snapshot.odds is None:
        return PredictionLog.PRICING_MISSING_PROVENANCE
    if missing_provenance_fields(snapshot.odds_provenance, snapshot.market_type):
        return PredictionLog.PRICING_MISSING_PROVENANCE
    if snapshot_timestamp_problems(snapshot):
        return PredictionLog.PRICING_MISSING_PROVENANCE

    return PredictionLog.PRICING_VERIFIED
