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
import os
import requests

from .models import PredictionLog, UserBankroll
from .bankroll_utils import calculate_stake_amount


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
    - session_id (optional): Include personalized stake recommendations
    """
    try:
        # Get query parameters
        league = request.GET.get('league', '').strip()
        limit = int(request.GET.get('limit', 10))
        session_id = request.GET.get('session_id', '').strip()
        
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
        
        # Check if user has bankroll for stake recommendations
        user_bankroll = None
        if session_id:
            try:
                user_bankroll = UserBankroll.objects.get(session_id=session_id)
                user_bankroll.check_and_reset_limits()
            except UserBankroll.DoesNotExist:
                pass
        
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
            
            # Add stake recommendation if user has bankroll
            if user_bankroll:
                try:
                    # Get odds for predicted outcome
                    predicted_odds = None
                    if pred.predicted_outcome.lower() == 'home':
                        predicted_odds = pred.odds_home
                        win_probability = pred.probability_home
                    elif pred.predicted_outcome.lower() == 'draw':
                        predicted_odds = pred.odds_draw
                        win_probability = pred.probability_draw
                    elif pred.predicted_outcome.lower() == 'away':
                        predicted_odds = pred.odds_away
                        win_probability = pred.probability_away
                    
                    if predicted_odds and win_probability:
                        stake_calc = calculate_stake_amount(
                            bankroll=user_bankroll.current_bankroll,
                            strategy=user_bankroll.staking_strategy,
                            win_probability=win_probability,
                            odds=predicted_odds,
                            confidence=pred.confidence * 100,  # Convert to percentage
                            fixed_amount=user_bankroll.fixed_stake_amount,
                            fixed_percentage=user_bankroll.fixed_stake_percentage,
                            max_stake_percentage=user_bankroll.max_stake_percentage
                        )
                        
                        recommendation['stake_recommendation'] = {
                            'recommended_stake': float(stake_calc['recommended_stake']),
                            'stake_percentage': stake_calc['stake_percentage'],
                            'currency': user_bankroll.currency,
                            'strategy': stake_calc['strategy'],
                            'risk_level': stake_calc['risk_level'],
                            'risk_explanation': stake_calc['risk_explanation'],
                            'warnings': stake_calc['warnings']
                        }
                except Exception as e:
                    # Don't fail the whole request if stake calc fails
                    recommendation['stake_recommendation'] = {
                        'error': str(e)
                    }
            
            recommendations.append(recommendation)
        
        response_data = {
            'success': True,
            'recommendations': recommendations,  # Frontend expects this field
            'data': recommendations,  # Keep for backwards compatibility
            'count': len(recommendations),
            'total': len(recommendations),  # Frontend also checks this
            'message': f'Found {len(recommendations)} recommendations'
        }
        
        # Add bankroll summary if available
        if user_bankroll:
            response_data['bankroll_summary'] = {
                'current_bankroll': float(user_bankroll.current_bankroll),
                'currency': user_bankroll.currency,
                'is_daily_limit_reached': user_bankroll.is_daily_limit_reached,
                'is_weekly_limit_reached': user_bankroll.is_weekly_limit_reached,
                'risk_profile': user_bankroll.risk_profile
            }
        
        return JsonResponse(response_data)
        
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
    
    GET /api/fixture/{fixture_id}/?session_id=xxx (optional)
    """
    try:
        prediction = PredictionLog.objects.get(fixture_id=fixture_id)
        session_id = request.GET.get('session_id', '').strip()
        
        # Check if user has bankroll for stake recommendations
        user_bankroll = None
        if session_id:
            try:
                user_bankroll = UserBankroll.objects.get(session_id=session_id)
                user_bankroll.check_and_reset_limits()
            except UserBankroll.DoesNotExist:
                pass
        
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
        
        # Add stake recommendation if user has bankroll
        if user_bankroll:
            try:
                # Get odds for predicted outcome
                predicted_odds = None
                if prediction.predicted_outcome.lower() == 'home':
                    predicted_odds = prediction.odds_home
                    win_probability = prediction.probability_home
                elif prediction.predicted_outcome.lower() == 'draw':
                    predicted_odds = prediction.odds_draw
                    win_probability = prediction.probability_draw
                elif prediction.predicted_outcome.lower() == 'away':
                    predicted_odds = prediction.odds_away
                    win_probability = prediction.probability_away
                
                if predicted_odds and win_probability:
                    stake_calc = calculate_stake_amount(
                        bankroll=user_bankroll.current_bankroll,
                        strategy=user_bankroll.staking_strategy,
                        win_probability=win_probability,
                        odds=predicted_odds,
                        confidence=prediction.confidence * 100,
                        fixed_amount=user_bankroll.fixed_stake_amount,
                        fixed_percentage=user_bankroll.fixed_stake_percentage,
                        max_stake_percentage=user_bankroll.max_stake_percentage
                    )
                    
                    fixture_data['stake_recommendation'] = {
                        'recommended_stake': float(stake_calc['recommended_stake']),
                        'stake_percentage': stake_calc['stake_percentage'],
                        'currency': user_bankroll.currency,
                        'strategy': stake_calc['strategy'],
                        'risk_level': stake_calc['risk_level'],
                        'risk_explanation': stake_calc['risk_explanation'],
                        'warnings': stake_calc['warnings']
                    }
            except Exception as e:
                # Don't fail the whole request if stake calc fails
                fixture_data['stake_recommendation'] = {'error': str(e)}
        
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
    Search fixtures by team names or league - QUERIES SPORTMONKS API DIRECTLY

    GET /api/search/
    Query params:
    - q: Search query (team name)
    - league (optional): Filter by league ID
    - limit (optional): Limit results (default: 20)
    """
    try:
        query = request.GET.get('q', '').strip()
        league_filter = request.GET.get('league', '').strip()
        limit = int(request.GET.get('limit', 20))

        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Search query is required'
            }, status=400)

        # Get SportMonks API token
        api_token = os.getenv('SPORTMONKS_API_TOKEN') or os.getenv('SPORTMONKS_TOKEN')
        if not api_token:
            # Fallback to database search if no API token
            return search_fixtures_from_database(request, query, league_filter, limit)

        # Search SportMonks API for upcoming fixtures
        print(f"🔍 Searching SportMonks for: {query}")

        # Calculate date range (next 14 days)
        now = timezone.now()
        start_date = now.strftime("%Y-%m-%d")
        end_date = (now + timedelta(days=14)).strftime("%Y-%m-%d")

        # Supported league IDs (27 leagues)
        supported_leagues = [8, 9, 24, 27, 72, 82, 181, 208, 244, 271, 301, 384, 387,
                            390, 444, 453, 462, 486, 501, 564, 567, 570, 573, 591, 600, 609, 1371]

        # Build API request using the /between endpoint for date filtering
        url = f"https://api.sportmonks.com/v3/football/fixtures/between/{start_date}/{end_date}"
        params = {
            'api_token': api_token,
            'include': 'participants;league;predictions',
            'filters': f'fixtureLeagues:{",".join(map(str, supported_leagues))}',
            'per_page': '200'  # Get more results to filter by team name
        }

        print(f"📅 Date range: {start_date} to {end_date}")
        print(f"🌐 SportMonks API URL: {url}")
        print(f"📋 Filters: {params['filters']}")

        try:
            response = requests.get(url, params=params, timeout=10)
            print(f"📡 SportMonks response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                fixtures_data = data.get('data', [])

                print(f"📊 SportMonks returned {len(fixtures_data)} total fixtures")

                # Debug: Show first few fixtures to see what we're getting
                if fixtures_data and len(fixtures_data) > 0:
                    print(f"🔍 Sample fixtures (showing first 3):")
                    for i, f in enumerate(fixtures_data[:3]):
                        parts = f.get('participants', [])
                        home = next((p for p in parts if p.get('meta', {}).get('location') == 'home'), {}).get('name', '?')
                        away = next((p for p in parts if p.get('meta', {}).get('location') == 'away'), {}).get('name', '?')
                        print(f"  {i+1}. {home} vs {away} - {f.get('starting_at', '?')}")

                # Filter fixtures by team name (case-insensitive)
                matching_fixtures = []
                query_lower = query.lower()

                for fixture in fixtures_data:
                    participants = fixture.get('participants', [])
                    if len(participants) < 2:
                        continue

                    home_team = next((p for p in participants if p.get('meta', {}).get('location') == 'home'), None)
                    away_team = next((p for p in participants if p.get('meta', {}).get('location') == 'away'), None)

                    if not home_team or not away_team:
                        continue

                    home_name = home_team.get('name', '')
                    away_name = away_team.get('name', '')
                    league_name = fixture.get('league', {}).get('name', 'Unknown')
                    league_id = fixture.get('league', {}).get('id', 0)

                    # Check if team name matches
                    if query_lower in home_name.lower() or query_lower in away_name.lower():
                        # Apply league filter if specified
                        if league_filter and str(league_id) != league_filter:
                            continue

                        # Check if fixture has predictions
                        predictions = fixture.get('predictions', [])
                        has_predictions = len([p for p in predictions if p.get('type_id') in [233, 237, 238]]) > 0

                        print(f"  ✓ Match found: {home_name} vs {away_name} ({league_name}) - {fixture.get('starting_at', '')}")

                        matching_fixtures.append({
                            'fixture_id': fixture.get('id'),
                            'home_team': home_name,
                            'away_team': away_name,
                            'league': league_name,
                            'kickoff': fixture.get('starting_at', ''),
                            'has_predictions': has_predictions,
                            'has_odds': False  # We don't fetch odds in search to keep it fast
                        })

                # Sort by kickoff time and limit
                matching_fixtures.sort(key=lambda x: x['kickoff'])
                matching_fixtures = matching_fixtures[:limit]

                print(f"✅ Found {len(matching_fixtures)} matching fixtures")

                return JsonResponse({
                    'success': True,
                    'results': matching_fixtures,
                    'data': matching_fixtures,
                    'count': len(matching_fixtures),
                    'query': query,
                    'message': f'Found {len(matching_fixtures)} upcoming fixtures'
                })

            else:
                print(f"⚠️ SportMonks API error: {response.status_code}")
                # Fallback to database search
                return search_fixtures_from_database(request, query, league_filter, limit)

        except requests.exceptions.Timeout:
            print("⏱️ SportMonks API timeout - falling back to database search")
            return search_fixtures_from_database(request, query, league_filter, limit)
        except Exception as e:
            print(f"❌ SportMonks API error: {str(e)}")
            return search_fixtures_from_database(request, query, league_filter, limit)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'results': [],
            'data': [],
            'count': 0
        }, status=500)


def search_fixtures_from_database(request, query, league_filter, limit):
    """Fallback: Search fixtures already in database"""
    try:
        from django.db.models import Q

        print("⚠️ Using database fallback search")

        # Build queryset
        now = timezone.now()
        end_date = now + timedelta(days=14)

        print(f"📅 Searching database for fixtures between {now} and {end_date}")

        # Use Q objects for proper OR logic with date filtering
        queryset = PredictionLog.objects.filter(
            kickoff__gte=now,
            kickoff__lte=end_date
        ).filter(
            Q(home_team__icontains=query) | Q(away_team__icontains=query)
        )

        # Filter by league if specified
        if league_filter:
            queryset = queryset.filter(league__icontains=league_filter)

        # Order by kickoff time
        fixtures = queryset.order_by('kickoff')[:limit]

        print(f"📊 Database search found {len(fixtures)} fixtures")

        # Convert to frontend format
        results = []
        for pred in fixtures:
            result = {
                'fixture_id': pred.fixture_id,
                'home_team': pred.home_team,
                'away_team': pred.away_team,
                'league': pred.league,
                'kickoff': pred.kickoff.isoformat(),
                'has_predictions': True,  # All DB entries have predictions
                'has_odds': bool(pred.odds_home or pred.odds_draw or pred.odds_away)
            }
            results.append(result)

        return JsonResponse({
            'success': True,
            'results': results,
            'data': results,
            'count': len(results),
            'query': query,
            'message': f'Found {len(results)} fixtures (database search)'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'results': [],
            'data': [],
            'count': 0
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def update_fixture_results(request):
    """
    Update fixture results for pending predictions from SportMonks API.
    
    POST /api/update-fixture-results/
    """
    try:
        # Get SportMonks API token
        api_token = os.getenv('SPORTMONKS_API_TOKEN') or os.getenv('SPORTMONKS_TOKEN')
        if not api_token:
            print("WARNING: SportMonks API token not found in environment")
            print("Please ensure SPORTMONKS_API_TOKEN is set in .env file")
            # Don't fail - just skip the update
            return JsonResponse({
                'success': True,
                'updated_count': 0,
                'skipped_count': 0,
                'error_count': 0,
                'total_checked': 0,
                'message': 'Skipped - API token not configured'
            })
        
        # Get pending predictions from last 7 days
        cutoff_date = timezone.now() - timedelta(days=7)
        pending_predictions = PredictionLog.objects.filter(
            kickoff__gte=cutoff_date,
            kickoff__lte=timezone.now(),
            actual_outcome__isnull=True
        ).order_by('kickoff')[:50]  # Limit to 50 to avoid rate limits
        
        print(f"\n{'='*60}")
        print(f"🔄 Updating fixture results")
        print(f"📅 Checking fixtures from last 7 days")
        print(f"📊 Found {pending_predictions.count()} pending predictions")
        print(f"{'='*60}\n")
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        updated_fixtures = []
        error_details = []
        
        for i, prediction in enumerate(pending_predictions, 1):
            try:
                print(f"[{i}/{pending_predictions.count()}] Checking: {prediction.home_team} vs {prediction.away_team} (ID: {prediction.fixture_id})")
                
                # Fetch fixture data from SportMonks
                url = f"https://api.sportmonks.com/v3/football/fixtures/{prediction.fixture_id}"
                params = {
                    'api_token': api_token,
                    'include': 'participants;scores;state',
                    'timezone': 'UTC'
                }
                
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                fixture_data = data.get('data')
                
                if not fixture_data:
                    print(f"  ⚠️ No fixture data returned")
                    skipped_count += 1
                    continue
                
                # Get match status
                state = fixture_data.get('state', {})
                match_status = state.get('short_name', 'UNKNOWN')
                
                print(f"  Status: {match_status}")
                
                # Only process finished matches
                if match_status not in ['FT', 'AET', 'APEN']:
                    print(f"  ⏸️ Skipped - Match not finished (status: {match_status})")
                    skipped_count += 1
                    continue
                
                # Get scores - SportMonks API v3 format
                scores = fixture_data.get('scores', [])
                if not scores:
                    print(f"No scores found for fixture {prediction.fixture_id}")
                    skipped_count += 1
                    continue
                
                # Find full-time scores
                home_score = None
                away_score = None
                
                # Get participants mapping
                participants = fixture_data.get('participants', [])
                home_participant_id = None
                away_participant_id = None
                
                for participant in participants:
                    location = participant.get('meta', {}).get('location')
                    if location == 'home':
                        home_participant_id = participant.get('id')
                    elif location == 'away':
                        away_participant_id = participant.get('id')
                
                print(f"Fixture {prediction.fixture_id}: home_id={home_participant_id}, away_id={away_participant_id}")
                
                # Look for final/current scores
                for score in scores:
                    description = (score.get('description') or '').upper()
                    type_id = score.get('type_id')
                    participant_id = score.get('participant_id')
                    
                    # Check if this is a final score (CURRENT, FT, or type_id 1525)
                    if description in ['CURRENT', 'FT', 'FULLTIME', 'FINAL'] or type_id == 1525:
                        score_data = score.get('score', {})
                        goals = score_data.get('goals', 0)
                        
                        # Try different score formats
                        if goals is None:
                            goals = score_data.get('participant', 0)
                        if goals is None:
                            goals = score_data.get('value', 0)
                        
                        if participant_id == home_participant_id:
                            home_score = int(goals) if goals is not None else None
                            print(f"  Found home score: {home_score}")
                        elif participant_id == away_participant_id:
                            away_score = int(goals) if goals is not None else None
                            print(f"  Found away score: {away_score}")
                
                if home_score is None or away_score is None:
                    print(f"Could not extract scores for fixture {prediction.fixture_id}: home={home_score}, away={away_score}")
                    print(f"Scores data: {scores}")
                    skipped_count += 1
                    continue
                
                # Determine outcome
                if home_score > away_score:
                    outcome = 'home'
                elif away_score > home_score:
                    outcome = 'away'
                else:
                    outcome = 'draw'
                
                # Update prediction
                prediction.actual_outcome = outcome
                prediction.actual_score_home = home_score
                prediction.actual_score_away = away_score
                prediction.match_status = match_status
                
                # Calculate performance
                prediction.calculate_performance()
                prediction.save()
                
                updated_count += 1
                updated_fixtures.append({
                    'fixture_id': prediction.fixture_id,
                    'match': f"{prediction.home_team} vs {prediction.away_team}",
                    'score': f"{home_score}-{away_score}",
                    'predicted': prediction.predicted_outcome,
                    'actual': outcome,
                    'correct': prediction.was_correct
                })
                
                print(f"✅ Updated: {prediction.home_team} vs {prediction.away_team} ({home_score}-{away_score})")
                print(f"   Predicted: {prediction.predicted_outcome} | Actual: {outcome} | {'✓ CORRECT' if prediction.was_correct else '✗ INCORRECT'}\n")
                
            except Exception as e:
                error_count += 1
                error_msg = str(e)
                error_details.append({
                    'fixture_id': prediction.fixture_id,
                    'match': f"{prediction.home_team} vs {prediction.away_team}",
                    'error': error_msg
                })
                print(f"❌ Error updating fixture {prediction.fixture_id} ({prediction.home_team} vs {prediction.away_team}): {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"\n{'='*60}")
        print(f"✅ Update complete!")
        print(f"   Updated: {updated_count}")
        print(f"   Skipped: {skipped_count} (not finished yet)")
        print(f"   Errors: {error_count}")
        print(f"{'='*60}\n")
        
        return JsonResponse({
            'success': True,
            'updated_count': updated_count,
            'skipped_count': skipped_count,
            'error_count': error_count,
            'total_checked': pending_predictions.count(),
            'message': f'Updated {updated_count} fixture results',
            'updated_fixtures': updated_fixtures[:10],  # Return first 10 for debugging
            'errors': error_details[:5] if error_details else []  # Return first 5 errors
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'updated_count': 0
        }, status=500)
