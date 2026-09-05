"""
Core models for SmartBet - Prediction Tracking & Bankroll Management
"""

import uuid

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal
import json


class PredictionLog(models.Model):
    """
    Tracks all predictions made by SmartBet for transparency and performance monitoring.
    Logs predictions BEFORE matches start, then updates with actual results.
    """
    # Match Identification
    fixture_id = models.IntegerField(unique=True, db_index=True)
    home_team = models.CharField(max_length=100)
    away_team = models.CharField(max_length=100)
    league = models.CharField(max_length=100)
    league_id = models.IntegerField(null=True, blank=True)
    kickoff = models.DateTimeField(db_index=True)
    
    # Our Prediction (logged BEFORE match starts - PROOF OF TIMESTAMP)
    predicted_outcome = models.CharField(max_length=10)  # 'Home', 'Draw', 'Away'
    confidence = models.FloatField()  # e.g., 62.5
    
    # Probability Distribution
    probability_home = models.FloatField()
    probability_draw = models.FloatField()
    probability_away = models.FloatField()
    
    # Team Form Data (stored as CSV string e.g., "W,L,W,D,W")
    home_team_form = models.CharField(max_length=50, null=True, blank=True)
    away_team_form = models.CharField(max_length=50, null=True, blank=True)
    
    # Betting Information
    odds_home = models.FloatField(null=True, blank=True)
    odds_draw = models.FloatField(null=True, blank=True)
    odds_away = models.FloatField(null=True, blank=True)
    bookmaker = models.CharField(max_length=50, null=True, blank=True)
    expected_value = models.FloatField(null=True, blank=True)

    # Bet-time odds for the *predicted* outcome (works for any market type).
    # For 1X2 this duplicates whichever of odds_home/draw/away matches predicted_outcome;
    # for O/U 2.5, BTTS, Double Chance this is the only place the actual bet odds live.
    odds = models.FloatField(null=True, blank=True)
    # The EV the prediction engine originally computed, before any client-side clamping
    # (e.g. evaluateValueZone). Lets us audit the raw signal without losing the displayed value.
    raw_expected_value = models.FloatField(null=True, blank=True)
    # Set when a row is excluded from public stats because we don't trust its data
    # (e.g. corrupt EV/odds from a known prior bug window). Counted in DB, hidden in UI.
    is_audit_excluded = models.BooleanField(default=False, db_index=True)

    # ── Pricing integrity (2026-07-29 odds-capture audit) ────────────────────
    # Until 2026-07-29 the recommendation pipeline selected odds by substring
    # ("2.5" anywhere in a market name/label) and took the first match in
    # arbitrary API order, so full-time picks could be priced with SECOND-HALF
    # quotes (market_id 53). Every price-dependent public statistic computed
    # before the fix is therefore unverifiable. Original point-in-time odds
    # cannot be reconstructed — SportMonks odds endpoints are not historical —
    # so those rows are preserved but permanently excluded from public pricing
    # statistics rather than back-filled with approximations.
    PRICING_VERIFIED = 'verified'
    PRICING_LEGACY_UNVERIFIED = 'legacy_unverified'
    PRICING_AUDIT_EXCLUDED = 'audit_excluded'
    PRICING_MISSING_PROVENANCE = 'missing_provenance'
    PRICING_INTEGRITY_CHOICES = [
        (PRICING_VERIFIED, 'Verified — price captured by the deterministic selector'),
        (PRICING_LEGACY_UNVERIFIED, 'Legacy — original odds cannot be verified'),
        (PRICING_AUDIT_EXCLUDED, 'Quarantined — known bad data'),
        (PRICING_MISSING_PROVENANCE, 'Missing or invalid price provenance'),
    ]
    pricing_integrity_status = models.CharField(
        max_length=24,
        choices=PRICING_INTEGRITY_CHOICES,
        default=PRICING_LEGACY_UNVERIFIED,
        db_index=True,
        help_text='Only PRICING_VERIFIED rows may appear in public pricing statistics.',
    )
    # Full audit trail for the recorded price: market_id, market description,
    # line, label, bookmaker, quote count/min/max, capture time, source entry id
    # and the selection policy. Shape mirrors OddsProvenance in
    # smartbet-frontend/app/lib/oddsSelection.ts.
    odds_provenance = models.JSONField(null=True, blank=True)
    # Identifies the pipeline run that produced this prediction.
    prediction_run_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    
    # Ensemble Info
    model_count = models.IntegerField(default=0)
    consensus = models.FloatField(null=True, blank=True)
    variance = models.FloatField(null=True, blank=True)
    ensemble_strategy = models.CharField(max_length=50, default='consensus_ensemble')
    
    # Actual Result (updated AFTER match completes)
    actual_outcome = models.CharField(max_length=10, null=True, blank=True)  # 'Home', 'Draw', 'Away'
    actual_score_home = models.IntegerField(null=True, blank=True)
    actual_score_away = models.IntegerField(null=True, blank=True)
    match_status = models.CharField(max_length=20, null=True, blank=True)  # 'FT', 'CANC', etc.
    
    # Performance Metrics (calculated after match)
    was_correct = models.BooleanField(null=True, blank=True)
    profit_loss_10 = models.FloatField(null=True, blank=True)  # P/L for $10 stake
    roi_percent = models.FloatField(null=True, blank=True)
    
    # Timestamps (CRITICAL for trust)
    prediction_logged_at = models.DateTimeField(auto_now_add=True, db_index=True)  # PROOF: logged before match
    result_logged_at = models.DateTimeField(null=True, blank=True)  # When we got the result
    
    # Metadata
    recommendation_score = models.FloatField(null=True, blank=True)  # Overall recommendation score
    is_recommended = models.BooleanField(default=False, db_index=True)  # True if this prediction was in the top recommendations
    
    # Multi-Market Support (V3)
    MARKET_TYPE_CHOICES = [
        ('1x2', 'Match Result'),
        ('btts', 'Both Teams to Score'),
        ('over_under_2.5', 'Over/Under 2.5'),
        ('double_chance', 'Double Chance'),
    ]
    market_type = models.CharField(
        max_length=20, 
        choices=MARKET_TYPE_CHOICES, 
        default='1x2',
        db_index=True
    )
    market_type_id = models.IntegerField(null=True, blank=True)  # SportMonks type_id
    market_score = models.FloatField(null=True, blank=True)  # MarketScore used for ranking
    
    notes = models.TextField(blank=True)  # Any special notes
    
    class Meta:
        ordering = ['-kickoff']
        indexes = [
            models.Index(fields=['fixture_id']),
            models.Index(fields=['kickoff']),
            models.Index(fields=['predicted_outcome']),
            models.Index(fields=['was_correct']),
            models.Index(fields=['league']),
            models.Index(fields=['is_recommended']),
            models.Index(fields=['is_recommended', 'was_correct']),  # Composite index for accuracy queries
            models.Index(fields=['is_recommended', '-kickoff']),  # Composite index for monitoring dashboard performance
        ]
        verbose_name = "Prediction Log"
        verbose_name_plural = "Prediction Logs"
    
    def __str__(self):
        return f"{self.home_team} vs {self.away_team} - Predicted: {self.predicted_outcome} ({self.confidence}%)"

    # Plausible bounds for sports-betting expected value. Anything outside this almost always
    # means a pricing/units bug — log it (and stash the raw value) rather than silently inflate stats.
    EV_PLAUSIBLE_MIN = -0.30
    EV_PLAUSIBLE_MAX = 0.50

    def save(self, *args, **kwargs):
        import logging
        log = logging.getLogger(__name__)

        # Confidence may arrive as percentage from some legacy callers; coerce to decimal.
        if self.confidence is not None and self.confidence > 1:
            self.confidence = self.confidence / 100.0

        # EV may arrive as percentage; coerce to decimal.
        if self.expected_value is not None and abs(self.expected_value) > 1:
            self.expected_value = self.expected_value / 100.0
        if self.raw_expected_value is not None and abs(self.raw_expected_value) > 1:
            self.raw_expected_value = self.raw_expected_value / 100.0

        # Stash the raw value before any clamp, so we can audit later.
        if self.expected_value is not None and self.raw_expected_value is None:
            self.raw_expected_value = self.expected_value

        # Clamp implausible EV. Sports markets don't price +50% edges; values higher mean
        # bad probabilities or a unit-mismatch bug. Mark for audit exclusion rather than
        # publishing inflated numbers. If a previously-bad row arrives with a clean EV on
        # update, leave the exclusion flag alone — audit decisions are managed elsewhere.
        if self.expected_value is not None and (
            self.expected_value > self.EV_PLAUSIBLE_MAX
            or self.expected_value < self.EV_PLAUSIBLE_MIN
        ):
            log.warning(
                "PredictionLog fixture=%s: implausible EV %.4f (raw=%s) — clamping and marking audit-excluded",
                self.fixture_id, self.expected_value, self.raw_expected_value,
            )
            self.expected_value = max(
                self.EV_PLAUSIBLE_MIN,
                min(self.EV_PLAUSIBLE_MAX, self.expected_value),
            )
            self.is_audit_excluded = True

        # Odds sanity: decimal odds must be > 1.0. A value < 1.01 is data corruption.
        if self.odds is not None and self.odds <= 1.01:
            log.warning(
                "PredictionLog fixture=%s: invalid odds %.4f — discarding",
                self.fixture_id, self.odds,
            )
            self.odds = None

        return super().save(*args, **kwargs)

    def calculate_performance(self):
        """
        Calculate performance metrics after match completes.
        Supports multi-market verification: 1X2, BTTS, O/U 2.5, Double Chance
        """
        if self.actual_outcome is None and self.actual_score_home is None:
            return  # No result data yet
            
        if not self.predicted_outcome:
            return  # No prediction to verify
        
        # Grading rules live in ONE place: core.services.market_evaluation.
        # This row is graded against ITS CURRENT pick, which is correct for the
        # latest-state view. Published claims are graded separately against
        # their own FROZEN pick — see claim_publication.derive_settlement.
        from core.services import market_evaluation

        market_type = getattr(self, 'market_type', '1x2') or '1x2'
        predicted = self.predicted_outcome.lower().strip()
        home_score = self.actual_score_home
        away_score = self.actual_score_away

        self.was_correct = market_evaluation.evaluate_prediction(
            market_type=market_type,
            predicted_outcome=self.predicted_outcome,
            home_score=home_score,
            away_score=away_score,
            fixture_status=self.match_status,
            actual_outcome=self.actual_outcome,
        )

        # ============= CALCULATE PROFIT/LOSS =============
        # Prefer the canonical `odds` field (works for any market). Fall back to per-outcome
        # 1X2 columns, and only as a last resort back-calculate from EV (legacy historical rows).
        market_odds = self.odds

        if not market_odds and market_type == '1x2':
            if predicted == 'home':
                market_odds = self.odds_home
            elif predicted == 'draw':
                market_odds = self.odds_draw
            elif predicted == 'away':
                market_odds = self.odds_away

        if not market_odds and self.expected_value and self.confidence and self.confidence > 0:
            # Legacy back-calc: EV = (prob * odds) - 1, so odds = (EV + 1) / prob.
            # Only reached for historical rows logged before `odds` was captured.
            market_odds = (self.expected_value + 1) / self.confidence
        
        # Calculate P/L
        if self.was_correct is True:
            if market_odds and market_odds > 1:
                self.profit_loss_10 = 10 * (market_odds - 1)
            else:
                self.profit_loss_10 = 0  # No odds available
        elif self.was_correct is False:
            self.profit_loss_10 = -10
        else:
            self.profit_loss_10 = None  # Undetermined
        
        # Calculate ROI
        if self.profit_loss_10 is not None:
            self.roi_percent = (self.profit_loss_10 / 10) * 100
        
        self.result_logged_at = timezone.now()
        self.save()


