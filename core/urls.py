from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MatchViewSet, PredictionsListView, leagues_list, matches_list, predict_custom_match, model_performance_stats
from . import premium_prediction_views

router = DefaultRouter()
router.register(r'matches', MatchViewSet, basename='match')

urlpatterns = [
    path('', include(router.urls)),
    path('api/predictions/', PredictionsListView.as_view(), name='predictions-list'),
    path('api/leagues/', leagues_list, name='leagues-list'),
    path('api/matches/', matches_list, name='matches-list'),
    path('api/predict_custom_match/', predict_custom_match, name='predict-custom-match'),
    path('api/model/performance/', model_performance_stats, name='model-performance-stats'),
    
    # Premium Model API Endpoints
    path('api/premium/model/status/', premium_prediction_views.premium_model_status, name='premium-model-status'),
    path('api/premium/model/performance/', premium_prediction_views.premium_model_performance, name='premium-model-performance'),
    path('api/premium/model/reload/', premium_prediction_views.reload_premium_model, name='premium-model-reload'),
    path('api/premium/predict/match/', premium_prediction_views.premium_predict_match, name='premium-predict-match'),
    path('api/premium/predict/batch/', premium_prediction_views.premium_batch_predict, name='premium-batch-predict'),
    path('api/premium/predictions/', premium_prediction_views.premium_predictions_list, name='premium-predictions-list'),
    path('api/premium/top-picks/', premium_prediction_views.premium_top_picks, name='premium-top-picks'),
] 