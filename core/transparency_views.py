"""
Transparency & Accuracy Tracking Views
Public endpoints showing SmartBet's real performance
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

from core.models import PredictionLog, PublishedClaim
from core.services.accuracy_calculator import AccuracyCalculator
from core.services import public_universe


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def public_accuracy_dashboard(request):
    """
    Public accuracy dashboard - complete transparency.
    
    GET /api/transparency/dashboard/
    
    Returns comprehensive accuracy metrics visible to all users.
    """
    try:
        calculator = AccuracyCalculator()
        stats = calculator.get_comprehensive_stats()
        
        # Add metadata
        stats['last_updated'] = timezone.now().isoformat()
        stats['methodology'] = {
            'what_we_track': 'Only our recommended bets - the top picks we show to users',
            'selection_criteria': 'Minimum 60% confidence AND positive Expected Value',
            'frequency': 'Top 10 best value bets updated daily',
            'data_source': 'Real match results from SportMonks API',
            'verification': 'Third-party API - results cannot be manipulated',
            'timestamp_proof': 'All predictions logged BEFORE matches start',
            'integrity': 'Historical data never deleted or edited',
            'honesty': 'We show both wins and losses - complete transparency'
        }
        stats['transparency_note'] = 'We track only what we recommend to you - honest accountability, not cherry-picked results'
        
        return Response({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def accuracy_summary(request):
    """
    Quick accuracy summary for display on homepage.
    
    GET /api/transparency/summary/
    """
    try:
        calculator = AccuracyCalculator()
        overall = calculator.get_overall_accuracy()
        roi = calculator.get_roi_simulation(stake_per_bet=10.0)
        
        # Get recent performance (last 7 days)
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent = PredictionLog.objects.filter(
            actual_outcome__isnull=False,
            kickoff__gte=seven_days_ago
        )
        
        recent_total = recent.count()
        recent_correct = recent.filter(was_correct=True).count()
        recent_accuracy = (recent_correct / recent_total * 100) if recent_total > 0 else 0
        
        return Response({
            'success': True,
            'summary': {
                'all_time_accuracy': overall['overall']['accuracy_percent'],
                'total_predictions': overall['overall']['total_predictions'],
                'recent_7_days': {
                    'accuracy': round(recent_accuracy, 1),
                    'total': recent_total
                },
                'roi': {
                    'percent': roi['roi_percent'],
                    'total_bets': roi['total_bets'],
                    'profit_loss': roi['total_profit_loss']
                },
                'methodology': {
                    'what_we_track': 'Only our recommended bets (top picks shown to users)',
                    'criteria': 'Minimum 60% confidence + Positive Expected Value',
                    'frequency': 'Top 10 recommendations updated daily',
                    'verification': 'Results fetched from SportMonks API',
                    'transparency': 'All predictions timestamped before matches start'
                }
            },
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def league_accuracy(request):
    """
    Accuracy breakdown by league.
    
    GET /api/transparency/leagues/
    """
    try:
        calculator = AccuracyCalculator()
        leagues = calculator.get_accuracy_by_league()
        
        return Response({
            'success': True,
            'leagues': leagues,
            'total_leagues': len(leagues)
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def recent_predictions_with_results(request):
    """
    Get recent predictions with their actual outcomes.
    
    GET /api/transparency/recent/
    Query params:
    - limit: Number of predictions (default 50)
    - show_all: Include pending or only completed (default false)
    """
    try:
        limit = request.GET.get('limit', None)
        show_all = request.GET.get('show_all', 'false').lower() == 'true'
        
        queryset = PredictionLog.objects.filter(is_recommended=True)
        
        if not show_all:
            queryset = queryset.filter(actual_outcome__isnull=False)
        
        queryset = queryset.order_by('-kickoff')
        
        if limit is not None:
            predictions = queryset[:int(limit)]
        else:
            predictions = queryset
        
        results = []
        for pred in predictions:
            results.append({
                'fixture_id': pred.fixture_id,
                'home_team': pred.home_team,
                'away_team': pred.away_team,
                'league': pred.league,
                'kickoff': pred.kickoff.isoformat(),
                'predicted_outcome': pred.predicted_outcome,
                'confidence': round(float(pred.confidence) * 100, 1),
                'expected_value': round(float(pred.expected_value or 0) * 100, 1),
                'odds': {
                    'home': pred.odds_home,
                    'draw': pred.odds_draw,
                    'away': pred.odds_away
                },
                'actual_outcome': pred.actual_outcome,
                'actual_score': f"{pred.actual_score_home}-{pred.actual_score_away}" if pred.actual_score_home is not None else None,
                'was_correct': pred.was_correct,
                'profit_loss': float(pred.profit_loss_10) if pred.profit_loss_10 else None,
                'prediction_logged_at': pred.prediction_logged_at.isoformat(),
                'status': pred.match_status or ('Pending' if not pred.actual_outcome else 'Completed')
            })
        
        return Response({
            'success': True,
            'predictions': results,
            'count': len(results)
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def quick_stats(request):
    """
    Quick stats for daily monitoring.
    
    GET /api/transparency/quick-stats/
    """
    try:
        completed = PredictionLog.objects.filter(
            actual_outcome__isnull=False,
            is_recommended=True
        )
        
        total = completed.count()
        correct = completed.filter(was_correct=True).count()
        accuracy = (correct / total * 100) if total > 0 else 0
        
        # Last 7 days
        week_ago = timezone.now() - timedelta(days=7)
        recent = completed.filter(kickoff__gte=week_ago)
        recent_total = recent.count()
        recent_correct = recent.filter(was_correct=True).count()
        recent_accuracy = (recent_correct / recent_total * 100) if recent_total > 0 else 0
        
        # Pending
        pending = PredictionLog.objects.filter(
            actual_outcome__isnull=True,
            is_recommended=True
        ).count()
        
        return Response({
            'success': True,
            'all_time': {
                'total': total,
                'correct': correct,
                'accuracy': round(accuracy, 1)
            },
            'last_7_days': {
                'total': recent_total,
                'correct': recent_correct,
                'accuracy': round(recent_accuracy, 1)
            },
            'pending': pending,
            'milestone_progress': {
                'next_milestone': 50 if total < 50 else 100 if total < 100 else 250,
                'current': total,
                'percentage': round((total / (50 if total < 50 else 100 if total < 100 else 250)) * 100, 1)
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def trigger_result_update(request):
    """
    Manually trigger result updates.
    Can be called by frontend refresh button.

    POST /api/transparency/update-results/
    """
    try:
        from core.services.result_updater import ResultUpdaterService

        updater = ResultUpdaterService()
        stats = updater.update_all_pending_results(max_predictions=50)

        return Response({
            'success': True,
            'stats': stats,
            'message': f"Updated {stats['updated']} predictions with {stats.get('accuracy', 0)}% accuracy"
        })

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


# Public message shown when a fixture has no immutable published claim.
UNPUBLISHED_PROOF_MESSAGE = (
    'This prediction has not been published as an immutable BetGlitch claim.'
)


def _record_block():
    roi = AccuracyCalculator().get_roi_simulation(stake_per_bet=10.0)
    return {
        'wins': roi['wins'],
        'losses': roi['losses'],
        'roi_percent': roi['roi_percent'],
        'total_bets': roi['total_bets'],
        # The public record counts only pricing-verified results; it restarts
        # at the pricing-integrity cutoff.
        'verified_record_only': True,
    }


def proof_card_data(request, fixture_id):
    """
    GET /api/proof/<fixture_id>/ — PUBLIC proof payload.

    Serves the immutable PublishedClaim and NOTHING ELSE. When no claim exists
    the response is an explicit unpublished state.

    It must never fall back to PredictionLog: that row is mutable — the
    pipeline overwrites odds, confidence and the selection on every re-run —
    so serving it publicly would present a changeable value under
    "logged before kickoff" language. Staff previews live at
    /api/proof/<id>/preview/ and are never exposed here.
    """
    claim = (
        PublishedClaim.objects.filter(fixture_id=fixture_id)
        .select_related('prediction')
        .order_by('-published_at')
        .first()
    )

    if claim is None:
        return JsonResponse({
            'found': True,
            'published': False,
            'state': 'unpublished',
            'message': UNPUBLISHED_PROOF_MESSAGE,
            'record': _record_block(),
        }, status=200)

    pred = claim.prediction
    resolved = pred.was_correct is not None
    result = {'resolved': bool(resolved), 'status': claim.result_status}
    if resolved:
        result.update({
            'actual_score_home': pred.actual_score_home,
            'actual_score_away': pred.actual_score_away,
            'was_correct': pred.was_correct,
        })

    # Confidence is stored 0-1 (verified 2026-07-29: zero rows above 1.0). The
    # 0-100 branch is retained defensively for any future writer.
    conf = claim.confidence or 0.0
    confidence_pct = round(conf * 100, 1) if conf <= 1 else round(conf, 1)

    return JsonResponse({
        'found': True,
        'published': True,
        'state': 'published',
        'claim_id': str(claim.claim_id),
        'claim_hash': claim.claim_hash,
        'pricing_integrity_status': claim.pricing_integrity_status,
        'pick': {
            'home_team': claim.home_team,
            'away_team': claim.away_team,
            'league': claim.league,
            'market_type': claim.market_type,
            'predicted_outcome': claim.predicted_outcome,
            'odds': claim.odds,
            'confidence': confidence_pct,
            'kickoff': claim.kickoff.isoformat(),
            'prediction_logged_at': claim.prediction_generated_at.isoformat(),
            'published_at': claim.published_at.isoformat(),
            # Lets a reader check the price against the exact market we used.
            'odds_provenance': claim.odds_provenance,
        },
        'result': result,
        'record': _record_block(),
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def proof_preview(request, fixture_id):
    """
    GET /api/proof/<fixture_id>/preview/ — STAFF ONLY.

    Renders the CURRENT, MUTABLE prediction so the team can preview a pick
    before it is published. Deliberately separate from the public proof URL,
    and explicitly labelled: none of this is an immutable claim, and it carries
    no "logged before kickoff" guarantee.
    """
    try:
        pred = PredictionLog.objects.get(fixture_id=fixture_id, is_recommended=True)
    except PredictionLog.DoesNotExist:
        return Response({'found': False}, status=404)

    conf = pred.confidence or 0.0
    return Response({
        'found': True,
        'published': False,
        'state': 'staff_preview',
        'warning': (
            'MUTABLE PREVIEW — these values come from the live prediction and '
            'can change on any pipeline re-run. Not an immutable claim.'
        ),
        'pricing_integrity_status': pred.pricing_integrity_status,
        'pick': {
            'home_team': pred.home_team,
            'away_team': pred.away_team,
            'league': pred.league,
            'market_type': pred.market_type,
            'predicted_outcome': pred.predicted_outcome,
            'odds': pred.odds,
            'confidence': round(conf * 100, 1) if conf <= 1 else round(conf, 1),
            'kickoff': pred.kickoff.isoformat(),
            'prediction_logged_at': pred.prediction_logged_at.isoformat(),
            'odds_provenance': pred.odds_provenance,
        },
        'provenance_problems': public_universe.missing_provenance_fields(
            pred.odds_provenance, pred.market_type
        ),
    })

