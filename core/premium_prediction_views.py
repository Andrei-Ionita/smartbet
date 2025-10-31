"""
Premium Model API Views for SmartBet Django Application
Provides REST API endpoints for ML model predictions
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.utils import timezone
from django.db.models import Q
from .models import Match, OddsSnapshot, MatchScoreModel
from .ml_model_manager import premium_model_manager
from .serializers import MatchSerializer
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@api_view(['GET'])
def premium_model_status(request):
    """
    Get the status and information about the premium ML model.
    
    GET /api/premium/model/status/
    """
    try:
        model_info = premium_model_manager.get_model_info()
        
        return Response({
            'success': True,
            'model': model_info,
            'endpoint': 'premium_model_status',
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Premium model status error: {str(e)}")
        return Response({
            'success': False,
            'error': str(e),
            'endpoint': 'premium_model_status'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def premium_predict_match(request):
    """
    Generate premium prediction for a specific match.
    
    POST /api/premium/predict/match/
    Body: {"match_id": 123}
    """
    try:
        match_id = request.data.get('match_id')
        if not match_id:
            return Response({
                'success': False,
                'error': 'match_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get match
        try:
            match = Match.objects.select_related(
                'home_team', 'away_team', 'league'
            ).prefetch_related('odds_snapshots').get(id=match_id)
        except Match.DoesNotExist:
            return Response({
                'success': False,
                'error': f'Match {match_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Generate prediction
        prediction = premium_model_manager.predict_match(match)
        
        if not prediction:
            return Response({
                'success': False,
                'error': 'Failed to generate prediction'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Add match details
        response_data = {
            'success': True,
            'match': {
                'id': match.id,
                'home_team': match.home_team.name_en,
                'away_team': match.away_team.name_en,
                'league': match.league.name_en,
                'kickoff': match.kickoff.isoformat(),
                'status': match.status
            },
            'prediction': prediction,
            'endpoint': 'premium_predict_match',
            'timestamp': timezone.now().isoformat()
        }
        
        return Response(response_data)
        
    except Exception as e:
        logger.error(f"Premium prediction error: {str(e)}")
        return Response({
            'success': False,
            'error': str(e),
            'endpoint': 'premium_predict_match'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@cache_page(60 * 15)  # Cache for 15 minutes
def premium_predictions_list(request):
    """
    Get premium predictions for upcoming matches.
    
    GET /api/premium/predictions/
    Query params: 
    - league (optional): Filter by league
    - limit (optional): Limit number of results (default: 10)
    - days_ahead (optional): Look ahead N days (default: 14)
    """
    try:
        # Get query parameters
        league = request.GET.get('league')
        limit = int(request.GET.get('limit', 10))
        days_ahead = int(request.GET.get('days_ahead', 14))
        
        # Date range
        now = timezone.now()
        end_date = now + timedelta(days=days_ahead)
        
        # Build queryset
        queryset = Match.objects.select_related(
            'home_team', 'away_team', 'league'
        ).prefetch_related('odds_snapshots').filter(
            status='NS',  # Not started
            kickoff__gte=now,
            kickoff__lte=end_date,
            odds_snapshots__isnull=False
        ).distinct()
        
        if league:
            queryset = queryset.filter(league__name_en__icontains=league)
        
        queryset = queryset.order_by('kickoff')[:limit]
        
        # Generate predictions
        matches = list(queryset)
        predictions = premium_model_manager.predict_batch(matches)
        
        return Response({
            'success': True,
            'count': len(predictions),
            'predictions': predictions,
            'filters': {
                'league': league,
                'limit': limit,
                'days_ahead': days_ahead
            },
            'endpoint': 'premium_predictions_list',
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Premium predictions list error: {str(e)}")
        return Response({
            'success': False,
            'error': str(e),
            'endpoint': 'premium_predictions_list'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def premium_batch_predict(request):
    """
    Generate premium predictions for multiple matches.
    
    POST /api/premium/predict/batch/
    Body: {"match_ids": [123, 456, 789]}
    """
    try:
        match_ids = request.data.get('match_ids', [])
        if not match_ids or not isinstance(match_ids, list):
            return Response({
                'success': False,
                'error': 'match_ids array is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(match_ids) > 50:  # Limit batch size
            return Response({
                'success': False,
                'error': 'Maximum 50 matches per batch'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get matches
        matches = Match.objects.select_related(
            'home_team', 'away_team', 'league'
        ).prefetch_related('odds_snapshots').filter(id__in=match_ids)
        
        if not matches.exists():
            return Response({
                'success': False,
                'error': 'No valid matches found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Generate predictions
        predictions = premium_model_manager.predict_batch(list(matches))
        
        return Response({
            'success': True,
            'requested_count': len(match_ids),
            'predictions_count': len(predictions),
            'predictions': predictions,
            'endpoint': 'premium_batch_predict',
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Premium batch prediction error: {str(e)}")
        return Response({
            'success': False,
            'error': str(e),
            'endpoint': 'premium_batch_predict'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def premium_top_picks(request):
    """
    Get top premium predictions with high confidence.
    
    GET /api/premium/top-picks/
    Query params:
    - min_confidence (optional): Minimum confidence level (default: 0.6)
    - limit (optional): Limit results (default: 5)
    """
    try:
        min_confidence = float(request.GET.get('min_confidence', 0.6))
        limit = int(request.GET.get('limit', 5))
        
        # Get upcoming matches with odds
        now = timezone.now()
        end_date = now + timedelta(days=3)  # Next 3 days
        
        matches = Match.objects.select_related(
            'home_team', 'away_team', 'league'
        ).prefetch_related('odds_snapshots').filter(
            status='NS',
            kickoff__gte=now,
            kickoff__lte=end_date,
            odds_snapshots__isnull=False
        ).distinct().order_by('kickoff')[:20]  # Get more to filter
        
        # Generate predictions
        all_predictions = premium_model_manager.predict_batch(list(matches))
        
        # Filter by confidence
        top_picks = [
            pred for pred in all_predictions 
            if pred['max_probability'] >= min_confidence
        ]
        
        # Sort by confidence and limit
        top_picks.sort(key=lambda x: x['max_probability'], reverse=True)
        top_picks = top_picks[:limit]
        
        return Response({
            'success': True,
            'count': len(top_picks),
            'top_picks': top_picks,
            'filters': {
                'min_confidence': min_confidence,
                'limit': limit
            },
            'endpoint': 'premium_top_picks',
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Premium top picks error: {str(e)}")
        return Response({
            'success': False,
            'error': str(e),
            'endpoint': 'premium_top_picks'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def reload_premium_model(request):
    """
    Reload the premium model (admin endpoint).
    
    POST /api/premium/model/reload/
    """
    try:
        success = premium_model_manager.load_model(force_reload=True)
        
        if success:
            model_info = premium_model_manager.get_model_info()
            return Response({
                'success': True,
                'message': 'Premium model reloaded successfully',
                'model': model_info,
                'endpoint': 'reload_premium_model',
                'timestamp': timezone.now().isoformat()
            })
        else:
            return Response({
                'success': False,
                'error': 'Failed to reload premium model'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"Premium model reload error: {str(e)}")
        return Response({
            'success': False,
            'error': str(e),
            'endpoint': 'reload_premium_model'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def premium_model_performance(request):
    """
    Get premium model performance metrics.
    
    GET /api/premium/model/performance/
    """
    try:
        if not premium_model_manager.is_loaded:
            premium_model_manager.load_model()
        
        model_info = premium_model_manager.get_model_info()
        
        if model_info['status'] != 'loaded':
            return Response({
                'success': False,
                'error': 'Model not loaded'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Get performance data from model package
        model_package = premium_model_manager.model_package
        performance = model_package.get('performance', {})
        data_info = model_package.get('data_info', {})
        original_metrics = model_package.get('original_metrics', {})
        
        return Response({
            'success': True,
            'performance': {
                'accuracy': performance.get('test_accuracy', 0),
                'train_accuracy': performance.get('train_accuracy', 0),
                'training_time_seconds': performance.get('training_time_seconds', 0),
                'original_cv_accuracy': original_metrics.get('cross_validation_scores', {}).get('accuracy', 0),
                'log_loss': original_metrics.get('cross_validation_scores', {}).get('log_loss', 0),
                'brier_scores': {
                    'home': original_metrics.get('cross_validation_scores', {}).get('brier_score_home', 0),
                    'draw': original_metrics.get('cross_validation_scores', {}).get('brier_score_draw', 0),
                    'away': original_metrics.get('cross_validation_scores', {}).get('brier_score_away', 0)
                }
            },
            'data': {
                'training_samples': data_info.get('training_samples', 0),
                'feature_count': data_info.get('feature_count', 0),
                'class_distribution': data_info.get('class_distribution', {})
            },
            'model': {
                'version': model_package.get('version', 'unknown'),
                'created_at': model_package.get('rebuilt_at', 'unknown'),
                'algorithm': 'LightGBM'
            },
            'endpoint': 'premium_model_performance',
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Premium model performance error: {str(e)}")
        return Response({
            'success': False,
            'error': str(e),
            'endpoint': 'premium_model_performance'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 