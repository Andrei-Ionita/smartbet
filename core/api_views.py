"""
Simple API views for SmartBet recommendations
Works with the current PredictionLog model structure
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import datetime, timedelta, timezone as dt_timezone
import hashlib
import hmac
import json
import logging
import os
import uuid
import requests
from django.db.models import Q

from django.db import transaction
from .models import (EmailSubscriber, IngestRequest, MarketingEvent,
                     PredictionLog, PredictionSnapshot, UserBankroll)
from .bankroll_utils import calculate_stake_amount
from .services.marketing import MarketingSyncError, sync_marketing_profile
from .services import (ingest_auth, public_universe, recommendation_ingest,
                       snapshot_recording)
from .services.redaction import redact, redact_exception

logger = logging.getLogger(__name__)


# Phase 2a: hard-blocks at the write boundary. The primary filter lives in the
# Next.js recommendation engine; this layer is defense-in-depth so a stale
# frontend (or a future caller bypassing the engine) can't poison PredictionLog.
# Source of truth for the same list: smartbet-frontend/app/api/recommendations/
# route.ts BLACKLISTED_LEAGUE_IDS (181/462/600/573/444).
PHASE_2A_BLACKLISTED_LEAGUES = {
    'Admiral Bundesliga',
    'Liga Portugal',
    'Super Lig',
    'Allsvenskan',
    'Eliteserien',
}
PHASE_2A_BLOCKED_OUTCOMES = ('under 2.5',)
# Phase 2b: hard EV cap. Tighter than the model's own EV_PLAUSIBLE_MAX (0.50)
# because backtest shows picks with EV in (0.20, 0.50] still underperform —
# they're the trap-zone the V2 enhancer was originally trying to address.
PHASE_2B_MAX_EV = 0.20
# Phase 2c (2026-05-25): soft watchlist. Leagues here must clear stricter
# confidence + EV thresholds than the baseline filter. Reasoning: persistent
# underperformance but sample too thin to blacklist. Revisit 2026-06-08.
#   Premier League: -52% yield weekend (n=4), -27% cumulative since Phase 2.
# Source-of-truth shared with smartbet-frontend WATCHLIST_LEAGUE_THRESHOLDS.
PHASE_2C_WATCHLIST_LEAGUES = {
    'Premier League': {'min_confidence': 0.65, 'min_ev': 0.12},
}


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
        ).filter(
            # Two-Track Filtering:
            # 1. Safe Bets: Confidence >= 60%
            # 2. Value Bets: Confidence >= 35% AND EV >= 10%
            Q(confidence__gte=0.60) | 
            Q(confidence__gte=0.35, expected_value__gte=0.10)
        ).order_by('-expected_value', '-confidence')  # Prioritize Value now
        
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
                'raw_expected_value': pred.raw_expected_value,
                'odds': pred.odds,
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
                
                # Two-Track System Metadata
                'bet_type': 'safe' if pred.confidence >= 0.60 else 'value',
                'bet_label': '🛡️ Safe Pick' if pred.confidence >= 0.60 else '💎 Value Bet',
                'recommendation_color': 'green' if pred.confidence >= 0.60 else 'blue',
                
                'ensemble_info': {
                    'model_count': pred.model_count,
                    'consensus': pred.consensus,
                    'variance': pred.variance,
                    'strategy': pred.ensemble_strategy
                },
                
                # Teams Data (Form)
                'teams_data': {
                    'home': {
                        'form': pred.home_team_form or '?????'
                    },
                    'away': {
                        'form': pred.away_team_form or '?????'
                    }
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
                        'error': redact_exception(e)
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
            'error': redact_exception(e),
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
                fixture_data['stake_recommendation'] = {'error': redact_exception(e)}
        
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
            'error': redact_exception(e)
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
        include_pending = request.GET.get('include_pending', 'true').lower() == 'true'
        
        # Get ALL recommended predictions - no limit!
        # This ensures complete transparency and no "missing" data.
        # Exclude archived (SportMonks no longer has the fixture) — these are
        # permanently un-settle-able and shouldn't appear in user-facing stats.
        queryset = PredictionLog.objects.filter(
            is_recommended=True
        ).exclude(
            match_status='archived'
        ).defer('notes', 'home_team_form', 'away_team_form').order_by('-kickoff')
        
        # If not including pending, only show completed matches
        if not include_pending:
            queryset = queryset.filter(actual_outcome__isnull=False)
        
        predictions = list(queryset)
        
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
                'raw_expected_value': round(pred.raw_expected_value * 100, 2) if pred.raw_expected_value and abs(pred.raw_expected_value) < 1 else round(pred.raw_expected_value, 2) if pred.raw_expected_value is not None else None,
                'odds': pred.odds,
                'odds_home': pred.odds_home,
                'odds_draw': pred.odds_draw,
                'odds_away': pred.odds_away,
                'bookmaker': pred.bookmaker,
                'is_audit_excluded': pred.is_audit_excluded,
                'pricing_integrity_status': pred.pricing_integrity_status,
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
                'is_completed': pred.actual_outcome is not None,
                # Multi-Market Support
                'market_type': getattr(pred, 'market_type', '1x2') or '1x2',
                'market_score': getattr(pred, 'market_score', None)
            }
            results.append(result)
        
        # Calculate summary statistics.
        # Audit-excluded rows are returned in `data` (so the table can render them with a
        # "excluded — see why" badge) but are kept OUT of all aggregate metrics. This is the
        # whole point of the quarantine flag — public stats reflect only data we trust.
        completed = [r for r in results if r['is_completed'] and not r.get('is_audit_excluded')]
        quarantined = [r for r in results if r['is_completed'] and r.get('is_audit_excluded')]
        correct = [r for r in completed if r['was_correct']]

        # 2026-07-29 audit: every PRICE-dependent figure must denominate on
        # pricing-verified rows only. Legacy rows were priced by substring
        # matching across seven SportMonks markets, so their odds — and
        # therefore any P/L, ROI or implied-probability figure derived from
        # them — cannot be verified. Accuracy counts are not price-dependent
        # and remain on `completed`, flagged as provisional in the payload.
        priced = [
            r for r in completed
            if r.get('pricing_integrity_status') == PredictionLog.PRICING_VERIFIED
        ]
        total_pl = sum([r['profit_loss_10'] for r in priced if r['profit_loss_10'] is not None])
        avg_roi = sum([r['roi_percent'] for r in priced if r['roi_percent'] is not None]) / len(priced) if priced else 0

        # Per-Market Accuracy Breakdown (also excludes quarantined rows)
        market_types = ['1x2', 'btts', 'over_under_2.5', 'double_chance']
        by_market = {}
        for market in market_types:
            market_completed = [r for r in completed if r.get('market_type') == market]
            market_correct = [r for r in market_completed if r['was_correct']]
            market_priced = [r for r in priced if r.get('market_type') == market]
            by_market[market] = {
                'total': len(market_completed),
                'correct': len(market_correct),
                'accuracy': round((len(market_correct) / len(market_completed) * 100), 1) if market_completed else None,
                # Price-dependent -> verified rows only.
                'profit_loss': round(sum([r['profit_loss_10'] for r in market_priced if r['profit_loss_10'] is not None]), 2),
                'priced_sample': len(market_priced),
            }
        
        # ============= BASELINE COMPARISON =============
        # "Implied probability baseline": what hit-rate would we expect if the bookmaker
        # priced the predicted outcome perfectly? Always use `r['odds']` (the actual bet-time
        # odds for the predicted outcome — works for any market). Fall back to per-outcome
        # 1X2 columns only for legacy rows where `odds` is null (pre-Stage-A data).
        # Price-derived: verified rows only.
        implied_probabilities = []
        for r in priced:
            odds = r.get('odds')
            if not odds:
                outcome = (r.get('predicted_outcome_raw') or r.get('predicted_outcome', '')).lower()
                if outcome == 'home':
                    odds = r.get('odds_home')
                elif outcome == 'draw':
                    odds = r.get('odds_draw')
                elif outcome == 'away':
                    odds = r.get('odds_away')
                # For O/U / BTTS / DC legacy rows we don't have bet-time odds at all —
                # back-calculate from EV + confidence if possible.
                elif r.get('expected_value') is not None and r.get('confidence'):
                    conf_dec = r['confidence'] / 100.0 if r['confidence'] > 1 else r['confidence']
                    ev_dec = r['expected_value'] / 100.0 if abs(r['expected_value']) > 1 else r['expected_value']
                    if conf_dec > 0:
                        odds = (ev_dec + 1) / conf_dec

            if odds and odds > 1:
                # Implied probability = 1 / odds (simplified, ignoring bookmaker margin)
                implied_probabilities.append(1 / odds)
        
        # Calculate baseline
        if implied_probabilities:
            avg_implied_prob = sum(implied_probabilities) / len(implied_probabilities)
            implied_baseline = round(avg_implied_prob * 100, 1)  # As percentage
        else:
            implied_baseline = None
        
        # Calculate edge over baseline
        actual_accuracy = round((len(correct) / len(completed) * 100), 1) if completed else None
        edge_vs_market = round(actual_accuracy - implied_baseline, 1) if actual_accuracy and implied_baseline else None
        
        # Yield = profit per unit staked. With flat $10 stakes, yield = total_pl / (n * 10) * 100.
        # This is the headline number bettors actually compare services on.
        yield_percent = round(total_pl / (len(completed) * 10) * 100, 2) if completed else None

        # "pending" excludes quarantined-but-incomplete rows on principle; the
        # quarantined_count surfaces them separately for transparency.
        pending_count = sum(1 for r in results if not r['is_completed'] and not r.get('is_audit_excluded'))

        # ── Public performance: resolved, verified PublishedClaims ONLY ──────
        # Headline figures must never mix the verified public record with
        # legacy tracked predictions. PredictionLog rows were mutable across
        # pipeline re-runs, so a stored predicted_outcome cannot be proven
        # identical to the one generated at its timestamp. Legacy data stays
        # below under `legacy_diagnostics`, explicitly labelled.
        from core.services.accuracy_calculator import AccuracyCalculator
        _calc = AccuracyCalculator()
        _public_acc = _calc.get_overall_accuracy()['overall']
        _public_roi = _calc.get_roi_simulation()
        _has_verified = _public_roi['total_bets'] > 0

        verified_public = {
            'has_verified_results': _has_verified,
            'total': _public_roi['total_bets'],
            'correct': _public_acc['correct_predictions'],
            'incorrect': _public_acc['incorrect_predictions'],
            # None (not 0) at zero sample so no surface can render 0% / +0%.
            'accuracy': _public_acc['accuracy_percent'] if _has_verified else None,
            'total_profit_loss': _public_roi['total_profit_loss'] if _has_verified else None,
            'roi_percent': _public_roi['roi_percent'] if _has_verified else None,
        }

        summary = {
            # THE public performance block. Everything else on this endpoint is
            # internal diagnostics.
            'verified_public': verified_public,
            'legacy_diagnostics': {
                'label': 'legacy / unverified — internal diagnostics only',
                'note': (
                    'Predictions from before the verified pricing cutoff. Their '
                    'original prices, and in some cases their original prediction '
                    'state, cannot be reconstructed to the current verification '
                    'standard. Not public performance.'
                ),
                'completed': len(completed),
                'correct': len(correct),
                'incorrect': len(completed) - len(correct),
                'accuracy': round((len(correct) / len(completed) * 100), 1) if completed else None,
                'total_profit_loss': round(total_pl, 2) if total_pl else 0,
                'average_roi': round(avg_roi, 2) if avg_roi else None,
                'by_market': by_market,
            },
            'total_recommended': len(results),
            'completed': len(completed),
            'pending': pending_count,
            'quarantined': len(quarantined),
            'yield_percent': yield_percent,
            # NEW: Baseline comparison metrics
            'implied_baseline': implied_baseline,  # Expected accuracy based on odds
            'edge_vs_market': edge_vs_market,  # Our accuracy minus baseline
            'baseline_comparison': {
                'our_accuracy': actual_accuracy,
                'market_implied': implied_baseline,
                'edge': edge_vs_market,
                'sample_size': len(implied_probabilities),
                'explanation': f"Our model achieves {actual_accuracy}% accuracy vs. {implied_baseline}% implied by odds (+{edge_vs_market}% edge)" if edge_vs_market and edge_vs_market > 0 else f"Our model achieves {actual_accuracy}% accuracy vs. {implied_baseline}% implied by odds ({edge_vs_market}% edge)" if edge_vs_market else None
            }
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
        traceback_str = traceback.format_exc()
        # A traceback frame can quote a URL or a header dict, so the traceback
        # is redacted too — not just the exception message.
        print(f"❌ ERROR in recommended-predictions: {redact_exception(e)}")
        print(redact(traceback_str))
        return JsonResponse({
            'success': False,
            'error': f"{redact_exception(e)} | {redact(traceback_str.splitlines()[-1])}",
            'data': [],
            'count': 0
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def log_recommendations(request):
    """
    Ingest one prediction run. SERVER-TO-SERVER ONLY.

    POST /api/log-recommendations/
    Body: {"recommendations": [{...}, {...}]}

    Until 2026-08-03 this was unauthenticated. It writes PredictionLog rows and
    appends immutable PredictionSnapshots, and because it keys on fixture_id and
    setattr()s the whole payload over any existing row, an anonymous caller
    could also OVERWRITE existing predictions — including their recorded odds —
    and craft `odds_provenance` that classified the result as `verified`, which
    put attacker-controlled rows into the publication queue.

    It now requires an HMAC-SHA256 signature (core.services.ingest_auth) and
    fails closed when no secret is configured. The scheduler does not come
    through here at all — it calls recommendation_ingest.ingest_recommendations
    in-process.
    """
    try:
        request_id = ingest_auth.verify(request)
    except ingest_auth.IngestAuthError as exc:
        # Reason to the log, never to the caller: which header was wrong and
        # which secret matched are both useful to an attacker.
        logger.warning('recommendation ingest rejected: %s', exc.reason)
        return JsonResponse({
            'code': 'recommendation_ingest_unauthorized',
            'detail': 'The recommendation ingest request was not authorized.',
        }, status=401)

    raw_body = request.body or b''
    if len(raw_body) > recommendation_ingest.MAX_BODY_BYTES:
        return JsonResponse({
            'code': 'recommendation_ingest_too_large',
            'detail': 'The recommendation ingest request was too large.',
        }, status=413)

    body_sha256 = hashlib.sha256(raw_body).hexdigest()

    # Replay ledger. Same id + same body is a legitimate retry and returns the
    # original result; same id + different body is a captured envelope being
    # reused and is refused.
    prior = IngestRequest.objects.filter(request_id=request_id).first()
    if prior is not None:
        if prior.body_sha256 == body_sha256:
            return JsonResponse(prior.response_payload or {'success': True})
        logger.warning(
            'recommendation ingest replay refused for request_id=%s', request_id
        )
        return JsonResponse({
            'code': 'recommendation_ingest_replayed',
            'detail': 'The recommendation ingest request was already processed.',
        }, status=409)

    try:
        payload = json.loads(raw_body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({
            'code': 'recommendation_ingest_invalid',
            'detail': 'The recommendation ingest body was not valid JSON.',
        }, status=400)

    recommendations = payload.get('recommendations') if isinstance(payload, dict) else None

    try:
        recommendation_ingest.validate_batch(recommendations)
    except recommendation_ingest.ValidationError as exc:
        # Row-level messages name the offending field only — no payload echo,
        # no internals.
        return JsonResponse({
            'code': 'recommendation_ingest_invalid',
            'detail': 'The recommendation ingest payload failed validation.',
            'errors': exc.errors[:50],
        }, status=400)

    # Derive the run id from the request id so a legitimate retry reuses it and
    # the snapshot uniqueness key dedupes instead of appending a second run.
    prediction_run_id = hashlib.sha256(request_id.encode('utf-8')).hexdigest()[:32]

    try:
        with transaction.atomic():
            result = recommendation_ingest.ingest_recommendations(
                recommendations,
                prediction_run_id=prediction_run_id,
                validate=False,
            )
            IngestRequest.objects.create(
                request_id=request_id,
                body_sha256=body_sha256,
                prediction_run_id=prediction_run_id,
                response_payload=result,
            )
    except Exception:
        # Correlate the traceback with the caller's request id; return nothing.
        logger.exception('recommendation ingest failed for request_id=%s', request_id)
        return JsonResponse({
            'code': 'recommendation_ingest_failed',
            'detail': 'The recommendation ingest could not be completed.',
        }, status=500)

    return JsonResponse(result)


# `mark_recommended_by_fixture_ids` was removed on 2026-08-03.
#
# An unauthenticated POST that set/cleared is_recommended across arbitrary
# fixture ids. It had no caller, and core/management/commands/
# restore_stripped_recommendations.py exists precisely because this endpoint
# once stripped is_recommended=True from live rows. The scheduler maintains
# those flags via the mark_recommended_predictions command.


# `fix_performance_metrics` was removed on 2026-08-03.
#
# An unauthenticated GET that iterated EVERY settled prediction and called
# calculate_performance() on each, rewriting profit_loss and roi_percent across
# the whole table. Described in its own docstring as "temporary". It had no
# caller anywhere in the codebase, and a GET must never perform operational
# writes. Recalculation belongs in a management command run deliberately.


@csrf_exempt
@require_http_methods(["GET"])
def search_fixtures(request):
    """
    Search fixtures by team names or league.

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

        api_token = os.getenv('SPORTMONKS_API_TOKEN') or os.getenv('SPORTMONKS_TOKEN')
        if not api_token:
            return search_fixtures_from_database(request, query, league_filter, limit)

        print(f"Searching SportMonks for: {query}")

        now = timezone.now()
        start_date = now.strftime("%Y-%m-%d")
        end_date = (now + timedelta(days=14)).strftime("%Y-%m-%d")
        supported_leagues = [8, 9, 24, 27, 72, 82, 181, 208, 244, 271, 301, 384, 387,
                            390, 444, 453, 462, 486, 501, 564, 567, 570, 573, 591, 600, 609, 1371]

        url = f"https://api.sportmonks.com/v3/football/fixtures/between/{start_date}/{end_date}"
        params = {
            'api_token': api_token,
            'include': 'participants;league;predictions',
            'filters': f'fixtureLeagues:{",".join(map(str, supported_leagues))}',
            'per_page': '200'
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                print(f"SportMonks API error: {response.status_code}")
                return search_fixtures_from_database(request, query, league_filter, limit)

            data = response.json()
            fixtures_data = data.get('data', [])
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

                if query_lower in home_name.lower() or query_lower in away_name.lower():
                    if league_filter and str(league_id) != league_filter:
                        continue

                    predictions = fixture.get('predictions', [])
                    has_predictions = len([p for p in predictions if p.get('type_id') in [233, 237, 238]]) > 0
                    matching_fixtures.append({
                        'fixture_id': fixture.get('id'),
                        'home_team': home_name,
                        'away_team': away_name,
                        'league': league_name,
                        'kickoff': fixture.get('starting_at', ''),
                        'has_predictions': has_predictions,
                        'has_odds': False
                    })

            matching_fixtures.sort(key=lambda x: x['kickoff'])
            matching_fixtures = matching_fixtures[:limit]

            return JsonResponse({
                'success': True,
                'results': matching_fixtures,
                'data': matching_fixtures,
                'count': len(matching_fixtures),
                'query': query,
                'message': f'Found {len(matching_fixtures)} upcoming fixtures'
            })
        except requests.exceptions.Timeout:
            print('SportMonks API timeout - falling back to database search')
            return search_fixtures_from_database(request, query, league_filter, limit)
        except Exception as e:
            # NEVER str(e) here. requests embeds the fully resolved URL in its
            # exception message, and SportMonks authenticates by query
            # parameter, so the unredacted text contains the live token. This
            # exact line printed it to CI stdout on 2026-08-06.
            print(f"SportMonks API error: {redact_exception(e)}")
            return search_fixtures_from_database(request, query, league_filter, limit)

    except Exception as e:
        # Same hazard, worse blast radius: this one goes into an HTTP response
        # body, so an unredacted provider error would hand the token to whoever
        # made the request.
        return JsonResponse({
            'success': False,
            'error': redact_exception(e),
            'results': [],
            'data': [],
            'count': 0
        }, status=500)


def search_fixtures_from_database(request, query, league_filter, limit):
    """Fallback: Search fixtures already in database"""
    try:
        print('Using database fallback search')
        now = timezone.now()
        end_date = now + timedelta(days=14)

        queryset = PredictionLog.objects.filter(
            kickoff__gte=now,
            kickoff__lte=end_date
        ).filter(
            Q(home_team__icontains=query) | Q(away_team__icontains=query)
        )

        if league_filter:
            queryset = queryset.filter(league__icontains=league_filter)

        fixtures = queryset.order_by('kickoff')[:limit]
        results = []
        for pred in fixtures:
            results.append({
                'fixture_id': pred.fixture_id,
                'home_team': pred.home_team,
                'away_team': pred.away_team,
                'league': pred.league,
                'kickoff': pred.kickoff.isoformat(),
                'has_predictions': True,
                'has_odds': bool(pred.odds_home or pred.odds_draw or pred.odds_away)
            })

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
            'error': redact_exception(e),
            'results': [],
            'data': [],
            'count': 0
        }, status=500)


