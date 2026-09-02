from django.contrib import admin
from .models import (
    EmailSubscriber,
    MarketingEvent,
    PerformanceSnapshot,
    PredictionLog,
    ProductEvent,
    PublicSelection,
    PublicSelectionClosingPrice,
    PublicSelectionResult,
    SchedulerHeartbeat,
    StrategyLabExperiment,
    StrategyLabObservation,
    StrategyLabSettlement,
)


@admin.register(PublicSelection)
class PublicSelectionAdmin(admin.ModelAdmin):
    list_display = ('category', 'fixture_id', 'home_team', 'away_team',
                    'source_key', 'predicted_outcome', 'odds', 'published_at')
    list_filter = ('category', 'source_key', 'reason_code', 'published_at')
    search_fields = ('fixture_id', 'home_team', 'away_team', 'source_key')
    readonly_fields = tuple(field.name for field in PublicSelection._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PublicSelectionResult)
class PublicSelectionResultAdmin(admin.ModelAdmin):
    list_display = ('selection', 'status', 'unit_profit', 'settled_at')
    list_filter = ('status', 'selection__category', 'settled_at')
    readonly_fields = tuple(
        field.name for field in PublicSelectionResult._meta.fields
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PublicSelectionClosingPrice)
class PublicSelectionClosingPriceAdmin(admin.ModelAdmin):
    list_display = (
        'selection', 'odds', 'closing_line_value', 'odds_captured_at',
    )
    readonly_fields = tuple(
        field.name for field in PublicSelectionClosingPrice._meta.fields
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProductEvent)
class ProductEventAdmin(admin.ModelAdmin):
    list_display = ('event_name', 'surface', 'action', 'has_results', 'duration_bucket', 'created_at')
    list_filter = ('event_name', 'surface', 'duration_bucket', 'created_at')
    search_fields = ('surface', 'action')
    readonly_fields = tuple(field.name for field in ProductEvent._meta.fields)
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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


@admin.register(EmailSubscriber)
class EmailSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'source', 'landing_page', 'language', 'league_interest', 'is_active', 'email_platform_status', 'subscribed_at')
    list_filter = ('is_active', 'language', 'source', 'email_platform_status', 'subscribed_at')
    search_fields = ('email', 'source', 'landing_page', 'utm_source', 'utm_campaign', 'league_interest')
    readonly_fields = ('subscribed_at', 'last_synced_at')


@admin.register(MarketingEvent)
class MarketingEventAdmin(admin.ModelAdmin):
    list_display = ('event_name', 'subscriber', 'source', 'page', 'created_at')
    list_filter = ('event_name', 'source', 'created_at')
    search_fields = ('page', 'source', 'subscriber__email')
    readonly_fields = ('created_at',)


@admin.register(SchedulerHeartbeat)
class SchedulerHeartbeatAdmin(admin.ModelAdmin):
    """Read-only operational gauge for the background worker.

    Settlement is scheduler-only, so a dead worker looks exactly like a healthy
    one with nothing to do — claims just stay PENDING. This is where a staff
    user checks which it is, without needing to call the API.
    """
    list_display = (
        'key', 'health_display', 'status', 'last_run_started_at',
        'last_success_at', 'results_updated', 'claims_settled',
    )
    readonly_fields = (
        'key', 'health_display', 'status',
        'last_run_started_at', 'last_run_completed_at',
        'last_success_at', 'last_failure_at',
        'last_duration_seconds', 'interval_minutes',
        'snapshots_created', 'results_updated', 'claims_settled',
        'last_failure_code', 'run_id', 'version', 'updated_at',
    )

    @admin.display(description='Health')
    def health_display(self, obj):
        return obj.health()

    def has_add_permission(self, request):
        # Written by the scheduler only; a hand-made row would misreport liveness.
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StrategyLabExperiment)
class StrategyLabExperimentAdmin(admin.ModelAdmin):
    list_display = ('name', 'version', 'market', 'status',
                    'decision_horizon_hours', 'minimum_settled_for_review')
    list_filter = ('status', 'market')
    readonly_fields = ('strategy_key', 'version', 'name', 'market',
                       'decision_horizon_hours', 'rules', 'rules_hash',
                       'minimum_settled_for_review', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StrategyLabObservation)
class StrategyLabObservationAdmin(admin.ModelAdmin):
    list_display = ('fixture_id', 'label', 'evidence_phase', 'odds',
                    'expected_return_lower', 'robust_positive_edge',
                    'hours_to_kickoff', 'observed_at')
    list_filter = ('experiment', 'evidence_phase', 'side',
                   'robust_positive_edge', 'league')
    search_fields = ('fixture_id', 'home_team', 'away_team', 'label')
    readonly_fields = tuple(
        field.name for field in StrategyLabObservation._meta.fields
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StrategyLabSettlement)
class StrategyLabSettlementAdmin(admin.ModelAdmin):
    list_display = ('observation', 'outcome', 'unit_profit', 'result_version',
                    'settled_at')
    list_filter = ('outcome', 'observation__experiment')
    readonly_fields = tuple(
        field.name for field in StrategyLabSettlement._meta.fields
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
