from django.urls import path, include
from django.contrib import admin
from . import api_views
from . import bankroll_views
from . import auth_views
from . import transparency_views

# Minimal URLs - using Next.js frontend with SportMonks API
# Keeping this file for Django admin compatibility

urlpatterns = [
    path('admin/', admin.site.urls), # Django admin
    
    # API endpoints for recommendations
    path('api/recommendations/', api_views.get_recommendations, name='get_recommendations'),
    path('api/recommended-predictions/', api_views.get_recommended_predictions_with_outcomes, name='get_recommended_predictions'),
    path('api/log-recommendations/', api_views.log_recommendations, name='log_recommendations'),
    path('api/mark-recommended/', api_views.mark_recommended_by_fixture_ids, name='mark_recommended'),
    path('api/fixture/<int:fixture_id>/', api_views.get_fixture_details, name='get_fixture_details'),
    path('api/search/', api_views.search_fixtures, name='search_fixtures'),
    path('api/fix-performance/', api_views.fix_performance_metrics, name='fix_performance_metrics'),
    path('api/update-fixture-results/', api_views.update_fixture_results, name='update_fixture_results'),
    
    # Bankroll Management API
    path('api/bankroll/create/', bankroll_views.create_bankroll, name='create_bankroll'),
    path('api/bankroll/<str:session_id>/', bankroll_views.get_bankroll, name='get_bankroll'),
    path('api/bankroll/<str:session_id>/update/', bankroll_views.update_bankroll, name='update_bankroll'),
    path('api/bankroll/<str:session_id>/stats/', bankroll_views.get_bankroll_stats, name='get_bankroll_stats'),
    path('api/bankroll/<str:session_id>/transactions/', bankroll_views.get_transactions, name='get_transactions'),
    path('api/bankroll/stake-recommendation/', bankroll_views.get_stake_recommendation, name='get_stake_recommendation'),
    path('api/bankroll/record-bet/', bankroll_views.record_bet, name='record_bet'),
    path('api/bankroll/settle-bet/<int:transaction_id>/', bankroll_views.settle_bet, name='settle_bet'),
    
    # Authentication API
    path('api/auth/register/', auth_views.register, name='register'),
    path('api/auth/login/', auth_views.login, name='login'),
    path('api/auth/logout/', auth_views.logout, name='logout'),
    path('api/auth/user/', auth_views.get_user, name='get_user'),
    path('api/auth/token/refresh/', auth_views.refresh_token, name='refresh_token'),
    
    # Transparency & Accuracy Tracking (Public)
    path('api/transparency/dashboard/', transparency_views.public_accuracy_dashboard, name='public_accuracy_dashboard'),
    path('api/transparency/summary/', transparency_views.accuracy_summary, name='accuracy_summary'),
    path('api/transparency/leagues/', transparency_views.league_accuracy, name='league_accuracy'),
    path('api/transparency/recent/', transparency_views.recent_predictions_with_results, name='recent_predictions'),
    path('api/transparency/quick-stats/', transparency_views.quick_stats, name='quick_stats'),
    path('api/transparency/update-results/', transparency_views.trigger_result_update, name='trigger_result_update'),
    
    # Email Capture / Newsletter
    path('api/subscribe/', api_views.subscribe_email, name='subscribe_email'),
]