class PredictionSnapshot(models.Model):
    """An IMMUTABLE record of one prediction, as it existed at one moment.

    WHY THIS EXISTS
    ---------------
    `PredictionLog` was doing two incompatible jobs: (a) the mutable latest state
    for a fixture, and (b) a historical prediction generated at a specific time.
    Because `prediction_logged_at` is `auto_now_add`, a fixture first seen weeks
    ago kept that original timestamp forever — so a fresh model run against an
    existing fixture produced a row pairing an OLD prediction timestamp with a
    NEWLY captured price. That combination cannot be published truthfully, which
    is why nothing was publishable after the 2026-07-30 pricing cutoff.

    A snapshot fixes that by recording one coherent prediction state: the run
    that produced it, when that run generated the prediction, and the price that
    run captured. Every genuinely new run appends a new snapshot; nothing is ever
    overwritten.

        Prediction run -> immutable PredictionSnapshot -> update latest-state
                                                          PredictionLog

    Snapshots are evidence CANDIDATES. They enter public performance only once
    explicitly published as a PublishedClaim.
    """
    snapshot_id = models.UUIDField(primary_key=True, editable=False)

    # Which run produced this, and the latest-state row it corresponds to.
    prediction_run_id = models.CharField(max_length=64, db_index=True)
    prediction = models.ForeignKey(
        'PredictionLog', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='snapshots',
        help_text='Latest-state row for this fixture. Convenience only — never '
                  'the authoritative source for a published claim.',
    )

    # Fixture identity, frozen.
    fixture_id = models.IntegerField(db_index=True)
    home_team = models.CharField(max_length=100)
    away_team = models.CharField(max_length=100)
    league = models.CharField(max_length=100)
    league_id = models.IntegerField(null=True, blank=True)
    kickoff = models.DateTimeField()

    # The prediction, frozen.
    market_type = models.CharField(max_length=20)
    predicted_outcome = models.CharField(max_length=32)
    confidence = models.FloatField()
    expected_value = models.FloatField(null=True, blank=True)
    is_recommended = models.BooleanField(default=False)
    model_version = models.CharField(max_length=64, null=True, blank=True)

    # The price, frozen, with full provenance.
    odds = models.FloatField(null=True, blank=True)
    odds_provenance = models.JSONField(null=True, blank=True)
    odds_captured_at = models.DateTimeField(null=True, blank=True)

    # Timestamps. `prediction_generated_at` is the RUN's generation time — not
    # PredictionLog.prediction_logged_at, which is the fixture's first-seen time.
    prediction_generated_at = models.DateTimeField()
    snapshot_created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    pricing_integrity_status = models.CharField(
        max_length=24,
        choices=PredictionLog.PRICING_INTEGRITY_CHOICES,
        default=PredictionLog.PRICING_LEGACY_UNVERIFIED,
        db_index=True,
    )
    is_audit_excluded = models.BooleanField(default=False, db_index=True)

    # Tamper detection over the frozen fields. Uses the SHARED canonical hasher
    # (core/services/integrity.py) rather than a second implementation — the
    # snapshot is the evidence a claim is built from, so a raw DB edit here must
    # be detectable, not merely discouraged.
    SNAPSHOT_HASH_VERSION = 'v1'
    snapshot_hash = models.CharField(max_length=64, db_index=True)
    snapshot_hash_version = models.CharField(max_length=8, default='v1')

    # A correction appends a new snapshot pointing at the one it replaces.
    supersedes = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.PROTECT,
        related_name='superseded_by',
    )
    correction_reason = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ['-prediction_generated_at']
        # UNIQUENESS POLICY: one run produces at most one prediction per fixture
        # and market, so a retry of the same run is idempotent rather than
        # duplicative. Two DIFFERENT runs over the same fixture legitimately
        # produce two snapshots, even when the outcome is identical — they are
        # distinct time-specific observations.
        constraints = [
            models.UniqueConstraint(
                fields=['prediction_run_id', 'fixture_id', 'market_type',
                        'predicted_outcome'],
                name='uniq_snapshot_per_run_fixture_market_outcome',
            ),
        ]
        indexes = [
            models.Index(fields=['fixture_id', '-prediction_generated_at']),
            models.Index(fields=['pricing_integrity_status']),
        ]
        verbose_name = 'Prediction Snapshot'

    def __str__(self):
        return (f'{self.home_team} v {self.away_team} — {self.predicted_outcome} '
                f'@ {self.odds} ({self.prediction_generated_at:%Y-%m-%d %H:%M})')

    # ── Immutability ─────────────────────────────────────────────────────────
    def canonical_payload(self):
        from core.services.integrity import norm_dt, norm_num

        prov = self.odds_provenance or {}
        return {
            'snapshot_hash_version': self.SNAPSHOT_HASH_VERSION,
            'prediction_run_id': self.prediction_run_id,
            'fixture_id': self.fixture_id,
            'home_team': self.home_team,
            'away_team': self.away_team,
            'league': self.league,
            'league_id': self.league_id,
            'kickoff': norm_dt(self.kickoff),
            'market_type': self.market_type,
            'predicted_outcome': self.predicted_outcome,
            'confidence': norm_num(self.confidence),
            'expected_value': norm_num(self.expected_value),
            'is_recommended': self.is_recommended,
            'model_version': self.model_version,
            'odds': norm_num(self.odds),
            'odds_market_id': prov.get('odds_market_id'),
            'odds_market_description': prov.get('odds_market_description'),
            'odds_line': norm_num(prov.get('odds_line')),
            'odds_label': prov.get('odds_label'),
            'odds_bookmaker_id': prov.get('odds_bookmaker_id'),
            'odds_bookmaker_name': prov.get('odds_bookmaker_name'),
            'odds_selection_policy': prov.get('odds_selection_policy'),
            'odds_captured_at': norm_dt(self.odds_captured_at),
            'prediction_generated_at': norm_dt(self.prediction_generated_at),
            'supersedes': str(self.supersedes_id) if self.supersedes_id else None,
            'correction_reason': self.correction_reason,
        }

    def compute_hash(self):
        from core.services.integrity import canonical_sha256

        return canonical_sha256(self.canonical_payload())

    def verify_integrity(self):
        return bool(self.snapshot_hash) and self.snapshot_hash == self.compute_hash()

    def save(self, *args, **kwargs):
        """Append-only. A snapshot is never rewritten."""
        if not self._state.adding:
            raise ValueError(
                'PredictionSnapshot is immutable — a new model run must append a '
                'new snapshot. Use correct() to record a superseding snapshot.'
            )
        import uuid

        if not self.snapshot_id:
            self.snapshot_id = uuid.uuid4()
        self.snapshot_hash_version = self.SNAPSHOT_HASH_VERSION
        self.snapshot_hash = self.compute_hash()
        super().save(*args, **kwargs)

    CORRECTABLE_FIELDS = (
        'prediction_run_id', 'prediction', 'fixture_id', 'home_team', 'away_team',
        'league', 'league_id', 'kickoff', 'market_type', 'predicted_outcome',
        'confidence', 'expected_value', 'is_recommended', 'model_version',
        'odds', 'odds_provenance', 'odds_captured_at', 'prediction_generated_at',
        'pricing_integrity_status', 'is_audit_excluded',
    )

    def correct(self, reason, **changes):
        """Append a superseding snapshot; never rewrite this one.

        The correction gets a DERIVED run id (`<original>+corr:<short-uuid>`).
        The uniqueness key includes `prediction_run_id`, and a correction is a
        distinct recording event rather than a retry of the original run, so
        reusing the original id would collide. Keeping the original id as a
        prefix preserves the lineage.
        """
        import uuid

        fields = {f: getattr(self, f) for f in self.CORRECTABLE_FIELDS}
        fields.update(changes)
        fields['prediction_run_id'] = (
            f'{self.prediction_run_id}+corr:{uuid.uuid4().hex[:8]}'
        )
        return PredictionSnapshot.objects.create(
            supersedes=self, correction_reason=reason, **fields
        )

    @property
    def is_superseded(self):
        return self.superseded_by.exists()

    @property
    def is_published(self):
        return self.published_claims.exists()


