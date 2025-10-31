"""
Simple API views for SmartBet recommendations
Works with the current PredictionLog model structure
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta
import json

from .models import PredictionLog


def generate_model_explanation(prediction):
    """Generate beautiful, comprehensive model insights"""
    
    # Determine prediction strength
    confidence = prediction.confidence
    if confidence >= 0.70:
        strength = "Very Strong"
        strength_emoji = "🔥"
    elif confidence >= 0.60:
        strength = "Strong" 
        strength_emoji = "⚡"
    elif confidence >= 0.55:
        strength = "Moderate"
        strength_emoji = "📊"
    else:
        strength = "Weak"
        strength_emoji = "⚠️"
    
    # Determine consensus quality
    consensus = prediction.consensus or 0
    if consensus >= 0.80:
        consensus_quality = "Excellent"
        consensus_emoji = "🎯"
    elif consensus >= 0.60:
        consensus_quality = "Good"
        consensus_emoji = "✅"
    else:
        consensus_quality = "Fair"
        consensus_emoji = "📈"
    
    # Determine variance interpretation
    variance = prediction.variance or 0
    if variance <= 10:
        variance_quality = "Very Low"
        variance_emoji = "🎯"
    elif variance <= 20:
        variance_quality = "Low"
        variance_emoji = "✅"
    elif variance <= 30:
        variance_quality = "Moderate"
        variance_emoji = "📊"
    else:
        variance_quality = "High"
        variance_emoji = "⚠️"
    
    # Generate outcome-specific insights
    outcome = prediction.predicted_outcome.lower()
    if outcome == 'home':
        outcome_insight = f"{prediction.home_team} has a {strength.lower()} advantage at home"
        outcome_emoji = "🏠"
    elif outcome == 'away':
        outcome_insight = f"{prediction.away_team} shows {strength.lower()} away form"
        outcome_emoji = "✈️"
    else:
        outcome_insight = f"Match shows {strength.lower()} draw potential"
        outcome_emoji = "🤝"
    
    # Generate EV insight
    ev = prediction.expected_value or 0
    if ev > 0.15:
        ev_quality = "Excellent"
        ev_emoji = "💰"
    elif ev > 0.10:
        ev_quality = "Very Good"
        ev_emoji = "💎"
    elif ev > 0.05:
        ev_quality = "Good"
        ev_emoji = "📈"
    elif ev > 0:
        ev_quality = "Positive"
        ev_emoji = "✅"
    else:
        ev_quality = "Negative"
        ev_emoji = "⚠️"
    
    # Generate league-specific insight
    league = prediction.league
    if "Premier League" in league:
        league_insight = "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League - High market efficiency"
    elif "La Liga" in league:
        league_insight = "🇪🇸 La Liga - Strong home advantage patterns"
    elif "Serie A" in league:
        league_insight = "🇮🇹 Serie A - Tactical defensive style"
    elif "Bundesliga" in league:
        league_insight = "🇩🇪 Bundesliga - High-scoring matches"
    elif "Ligue 1" in league:
        league_insight = "🇫🇷 Ligue 1 - Competitive balance"
    else:
        league_insight = f"🌍 {league} - Regional characteristics"
    
    # Generate comprehensive explanation
    explanation = f"{strength_emoji} {strength} {outcome_insight} ({confidence:.1%} confidence). {consensus_emoji} {consensus_quality} model consensus ({consensus:.0%}) with {variance_quality} variance ({variance_emoji}). {ev_emoji} {ev_quality} expected value ({ev:.1%}). {league_insight}. {prediction.model_count} models analyzed using {prediction.ensemble_strategy.replace('_', ' ').title()}."
    
    return explanation


@csrf_exempt
@require_http_methods(["GET"])
def get_recommendations(request):
    """
    Get betting recommendations from PredictionLog
    
    GET /api/recommendations/
    Query params:
    - league (optional): Filter by league
    - limit (optional): Limit number of results (default: 10)
    """
    try:
        # Get query parameters
        league = request.GET.get('league', '').strip()
        limit = int(request.GET.get('limit', 10))
        
        # Build queryset for future predictions
        now = timezone.now()
        end_date = now + timedelta(days=14)  # 14-day window
        
        queryset = PredictionLog.objects.filter(
            kickoff__gte=now,
            kickoff__lte=end_date,
            predicted_outcome__isnull=False,
            confidence__gte=0.55  # 55% minimum confidence
        ).order_by('-confidence', '-expected_value')
        
        # Filter by league if specified
        if league:
            queryset = queryset.filter(league__icontains=league)
        
        # Limit results
        predictions = queryset[:limit]
        
        # Convert to frontend format
        recommendations = []
        for pred in predictions:
            recommendation = {
                'fixture_id': pred.fixture_id,
                'home_team': pred.home_team,
                'away_team': pred.away_team,
                'league': pred.league,
                'kickoff': pred.kickoff.isoformat(),
                'predicted_outcome': pred.predicted_outcome.capitalize() if pred.predicted_outcome else 'Home',
                'confidence': pred.confidence,
                'expected_value': pred.expected_value,
                'ev': pred.expected_value,  # Frontend expects 'ev' field
                'odds_home': pred.odds_home,
                'odds_draw': pred.odds_draw,
                'odds_away': pred.odds_away,
                'bookmaker': pred.bookmaker or 'Unknown',
                # Frontend expects 'odds_data' object
                'odds_data': {
                    'home': pred.odds_home,
                    'draw': pred.odds_draw,
                    'away': pred.odds_away,
                    'bookmaker': pred.bookmaker or 'Unknown'
                },
                # Frontend expects 'probabilities' object
                'probabilities': {
                    'home': pred.probability_home,
                    'draw': pred.probability_draw,
                    'away': pred.probability_away
                },
                'model_count': pred.model_count,
                'consensus': pred.consensus,
                'variance': pred.variance,
                'ensemble_strategy': pred.ensemble_strategy,
                'recommendation_score': pred.recommendation_score,
                'notes': pred.notes,
                # Rich model insights for beautiful display
                'explanation': generate_model_explanation(pred),
                'debug_info': {
                    'consensus': pred.consensus,
                    'variance': pred.variance,
                    'model_count': pred.model_count,
                    'strategy': pred.ensemble_strategy
                },
                # EV analysis for explore page
                'ev_analysis': {
                    'home': pred.expected_value if pred.predicted_outcome.lower() == 'home' else None,
                    'draw': pred.expected_value if pred.predicted_outcome.lower() == 'draw' else None,
                    'away': pred.expected_value if pred.predicted_outcome.lower() == 'away' else None,
                    'best_bet': pred.predicted_outcome.lower(),
                    'best_ev': pred.expected_value
                },
                # Additional fields for explore page
                'prediction_confidence': pred.confidence,
                'prediction_strength': 'Very Strong' if pred.confidence >= 0.70 else 'Strong' if pred.confidence >= 0.60 else 'Moderate',
                'ensemble_info': {
                    'model_count': pred.model_count,
                    'consensus': pred.consensus,
                    'variance': pred.variance,
                    'strategy': pred.ensemble_strategy
                }
            }
            recommendations.append(recommendation)
        
        return JsonResponse({
            'success': True,
            'data': recommendations,
            'count': len(recommendations),
            'message': f'Found {len(recommendations)} recommendations'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'data': [],
            'count': 0
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_fixture_details(request, fixture_id):
    """
    Get detailed information for a specific fixture
    
    GET /api/fixture/{fixture_id}/
    """
    try:
        prediction = PredictionLog.objects.get(fixture_id=fixture_id)
        
        fixture_data = {
            'fixture_id': prediction.fixture_id,
            'home_team': prediction.home_team,
            'away_team': prediction.away_team,
            'league': prediction.league,
            'league_id': prediction.league_id,
            'kickoff': prediction.kickoff.isoformat(),
            'predicted_outcome': prediction.predicted_outcome.capitalize() if prediction.predicted_outcome else 'Home',
            'confidence': prediction.confidence,
            'expected_value': prediction.expected_value,
            'odds_home': prediction.odds_home,
            'odds_draw': prediction.odds_draw,
            'odds_away': prediction.odds_away,
            'bookmaker': prediction.bookmaker,
            # Frontend expects 'probabilities' object
            'probabilities': {
                'home': prediction.probability_home,
                'draw': prediction.probability_draw,
                'away': prediction.probability_away
            },
            'model_count': prediction.model_count,
            'consensus': prediction.consensus,
            'variance': prediction.variance,
            'ensemble_strategy': prediction.ensemble_strategy,
            'recommendation_score': prediction.recommendation_score,
            'notes': prediction.notes,
            'prediction_logged_at': prediction.prediction_logged_at.isoformat(),
            'actual_outcome': prediction.actual_outcome,
            'actual_score_home': prediction.actual_score_home,
            'actual_score_away': prediction.actual_score_away,
            'match_status': prediction.match_status,
            'was_correct': prediction.was_correct,
            'profit_loss_10': prediction.profit_loss_10,
            'roi_percent': prediction.roi_percent
        }
        
        return JsonResponse({
            'success': True,
            'data': fixture_data
        })
        
    except PredictionLog.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Fixture {fixture_id} not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_recommended_predictions_with_outcomes(request):
    """
    Get recommended predictions with their actual outcomes for monitoring.
    
    GET /api/recommended-predictions/
    Query params:
    - limit (optional): Limit number of results (default: 50)
    - include_pending (optional): Include matches that haven't finished yet (default: true)
    """
    try:
        limit = int(request.GET.get('limit', 50))
        include_pending = request.GET.get('include_pending', 'true').lower() == 'true'
        
        # Get all recommended predictions
        queryset = PredictionLog.objects.filter(
            is_recommended=True
        ).order_by('-kickoff')
        
        # If not including pending, only show completed matches
        if not include_pending:
            queryset = queryset.filter(actual_outcome__isnull=False)
        
        predictions = queryset[:limit]
        
        # Convert to frontend format
        results = []
        for pred in predictions:
            result = {
                'fixture_id': pred.fixture_id,
                'home_team': pred.home_team,
                'away_team': pred.away_team,
                'league': pred.league,
                'kickoff': pred.kickoff.isoformat(),
                'predicted_outcome': pred.predicted_outcome.capitalize() if pred.predicted_outcome else 'Unknown',
                'predicted_outcome_raw': pred.predicted_outcome,  # For comparison
                # Convert confidence to percentage if stored as decimal
                'confidence': round(pred.confidence * 100, 1) if pred.confidence and pred.confidence < 1 else round(pred.confidence, 1),
                # Convert EV to percentage if stored as decimal
                'expected_value': round(pred.expected_value * 100, 2) if pred.expected_value and pred.expected_value < 1 else round(pred.expected_value, 2) if pred.expected_value else None,
                'odds_home': pred.odds_home,
                'odds_draw': pred.odds_draw,
                'odds_away': pred.odds_away,
                'bookmaker': pred.bookmaker,
                'actual_outcome': pred.actual_outcome.capitalize() if pred.actual_outcome else None,
                'actual_outcome_raw': pred.actual_outcome,  # For comparison
                'actual_score_home': pred.actual_score_home,
                'actual_score_away': pred.actual_score_away,
                'match_status': pred.match_status,
                'was_correct': pred.was_correct,
                'profit_loss_10': round(pred.profit_loss_10, 2) if pred.profit_loss_10 is not None else None,
                'roi_percent': round(pred.roi_percent, 2) if pred.roi_percent is not None else None,
                'probabilities': {
                    'home': round(pred.probability_home * 100, 1),
                    'draw': round(pred.probability_draw * 100, 1),
                    'away': round(pred.probability_away * 100, 1)
                },
                'model_count': pred.model_count,
                'consensus': round(pred.consensus * 100, 1) if pred.consensus else None,
                'variance': round(pred.variance, 2) if pred.variance else None,
                'prediction_logged_at': pred.prediction_logged_at.isoformat(),
                'result_logged_at': pred.result_logged_at.isoformat() if pred.result_logged_at else None,
                'is_completed': pred.actual_outcome is not None
            }
            results.append(result)
        
        # Calculate summary statistics
        completed = [r for r in results if r['is_completed']]
        correct = [r for r in completed if r['was_correct']]
        total_pl = sum([r['profit_loss_10'] for r in completed if r['profit_loss_10'] is not None])
        avg_roi = sum([r['roi_percent'] for r in completed if r['roi_percent'] is not None]) / len(completed) if completed else 0
        
        summary = {
            'total_recommended': len(results),
            'completed': len(completed),
            'pending': len(results) - len(completed),
            'correct': len(correct),
            'incorrect': len(completed) - len(correct),
            'accuracy': round((len(correct) / len(completed) * 100), 1) if completed else None,
            'total_profit_loss': round(total_pl, 2) if total_pl else 0,
            'average_roi': round(avg_roi, 2) if avg_roi else None
        }
        
        return JsonResponse({
            'success': True,
            'data': results,
            'summary': summary,
            'count': len(results),
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e),
            'data': [],
            'count': 0
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def log_recommendations(request):
    """
    Log recommendations from the home page API to PredictionLog database.
    
    POST /api/log-recommendations/
    Body: {"recommendations": [{...}, {...}]}
    """
    try:
        import json
        from datetime import datetime
        data = json.loads(request.body)
        recommendations = data.get('recommendations', [])
        
        if not recommendations:
            return JsonResponse({
                'success': False,
                'error': 'recommendations array is required'
            }, status=400)
        
        logged_count = 0
        updated_count = 0
        
        for rec in recommendations:
            fixture_id = rec.get('fixture_id')
            if not fixture_id:
                continue
            
            # Parse kickoff date
            kickoff_str = rec.get('kickoff')
            try:
                if isinstance(kickoff_str, str):
                    # Parse ISO format
                    kickoff = datetime.fromisoformat(kickoff_str.replace('Z', '+00:00'))
                else:
                    kickoff = timezone.now()
            except:
                kickoff = timezone.now()
            
            # Normalize data formats
            probabilities = rec.get('probabilities', {})
            prob_home = probabilities.get('home', 0)
            prob_draw = probabilities.get('draw', 0)
            prob_away = probabilities.get('away', 0)
            
            # Normalize confidence
            confidence = rec.get('confidence', 0)
            if confidence > 1:
                confidence = confidence / 100
            
            # Normalize EV
            expected_value = rec.get('expected_value') or rec.get('ev')
            if expected_value is not None and expected_value > 1:
                expected_value = expected_value / 100
            
            # Normalize probabilities
            if prob_home > 1:
                prob_home = prob_home / 100
            if prob_draw > 1:
                prob_draw = prob_draw / 100
            if prob_away > 1:
                prob_away = prob_away / 100
            
            odds_data = rec.get('odds_data', {})
            predicted_outcome = rec.get('predicted_outcome', 'Home').lower()
            
            # Check if exists
            existing = PredictionLog.objects.filter(fixture_id=fixture_id).first()
            
            prediction_data = {
                'home_team': rec.get('home_team', 'Unknown'),
                'away_team': rec.get('away_team', 'Unknown'),
                'league': rec.get('league', 'Unknown'),
                'league_id': None,
                'kickoff': kickoff,
                'predicted_outcome': predicted_outcome,
                'confidence': confidence,
                'probability_home': prob_home,
                'probability_draw': prob_draw,
                'probability_away': prob_away,
                'odds_home': odds_data.get('home'),
                'odds_draw': odds_data.get('draw'),
                'odds_away': odds_data.get('away'),
                'bookmaker': odds_data.get('bookmaker'),
                'expected_value': expected_value,
                'model_count': rec.get('ensemble_info', {}).get('model_count', 0),
                'consensus': rec.get('ensemble_info', {}).get('consensus'),
                'variance': rec.get('ensemble_info', {}).get('variance'),
                'ensemble_strategy': rec.get('ensemble_info', {}).get('strategy', 'consensus_ensemble'),
                'recommendation_score': rec.get('revenue_vs_risk_score'),
                'is_recommended': True
            }
            
            if existing:
                # Update existing
                for key, value in prediction_data.items():
                    setattr(existing, key, value)
                existing.is_recommended = True
                existing.save()
                updated_count += 1
            else:
                # Create new
                PredictionLog.objects.create(fixture_id=fixture_id, **prediction_data)
                logged_count += 1
        
        return JsonResponse({
            'success': True,
            'logged_count': logged_count,
            'updated_count': updated_count,
            'total': logged_count + updated_count,
            'message': f'Logged {logged_count} new, updated {updated_count} existing recommendations'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def mark_recommended_by_fixture_ids(request):
    """
    Mark predictions as recommended based on fixture_ids from the home page recommendations API.
    
    POST /api/mark-recommended/
    Body: {"fixture_ids": [123, 456, 789]}
    """
    try:
        import json
        data = json.loads(request.body)
        fixture_ids = data.get('fixture_ids', [])
        
        if not fixture_ids:
            return JsonResponse({
                'success': False,
                'error': 'fixture_ids array is required'
            }, status=400)
        
        # Check how many of these fixture_ids exist in the database
        existing_fixtures = PredictionLog.objects.filter(fixture_id__in=fixture_ids).count()
        
        if existing_fixtures == 0:
            # If none exist, don't unmark anything - just return success
            return JsonResponse({
                'success': True,
                'marked_count': 0,
                'fixture_ids': fixture_ids,
                'existing_count': 0,
                'message': 'No matching predictions found in database - skipping update'
            })
        
        # Only unmark if we have matching predictions to mark
        # This prevents unmarking everything when fixture_ids don't match
        PredictionLog.objects.filter(is_recommended=True).update(is_recommended=False)
        
        # Mark the new ones as recommended
        updated = PredictionLog.objects.filter(
            fixture_id__in=fixture_ids
        ).update(is_recommended=True)
        
        return JsonResponse({
            'success': True,
            'marked_count': updated,
            'fixture_ids': fixture_ids,
            'existing_count': existing_fixtures,
            'message': f'Marked {updated} predictions as recommended'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def search_fixtures(request):
    """
    Search fixtures by team names or league
    
    GET /api/search/
    Query params:
    - q: Search query
    - league (optional): Filter by league
    """
    try:
        query = request.GET.get('q', '').strip()
        league = request.GET.get('league', '').strip()
        
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Search query is required'
            }, status=400)
        
        # Build queryset
        now = timezone.now()
        end_date = now + timedelta(days=14)
        
        queryset = PredictionLog.objects.filter(
            kickoff__gte=now,
            kickoff__lte=end_date
        ).filter(
            home_team__icontains=query
        ) | PredictionLog.objects.filter(
            kickoff__gte=now,
            kickoff__lte=end_date
        ).filter(
            away_team__icontains=query
        )
        
        # Filter by league if specified
        if league:
            queryset = queryset.filter(league__icontains=league)
        
        # Order by kickoff time
        fixtures = queryset.order_by('kickoff')[:20]
        
        # Convert to frontend format
        results = []
        for pred in fixtures:
            result = {
                'fixture_id': pred.fixture_id,
                'home_team': pred.home_team,
                'away_team': pred.away_team,
                'league': pred.league,
                'kickoff': pred.kickoff.isoformat(),
                'predicted_outcome': pred.predicted_outcome.capitalize() if pred.predicted_outcome else 'Home',
                'confidence': pred.confidence,
                'expected_value': pred.expected_value
            }
            results.append(result)
        
        return JsonResponse({
            'success': True,
            'results': results,  # Frontend expects 'results' not 'data'
            'data': results,     # Keep both for compatibility
            'count': len(results),
            'query': query
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'data': [],
            'count': 0
        }, status=500)
