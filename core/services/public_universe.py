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
from datetime import timezone as dt_timezone

from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.models import PredictionLog

logger = logging.getLogger(__name__)

# ── Confidence gate ──────────────────────────────────────────────────────────
# over_under_2.5 uses the lowered 0.55 threshold (ROI tuning E4); every other
# market keeps the 0.60 default. Single source of truth for the gate.
PER_MARKET_CONF_THRESHOLDS = {'over_under_2.5': 0.55}
DEFAULT_CONF_THRESHOLD = 0.60

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
        .select_related('prediction')
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
        out.append(claim)
    return out


def resolved_claims():
    """Verified claims whose match has settled. The public performance set."""
    from core.models import PublishedClaim

    return [
        c for c in verified_claims()
        if c.prediction.was_correct is not None
        and c.result_status in (PublishedClaim.STATUS_WON, PublishedClaim.STATUS_LOST)
    ]


def claim_profit_loss(claim, stake=10.0):
    """Flat-stake P/L for a settled claim, computed from the CLAIM's price.

    Deliberately not `prediction.profit_loss_10`: that was derived from the
    mutable row's odds. Public money figures must use the published price.
    """
    if claim.prediction.was_correct is None or not claim.odds:
        return None
    return stake * (claim.odds - 1) if claim.prediction.was_correct else -stake


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
