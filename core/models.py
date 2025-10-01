"""
Core models for the SmartBet application.
"""

from django.db import models
from django.utils import timezone


class League(models.Model):
    """Football league/competition."""
    name_ro = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    api_id = models.IntegerField(null=True, blank=True)
    slug = models.SlugField(max_length=100, null=True, blank=True)
    
    def __str__(self):
        return self.name_en


class Team(models.Model):
    """Football team."""
    name_ro = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    logo_url = models.URLField(null=True, blank=True)
    api_id = models.CharField(max_length=50, null=True, blank=True)
    
    def __str__(self):
        return self.name_en


class Match(models.Model):
    """Football match."""
    MATCH_STATUS_CHOICES = [
        ('NS', 'Not Started'),
        ('1H', 'First Half'),
        ('HT', 'Half Time'),
        ('2H', 'Second Half'),
        ('FT', 'Full Time'),
        ('AET', 'After Extra Time'),
        ('PEN', 'Penalties'),
        ('PST', 'Postponed'),
        ('CANC', 'Cancelled'),
        ('ABD', 'Abandoned'),
        ('TBA', 'To Be Announced'),
        ('WO', 'Walkover'),
        ('LIVE', 'Live'),
        ('ET', 'Extra Time'),
        ('BT', 'Break Time'),
        ('APEN', 'After Penalties'),
        ('SUSP', 'Suspended'),
        ('INT', 'Interrupted'),
        ('POSTP', 'Postponed'),
        ('AWARDED', 'Awarded'),
    ]
    
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='matches')
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')
    kickoff = models.DateTimeField()
    status = models.CharField(max_length=10, choices=MATCH_STATUS_CHOICES, default='NS')
    api_ref = models.CharField(max_length=50, null=True, blank=True)
    
    # Results
    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)
    
    # Additional data from SportMonks
    venue = models.CharField(max_length=255, null=True, blank=True)
    
    # Team statistics (new fields)
    avg_goals_home = models.FloatField(null=True, blank=True)
    avg_goals_away = models.FloatField(null=True, blank=True)
    avg_cards_home = models.FloatField(null=True, blank=True)
    avg_cards_away = models.FloatField(null=True, blank=True)
    team_form_home = models.FloatField(null=True, blank=True)
    team_form_away = models.FloatField(null=True, blank=True)
    injured_starters_home = models.IntegerField(null=True, blank=True)
    injured_starters_away = models.IntegerField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Matches"
        ordering = ['-kickoff']
        indexes = [
            models.Index(fields=['kickoff']),
            models.Index(fields=['status']),
            models.Index(fields=['api_ref']),
        ]
    
    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"
        
    @property
    def is_live(self):
        """Check if the match is currently live."""
        return self.status in ['1H', '2H', 'HT', 'ET', 'BT', 'PEN', 'LIVE']


class OddsSnapshot(models.Model):
    """Snapshot of betting odds for a match."""
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='odds_snapshots')
    bookmaker = models.CharField(max_length=50)
    
    # Current odds
    odds_home = models.FloatField()
    odds_draw = models.FloatField()
    odds_away = models.FloatField()
    
    # Opening and closing odds (for historical data)
    opening_odds_home = models.FloatField(null=True, blank=True)
    opening_odds_draw = models.FloatField(null=True, blank=True)
    opening_odds_away = models.FloatField(null=True, blank=True)
    
    closing_odds_home = models.FloatField(null=True, blank=True)
    closing_odds_draw = models.FloatField(null=True, blank=True)
    closing_odds_away = models.FloatField(null=True, blank=True)
    
    fetched_at = models.DateTimeField()
    
    def __str__(self):
        return f"{self.match} - {self.bookmaker} odds"


class MatchScoreModel(models.Model):
    """Stored match score predictions."""
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='match_scores')
    fixture_id = models.CharField(max_length=50)
    home_team_score = models.FloatField()
    away_team_score = models.FloatField()
    confidence_level = models.CharField(max_length=20)
    predicted_outcome = models.CharField(max_length=10)
    recommended_bet = models.CharField(max_length=100)
    source = models.CharField(max_length=50)
    generated_at = models.DateTimeField()
    expected_value = models.FloatField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Match Score"
        verbose_name_plural = "Match Scores"
        
    def __str__(self):
        return f"{self.match} - {self.predicted_outcome} ({self.confidence_level})"


class MatchMetadata(models.Model):
    """
    Additional metadata for matches from external APIs.
    Stores JSON data like lineups, events, statistics, injuries, etc.
    """
    match = models.OneToOneField(Match, on_delete=models.CASCADE, related_name='metadata')
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Match Metadata"
        verbose_name_plural = "Match Metadata"
        
    def __str__(self):
        return f"Metadata for {self.match}"