class PublishedClaim(models.Model):
    """
    An immutable, insert-only snapshot of a claim made publicly.

    WHY THIS EXISTS
    ---------------
    `PredictionLog` rows are MUTABLE: the recommendation pipeline overwrites
    every field on each re-run (see core/api_views.py), while
    `prediction_logged_at` is `auto_now_add` and never changes. A public proof
    URL could therefore display a different pick or price than the one actually
    posted, while still asserting the original timestamp — the precise
    behaviour BetGlitch's transparency claim exists to rule out.

    This model separates two genuinely different objects:
      * the LIVE prediction (PredictionLog) — free to keep improving;
      * the PUBLISHED CLAIM (here) — frozen the moment it goes public.

    Settlement never rewrites a claim: results are read from the linked
    PredictionLog and rendered separately.
    """
    STATUS_PENDING = 'PENDING'
    STATUS_WON = 'WON'
    STATUS_LOST = 'LOST'
    STATUS_VOID = 'VOID'
    STATUS_CANCELLED = 'CANCELLED'
    RESULT_STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_WON, 'Won'),
        (STATUS_LOST, 'Lost'),
        (STATUS_VOID, 'Void'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    claim_id = models.UUIDField(primary_key=True, editable=False)
    # The IMMUTABLE snapshot this claim was frozen from — the authoritative
    # source. Nullable only for claims created before the snapshot layer existed.
    snapshot = models.ForeignKey(
        'PredictionSnapshot', on_delete=models.PROTECT, null=True, blank=True,
        related_name='published_claims',
    )
    # Latest-state row, for convenience joins and settlement lookups only.
    prediction = models.ForeignKey(
        PredictionLog, on_delete=models.PROTECT, related_name='published_claims'
    )

    # ── Frozen claim fields (never updated after insert) ─────────────────────
    fixture_id = models.IntegerField(db_index=True)
    home_team = models.CharField(max_length=100)
    away_team = models.CharField(max_length=100)
    league = models.CharField(max_length=100)
    league_id = models.IntegerField(null=True, blank=True)
    kickoff = models.DateTimeField()
    market_type = models.CharField(max_length=20)
    predicted_outcome = models.CharField(max_length=32)
    confidence = models.FloatField()
    odds = models.FloatField()

    # Price provenance, copied from the selector (see oddsSelection.ts).
    odds_provenance = models.JSONField()
    odds_captured_at = models.DateTimeField(null=True, blank=True)

    prediction_generated_at = models.DateTimeField()
    published_at = models.DateTimeField(default=timezone.now)
    model_version = models.CharField(max_length=64, null=True, blank=True)
    prediction_run_id = models.CharField(max_length=64, null=True, blank=True)

    pricing_integrity_status = models.CharField(
        max_length=24,
        choices=PredictionLog.PRICING_INTEGRITY_CHOICES,
        default=PredictionLog.PRICING_VERIFIED,
    )
    # sha256 over the frozen claim fields. A hash DETECTS modification; it does
    # not prevent it. Prevention comes from save() refusing updates and from
    # corrections being recorded as new, superseding claims.
    claim_hash = models.CharField(max_length=64, unique=True)
    claim_hash_version = models.CharField(max_length=8, default='v1')

    # Corrections are recorded SEPARATELY rather than rewriting the original.
    # A corrected claim is a NEW row pointing at the one it replaces; the
    # original stays readable forever with its own hash intact.
    supersedes = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.PROTECT,
        related_name='superseded_by',
    )
    correction_reason = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['fixture_id']),
            models.Index(fields=['-published_at']),
        ]

    def __str__(self):
        return f'{self.home_team} v {self.away_team} — {self.predicted_outcome} @ {self.odds}'

    # ── Immutability & canonical integrity hash ──────────────────────────────
    # The hash covers a DETERMINISTIC canonical payload: explicit field order via
    # sorted JSON keys, timestamps normalised to UTC microsecond ISO-8601,
    # decimals normalised through Decimal so 1.80 and 1.8 hash identically, and
    # an explicit schema version so future changes can verify older claims.
    #
    # Settlement is deliberately NOT part of this payload — it lives in a
    # separate PublishedClaimResult row, so recording a result can never alter a
    # claim's hash.
    CLAIM_HASH_VERSION = 'v1'

    def canonical_payload(self):
        """The exact dict that is hashed. Documented and stable."""
        from core.services.integrity import norm_dt as _dt, norm_num as _num

        prov = self.odds_provenance or {}

        return {
            'claim_hash_version': self.CLAIM_HASH_VERSION,
            # source references
            'source_snapshot_id': str(self.snapshot_id) if self.snapshot_id else None,
            'source_prediction_id': self.prediction_id,
            # fixture identity
            'fixture_id': self.fixture_id,
            'home_team': self.home_team,
            'away_team': self.away_team,
            'league': self.league,
            'league_id': self.league_id,
            'kickoff': _dt(self.kickoff),
            # the claim itself
            'market_type': self.market_type,
            'predicted_outcome': self.predicted_outcome,
            'confidence': _num(self.confidence),
            'odds': _num(self.odds),
            # price provenance
            'odds_market_id': prov.get('odds_market_id'),
            'odds_market_description': prov.get('odds_market_description'),
            'odds_line': _num(prov.get('odds_line')),
            'odds_label': prov.get('odds_label'),
            'odds_bookmaker_id': prov.get('odds_bookmaker_id'),
            'odds_bookmaker_name': prov.get('odds_bookmaker_name'),
            'odds_selection_policy': prov.get('odds_selection_policy'),
            'odds_captured_at': _dt(self.odds_captured_at),
            # timestamps and lineage
            'prediction_generated_at': _dt(self.prediction_generated_at),
            'published_at': _dt(self.published_at),
            'prediction_run_id': self.prediction_run_id,
            'model_version': self.model_version,
            'supersedes': str(self.supersedes_id) if self.supersedes_id else None,
            'correction_reason': self.correction_reason,
        }

    def compute_hash(self):
        """SHA-256 over the canonical payload. THE authoritative computation."""
        from core.services.integrity import canonical_sha256

        return canonical_sha256(self.canonical_payload())

    def verify_integrity(self):
        """THE authoritative verification method. True when untampered."""
        return bool(self.claim_hash) and self.claim_hash == self.compute_hash()

    def save(self, *args, **kwargs):
        """Insert-only. Any attempt to update a published claim is a bug."""
        if not self._state.adding:
            raise ValueError(
                'PublishedClaim is immutable — a published claim can never be '
                'updated. Record settlement on PublishedClaimResult, or publish '
                'a correcting claim via correct().'
            )
        import uuid

        if not self.claim_id:
            self.claim_id = uuid.uuid4()
        self.claim_hash_version = self.CLAIM_HASH_VERSION
        self.claim_hash = self.compute_hash()
        super().save(*args, **kwargs)

    @property
    def is_superseded(self):
        """True when a later, corrected claim replaced this one."""
        return self.superseded_by.exists()

    CORRECTABLE_FIELDS = (
        'fixture_id', 'home_team', 'away_team', 'league', 'league_id', 'kickoff',
        'market_type', 'predicted_outcome', 'confidence', 'odds',
        'odds_provenance', 'odds_captured_at', 'prediction_generated_at',
        'model_version', 'prediction_run_id',
    )

    def correct(self, reason, **changes):
        """Record a correction as a NEW claim; never rewrite this one.

        Returns the superseding claim. The original stays readable with its
        original hash intact — which is what makes "corrections are recorded
        separately" a true statement rather than a slogan.
        """
        fields = {f: getattr(self, f) for f in self.CORRECTABLE_FIELDS}
        fields.update(changes)
        return PublishedClaim.objects.create(
            prediction=self.prediction,
            pricing_integrity_status=self.pricing_integrity_status,
            supersedes=self,
            correction_reason=reason,
            **fields,
        )

    @property
    def result_status(self):
        """Settlement state, read from the separate result record.

        PENDING means no settlement has been recorded. Never derived from the
        mutable prediction row — settlement is an explicit, recorded event.
        """
        result = getattr(self, 'result', None)
        return result.status if result is not None else self.STATUS_PENDING

    @property
    def is_resolved(self):
        """Counts toward win/loss and ROI. VOID/CANCELLED deliberately do not."""
        return self.result_status in (self.STATUS_WON, self.STATUS_LOST)

    @property
    def card_cache_version(self):
        """Cache identity for the PUBLIC CARD's current rendered state.

        Next derives an Open Graph image query hash from the opengraph-image
        MODULE CONTENTS, so it does not change when settlement changes the data
        — a crawler would keep serving the PENDING image forever. The public
        page therefore versions the image URL itself with this value.

        Combines the immutable claim hash with an immutable settlement
        identity, so PENDING and every settled state have distinct cache
        identities, and a corrected settlement can never reuse an earlier one.

        The CLAIM hash itself is untouched — settlement stays out of it.
        """
        result = getattr(self, 'result', None)
        suffix = result.result_version if result is not None else 'pending'
        return f'{self.claim_hash[:16]}.{suffix}'


class PublishedClaimResult(models.Model):
    """Settlement of a published claim, recorded SEPARATELY from the claim.

    WHY A SEPARATE TABLE (rather than result fields on PublishedClaim)
    -----------------------------------------------------------------
    1. PublishedClaim stays strictly insert-only. Its `save()` can refuse EVERY
       update, so immutability is structural rather than a policy someone has to
       remember. With result columns on the claim, `save()` would need to permit
       some writes, and the invariant would rest on a field allowlist.
    2. The claim hash covers claim fields only. A separate table makes it
       impossible for settlement to enter the hashed payload by accident.
    3. Settlement has its own metadata — when it settled, which third-party
       source said so — that has no meaning at publication time.
    4. It models the domain honestly: what we claimed, and separately, what
       happened.

    Transitions are PENDING (no row) -> WON | LOST | VOID | CANCELLED. Recording
    a contradictory status is rejected, not silently applied.
    """
    claim = models.OneToOneField(
        PublishedClaim, on_delete=models.PROTECT, related_name='result',
        primary_key=True,
    )
    status = models.CharField(
        max_length=12,
        choices=[
            (PublishedClaim.STATUS_WON, 'Won'),
            (PublishedClaim.STATUS_LOST, 'Lost'),
            (PublishedClaim.STATUS_VOID, 'Void'),
            (PublishedClaim.STATUS_CANCELLED, 'Cancelled'),
        ],
    )
    actual_score_home = models.IntegerField(null=True, blank=True)
    actual_score_away = models.IntegerField(null=True, blank=True)
    settled_at = models.DateTimeField(default=timezone.now)
    # Which third party settled it, and the reference we can be checked against.
    result_source = models.CharField(max_length=64, default='sportmonks')
    result_reference = models.CharField(max_length=128, null=True, blank=True)

    class Meta:
        verbose_name = 'Published Claim Result'

    def __str__(self):
        return f'{self.claim_id} -> {self.status}'

    def save(self, *args, **kwargs):
        """Insert-only, exactly like the claim it settles."""
        if not self._state.adding:
            raise ValueError(
                'PublishedClaimResult is immutable — a recorded settlement can '
                'never be rewritten.'
            )
        super().save(*args, **kwargs)

    @property
    def result_version(self):
        """Stable identity for this settlement, from immutable settlement data.

        Used to version the public card's Open Graph image URL so a settled card
        can never reuse the PENDING image's cache identity.
        """
        from core.services.integrity import canonical_sha256, norm_dt

        return canonical_sha256({
            'status': self.status,
            'settled_at': norm_dt(self.settled_at),
            'actual_score_home': self.actual_score_home,
            'actual_score_away': self.actual_score_away,
        })[:16]


