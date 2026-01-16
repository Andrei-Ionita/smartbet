"""
Core models for SmartBet - Prediction Tracking & Bankroll Management
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
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
    
    def calculate_performance(self):
        """
        Calculate performance metrics after match completes.
        Supports multi-market verification: 1X2, BTTS, O/U 2.5, Double Chance
        """
        if self.actual_outcome is None and self.actual_score_home is None:
            return  # No result data yet
            
        if not self.predicted_outcome:
            return  # No prediction to verify
        
        # Get market type (default to 1x2 for legacy predictions)
        market_type = getattr(self, 'market_type', '1x2') or '1x2'
        predicted = self.predicted_outcome.lower().strip()
        
        # Get scores for goal-based markets
        home_score = self.actual_score_home
        away_score = self.actual_score_away
        total_goals = (home_score or 0) + (away_score or 0)
        
        # Determine 1X2 actual outcome for reference
        if home_score is not None and away_score is not None:
            if home_score > away_score:
                actual_1x2 = 'home'
            elif away_score > home_score:
                actual_1x2 = 'away'
            else:
                actual_1x2 = 'draw'
        else:
            actual_1x2 = (self.actual_outcome or '').lower()
        
        # ============= VERIFY BY MARKET TYPE =============
        if market_type == '1x2':
            # Standard 1X2 verification
            self.was_correct = (predicted == actual_1x2)
            
        elif market_type == 'btts':
            # Both Teams to Score
            if home_score is not None and away_score is not None:
                both_scored = (home_score > 0) and (away_score > 0)
                predicted_btts_yes = 'yes' in predicted or 'btts yes' in predicted
                self.was_correct = (predicted_btts_yes == both_scored)
            else:
                self.was_correct = None  # Cannot verify without scores
                
        elif market_type == 'over_under_2.5':
            # Over/Under 2.5 Goals
            if home_score is not None and away_score is not None:
                is_over = total_goals > 2.5
                predicted_over = 'over' in predicted
                self.was_correct = (predicted_over == is_over)
            else:
                self.was_correct = None
                
        elif market_type == 'double_chance':
            # Double Chance: 1X (Home or Draw), X2 (Draw or Away), 12 (Home or Away)
            if actual_1x2:
                if '1x' in predicted or 'home' in predicted and 'draw' in predicted:
                    # Home or Draw
                    self.was_correct = actual_1x2 in ['home', 'draw']
                elif 'x2' in predicted or 'draw' in predicted and 'away' in predicted:
                    # Draw or Away
                    self.was_correct = actual_1x2 in ['draw', 'away']
                elif '12' in predicted:
                    # Home or Away (no draw)
                    self.was_correct = actual_1x2 in ['home', 'away']
                else:
                    self.was_correct = None
            else:
                self.was_correct = None
        else:
            # Unknown market type, fall back to 1X2 logic
            self.was_correct = (predicted == actual_1x2)
        
        # ============= CALCULATE PROFIT/LOSS =============
        # For multi-market, we use the stored odds from best_market
        market_odds = getattr(self, 'odds_home', None)  # Default to home odds
        
        # Try to get the correct odds based on prediction
        if market_type == '1x2':
            if predicted == 'home' and self.odds_home:
                market_odds = self.odds_home
            elif predicted == 'draw' and self.odds_draw:
                market_odds = self.odds_draw
            elif predicted == 'away' and self.odds_away:
                market_odds = self.odds_away
        # For other markets, odds would be stored in a dedicated field (future enhancement)
        # For now, use expected_value to back-calculate approximate odds
        elif self.expected_value and self.confidence:
            # EV = (prob * odds) - 1, so odds = (EV + 1) / prob
            if self.confidence > 0:
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