# `update_fixture_results` was removed on 2026-08-03.
#
# It was csrf_exempt with no authentication at all, and the PUBLIC /monitoring
# page POSTed to it on every mount via a Next.js proxy route. Each call walked
# up to 50 pending predictions, made one SportMonks request per prediction and
# wrote actual_outcome/match_status. Any anonymous visitor could therefore burn
# provider quota and race the scheduler for the same rows.
#
# It also duplicated ResultUpdaterService with a divergent inline
# implementation. Result recording now has exactly one path:
#   run_scheduler -> update_results (ResultUpdaterService) -> settle_published_claims
# Manual operation: `python manage.py update_results --max N`.


def _normalize_interests(raw_value):
    if isinstance(raw_value, list):
        return [str(item).strip() for item in raw_value if str(item).strip()]
    if isinstance(raw_value, str) and raw_value.strip():
        return [item.strip() for item in raw_value.split(',') if item.strip()]
    return []


def _clean_text(value, default=''):
    if value is None:
        return default
    return str(value).strip()


def _validate_email(email):
    import re

    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None


def _record_marketing_event(event_name, subscriber=None, source='', page='', metadata=None):
    return MarketingEvent.objects.create(
        subscriber=subscriber,
        event_name=event_name,
        source=_clean_text(source),
        page=_clean_text(page),
        metadata=metadata or {},
    )


