"""
Core models for SmartBet - Prediction Tracking Only
"""

from django.db import models
from django.utils import timezone
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
        ]
        verbose_name = "Prediction Log"
        verbose_name_plural = "Prediction Logs"
    
    def __str__(self):
        return f"{self.home_team} vs {self.away_team} - Predicted: {self.predicted_outcome} ({self.confidence}%)"
    
    def calculate_performance(self):
        """Calculate performance metrics after match completes."""
        if self.actual_outcome and self.predicted_outcome:
            self.was_correct = (self.predicted_outcome == self.actual_outcome)
            
            # Calculate P/L for $10 stake on predicted outcome
            if self.was_correct:
                if self.predicted_outcome == 'Home' and self.odds_home:
                    self.profit_loss_10 = 10 * (self.odds_home - 1)
                elif self.predicted_outcome == 'Draw' and self.odds_draw:
                    self.profit_loss_10 = 10 * (self.odds_draw - 1)
                elif self.predicted_outcome == 'Away' and self.odds_away:
                    self.profit_loss_10 = 10 * (self.odds_away - 1)
            else:
                self.profit_loss_10 = -10
            
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


