"""
Core models for SmartBet - Prediction Tracking & Bankroll Management
"""

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
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
    STAKING_STRATEGIES = [
        ('kelly', 'Kelly Criterion'),
        ('kelly_fractional', 'Fractional Kelly (1/4)'),
        ('fixed_percentage', 'Fixed Percentage'),
        ('fixed_amount', 'Fixed Amount'),
        ('confidence_scaled', 'Confidence Scaled'),
    ]
    staking_strategy = models.CharField(
        max_length=20, 
        choices=STAKING_STRATEGIES, 
        default='kelly_fractional'
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