class PublicSelection(models.Model):
    """An append-only selection BetGlitch actually displayed to the public.

    Gems remain :class:`PublishedClaim` because they carry the stricter Gem
    qualification and independent anchoring lifecycle.  Homepage and strategy
    selections are a different promise: they are useful, clearly-labelled
    selections whose complete outcomes will be tracked.  Keeping them in their
    own immutable table prevents the broader record from weakening or
    masquerading as the Gem record.
    """

    CATEGORY_HOMEPAGE = 'homepage'
    CATEGORY_STRATEGY = 'strategy'
    CATEGORY_CHOICES = [
        (CATEGORY_HOMEPAGE, 'Homepage selection'),
        (CATEGORY_STRATEGY, 'Strategy selection'),
    ]

    REASON_VALUE = 'potential_value'
    REASON_STRONG = 'strong_signal'
    REASON_STRATEGY = 'strategy_match'
    REASON_CHOICES = [
        (REASON_VALUE, 'Potential value'),
        (REASON_STRONG, 'Strong model signal'),
        (REASON_STRATEGY, 'Strategy match'),
    ]

    selection_id = models.UUIDField(primary_key=True, editable=False)
    category = models.CharField(max_length=16, choices=CATEGORY_CHOICES,
                                db_index=True)
    source_key = models.CharField(max_length=80, db_index=True)
    source_version = models.CharField(max_length=128, blank=True, default='')
    source_ref = models.CharField(max_length=160, unique=True)
    reason_code = models.CharField(max_length=32, choices=REASON_CHOICES)

    # Optional immutable evidence row behind a strategy selection. Homepage
    # selections are frozen from the worker-produced decision-board snapshot.
    source_strategy_observation = models.ForeignKey(
        'StrategyLabObservation', null=True, blank=True,
        on_delete=models.PROTECT, related_name='public_selections',
    )

    fixture_id = models.IntegerField(db_index=True)
    home_team = models.CharField(max_length=100)
    away_team = models.CharField(max_length=100)
    league = models.CharField(max_length=100, blank=True, default='')
    league_id = models.IntegerField(null=True, blank=True)
    kickoff = models.DateTimeField(db_index=True)

    market_type = models.CharField(max_length=40)
    predicted_outcome = models.CharField(max_length=120)
    side = models.CharField(max_length=32, blank=True, default='')
    line = models.FloatField(null=True, blank=True)
    model_score = models.FloatField(null=True, blank=True)

    odds = models.FloatField()
    bookmaker = models.CharField(max_length=64, blank=True, default='')
    bookmaker_count = models.PositiveIntegerField(default=1)
    odds_captured_at = models.DateTimeField()
    published_at = models.DateTimeField(default=timezone.now, db_index=True)

    selection_hash = models.CharField(max_length=64, unique=True)
    selection_hash_version = models.CharField(max_length=8, default='v1')

    class Meta:
        ordering = ['-published_at']
        constraints = [
            models.UniqueConstraint(
                fields=['category', 'source_key', 'fixture_id'],
                name='uniq_public_selection_source_fixture',
            ),
        ]
        indexes = [
            models.Index(fields=['category', '-published_at']),
            models.Index(fields=['fixture_id', 'category']),
        ]

    SELECTION_HASH_VERSION = 'v1'

    def canonical_payload(self):
        from core.services.integrity import norm_dt, norm_num

        return {
            'selection_hash_version': self.SELECTION_HASH_VERSION,
            'category': self.category,
            'source_key': self.source_key,
            'source_version': self.source_version,
            'source_ref': self.source_ref,
            'reason_code': self.reason_code,
            'source_strategy_observation_id': (
                str(self.source_strategy_observation_id)
                if self.source_strategy_observation_id else None
            ),
            'fixture_id': self.fixture_id,
            'home_team': self.home_team,
            'away_team': self.away_team,
            'league': self.league,
            'league_id': self.league_id,
            'kickoff': norm_dt(self.kickoff),
            'market_type': self.market_type,
            'predicted_outcome': self.predicted_outcome,
            'side': self.side,
            'line': norm_num(self.line),
            'model_score': norm_num(self.model_score),
            'odds': norm_num(self.odds),
            'bookmaker': self.bookmaker,
            'bookmaker_count': self.bookmaker_count,
            'odds_captured_at': norm_dt(self.odds_captured_at),
            'published_at': norm_dt(self.published_at),
        }

    def compute_hash(self):
        from core.services.integrity import canonical_sha256

        return canonical_sha256(self.canonical_payload())

    def verify_integrity(self):
        return bool(self.selection_hash) and self.selection_hash == self.compute_hash()

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError(
                'PublicSelection is immutable — publish a new version rather '
                'than rewriting a displayed selection.'
            )
        if not self.selection_id:
            self.selection_id = uuid.uuid4()
        self.selection_hash_version = self.SELECTION_HASH_VERSION
        self.selection_hash = self.compute_hash()
        super().save(*args, **kwargs)

    @property
    def result_status(self):
        result = getattr(self, 'result', None)
        return result.status if result is not None else PublicSelectionResult.STATUS_PENDING

    def __str__(self):
        return (
            f'{self.category}: {self.home_team} v {self.away_team} — '
            f'{self.predicted_outcome} @ {self.odds}'
        )


class SelectionBoard(models.Model):
    """Atomic, append-only publication of the market boards and homepage."""
    version = models.CharField(max_length=64, db_index=True)
    generated_at = models.DateTimeField(default=timezone.now, db_index=True)
    payload = models.JSONField(default=dict)
    evidence_hash = models.CharField(max_length=64, unique=True)

    class Meta:
        ordering = ['-generated_at', '-pk']

    def save(self, *args, **kwargs):
        from core.services.integrity import canonical_sha256
        if not self._state.adding:
            raise ValueError('Selection boards are immutable')
        self.evidence_hash = canonical_sha256({
            'version': self.version, 'at': self.generated_at.isoformat(),
            'payload': self.payload,
        })
        super().save(*args, **kwargs)


class HomepageSelectionAppearance(models.Model):
    """Homepage membership, pointing to the same market selection receipt."""
    version = models.CharField(max_length=64)
    fixture_id = models.IntegerField()
    selection = models.ForeignKey(PublicSelection, on_delete=models.PROTECT)
    board = models.ForeignKey(SelectionBoard, on_delete=models.PROTECT)
    published_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=['version', 'fixture_id'], name='uniq_homepage_version_fixture',
        )]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError('Homepage membership is immutable')
        super().save(*args, **kwargs)


class PublicSelectionResult(models.Model):
    """Insert-only settlement for a displayed public selection."""

    STATUS_PENDING = 'PENDING'
    STATUS_WON = 'WON'
    STATUS_HALF_WON = 'HALF_WON'
    STATUS_PUSH = 'PUSH'
    STATUS_HALF_LOST = 'HALF_LOST'
    STATUS_LOST = 'LOST'
    STATUS_VOID = 'VOID'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_CHOICES = [
        (STATUS_WON, 'Won'),
        (STATUS_HALF_WON, 'Half won'),
        (STATUS_PUSH, 'Push'),
        (STATUS_HALF_LOST, 'Half lost'),
        (STATUS_LOST, 'Lost'),
        (STATUS_VOID, 'Void'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    selection = models.OneToOneField(
        PublicSelection, on_delete=models.PROTECT,
        related_name='result', primary_key=True,
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    unit_profit = models.FloatField()
    actual_score_home = models.IntegerField(null=True, blank=True)
    actual_score_away = models.IntegerField(null=True, blank=True)
    settled_at = models.DateTimeField(default=timezone.now)
    result_source = models.CharField(max_length=64, default='sportmonks')
    result_reference = models.CharField(max_length=160, blank=True, default='')

    class Meta:
        verbose_name = 'Public Selection Result'

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError(
                'PublicSelectionResult is insert-only — a corrected provider '
                'result must be recorded separately.'
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.selection_id} -> {self.status} ({self.unit_profit:+.3f}u)'


class PublicSelectionClosingPrice(models.Model):
    """Append-only closest verified pre-kickoff price for a public selection."""

    closing_price_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    selection = models.OneToOneField(
        PublicSelection, on_delete=models.PROTECT,
        related_name='closing_price',
    )
    odds = models.FloatField()
    bookmaker = models.CharField(max_length=64, blank=True, default='')
    bookmaker_count = models.PositiveIntegerField(default=1)
    odds_captured_at = models.DateTimeField()
    recorded_at = models.DateTimeField(default=timezone.now)
    source_ref = models.CharField(max_length=160)
    closing_line_value = models.FloatField(
        help_text='Published decimal odds / closing decimal odds - 1.',
    )
    evidence_hash = models.CharField(max_length=64, unique=True)

    class Meta:
        ordering = ['-recorded_at']

    def canonical_payload(self):
        from core.services.integrity import norm_dt, norm_num

        return {
            'selection_id': str(self.selection_id),
            'odds': norm_num(self.odds),
            'bookmaker': self.bookmaker,
            'bookmaker_count': self.bookmaker_count,
            'odds_captured_at': norm_dt(self.odds_captured_at),
            'recorded_at': norm_dt(self.recorded_at),
            'source_ref': self.source_ref,
            'closing_line_value': norm_num(self.closing_line_value),
        }

    def save(self, *args, **kwargs):
        from core.services.integrity import canonical_sha256

        if not self._state.adding:
            raise ValueError(
                'PublicSelectionClosingPrice is insert-only — closing '
                'evidence cannot be rewritten.'
            )
        self.evidence_hash = canonical_sha256(self.canonical_payload())
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f'{self.selection_id} close {self.odds:.2f} '
            f'({self.closing_line_value:+.3%})'
        )


class PerformanceSnapshot(models.Model):
    """
    Daily/weekly snapshots of overall performance metrics.
    Used for historical performance tracking and charts.
    """
    snapshot_date = models.DateField(unique=True, db_index=True)
    
    # Overall Metrics
    total_predictions = models.IntegerField(default=0)
    correct_predictions = models.IntegerField(default=0)
    accuracy_percent = models.FloatField(default=0.0)
    
    # By Outcome
    home_predictions = models.IntegerField(default=0)
    home_correct = models.IntegerField(default=0)
    home_accuracy = models.FloatField(default=0.0)
    
    draw_predictions = models.IntegerField(default=0)
    draw_correct = models.IntegerField(default=0)
    draw_accuracy = models.FloatField(default=0.0)
    
    away_predictions = models.IntegerField(default=0)
    away_correct = models.IntegerField(default=0)
    away_accuracy = models.FloatField(default=0.0)
    
    # Financial Metrics
    total_profit_loss = models.FloatField(default=0.0)
    roi_percent = models.FloatField(default=0.0)
    
    # By Confidence Level
    high_confidence_predictions = models.IntegerField(default=0)  # 70%+
    high_confidence_correct = models.IntegerField(default=0)
    high_confidence_accuracy = models.FloatField(default=0.0)
    
    medium_confidence_predictions = models.IntegerField(default=0)  # 60-70%
    medium_confidence_correct = models.IntegerField(default=0)
    medium_confidence_accuracy = models.FloatField(default=0.0)
    
    low_confidence_predictions = models.IntegerField(default=0)  # 55-60%
    low_confidence_correct = models.IntegerField(default=0)
    low_confidence_accuracy = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-snapshot_date']
        verbose_name = "Performance Snapshot"
        verbose_name_plural = "Performance Snapshots"
    
    def __str__(self):
        return f"Performance on {self.snapshot_date}: {self.accuracy_percent}% accuracy"


class UserBankroll(models.Model):
    """
    User's bankroll management settings and current state.
    Tracks total bankroll, limits, and risk preferences.
    """
    # User Identification - support both authenticated users and anonymous sessions
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='bankroll')
    session_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)  # For anonymous users
    user_email = models.EmailField(null=True, blank=True)  # Optional for registered users
    
    # Bankroll Settings
    initial_bankroll = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Starting bankroll amount"
    )
    current_bankroll = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Current available bankroll"
    )
    currency = models.CharField(max_length=3, default='USD')
    
    # Risk Management Settings
    daily_loss_limit = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Maximum loss allowed per day"
    )
    weekly_loss_limit = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Maximum loss allowed per week"
    )
    max_stake_percentage = models.FloatField(
        default=5.0,
        validators=[MinValueValidator(0.1), MaxValueValidator(25.0)],
        help_text="Maximum percentage of bankroll to stake on single bet"
    )
    
    # Staking Strategy
    #
    # Kelly (full and fractional) and confidence_scaled are GONE, and so is the
    # Kelly default. All three size a stake from an estimated edge over the
    # price, which requires a calibrated probability. BetGlitch's signal score
    # is not one: measured on 304 graded calls its AUC is 0.554, so a Kelly
    # fraction built on it is not a stake size — it is a number shaped like
    # one. Existing rows keep their stored value; nothing is rewritten.
    #
    # What remains are flat schemes that need no edge estimate at all, because
    # this is a JOURNAL of bets the user chose, not a staking engine.
    STAKING_STRATEGIES = [
        ('fixed_amount', 'Fixed Amount'),
        ('fixed_percentage', 'Fixed Percentage'),
    ]
    staking_strategy = models.CharField(
        max_length=20,
        choices=STAKING_STRATEGIES,
        default='fixed_amount'
    )
    fixed_stake_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="For fixed_amount strategy"
    )
    fixed_stake_percentage = models.FloatField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0.1), MaxValueValidator(10.0)],
        help_text="For fixed_percentage strategy"
    )
    
    # Risk Profile
    RISK_PROFILES = [
        ('conservative', 'Conservative'),
        ('balanced', 'Balanced'),
        ('aggressive', 'Aggressive'),
    ]
    risk_profile = models.CharField(
        max_length=20, 
        choices=RISK_PROFILES, 
        default='balanced'
    )
    
    # Limits Status
    is_daily_limit_reached = models.BooleanField(default=False)
    is_weekly_limit_reached = models.BooleanField(default=False)
    daily_loss_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    weekly_loss_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    last_daily_reset = models.DateField(default=timezone.now)
    last_weekly_reset = models.DateField(default=timezone.now)
    
    # Statistics
    total_bets_placed = models.IntegerField(default=0)
    total_wagered = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_profit_loss = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    roi_percent = models.FloatField(default=0.0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "User Bankroll"
        verbose_name_plural = "User Bankrolls"
        constraints = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False) | models.Q(session_id__isnull=False),
                name='user_or_session_required'
            )
        ]
    
    def __str__(self):
        if self.user:
            return f"Bankroll for {self.user.username} - {self.currency} {self.current_bankroll}"
        return f"Bankroll for {self.session_id[:8]}... - {self.currency} {self.current_bankroll}"
    
    def check_and_reset_limits(self):
        """Check if daily/weekly limits need to be reset."""
        today = timezone.now().date()
        
        # Reset daily limit if new day
        if self.last_daily_reset < today:
            self.daily_loss_amount = Decimal('0.00')
            self.is_daily_limit_reached = False
            self.last_daily_reset = today
        
        # Reset weekly limit if new week (Monday)
        days_since_monday = today.weekday()
        week_start = today - timezone.timedelta(days=days_since_monday)
        if self.last_weekly_reset < week_start:
            self.weekly_loss_amount = Decimal('0.00')
            self.is_weekly_limit_reached = False
            self.last_weekly_reset = week_start
        
        self.save()
    
    def can_place_bet(self, stake_amount):
        """Check if user can place a bet with given stake."""
        self.check_and_reset_limits()
        
        if stake_amount > self.current_bankroll:
            return False, "Insufficient bankroll"
        
        if self.is_daily_limit_reached:
            return False, "Daily loss limit reached"
        
        if self.is_weekly_limit_reached:
            return False, "Weekly loss limit reached"
        
        # Check if stake would exceed max stake percentage
        max_stake = (float(self.current_bankroll) * self.max_stake_percentage) / 100
        if stake_amount > max_stake:
            return False, f"Stake exceeds maximum ({self.max_stake_percentage}% of bankroll)"
        
        return True, "OK"
    
    def update_bankroll(self, profit_loss, stake_amount):
        """Update bankroll after bet settles."""
        self.current_bankroll += Decimal(str(profit_loss))
        self.total_profit_loss += Decimal(str(profit_loss))
        self.total_wagered += Decimal(str(stake_amount))
        
        # Update loss tracking
        if profit_loss < 0:
            self.daily_loss_amount += abs(Decimal(str(profit_loss)))
            self.weekly_loss_amount += abs(Decimal(str(profit_loss)))
            
            # Check if limits reached
            if self.daily_loss_limit and self.daily_loss_amount >= self.daily_loss_limit:
                self.is_daily_limit_reached = True
            
            if self.weekly_loss_limit and self.weekly_loss_amount >= self.weekly_loss_limit:
                self.is_weekly_limit_reached = True
        
        # Calculate ROI
        if self.total_wagered > 0:
            self.roi_percent = (float(self.total_profit_loss) / float(self.total_wagered)) * 100
        
        self.save()