def _sync_subscriber(subscriber, action, metadata=None):
    try:
        sync_marketing_profile(subscriber, action, metadata or {})
    except MarketingSyncError:
        if subscriber.email_platform_status in ('pending', 'reactivated'):
            subscriber.email_platform_status = 'sync_failed'
            subscriber.save(update_fields=['email_platform_status'])


def _subscriber_payload(data):
    return {
        'source': _clean_text(data.get('source'), 'homepage') or 'homepage',
        'landing_page': _clean_text(data.get('landing_page')),
        'utm_source': _clean_text(data.get('utm_source')),
        'utm_medium': _clean_text(data.get('utm_medium')),
        'utm_campaign': _clean_text(data.get('utm_campaign')),
        'language': _clean_text(data.get('language'), 'en') or 'en',
        'league_interest': _clean_text(data.get('league_interest')),
        'interests': _normalize_interests(data.get('interests', [])),
    }


@csrf_exempt
@require_http_methods(["POST"])
def subscribe_email(request):
    """
    Email capture endpoint for newsletter/updates.
    POST /api/subscribe/
    Body: { "email": "user@example.com", "source": "homepage" }
    """
    try:
        data = json.loads(request.body)
        email = _clean_text(data.get('email')).lower()
        payload = _subscriber_payload(data)

        if not email:
            return JsonResponse({
                'success': False,
                'error': 'Email is required'
            }, status=400)

        if not _validate_email(email):
            return JsonResponse({
                'success': False,
                'error': 'Please enter a valid email address'
            }, status=400)

        existing = EmailSubscriber.objects.filter(email=email).first()
        if existing:
            updated_fields = []
            for field, value in payload.items():
                if getattr(existing, field) != value and value not in ('', []):
                    setattr(existing, field, value)
                    updated_fields.append(field)

            if existing.is_active:
                if updated_fields:
                    existing.save(update_fields=updated_fields)
                return JsonResponse({
                    'success': True,
                    'message': 'You are already subscribed!',
                    'already_subscribed': True,
                    'subscriber_id': existing.id
                })

            existing.is_active = True
            existing.source = payload['source']
            existing.email_platform_status = 'reactivated'
            updated_fields.extend(['is_active', 'source', 'email_platform_status'])
            existing.save(update_fields=sorted(set(updated_fields)))

            _record_marketing_event('email_subscribed', existing, payload['source'], payload['landing_page'], {'reactivated': True})
            _record_marketing_event('welcome_sequence_started', existing, payload['source'], payload['landing_page'], {'reactivated': True})
            _sync_subscriber(existing, 'reactivate', {'reactivated': True})

            return JsonResponse({
                'success': True,
                'message': 'Welcome back! Your subscription has been reactivated.',
                'reactivated': True,
                'subscriber_id': existing.id
            })

        subscriber = EmailSubscriber.objects.create(email=email, **payload)
        _record_marketing_event('email_subscribed', subscriber, payload['source'], payload['landing_page'], {
            'utm_source': payload['utm_source'],
            'utm_medium': payload['utm_medium'],
            'utm_campaign': payload['utm_campaign'],
            'league_interest': payload['league_interest'],
        })
        _record_marketing_event('welcome_sequence_started', subscriber, payload['source'], payload['landing_page'], {
            'trigger': 'subscription'
        })
        _sync_subscriber(subscriber, 'subscribe', {'trigger': 'subscription'})

        print(f"New subscriber: {email} from {payload['source']}")

        return JsonResponse({
            'success': True,
            'message': 'Thank you for subscribing! You will receive our best picks weekly.',
            'subscriber_id': subscriber.id
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON body'
        }, status=400)
    except Exception as e:
        print(f"Email subscription error: {redact_exception(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Something went wrong. Please try again.'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def track_marketing_event(request):
    try:
        data = json.loads(request.body)
        event_name = _clean_text(data.get('event_name'))
        valid_events = {choice for choice, _ in MarketingEvent.EVENT_CHOICES}
        if event_name not in valid_events:
            return JsonResponse({'success': False, 'error': 'Unsupported event_name'}, status=400)

        subscriber = None
        subscriber_id = data.get('subscriber_id')
        email = _clean_text(data.get('email')).lower()
        if subscriber_id:
            subscriber = EmailSubscriber.objects.filter(id=subscriber_id).first()
        elif email:
            subscriber = EmailSubscriber.objects.filter(email=email).first()

        metadata = data.get('metadata') if isinstance(data.get('metadata'), dict) else {}
        page = _clean_text(data.get('page'))
        source = _clean_text(data.get('source'))

        event = _record_marketing_event(event_name, subscriber, source, page, metadata)

        if subscriber and event_name == 'paid_converted':
            subscriber.email_platform_status = 'paid'
            subscriber.save(update_fields=['email_platform_status'])
            _sync_subscriber(subscriber, 'paid_converted', metadata)

        return JsonResponse({
            'success': True,
            'event_id': event.id
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON body'}, status=400)
    except Exception as e:
        print(f"Marketing event tracking error: {redact_exception(e)}")
        return JsonResponse({'success': False, 'error': 'Something went wrong. Please try again.'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def marketing_webhook(request):
    """
    Inbound marketing platform webhook (Brevo).

    POST /api/marketing/webhook/
    Header: X-Marketing-Webhook-Secret

    FAILS CLOSED. The previous check compared the header to the configured
    secret only when a secret was configured, so an unset
    MARKETING_WEBHOOK_SECRET skipped the comparison entirely and left the
    endpoint fully public. It was unset in production, which meant any
    anonymous caller who knew a subscriber's email address could unsubscribe
    them, reactivate them, mark them as `paid`, or inject marketing events.

    An absent secret now disables the webhook rather than opening it.
    """
    try:
        expected_secret = os.getenv('MARKETING_WEBHOOK_SECRET', '').strip()
        provided_secret = request.headers.get('X-Marketing-Webhook-Secret', '').strip()

        if not expected_secret:
            # Configuration error, not a client error. Log it here; the caller
            # is told only that it was not authorised, so an attacker cannot
            # distinguish "unconfigured" from "wrong secret".
            logger.error(
                'marketing webhook rejected: MARKETING_WEBHOOK_SECRET is not configured'
            )
            return JsonResponse({
                'code': 'webhook_unauthorized',
                'detail': 'The webhook request was not authorized.',
            }, status=401)

        # Constant-time: a plain != leaks secret length and prefix through
        # response timing.
        if not hmac.compare_digest(provided_secret, expected_secret):
            logger.warning('marketing webhook rejected: signature mismatch')
            return JsonResponse({
                'code': 'webhook_unauthorized',
                'detail': 'The webhook request was not authorized.',
            }, status=401)

        data = json.loads(request.body)
        metadata = data.get('metadata') if isinstance(data.get('metadata'), dict) else {}
        source = _clean_text(data.get('source'))
        page = _clean_text(data.get('page'))
        brevo_event = _clean_text(data.get('event')).lower()
        action = _clean_text(data.get('action')).lower()

        if brevo_event:
            action_map = {
                'click': 'email_clicked',
                'clicked': 'email_clicked',
                'unique_click': 'email_clicked',
                'unsubscribe': 'unsubscribe',
                'unsubscribed': 'unsubscribe',
            }
            action = action_map.get(brevo_event, action)
            if not source:
                source = 'brevo_webhook'
            if not page:
                page = _clean_text(data.get('link'))
            metadata = {
                **metadata,
                'brevo_event': brevo_event,
                'message_id': data.get('message-id') or data.get('messageId'),
                'subject': data.get('subject'),
            }

        email = _clean_text(data.get('email') or data.get('recipient')).lower()
        subscriber_id = data.get('subscriber_id')

        subscriber = None
        if subscriber_id:
            subscriber = EmailSubscriber.objects.filter(id=subscriber_id).first()
        elif email:
            subscriber = EmailSubscriber.objects.filter(email=email).first()

        if not subscriber:
            return JsonResponse({'success': False, 'error': 'Subscriber not found'}, status=404)

        if action == 'unsubscribe':
            subscriber.is_active = False
            subscriber.email_platform_status = 'unsubscribed'
            subscriber.save(update_fields=['is_active', 'email_platform_status'])
        elif action == 'reactivate':
            subscriber.is_active = True
            subscriber.email_platform_status = 'reactivated'
            subscriber.save(update_fields=['is_active', 'email_platform_status'])
            _record_marketing_event('email_subscribed', subscriber, source, page, {'reactivated_via_webhook': True, **metadata})
            _record_marketing_event('welcome_sequence_started', subscriber, source, page, {'reactivated_via_webhook': True})
        elif action == 'weekly_picks_sent':
            _record_marketing_event('weekly_picks_sent', subscriber, source, page, metadata)
        elif action == 'email_clicked':
            _record_marketing_event('email_clicked', subscriber, source, page, metadata)
        elif action == 'paid_converted':
            subscriber.email_platform_status = 'paid'
            subscriber.save(update_fields=['email_platform_status'])
            _record_marketing_event('paid_converted', subscriber, source, page, metadata)
        else:
            return JsonResponse({'success': False, 'error': 'Unsupported action'}, status=400)

        return JsonResponse({'success': True})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON body'}, status=400)
    except Exception:
        # Full traceback to the log; the caller learns nothing about internals.
        logger.exception('marketing webhook failed')
        return JsonResponse({
            'code': 'webhook_failed',
            'detail': 'The webhook could not be processed.',
        }, status=500)
