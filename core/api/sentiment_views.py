"""
API Views for Sentiment Analysis & Trap Detection

Provides endpoints to access sentiment data and trigger analysis.
"""

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, Avg
from datetime import datetime, timedelta
import json

from ..models import MatchSentiment
from ..services.sentiment_analyzer import SentimentAnalyzer


@api_view(['GET'])
def get_match_sentiment(request, match_id):
    """
    Get sentiment analysis data for a specific match.
    
    GET /api/sentiment/{match_id}/
    """
    try:
        # Try to get sentiment data for this match
        sentiment = MatchSentiment.objects.filter(fixture_id=match_id).first()
        
        if not sentiment:
            return Response({
                'success': False,
                'message': 'No sentiment data available for this match',
                'match_id': match_id
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Serialize the data
        data = {
            'match_id': sentiment.fixture_id,
            'home_team': sentiment.home_team,
            'away_team': sentiment.away_team,
            'league': sentiment.league,
            'match_date': sentiment.match_date.isoformat(),
            
            # Sentiment metrics
            'sentiment': {
                'home_mentions': sentiment.home_mentions_count,
                'away_mentions': sentiment.away_mentions_count,
                'total_mentions': sentiment.total_mentions,
                'home_sentiment_score': sentiment.home_sentiment_score,
                'away_sentiment_score': sentiment.away_sentiment_score,
                'public_attention_ratio': sentiment.public_attention_ratio,
                'top_keywords': sentiment.top_keywords,
                'data_sources': sentiment.data_sources
            },
            
            # Trap analysis
            'trap_analysis': {
                'trap_score': sentiment.trap_score,
                'trap_level': sentiment.trap_level,
                'alert_message': sentiment.alert_message,
                'recommendation': sentiment.recommendation,
                'confidence_divergence': sentiment.confidence_divergence,
                'is_high_risk': sentiment.is_high_trap_risk
            },
            
            # Metadata
            'analysis_info': {
                'scraped_at': sentiment.scraped_at.isoformat(),
                'updated_at': sentiment.updated_at.isoformat(),
                'analysis_version': sentiment.analysis_version
            }
        }
        
        return Response({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
            'message': 'Failed to fetch sentiment data'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def analyze_sentiment(request):
    """
    Trigger sentiment analysis for a specific match.
    
    POST /api/sentiment/analyze/
    Body: {
        "match_id": 123456,
        "home_team": "Arsenal",
        "away_team": "Chelsea", 
        "league": "Premier League",
        "match_date": "2024-01-15T15:00:00Z",
        "prediction_probs": {"home": 0.65, "draw": 0.20, "away": 0.15},
        "odds_data": {"home": 2.50, "draw": 3.20, "away": 2.80}  // optional
    }
    """
    try:
        # Extract data from request
        match_id = request.data.get('match_id')
        home_team = request.data.get('home_team')
        away_team = request.data.get('away_team')
        league = request.data.get('league')
        match_date_str = request.data.get('match_date')
        prediction_probs = request.data.get('prediction_probs', {})
        odds_data = request.data.get('odds_data')
        
        # Validate required fields
        if not all([match_id, home_team, away_team, league, match_date_str]):
            return Response({
                'success': False,
                'message': 'Missing required fields: match_id, home_team, away_team, league, match_date'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Parse match date
        try:
            match_date = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
        except ValueError:
            return Response({
                'success': False,
                'message': 'Invalid match_date format. Use ISO format.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if analysis already exists
        existing_sentiment = MatchSentiment.objects.filter(fixture_id=match_id).first()
        
        # Initialize sentiment analyzer
        analyzer = SentimentAnalyzer()
        
        # Run sentiment analysis
        sentiment_data, trap_analysis = analyzer.analyze_match_sentiment(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            match_date=match_date,
            prediction_probs=prediction_probs,
            odds_data=odds_data
        )
        
        if not sentiment_data or not trap_analysis:
            return Response({
                'success': False,
                'message': 'Failed to analyze sentiment. No data found or API error.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Save or update sentiment data
        if existing_sentiment:
            # Update existing record
            existing_sentiment.home_mentions_count = sentiment_data.home_mentions_count
            existing_sentiment.away_mentions_count = sentiment_data.away_mentions_count
            existing_sentiment.home_sentiment_score = sentiment_data.home_sentiment_score
            existing_sentiment.away_sentiment_score = sentiment_data.away_sentiment_score
            existing_sentiment.public_attention_ratio = sentiment_data.public_attention_ratio
            existing_sentiment.trap_score = trap_analysis.trap_score
            existing_sentiment.trap_level = trap_analysis.trap_level
            existing_sentiment.alert_message = trap_analysis.alert_message
            existing_sentiment.recommendation = trap_analysis.recommendation
            existing_sentiment.confidence_divergence = trap_analysis.confidence_divergence
            existing_sentiment.data_sources = sentiment_data.data_sources
            existing_sentiment.top_keywords = sentiment_data.top_keywords
            existing_sentiment.total_mentions = sentiment_data.total_mentions
            existing_sentiment.save()
            
            sentiment_obj = existing_sentiment
        else:
            # Create new record
            sentiment_obj = MatchSentiment.objects.create(
                fixture_id=match_id,
                home_team=home_team,
                away_team=away_team,
                league=league,
                match_date=match_date,
                home_mentions_count=sentiment_data.home_mentions_count,
                away_mentions_count=sentiment_data.away_mentions_count,
                home_sentiment_score=sentiment_data.home_sentiment_score,
                away_sentiment_score=sentiment_data.away_sentiment_score,
                public_attention_ratio=sentiment_data.public_attention_ratio,
                trap_score=trap_analysis.trap_score,
                trap_level=trap_analysis.trap_level,
                alert_message=trap_analysis.alert_message,
                recommendation=trap_analysis.recommendation,
                confidence_divergence=trap_analysis.confidence_divergence,
                data_sources=sentiment_data.data_sources,
                top_keywords=sentiment_data.top_keywords,
                total_mentions=sentiment_data.total_mentions
            )
        
        # Return the analysis results
        return Response({
            'success': True,
            'message': 'Sentiment analysis completed successfully',
            'data': {
                'match_id': sentiment_obj.fixture_id,
                'sentiment_summary': sentiment_obj.sentiment_summary,
                'trap_analysis': {
                    'trap_score': sentiment_obj.trap_score,
                    'trap_level': sentiment_obj.trap_level,
                    'alert_message': sentiment_obj.alert_message,
                    'recommendation': sentiment_obj.recommendation,
                    'is_high_risk': sentiment_obj.is_high_trap_risk
                },
                'analysis_timestamp': sentiment_obj.scraped_at.isoformat()
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
            'message': 'Failed to analyze sentiment'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_trap_alerts(request):
    """
    Get today's trap alerts for matches with high trap risk.
    
    GET /api/sentiment/trap-alerts/
    Query params:
        - hours_ahead: Number of hours ahead to check (default: 48)
        - min_trap_score: Minimum trap score to include (default: 3)
    """
    try:
        # Get query parameters
        hours_ahead = int(request.GET.get('hours_ahead', 48))
        min_trap_score = int(request.GET.get('min_trap_score', 3))
        
        # Calculate time range
        now = timezone.now()
        future_time = now + timedelta(hours=hours_ahead)
        
        # Get high-risk matches
        trap_alerts = MatchSentiment.objects.filter(
            match_date__gte=now,
            match_date__lte=future_time,
            trap_score__gte=min_trap_score
        ).order_by('-trap_score', 'match_date')
        
        alerts_data = []
        for sentiment in trap_alerts:
            alerts_data.append({
                'match_id': sentiment.fixture_id,
                'home_team': sentiment.home_team,
                'away_team': sentiment.away_team,
                'league': sentiment.league,
                'match_date': sentiment.match_date.isoformat(),
                'trap_score': sentiment.trap_score,
                'trap_level': sentiment.trap_level,
                'alert_message': sentiment.alert_message,
                'recommendation': sentiment.recommendation,
                'public_attention_ratio': sentiment.public_attention_ratio,
                'confidence_divergence': sentiment.confidence_divergence,
                'alert_color': sentiment.get_alert_color(),
                'alert_icon': sentiment.get_alert_icon()
            })
        
        return Response({
            'success': True,
            'data': {
                'alerts': alerts_data,
                'total_alerts': len(alerts_data),
                'time_range': {
                    'from': now.isoformat(),
                    'to': future_time.isoformat()
                },
                'filters': {
                    'hours_ahead': hours_ahead,
                    'min_trap_score': min_trap_score
                }
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
            'message': 'Failed to fetch trap alerts'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_sentiment_stats(request):
    """
    Get overall sentiment analysis statistics.
    
    GET /api/sentiment/stats/
    """
    try:
        # Get basic stats
        total_analyses = MatchSentiment.objects.count()
        
        # Trap level distribution
        trap_levels = MatchSentiment.objects.values('trap_level').distinct()
        trap_distribution = {}
        for level in trap_levels:
            count = MatchSentiment.objects.filter(trap_level=level['trap_level']).count()
            trap_distribution[level['trap_level']] = count
        
        # Recent analyses (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_analyses = MatchSentiment.objects.filter(scraped_at__gte=week_ago).count()
        
        # Average trap score
        avg_trap_score = MatchSentiment.objects.aggregate(
            avg_trap_score=Avg('trap_score')
        )['avg_trap_score'] or 0
        
        return Response({
            'success': True,
            'data': {
                'total_analyses': total_analyses,
                'recent_analyses_7_days': recent_analyses,
                'average_trap_score': round(avg_trap_score, 2),
                'trap_level_distribution': trap_distribution,
                'generated_at': timezone.now().isoformat()
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
            'message': 'Failed to fetch sentiment stats'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