class BankrollTransaction(models.Model):
    """
    Individual betting transactions linked to user's bankroll.
    Tracks stakes, outcomes, and P/L.
    """
    bankroll = models.ForeignKey(
        UserBankroll, 
        on_delete=models.CASCADE, 
        related_name='transactions'
    )
    prediction_log = models.ForeignKey(
        PredictionLog, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='bankroll_transactions'
    )
    
    # Transaction Details
    TRANSACTION_TYPES = [
        ('bet_placed', 'Bet Placed'),
        ('bet_won', 'Bet Won'),
        ('bet_lost', 'Bet Lost'),
        ('bet_void', 'Bet Void'),
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
    ]
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    
    # Bet Details (if applicable)
    fixture_id = models.IntegerField(null=True, blank=True, db_index=True)
    match_description = models.CharField(max_length=200, blank=True)
    selected_outcome = models.CharField(max_length=10, blank=True)  # 'Home', 'Draw', 'Away'
    odds = models.FloatField(null=True, blank=True)
    stake_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    potential_return = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    actual_return = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    profit_loss = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Bankroll State
    bankroll_before = models.DecimalField(max_digits=10, decimal_places=2)
    bankroll_after = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Staking Info
    recommended_stake = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="What SmartBet recommended"
    )
    staking_strategy_used = models.CharField(max_length=20, blank=True)
    
    # Status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('settled_won', 'Settled - Won'),
        ('settled_lost', 'Settled - Lost'),
        ('settled_void', 'Settled - Void'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    settled_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['bankroll', 'transaction_type']),
            models.Index(fields=['bankroll', 'status']),
            models.Index(fields=['fixture_id']),
        ]
        verbose_name = "Bankroll Transaction"
        verbose_name_plural = "Bankroll Transactions"
    
    def __str__(self):
        return f"{self.transaction_type} - {self.stake_amount} on {self.match_description}"
    
    def settle(self, won=True, void=False):
        """Settle a pending bet."""
        if self.status != 'pending':
            return
        
        if void:
            self.status = 'settled_void'
            self.actual_return = self.stake_amount
            self.profit_loss = Decimal('0.00')
            self.transaction_type = 'bet_void'
        elif won:
            self.status = 'settled_won'
            self.actual_return = Decimal(str(self.stake_amount)) * Decimal(str(self.odds))
            self.profit_loss = self.actual_return - Decimal(str(self.stake_amount))
            self.transaction_type = 'bet_won'
        else:
            self.status = 'settled_lost'
            self.actual_return = Decimal('0.00')
            self.profit_loss = -Decimal(str(self.stake_amount))
            self.transaction_type = 'bet_lost'
        
        self.settled_at = timezone.now()
        self.bankroll_after = self.bankroll_before + (self.profit_loss or Decimal('0.00'))
        
        # Update associated bankroll
        if self.profit_loss:
            self.bankroll.update_bankroll(
                profit_loss=float(self.profit_loss),
                stake_amount=float(self.stake_amount)
            )
        
        self.save()


class StakeRecommendation(models.Model):
    """
    Stake recommendations for predictions based on bankroll and strategy.
    Generated when user views a prediction.
    """
    bankroll = models.ForeignKey(
        UserBankroll, 
        on_delete=models.CASCADE, 
        related_name='stake_recommendations'
    )
    prediction_log = models.ForeignKey(
        PredictionLog, 
        on_delete=models.CASCADE, 
        related_name='stake_recommendations'
    )
    
    # Recommendation Details
    recommended_stake_amount = models.DecimalField(max_digits=10, decimal_places=2)
    recommended_stake_percentage = models.FloatField()
    strategy_used = models.CharField(max_length=20)
    
    # Kelly Criterion Specifics
    kelly_percentage = models.FloatField(null=True, blank=True)
    kelly_full_stake = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    kelly_fraction_used = models.FloatField(default=0.25)  # Default 1/4 Kelly
    
    # Risk Assessment
    RISK_LEVELS = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
    ]
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS)
    risk_explanation = models.TextField()
    
    # Warnings
    has_warnings = models.BooleanField(default=False)
    warnings = models.JSONField(default=list, blank=True)
    
    # Context at time of recommendation
    bankroll_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    max_stake_allowed = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Stake Recommendation"
        verbose_name_plural = "Stake Recommendations"
    
    def __str__(self):
        return f"Stake: {self.recommended_stake_amount} for {self.prediction_log}"


class EmailSubscriber(models.Model):
    """
    Stores email subscribers for newsletter/updates.
    Simple email capture for lead generation.
    """
    email = models.EmailField(unique=True, db_index=True)
    source = models.CharField(max_length=50, default='homepage')  # Where they signed up
    landing_page = models.CharField(max_length=255, blank=True, default='')
    utm_source = models.CharField(max_length=100, blank=True, default='')
    utm_medium = models.CharField(max_length=100, blank=True, default='')
    utm_campaign = models.CharField(max_length=150, blank=True, default='')
    language = models.CharField(max_length=10, blank=True, default='en')
    league_interest = models.CharField(max_length=100, blank=True, default='')
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # Can unsubscribe
    email_platform_status = models.CharField(max_length=30, blank=True, default='pending')
    last_synced_at = models.DateTimeField(null=True, blank=True)
    
    # Optional: Track what they're interested in
    interests = models.JSONField(default=list, blank=True)  # e.g., ['weekly_picks', 'premium_launch']
    
    class Meta:
        ordering = ['-subscribed_at']
        verbose_name = "Email Subscriber"
        verbose_name_plural = "Email Subscribers"
    
    def __str__(self):
        return f"{self.email} ({self.source})"


class MarketingEvent(models.Model):
    """
    Append-only marketing telemetry used for attribution and lifecycle automation.
    """
    EVENT_CHOICES = [
        ('email_subscribed', 'Email Subscribed'),
        ('welcome_sequence_started', 'Welcome Sequence Started'),
        ('weekly_picks_sent', 'Weekly Picks Sent'),
        ('email_clicked', 'Email Clicked'),
        ('pricing_viewed', 'Pricing Viewed'),
        ('paid_converted', 'Paid Converted'),
    ]

    subscriber = models.ForeignKey(
        EmailSubscriber,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='marketing_events'
    )
    event_name = models.CharField(max_length=50, choices=EVENT_CHOICES, db_index=True)
    source = models.CharField(max_length=50, blank=True, default='')
    page = models.CharField(max_length=255, blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_name', '-created_at']),
            models.Index(fields=['source', '-created_at']),
        ]
        verbose_name = "Marketing Event"
        verbose_name_plural = "Marketing Events"

    def __str__(self):
        return f"{self.event_name} @ {self.created_at:%Y-%m-%d %H:%M:%S}"


