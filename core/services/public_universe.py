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
from django.db.models import Q
from django.utils import timezone

from core.models import PredictionLog

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
# TODO(deploy): set to the actual production deploy timestamp of the odds fix,
# then run `manage.py classify_pricing_integrity`. Until then no row is
# verified, and the public record is correctly empty.
PRICING_INTEGRITY_CUTOFF = timezone.datetime(
    2026, 7, 29, 0, 0, 0, tzinfo=timezone.get_current_timezone()
)

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


def status_for(provenance, logged_at, is_audit_excluded, odds) -> str:
    """Integrity status for a set of raw values. Pure — performs no writes.

    Used both when writing new predictions and when classifying existing rows,
    so the two can never drift apart.
    """
    if is_audit_excluded:
        return PredictionLog.PRICING_AUDIT_EXCLUDED

    if logged_at is not None and logged_at < PRICING_INTEGRITY_CUTOFF:
        return PredictionLog.PRICING_LEGACY_UNVERIFIED

    if not isinstance(provenance, dict):
        return PredictionLog.PRICING_MISSING_PROVENANCE
    if provenance.get('odds_selection_policy') not in VERIFIED_ODDS_POLICIES:
        return PredictionLog.PRICING_MISSING_PROVENANCE
    if not provenance.get('odds_market_id') or not provenance.get('odds'):
        return PredictionLog.PRICING_MISSING_PROVENANCE
    if odds is None:
        return PredictionLog.PRICING_MISSING_PROVENANCE

    return PredictionLog.PRICING_VERIFIED


def classify_row(pred: PredictionLog) -> str:
    """Integrity status a stored row should carry. Pure — performs no writes."""
    return status_for(
        pred.odds_provenance,
        pred.prediction_logged_at,
        pred.is_audit_excluded,
        pred.odds,
    )
