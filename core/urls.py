from django.urls import path, include
from django.contrib import admin
from . import api_views

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
]