class ProductEvent(models.Model):
    """Privacy-minimal, append-only product telemetry.

    The browser creates a random identifier scoped to one tab session. The
    server immediately hashes it with ``SECRET_KEY`` and never stores the raw
    value. Properties are explicit columns rather than an arbitrary JSON blob,
    so new personal data cannot quietly enter the event stream.
    """

    EVENT_CHOICES = [
        ('page_viewed', 'Page Viewed'),
        ('page_dwell', 'Page Dwell'),
        ('home_primary_cta', 'Homepage Primary CTA'),
        ('home_verified_record_cta', 'Homepage Verified Record CTA'),
        ('explore_search', 'Explore Search'),
        ('fixture_opened', 'Fixture Opened'),
        ('research_shared', 'Research Shared'),
        ('published_proof_opened', 'Published Proof Opened'),
        ('registration_started', 'Registration Started'),
        ('registration_completed', 'Registration Completed'),
        ('first_login', 'First Login'),
        ('onboarding_action', 'Onboarding Action'),
        ('dashboard_visited', 'Dashboard Visited'),
        ('beta_page_viewed', 'Beta Page Viewed'),
    ]
    DURATION_BUCKET_CHOICES = [
        ('under_10s', 'Under 10 seconds'),
        ('10_to_30s', '10 to 30 seconds'),
        ('30_to_120s', '30 seconds to 2 minutes'),
        ('2_to_5m', '2 to 5 minutes'),
        ('over_5m', 'Over 5 minutes'),
    ]

    session_hash = models.CharField(max_length=64, db_index=True)
    event_name = models.CharField(max_length=50, choices=EVENT_CHOICES, db_index=True)
    surface = models.CharField(max_length=120, blank=True, default='', db_index=True)
    action = models.CharField(max_length=80, blank=True, default='')
    has_results = models.BooleanField(null=True, blank=True)
    duration_bucket = models.CharField(
        max_length=20,
        choices=DURATION_BUCKET_CHOICES,
        blank=True,
        default='',
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_name', '-created_at']),
            models.Index(fields=['session_hash', 'created_at']),
            models.Index(fields=['surface', '-created_at']),
        ]
        verbose_name = 'Product Event'
        verbose_name_plural = 'Product Events'

    def __str__(self):
        return f'{self.event_name} on {self.surface or "unknown"}'


class UserProfile(models.Model):
    """Per-user subscription + persistence data that doesn't belong on the auth User row.

    Auto-created via a post_save signal when a User is registered so we can read
    .profile.tier without null-checking on every request path.
    """

    TIER_FREE = 'free'
    TIER_PRO = 'pro'
    TIER_CHOICES = [
        (TIER_FREE, 'Free'),
        (TIER_PRO, 'Pro'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile'
    )
    tier = models.CharField(
        max_length=10,
        choices=TIER_CHOICES,
        default=TIER_FREE,
        db_index=True,
    )
    # Polar subscription id (preserved so we can correlate webhook events
    # to the user when a re-upgrade or cancellation comes in).
    polar_subscription_id = models.CharField(max_length=100, null=True, blank=True)
    tier_updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user.username} ({self.tier})"

    def set_tier(self, new_tier: str, polar_subscription_id: str = None):
        """Set tier + bookkeeping in one shot. Idempotent."""
        if new_tier not in dict(self.TIER_CHOICES):
            raise ValueError(f'Unknown tier: {new_tier!r}')
        self.tier = new_tier
        if polar_subscription_id:
            self.polar_subscription_id = polar_subscription_id
        self.tier_updated_at = timezone.now()
        self.save(update_fields=['tier', 'polar_subscription_id', 'tier_updated_at'])


@receiver(post_save, sender=User)
def _create_user_profile(sender, instance, created, **kwargs):
    """Make sure every User has a UserProfile (default tier='free')."""
    if created:
        UserProfile.objects.get_or_create(user=instance)


class SchedulerHeartbeat(models.Model):
    """
    Operational liveness record for the background scheduler worker.

    Exists because settlement is entirely scheduler-driven — there is no public
    route that can trigger it — so a silently dead worker would look identical
    to a healthy one with nothing to do: published claims would simply stay
    PENDING forever and no page would say why.

    Deliberately a single row, updated in place. This is an operational gauge,
    not an audit log; PredictionLog, PublishedClaim and PublishedClaimResult
    remain the records of what actually happened.

    Nothing here is public. Counts and failure codes are staff-only, and the
    full exception text is never stored — it goes to the logs against `run_id`.
    """
    SINGLETON_KEY = 'scheduler'

    STATUS_RUNNING = 'running'
    STATUS_SUCCESS = 'success'
    # The loop finished but at least one stage raised. Previously indistinguishable
    # from a clean run: run_task() swallows per-stage exceptions so settlement
    # survives a provider outage, which also meant a cycle where every stage
    # failed still reported 'success'.
    STATUS_DEGRADED = 'degraded'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_RUNNING, 'Running'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_DEGRADED, 'Degraded'),
        (STATUS_FAILED, 'Failed'),
    ]

    # Health as reported to staff. Derived, not stored — see `health()`.
    HEALTH_NEVER_RUN = 'never_run'
    HEALTH_HEALTHY = 'healthy'
    HEALTH_DEGRADED = 'degraded'
    HEALTH_DELAYED = 'delayed'
    HEALTH_FAILED = 'failed'

    key = models.CharField(max_length=32, unique=True, default=SINGLETON_KEY)

    last_run_started_at = models.DateTimeField(null=True, blank=True)
    last_run_completed_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_failure_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_RUNNING)
    last_duration_seconds = models.FloatField(null=True, blank=True)

    # Counts for the most recent completed run, measured as table deltas so they
    # stay correct regardless of how the individual commands report themselves.
    snapshots_created = models.IntegerField(default=0)
    results_updated = models.IntegerField(default=0)
    claims_settled = models.IntegerField(default=0)

    # Per-stage outcome for the most recent run: {stage_name: 'ok'|'failed'}.
    # Kept alongside the aggregate so a degraded run names its failure.
    stage_status = models.JSONField(null=True, blank=True)

    # Short, safe identifier — never an exception message.
    last_failure_code = models.CharField(max_length=64, blank=True, default='')
    # Correlates this record with the full traceback in the application logs.
    run_id = models.CharField(max_length=36, blank=True, default='')

    interval_minutes = models.IntegerField(default=60)
    version = models.CharField(max_length=64, blank=True, default='')

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Scheduler Heartbeat"
        verbose_name_plural = "Scheduler Heartbeat"

    def __str__(self):
        return f"{self.key}: {self.health()} (status={self.status})"

    def is_stale(self, now=None) -> bool:
        """
        True when the worker has not STARTED a run recently enough.

        Keyed off `last_run_started_at`, not completion: a run that begins and
        then hangs must eventually read as delayed rather than staying healthy
        on the strength of the previous success.

        The allowance is two intervals plus five minutes, so a single slow or
        skipped cycle does not raise a false alarm on an hourly cadence.
        """
        if self.last_run_started_at is None:
            return True
        now = now or timezone.now()
        interval = self.interval_minutes or 60
        allowance = timedelta(minutes=interval * 2 + 5)
        return (now - self.last_run_started_at) > allowance

    def health(self, now=None) -> str:
        if self.last_run_started_at is None:
            return self.HEALTH_NEVER_RUN
        if self.status == self.STATUS_FAILED:
            return self.HEALTH_FAILED
        if self.is_stale(now=now):
            return self.HEALTH_DELAYED
        # A cycle that ran on time but lost a stage is not healthy. Staleness
        # still wins: a degraded run an hour ago is a worse signal than the
        # stage failure itself.
        if self.status == self.STATUS_DEGRADED:
            return self.HEALTH_DEGRADED
        return self.HEALTH_HEALTHY


class IngestRequest(models.Model):
    """
    Replay ledger for signed server-to-server ingest requests.

    Distinguishes a legitimate retry from a malicious replay. Both arrive with
    the same `X-BetGlitch-Request-ID`; the difference is the body:

    * same request id + same body hash  -> legitimate retry. Idempotent: the
      stored result is returned and nothing is written a second time.
    * same request id + DIFFERENT body  -> rejected. Someone captured a valid
      signature envelope and is trying to reuse it for other content.

    Rows are cheap and small; prune anything older than the replay window plus
    a margin if the table ever needs it.
    """
    request_id = models.CharField(max_length=64, unique=True, db_index=True)
    body_sha256 = models.CharField(max_length=64)
    # The run id derived from this request, so a retry re-uses it and the
    # snapshot uniqueness key dedupes rather than appending a second run.
    prediction_run_id = models.CharField(max_length=64, db_index=True)
    response_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Ingest Request"
        verbose_name_plural = "Ingest Requests"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.request_id} @ {self.created_at:%Y-%m-%d %H:%M:%S}"


class GemFeedCache(models.Model):
    """The latest successfully completed Gem scan.

    Gem discovery is deliberately expensive: it reads every supported league,
    evaluates the available markets and then applies the versioned Gem gates.
    That work belongs in the hourly worker, not in a visitor's HTTP request.

    This singleton is an operational cache, not part of the immutable public
    record. A successful scan replaces it atomically; a failed scan leaves the
    previous value untouched. Empty successful scans are stored too, because
    "nothing qualified" is a real result rather than a cache miss.
    """

    CACHE_KEY = 'current'

    key = models.CharField(
        max_length=16,
        primary_key=True,
        default=CACHE_KEY,
        editable=False,
    )
    payload = models.JSONField(default=dict)
    generated_at = models.DateTimeField(db_index=True)
    refreshed_at = models.DateTimeField(auto_now=True)
    ranking_version = models.CharField(max_length=128, null=True, blank=True)
    recommendation_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Gem feed cache'

    def __str__(self):
        return (
            f'Gem feed ({self.recommendation_count} rows, '
            f'{self.generated_at:%Y-%m-%d %H:%M:%S})'
        )


