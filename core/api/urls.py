"""
URL patterns for Sentiment Analysis API
"""

from django.urls import path
from . import sentiment_views

app_name = 'sentiment_api'

urlpatterns = [
    # Get sentiment data for specific match
    path('sentiment/<int:match_id>/', sentiment_views.get_match_sentiment, name='get_match_sentiment'),
    
    # Trigger sentiment analysis
    path('sentiment/analyze/', sentiment_views.analyze_sentiment, name='analyze_sentiment'),
    
    # Get trap alerts
    path('sentiment/trap-alerts/', sentiment_views.get_trap_alerts, name='get_trap_alerts'),
    
    # Get sentiment statistics
    path('sentiment/stats/', sentiment_views.get_sentiment_stats, name='get_sentiment_stats'),
]
