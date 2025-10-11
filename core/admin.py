from django.contrib import admin
from .models import PredictionLog, PerformanceSnapshot, MatchSentiment


@admin.register(PredictionLog)
class PredictionLogAdmin(admin.ModelAdmin):
    list_display = ('fixture_id', 'home_team', 'away_team', 'league', 'kickoff', 
                    'predicted_outcome', 'confidence', 'actual_outcome', 'was_correct', 
                    'prediction_logged_at')
    list_filter = ('predicted_outcome', 'actual_outcome', 'was_correct', 'league', 
                   'kickoff', 'ensemble_strategy')
    search_fields = ('home_team', 'away_team', 'league', 'fixture_id')
    readonly_fields = ('prediction_logged_at', 'result_logged_at', 'was_correct', 
                       'profit_loss_10', 'roi_percent')
    date_hierarchy = 'kickoff'
    
    fieldsets = (
        ('Match Information', {
            'fields': ('fixture_id', 'home_team', 'away_team', 'league', 'league_id', 'kickoff')
        }),
        ('Prediction (Logged Before Match)', {
            'fields': ('predicted_outcome', 'confidence', 'probability_home', 
                      'probability_draw', 'probability_away', 'prediction_logged_at')
        }),
        ('Betting Information', {
            'fields': ('odds_home', 'odds_draw', 'odds_away', 'bookmaker', 'expected_value')
        }),
        ('Ensemble Details', {
            'fields': ('model_count', 'consensus', 'variance', 'ensemble_strategy')
        }),
        ('Actual Result (After Match)', {
            'fields': ('actual_outcome', 'actual_score_home', 'actual_score_away', 
                      'match_status', 'result_logged_at')
        }),
        ('Performance Metrics', {
            'fields': ('was_correct', 'profit_loss_10', 'roi_percent')
        }),
        ('Additional Info', {
            'fields': ('recommendation_score', 'notes')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related()


@admin.register(PerformanceSnapshot)
class PerformanceSnapshotAdmin(admin.ModelAdmin):
    list_display = ('snapshot_date', 'total_predictions', 'correct_predictions', 
                    'accuracy_percent', 'roi_percent', 'total_profit_loss')
    list_filter = ('snapshot_date',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'snapshot_date'
    
    fieldsets = (
        ('Date', {
            'fields': ('snapshot_date',)
        }),
        ('Overall Performance', {
            'fields': ('total_predictions', 'correct_predictions', 'accuracy_percent', 
                      'total_profit_loss', 'roi_percent')
        }),
        ('By Outcome', {
            'fields': (
                ('home_predictions', 'home_correct', 'home_accuracy'),
                ('draw_predictions', 'draw_correct', 'draw_accuracy'),
                ('away_predictions', 'away_correct', 'away_accuracy'),
            )
        }),
        ('By Confidence Level', {
            'fields': (
                ('high_confidence_predictions', 'high_confidence_correct', 'high_confidence_accuracy'),
                ('medium_confidence_predictions', 'medium_confidence_correct', 'medium_confidence_accuracy'),
                ('low_confidence_predictions', 'low_confidence_correct', 'low_confidence_accuracy'),
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(MatchSentiment)
class MatchSentimentAdmin(admin.ModelAdmin):
    list_display = ('fixture_id', 'home_team', 'away_team', 'league', 'match_date', 
                    'trap_level', 'trap_score', 'public_attention_ratio', 'total_mentions')
    list_filter = ('trap_level', 'league', 'match_date', 'analysis_version')
    search_fields = ('home_team', 'away_team', 'league', 'fixture_id')
    readonly_fields = ('scraped_at', 'updated_at')
    date_hierarchy = 'match_date'
    ordering = ['-match_date', '-trap_score']
    
    fieldsets = (
        ('Match Information', {
            'fields': ('fixture_id', 'home_team', 'away_team', 'league', 'match_date')
        }),
        ('Sentiment Analysis', {
            'fields': ('home_mentions_count', 'away_mentions_count', 'total_mentions',
                      'home_sentiment_score', 'away_sentiment_score', 'public_attention_ratio')
        }),
        ('Trap Detection', {
            'fields': ('trap_score', 'trap_level', 'alert_message', 'recommendation', 
                      'confidence_divergence')
        }),
        ('Metadata', {
            'fields': ('data_sources', 'top_keywords', 'analysis_version', 
                      'scraped_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