class SignalObservation(models.Model):
    """An APPEND-ONLY record of one provider outcome, exactly as observed.

    WHY THIS EXISTS
    ---------------
    The 2026-08-04 calibration audit could not answer its own question. Three
    gaps caused that, and this model closes all three:

      1. Only the SELECTED side of a market was ever stored. A calibration set
         needs the losing side too — you cannot measure whether "Over 2.5 at
         0.62" is honest without the rows where Under was chosen.
      2. The raw provider probability was computed, sent over the wire and
         thrown away. Only `confidence` survived, which is
         `provider_probability * form_multiplier` capped at 0.95 — a heuristic
         blend, not a probability, and irreversible once stored.
      3. Only markets that won the ranking were persisted, so BTTS ended with
         14 settled rows and double chance with none. Selection bias by
         construction.

    Every supported fixture-market-outcome candidate is written here BEFORE any
    ranking, with the raw vector intact and the BetGlitch transformation stored
    separately alongside it. Nothing here is public and nothing here feeds the
    verified record; it is evidence for a model BetGlitch does not yet own.

    INSERT-ONLY. `save()` refuses updates for the same reason PublishedClaim
    does: an invariant enforced structurally cannot be forgotten later.
    """
    observation_id = models.UUIDField(primary_key=True, editable=False)

    # ── identity of the observation ──────────────────────────────────────────
    ingestion_run_id = models.CharField(max_length=64, db_index=True)
    # sha256 over the provider payload for this fixture-market-outcome. Two
    # replays of one payload produce one row, so a scheduler retry cannot
    # inflate the evidence count.
    source_payload_hash = models.CharField(max_length=64, unique=True)

    fixture_id = models.IntegerField(db_index=True)
    home_team = models.CharField(max_length=100)
    away_team = models.CharField(max_length=100)
    league = models.CharField(max_length=100, blank=True, default='')
    league_id = models.IntegerField(null=True, blank=True)
    kickoff = models.DateTimeField(db_index=True)

    observed_at = models.DateTimeField(db_index=True)
    hours_to_kickoff = models.FloatField(
        help_text='kickoff - observed_at, in hours. Negative means post-kickoff '
                  'and the row must be excluded from decision evaluation.',
    )

    # ── the market and the ONE outcome this row describes ────────────────────
    market = models.CharField(max_length=24, db_index=True)
    outcome = models.CharField(max_length=24)

    # ── raw provider values, never overwritten by anything BetGlitch computes ─
    provider = models.CharField(max_length=32, default='sportmonks')
    provider_type_id = models.IntegerField(null=True, blank=True)
    provider_model_version = models.CharField(max_length=64, blank=True, default='')
    provider_predicted_at = models.DateTimeField(null=True, blank=True)
    provider_context = models.JSONField(
        default=dict, blank=True,
        help_text='Pre-match provider quality context observed with the signal: '
                  'fixture predictability, league/market report card and native '
                  'value-bet payload. Stored raw so future strategies can be '
                  'evaluated without reconstructing data after kickoff.',
    )
    raw_probability = models.FloatField(
        help_text='Provider value for THIS outcome, exactly as supplied.',
    )
    normalized_probability = models.FloatField(
        help_text='raw/100 when the provider supplies percentages, else raw. '
                  'No BetGlitch heuristic is applied here.',
    )
    # The COMPLETE vector this outcome came from, outcome name -> normalized
    # value. Kept whole so a missing side can never be inferred as 1-p.
    raw_vector = models.JSONField()
    vector_sum = models.FloatField(
        help_text='Sum of the normalized vector. Stored rather than assumed: a '
                  'vector that does not sum to 1 must not be treated as a '
                  'probability distribution.',
    )
    vector_complete = models.BooleanField(
        default=False,
        help_text='True only when every outcome the market requires is present.',
    )

    # ── BetGlitch transformation, stored SEPARATELY from the raw values ──────
    is_selected_outcome = models.BooleanField(
        default=False, help_text='Did the live pipeline pick this side?',
    )
    probability_gap = models.FloatField(null=True, blank=True)
    form_multiplier = models.FloatField(null=True, blank=True)
    form_inputs = models.JSONField(
        null=True, blank=True,
        help_text='Everything that produced form_multiplier, so the heuristic '
                  'can be re-derived or reversed later.',
    )
    adjusted_score = models.FloatField(
        null=True, blank=True,
        help_text='min(normalized_probability * form_multiplier, cap). NOT a '
                  'calibrated probability — see the class docstring.',
    )
    cap_applied = models.BooleanField(default=False)
    market_score = models.FloatField(
        null=True, blank=True, help_text='Ranking score. Dimensionless.',
    )
    ranking_ev = models.FloatField(null=True, blank=True)
    is_best_market = models.BooleanField(default=False)
    selection_reason = models.CharField(max_length=120, blank=True, default='')
    variant_b_available = models.BooleanField(
        default=False,
        help_text='True only when the live heuristic actually produced an '
                  'adjusted score for this row. Missing Variant B is reported, '
                  'never inferred.',
    )
    variant_b_missing_reason = models.CharField(max_length=80, blank=True, default='')
    live_activation_state = models.CharField(
        max_length=16, blank=True, default='',
        help_text="'shadow' when the form heuristic was computed but NOT applied "
                  "to public output, 'live' when it was. Lets a row be read back "
                  "as which regime produced it without rewriting old evidence.",
    )
    pipeline_version = models.CharField(max_length=80, blank=True, default='')
    calculation_version = models.CharField(
        max_length=80, blank=True, default='',
        help_text='Frontend build/commit identifier for the code that produced '
                  'these numbers.',
    )

    # ── canonical price for THIS outcome ─────────────────────────────────────
    price_status = models.CharField(max_length=24, blank=True, default='')
    odds = models.FloatField(null=True, blank=True)
    bookmaker = models.CharField(max_length=64, blank=True, default='')
    odds_captured_at = models.DateTimeField(null=True, blank=True)
    odds_provenance = models.JSONField(null=True, blank=True)
    provenance_complete = models.BooleanField(default=False)
    market_price_vector = models.JSONField(
        null=True, blank=True,
        help_text='Every outcome price for this market, so a de-vigged '
                  'baseline can be computed. A baseline from the selected '
                  'outcome alone is not a baseline.',
    )
    price_vector_complete = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Signal Observation'
        ordering = ['-observed_at']
        indexes = [
            models.Index(fields=['fixture_id', 'market', 'outcome']),
            models.Index(fields=['-observed_at']),
            models.Index(fields=['kickoff']),
            models.Index(fields=['ingestion_run_id']),
        ]

    def __str__(self):
        return (f'{self.fixture_id} {self.market}/{self.outcome} '
                f'@{self.hours_to_kickoff:.1f}h')

    def save(self, *args, **kwargs):
        """Insert-only. A later probability or price appends a new row."""
        if not self._state.adding:
            raise ValueError(
                'SignalObservation is append-only — evidence is never revised. '
                'Record a new observation instead.'
            )
        super().save(*args, **kwargs)


class FixtureContextObservation(models.Model):
    """Append-only pre-match context for one fixture.

    SignalObservation preserves probabilities and prices. This companion model
    preserves the information that can explain why a view changed: lineup
    availability, formations, absences, form, venue and referee coverage.

    A row is written only when that canonical context changes. ``observed_at``
    is deliberately not part of the content hash, so an unchanged scheduler
    retry cannot manufacture activity in the public timeline.
    """

    LINEUP_CONFIRMED = 'confirmed'
    LINEUP_AVAILABLE = 'available_unconfirmed'
    LINEUP_UNAVAILABLE = 'unavailable'
    LINEUP_STATUS_CHOICES = [
        (LINEUP_CONFIRMED, 'Confirmed'),
        (LINEUP_AVAILABLE, 'Available, not confirmed'),
        (LINEUP_UNAVAILABLE, 'Unavailable'),
    ]

    observation_id = models.UUIDField(primary_key=True, editable=False)
    ingestion_run_id = models.CharField(max_length=64, db_index=True)
    source_payload_hash = models.CharField(max_length=64, unique=True)

    fixture_id = models.IntegerField(db_index=True)
    home_team = models.CharField(max_length=100)
    away_team = models.CharField(max_length=100)
    league = models.CharField(max_length=100, blank=True, default='')
    league_id = models.IntegerField(null=True, blank=True)
    kickoff = models.DateTimeField(db_index=True)
    observed_at = models.DateTimeField(db_index=True)
    hours_to_kickoff = models.FloatField()

    fixture_predictable = models.BooleanField(null=True, blank=True)
    lineup_status = models.CharField(
        max_length=24,
        choices=LINEUP_STATUS_CHOICES,
        default=LINEUP_UNAVAILABLE,
    )
    home_formation = models.CharField(max_length=32, blank=True, default='')
    away_formation = models.CharField(max_length=32, blank=True, default='')
    home_form = models.CharField(max_length=20, blank=True, default='')
    away_form = models.CharField(max_length=20, blank=True, default='')
    home_sidelined_count = models.PositiveSmallIntegerField(default=0)
    away_sidelined_count = models.PositiveSmallIntegerField(default=0)

    # Raw-but-compact provider facts. They remain separate so future feature
    # work does not have to reconstruct a historical payload after kickoff.
    sidelined = models.JSONField(default=list, blank=True)
    lineups = models.JSONField(default=list, blank=True)
    referees = models.JSONField(default=list, blank=True)
    venue = models.JSONField(null=True, blank=True)
    neutral_venue = models.BooleanField(null=True, blank=True)
    data_availability = models.JSONField(default=dict, blank=True)

    provider = models.CharField(max_length=32, default='sportmonks')
    calculation_version = models.CharField(max_length=80, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Fixture Context Observation'
        ordering = ['-observed_at']
        indexes = [
            models.Index(fields=['fixture_id', 'observed_at']),
            models.Index(fields=['kickoff']),
            models.Index(fields=['ingestion_run_id']),
        ]

    def __str__(self):
        return f'{self.fixture_id} context @ {self.hours_to_kickoff:.1f}h'

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError(
                'FixtureContextObservation is append-only — record a new '
                'observation instead of changing history.'
            )
        super().save(*args, **kwargs)


class FixtureResultObservation(models.Model):
    """An APPEND-ONLY provider result for one fixture, at one point in time.

    WHY THIS IS SEPARATE FROM SignalObservation
    -------------------------------------------
    A fixture has ~10 signal observations per sweep and many sweeps. Copying the
    result onto each of them would store one fact hundreds of times and make a
    provider correction a mass-update — the exact mutation pattern the evidence
    layer exists to avoid. One row per fixture per RESULT VERSION instead.

    WHY VERSIONS RATHER THAN UPDATES
    --------------------------------
    Providers do correct scores. Overwriting would erase the fact that we once
    believed something else, which is the part an audit actually needs. A
    correction appends `result_version + 1` pointing at the row it supersedes;
    the earlier belief stays readable forever.

    Evidence evaluation is NOT bet settlement. This model never decides whether
    a published claim won — `settle_published_claims` owns that, under its own
    void/cancel rules. This is only "what did the provider say the score was".
    """
    # Ordinary football markets settle on the 90-minute result. Extra time and
    # penalties are recorded but deliberately not scored: the provider's headline
    # score for those fixtures is not the number these markets settle on.
    STATUS_ELIGIBLE_FINAL = {'FT'}
    STATUS_EXTRA_TIME = {'AET', 'FT_PEN', 'PEN_BREAK', 'EXTRA_TIME'}
    STATUS_IN_PLAY = {
        'INPLAY_1ST_HALF', 'INPLAY_2ND_HALF', 'HT', 'BREAK', 'INPLAY_ET',
        'INPLAY_PENALTIES', 'PEN_LIVE',
    }
    STATUS_NOT_STARTED = {'NS', 'TBA', 'DELAYED'}
    STATUS_VOIDLIKE = {'POSTP', 'CANCL', 'SUSP', 'ABAN', 'AWARDED', 'WO', 'DELETED'}

    result_id = models.UUIDField(primary_key=True, editable=False)

    fixture_id = models.IntegerField(db_index=True)
    home_team = models.CharField(max_length=100, blank=True, default='')
    away_team = models.CharField(max_length=100, blank=True, default='')
    league = models.CharField(max_length=100, blank=True, default='')
    league_id = models.IntegerField(null=True, blank=True)
    kickoff = models.DateTimeField(db_index=True)

    # ── what the provider said ───────────────────────────────────────────────
    provider = models.CharField(max_length=32, default='sportmonks')
    provider_status = models.CharField(
        max_length=32, db_index=True,
        help_text='Raw provider state string, stored verbatim.',
    )
    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)
    score_type = models.CharField(
        max_length=24, blank=True, default='',
        help_text="Which score this is, e.g. 'CURRENT' / '2ND_HALF' / 'FT'.",
    )
    provider_result_at = models.DateTimeField(null=True, blank=True)
    raw_scores = models.JSONField(
        null=True, blank=True,
        help_text='Every score entry the provider returned, so the chosen one '
                  'can be re-derived rather than trusted.',
    )

    # ── our classification of that ───────────────────────────────────────────
    is_final = models.BooleanField(
        default=False,
        help_text='Provider status is an eligible final state AND both scores '
                  'are present. Only these may be scored.',
    )
    is_scoreable = models.BooleanField(
        default=False,
        help_text='is_final AND the status permits deriving ordinary market '
                  'outcomes. Extra-time and void-like states are never '
                  'scoreable even when a score exists.',
    )
    ineligible_reason = models.CharField(max_length=64, blank=True, default='')
    confirmed = models.BooleanField(
        default=False,
        help_text='A later independent observation returned the same final '
                  'score. Unconfirmed finals are provisional.',
    )

    # ── versioning ───────────────────────────────────────────────────────────
    result_version = models.PositiveIntegerField(default=1)
    supersedes = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.PROTECT,
        related_name='superseded_by',
    )
    is_correction = models.BooleanField(default=False)

    captured_at = models.DateTimeField(db_index=True)
    ingestion_run_id = models.CharField(max_length=64, db_index=True)
    source_payload_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Fixture Result Observation'
        ordering = ['-captured_at']
        indexes = [
            models.Index(fields=['fixture_id', '-result_version']),
            models.Index(fields=['-captured_at']),
            models.Index(fields=['is_scoreable']),
        ]

    def __str__(self):
        score = (f'{self.home_score}-{self.away_score}'
                 if self.home_score is not None else 'no score')
        return f'{self.fixture_id} v{self.result_version} {self.provider_status} {score}'

    def save(self, *args, **kwargs):
        """Insert-only. A provider correction appends a new version."""
        if not self._state.adding:
            raise ValueError(
                'FixtureResultObservation is append-only — a corrected score '
                'is a new result_version, never an edit.'
            )
        super().save(*args, **kwargs)


