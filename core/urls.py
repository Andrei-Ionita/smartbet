from django.urls import path
from . import api_views
from . import bankroll_views
from . import auth_views
from . import transparency_views
from . import internal_views
from .feature_flags import account_features_required

account_only = account_features_required

# Minimal URLs - using Next.js frontend with SportMonks API
# Keeping this file for Django admin compatibility

urlpatterns = [
    # API endpoints for recommendations
    path('api/recommendations/', api_views.get_recommendations, name='get_recommendations'),
    path('api/recommended-predictions/', api_views.get_recommended_predictions_with_outcomes, name='get_recommended_predictions'),
    path('api/log-recommendations/', api_views.log_recommendations, name='log_recommendations'),
    path('api/fixture/<int:fixture_id>/', api_views.get_fixture_details, name='get_fixture_details'),
    path('api/fixture/<int:fixture_id>/context-timeline/', api_views.get_fixture_context_timeline, name='get_fixture_context_timeline'),
    path('api/search/', api_views.search_fixtures, name='search_fixtures'),
    # REMOVED 2026-08-03: 'api/fix-performance/' (an unauthenticated GET that
    # rewrote performance metrics on every settled row) and
    # 'api/mark-recommended/' (an unauthenticated POST that set/cleared
    # is_recommended on arbitrary fixtures). Neither had a caller.
    # REMOVED 2026-08-03: 'api/update-fixture-results/'. An unauthenticated,
    # csrf_exempt POST that any anonymous visitor could fire — and the public
    # /monitoring page fired it on every mount. It walked up to 50 pending
    # predictions, made one SportMonks call each and wrote actual_outcome.
    # Result recording belongs to the scheduler:
    #   run_scheduler → update_results → settle_published_claims
    # Manual operation: `python manage.py update_results --max N`.

    # Bankroll Management API
    path('api/bankroll/create/', account_only(bankroll_views.create_bankroll), name='create_bankroll'),
    path('api/bankroll/<str:session_id>/', account_only(bankroll_views.get_bankroll), name='get_bankroll'),
    path('api/bankroll/<str:session_id>/update/', account_only(bankroll_views.update_bankroll), name='update_bankroll'),
    path('api/bankroll/<str:session_id>/stats/', account_only(bankroll_views.get_bankroll_stats), name='get_bankroll_stats'),
    path('api/bankroll/<str:session_id>/transactions/', account_only(bankroll_views.get_transactions), name='get_transactions'),
    path('api/bankroll/stake-recommendation/', account_only(bankroll_views.get_stake_recommendation), name='get_stake_recommendation'),
    path('api/bankroll/record-bet/', account_only(bankroll_views.record_bet), name='record_bet'),
    path('api/bankroll/settle-bet/<int:transaction_id>/', account_only(bankroll_views.settle_bet), name='settle_bet'),
    
    # Authentication API
    path('api/auth/register/', account_only(auth_views.register), name='register'),
    path('api/auth/login/', account_only(auth_views.login), name='login'),
    path('api/auth/logout/', account_only(auth_views.logout), name='logout'),
    path('api/auth/user/', account_only(auth_views.get_user), name='get_user'),
    path('api/auth/token/refresh/', account_only(auth_views.refresh_token), name='refresh_token'),
    path('api/auth/password-reset/request/', account_only(auth_views.request_password_reset), name='request_password_reset'),
    path('api/auth/password-reset/confirm/', account_only(auth_views.confirm_password_reset), name='confirm_password_reset'),
    path('api/auth/account/', account_only(auth_views.delete_account), name='delete_account'),
    path('api/auth/upgrade-tier/', account_only(auth_views.upgrade_tier), name='upgrade_tier'),
    
    # Transparency & Accuracy Tracking (Public)
    path('api/transparency/dashboard/', transparency_views.public_accuracy_dashboard, name='public_accuracy_dashboard'),
    path('api/transparency/summary/', transparency_views.accuracy_summary, name='accuracy_summary'),
    path('api/transparency/leagues/', transparency_views.league_accuracy, name='league_accuracy'),
    path('api/transparency/recent/', transparency_views.recent_predictions_with_results, name='recent_predictions'),
    path('api/transparency/quick-stats/', transparency_views.quick_stats, name='quick_stats'),
    path('api/transparency/calibration/', transparency_views.calibration_evidence, name='calibration_evidence'),
    path('api/transparency/prediction-archive/', transparency_views.prediction_evidence_archive, name='prediction_evidence_archive'),
    path('api/transparency/strategies/', transparency_views.public_strategy_lab, name='public_strategy_lab'),
    path('api/transparency/strategies/<str:strategy_key>/current-fits/', transparency_views.public_strategy_fits, name='public_strategy_fits'),
    # REMOVED 2026-08-03: 'api/transparency/update-results/'. Same class of
    # problem — AllowAny + csrf_exempt, ran ResultUpdaterService against
    # production and returned str(e) to the caller. Its only caller (a button
    # on the public track-record page) was removed on 2026-08-03.
    path('api/proof/<int:fixture_id>/', transparency_views.proof_card_data, name='proof_card_data'),
    # Staff-only mutable preview. Deliberately a different path from the public
    # proof URL so a mutable prediction can never be served as public proof.
    path('api/proof/<int:fixture_id>/preview/', transparency_views.proof_preview, name='proof_preview'),
    # STABLE public proof identity. A fixture may carry several claims (different
    # markets), so the claim UUID — not the fixture id — is canonical.
    # PUBLIC list of immutable published claims. GET-only, PublishedClaim is the
    # sole authority — the public published-picks section used to derive itself
    # from the mutable transparency feed.
    path('api/proof/claims/', transparency_views.published_claims_list, name='published_claims_list'),
    path('api/proof/claim/<uuid:claim_id>/', transparency_views.proof_by_claim, name='proof_by_claim'),
    # Independent timestamping. Public and unauthenticated by design: proof
    # nobody can check is not proof.
    path('api/proof/anchors/', transparency_views.anchors_list, name='anchors_list'),
    path('api/proof/anchors/<str:digest>/', transparency_views.anchor_detail, name='anchor_detail'),
    path('api/proof/anchors/<str:digest>/proof/', transparency_views.anchor_proof, name='anchor_proof'),
    # Staff-only publication queue: publishable verified snapshots.
    path('api/proof/queue/', transparency_views.publication_queue, name='publication_queue'),
    # Staff-only, POST-only explicit publication of ONE chosen snapshot.
    path('api/proof/snapshot/<uuid:snapshot_id>/publish/', transparency_views.publish_snapshot_view, name='publish_snapshot'),
    # Compatibility: resolves to one unambiguous eligible snapshot, else refuses.
    path('api/proof/<int:prediction_id>/publish/', transparency_views.publish_claim_view, name='publish_claim'),
    
    # Internal operations — staff only, never linked from a public page.
    path('api/internal/scheduler-health/', internal_views.scheduler_health, name='scheduler_health'),
    path('api/internal/strategies-lab/', internal_views.strategies_lab, name='strategies_lab'),

    # Email Capture / Newsletter
    path('api/subscribe/', account_only(api_views.subscribe_email), name='subscribe_email'),
    path('api/marketing/events/', account_only(api_views.track_marketing_event), name='track_marketing_event'),
    path('api/marketing/webhook/', account_only(api_views.marketing_webhook), name='marketing_webhook'),
]