class StrategyLabExperiment(models.Model):
    """One versioned, forward-only strategy tested outside public picks.

    Rules and their hash identify the experiment. A materially changed rule is
    a new version, so results from different methods are never blended.
    """
    STATUS_SHADOW = 'shadow'
    STATUS_CANDIDATE = 'candidate'
    STATUS_VALIDATED = 'validated'
    STATUS_RETIRED = 'retired'
    STATUS_CHOICES = [
        (STATUS_SHADOW, 'Shadow'),
        (STATUS_CANDIDATE, 'Candidate'),
        (STATUS_VALIDATED, 'Validated'),
        (STATUS_RETIRED, 'Retired'),
    ]

    experiment_id = models.UUIDField(primary_key=True, default=uuid.uuid4,
                                     editable=False)
    strategy_key = models.CharField(max_length=80)
    version = models.CharField(max_length=24)
    name = models.CharField(max_length=120)
    market = models.CharField(max_length=40)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES,
                              default=STATUS_SHADOW, db_index=True)
    decision_horizon_hours = models.FloatField(default=1.0)
    rules = models.JSONField(default=dict)
    rules_hash = models.CharField(max_length=64, unique=True)
    minimum_settled_for_review = models.PositiveIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['strategy_key', 'version'],
                name='uniq_strategy_lab_key_version',
            ),
        ]
        ordering = ['strategy_key', 'version']

    def __str__(self):
        return f'{self.name} {self.version} ({self.status})'

    def save(self, *args, **kwargs):
        if not self._state.adding:
            original = type(self).objects.filter(pk=self.pk).values(
                'strategy_key', 'version', 'name', 'market', 'rules_hash',
                'rules', 'decision_horizon_hours',
                'minimum_settled_for_review',
            ).first()
            if original and any(
                original[field] != getattr(self, field)
                for field in original
            ):
                raise ValueError(
                    'Strategy rules are immutable - create a new experiment '
                    'version instead of rewriting its evidence.'
                )
        super().save(*args, **kwargs)


class StrategyLabObservation(models.Model):
    """Append-only candidate generated by a versioned shadow strategy."""
    PHASE_RETROSPECTIVE = 'retrospective'
    PHASE_FORWARD = 'forward'
    PHASE_CHOICES = [
        (PHASE_RETROSPECTIVE, 'Retrospective backtest'),
        (PHASE_FORWARD, 'Forward validation'),
    ]

    observation_id = models.UUIDField(primary_key=True, default=uuid.uuid4,
                                      editable=False)
    experiment = models.ForeignKey(
        StrategyLabExperiment, on_delete=models.PROTECT,
        related_name='observations',
    )
    source_signal = models.ForeignKey(
        SignalObservation, null=True, blank=True, on_delete=models.PROTECT,
        related_name='strategy_lab_observations',
        help_text='Exact immutable signal row that produced this candidate. '
                  'Null only for specialist candidates such as Asian Handicap.',
    )
    evidence_phase = models.CharField(
        max_length=16, choices=PHASE_CHOICES, default=PHASE_FORWARD,
        db_index=True,
        help_text='Retrospective rows may reject a strategy but can never make '
                  'it eligible for public promotion.',
    )
    ingestion_run_id = models.CharField(max_length=64, db_index=True)
    source_payload_hash = models.CharField(max_length=64, unique=True)

    fixture_id = models.IntegerField(db_index=True)
    home_team = models.CharField(max_length=100)
    away_team = models.CharField(max_length=100)
    league = models.CharField(max_length=100, blank=True, default='')
    league_id = models.IntegerField(null=True, blank=True)
    kickoff = models.DateTimeField(db_index=True)
    observed_at = models.DateTimeField(db_index=True)
    hours_to_kickoff = models.FloatField()

    market = models.CharField(max_length=40)
    market_id = models.IntegerField(null=True, blank=True)
    side = models.CharField(max_length=32)
    handicap = models.FloatField(null=True, blank=True)
    label = models.CharField(max_length=120)
    selection_payload = models.JSONField(
        default=dict, blank=True,
        help_text='Market-specific inputs needed to reproduce selection and settlement.',
    )

    odds = models.FloatField()
    bookmaker = models.CharField(max_length=64)
    bookmaker_count = models.PositiveIntegerField(default=1)
    price_min = models.FloatField()
    price_max = models.FloatField()
    odds_captured_at = models.DateTimeField()
    price_provenance = models.JSONField(default=dict)

    model_mass = models.FloatField()
    expected_return_lower = models.FloatField()
    expected_return_upper = models.FloatField()
    robust_positive_edge = models.BooleanField(default=False, db_index=True)
    calculation_version = models.CharField(max_length=80, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-observed_at']
        indexes = [
            models.Index(fields=['experiment', 'fixture_id', 'side', 'handicap']),
            models.Index(fields=['kickoff', 'robust_positive_edge']),
        ]

    def __str__(self):
        return f'{self.fixture_id} {self.label} @ {self.odds}'

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError(
                'StrategyLabObservation is append-only - record a new '
                'observation instead.'
            )
        super().save(*args, **kwargs)


class StrategyLabSettlement(models.Model):
    """Append-only grading of one chosen lab observation against one result version."""
    OUTCOME_FULL_WIN = 'full_win'
    OUTCOME_HALF_WIN = 'half_win'
    OUTCOME_PUSH = 'push'
    OUTCOME_HALF_LOSS = 'half_loss'
    OUTCOME_FULL_LOSS = 'full_loss'
    OUTCOME_CHOICES = [
        (OUTCOME_FULL_WIN, 'Full win'),
        (OUTCOME_HALF_WIN, 'Half win'),
        (OUTCOME_PUSH, 'Push'),
        (OUTCOME_HALF_LOSS, 'Half loss'),
        (OUTCOME_FULL_LOSS, 'Full loss'),
    ]

    settlement_id = models.UUIDField(primary_key=True, default=uuid.uuid4,
                                     editable=False)
    observation = models.ForeignKey(
        StrategyLabObservation, on_delete=models.PROTECT,
        related_name='settlements',
    )
    result = models.ForeignKey(
        FixtureResultObservation, on_delete=models.PROTECT,
        related_name='strategy_lab_settlements',
    )
    result_version = models.PositiveIntegerField()
    home_score = models.IntegerField()
    away_score = models.IntegerField()
    outcome = models.CharField(max_length=16, choices=OUTCOME_CHOICES)
    unit_profit = models.FloatField()
    settlement_hash = models.CharField(max_length=64, unique=True)
    settled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-settled_at']
        constraints = [
            models.UniqueConstraint(
                fields=['observation', 'result'],
                name='uniq_strategy_lab_observation_result',
            ),
        ]
        indexes = [
            models.Index(fields=['outcome']),
            models.Index(fields=['result_version']),
        ]

    def __str__(self):
        return f'{self.observation} -> {self.outcome} ({self.unit_profit:+.3f})'

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError(
                'StrategyLabSettlement is append-only - a corrected provider '
                'result creates a new settlement.'
            )
        super().save(*args, **kwargs)


class ClaimAnchor(models.Model):
    """A digest of published claims, timestamped by parties who are not us.

    BetGlitch's own claim hash proves tamper-evidence: change a field and the
    hash stops matching. It cannot prove WHEN the record existed, because we
    serve both the record and the hash. A public reviewer named that gap on
    2026-08-08, and this model closes it.

    The digest is submitted to independent OpenTimestamps calendars, which
    aggregate it into the Bitcoin chain. The resulting proof lets anyone
    demonstrate the digest existed before a given block — no BetGlitch
    cooperation required, and no account, key or vendor relationship needed to
    create or to check it.

    Anchoring happens AT PUBLICATION, never overnight: a timestamp taken after
    kickoff would prove nothing about foresight.
    """
    STATUS_PENDING = 'PENDING'
    STATUS_CONFIRMED = 'CONFIRMED'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Submitted to calendars, awaiting Bitcoin block'),
        (STATUS_CONFIRMED, 'Attested in a Bitcoin block'),
    ]

    anchor_id = models.UUIDField(primary_key=True, default=uuid.uuid4,
                                 editable=False)

    # SHA-256 over `manifest`. Unique: the same set of claims always produces
    # the same digest, so a retried run links rather than double-stamps.
    digest = models.CharField(max_length=64, unique=True, db_index=True)

    # The exact bytes the digest was taken over, kept public so a third party
    # can rebuild it from /api/proof/claims/ and compare.
    manifest = models.TextField()
    manifest_version = models.CharField(max_length=64)

    claim_count = models.IntegerField()
    calendars = models.JSONField(default=list)

    # The serialized .ots proof. Grows an attestation when upgraded.
    ots_proof = models.BinaryField(null=True, blank=True)

    status = models.CharField(max_length=16, choices=STATUS_CHOICES,
                              default=STATUS_PENDING, db_index=True)
    bitcoin_block_height = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(db_index=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.digest[:12]} ({self.claim_count} claims, {self.status})'


class ClaimAnchorEntry(models.Model):
    """Join row: which claims a given anchor covers.

    A separate table rather than a field on PublishedClaim, because a published
    claim is insert-only — writing an anchor reference onto it after the fact
    would trip its own immutability guard, and rightly so.
    """
    anchor = models.ForeignKey(ClaimAnchor, on_delete=models.CASCADE,
                               related_name='entries')
    claim = models.ForeignKey('PublishedClaim', on_delete=models.CASCADE,
                              related_name='anchor_entries')
    # The hash AS ANCHORED. If the live claim ever stopped matching this, the
    # anchored proof is the evidence of it.
    claim_hash = models.CharField(max_length=64)

    class Meta:
        unique_together = [('anchor', 'claim')]
        indexes = [models.Index(fields=['claim'])]

    def __str__(self):
        return f'{self.claim_id} in {self.anchor_id}'
