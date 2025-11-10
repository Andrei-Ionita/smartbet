"""
API Views for Bankroll Management
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional

from .models import UserBankroll, BankrollTransaction, StakeRecommendation, PredictionLog
from .bankroll_utils import (
    calculate_stake_amount,
    calculate_kelly_criterion,
    check_bankroll_limits,
    get_risk_profile_settings,
    simulate_bet_outcomes
)


def get_bankroll_for_request(request, session_id=None) -> Optional[UserBankroll]:
    """
    Get bankroll for either authenticated user or session_id.
    Prioritizes authenticated user if available.
    """
    # If user is authenticated, use their bankroll
    if request.user and request.user.is_authenticated:
        try:
            return UserBankroll.objects.get(user=request.user)
        except UserBankroll.DoesNotExist:
            return None
    
    # Fall back to session_id for anonymous users
    if session_id:
        try:
            return UserBankroll.objects.get(session_id=session_id, user__isnull=True)
        except UserBankroll.DoesNotExist:
            return None
    
    return None


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def create_bankroll(request):
    """
    Create a new user bankroll.
    
    For authenticated users: Links to user account
    For anonymous users: Requires session_id
    
    Required fields:
    - initial_bankroll: Starting amount
    - session_id: (only for anonymous users)
    
    Optional fields:
    - currency: Default 'USD'
    - risk_profile: 'conservative', 'balanced', or 'aggressive'
    - staking_strategy: Strategy to use
    - daily_loss_limit: Daily loss limit
    - weekly_loss_limit: Weekly loss limit
    - max_stake_percentage: Max stake % per bet
    """
    try:
        initial_bankroll = request.data.get('initial_bankroll')
        
        if not initial_bankroll:
            return Response({
                'error': 'initial_bankroll is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Determine if user is authenticated or anonymous
        is_authenticated = request.user and request.user.is_authenticated
        
        if is_authenticated:
            # Check if user already has a bankroll
            if UserBankroll.objects.filter(user=request.user).exists():
                return Response({
                    'error': 'You already have a bankroll'
                }, status=status.HTTP_400_BAD_REQUEST)
            user = request.user
            session_id = None
        else:
            # Anonymous user - require session_id
            session_id = request.data.get('session_id')
            if not session_id:
                return Response({
                    'error': 'session_id required for anonymous users'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if bankroll already exists for this session
            if UserBankroll.objects.filter(session_id=session_id, user__isnull=True).exists():
                return Response({
                    'error': 'Bankroll already exists for this session'
                }, status=status.HTTP_400_BAD_REQUEST)
            user = None
        
        # Get risk profile settings
        risk_profile = request.data.get('risk_profile', 'balanced')
        profile_settings = get_risk_profile_settings(risk_profile)
        
        # Calculate suggested limits based on risk profile
        initial_amount = Decimal(str(initial_bankroll))
        suggested_daily_limit = initial_amount * Decimal(str(profile_settings['daily_loss_limit_pct'] / 100))
        suggested_weekly_limit = initial_amount * Decimal(str(profile_settings['weekly_loss_limit_pct'] / 100))
        
        # Create bankroll
        bankroll = UserBankroll.objects.create(
            user=user,
            session_id=session_id,
            initial_bankroll=initial_amount,
            current_bankroll=initial_amount,
            currency=request.data.get('currency', 'USD'),
            risk_profile=risk_profile,
            staking_strategy=request.data.get('staking_strategy', profile_settings['recommended_strategy']),
            daily_loss_limit=request.data.get('daily_loss_limit', suggested_daily_limit),
            weekly_loss_limit=request.data.get('weekly_loss_limit', suggested_weekly_limit),
            max_stake_percentage=request.data.get('max_stake_percentage', profile_settings['max_stake_percentage']),
            fixed_stake_amount=request.data.get('fixed_stake_amount'),
            fixed_stake_percentage=request.data.get('fixed_stake_percentage'),
            user_email=request.data.get('user_email') if not is_authenticated else user.email
        )
        
        return Response({
            'success': True,
            'bankroll': serialize_bankroll(bankroll),
            'profile_settings': profile_settings,
            'message': f'Bankroll created successfully with {risk_profile} profile'
        }, status=status.HTTP_201_CREATED)
        
    except InvalidOperation as e:
        return Response({
            'error': f'Invalid number format: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': f'Failed to create bankroll: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['GET'])
def get_bankroll(request, session_id):
    """Get bankroll details for a session."""
    try:
        bankroll = UserBankroll.objects.get(session_id=session_id)
        bankroll.check_and_reset_limits()
        
        # Get recent transactions
        recent_transactions = BankrollTransaction.objects.filter(
            bankroll=bankroll
        ).order_by('-created_at')[:10]
        
        # Calculate performance metrics
        pending_bets = BankrollTransaction.objects.filter(
            bankroll=bankroll,
            status='pending'
        )
        
        return Response({
            'bankroll': serialize_bankroll(bankroll),
            'recent_transactions': [serialize_transaction(t) for t in recent_transactions],
            'pending_bets': pending_bets.count(),
            'pending_exposure': sum(float(t.stake_amount) for t in pending_bets),
            'profile_settings': get_risk_profile_settings(bankroll.risk_profile)
        })
        
    except UserBankroll.DoesNotExist:
        return Response({
            'error': 'Bankroll not found',
            'exists': False
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Failed to get bankroll: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['PUT'])
def update_bankroll(request, session_id):
    """Update bankroll settings."""
    try:
        bankroll = UserBankroll.objects.get(session_id=session_id)
        
        # Update allowed fields
        updateable_fields = [
            'risk_profile', 'staking_strategy', 'daily_loss_limit',
            'weekly_loss_limit', 'max_stake_percentage',
            'fixed_stake_amount', 'fixed_stake_percentage'
        ]
        
        for field in updateable_fields:
            if field in request.data:
                value = request.data[field]
                if field in ['daily_loss_limit', 'weekly_loss_limit', 'fixed_stake_amount']:
                    value = Decimal(str(value)) if value else None
                setattr(bankroll, field, value)
        
        bankroll.save()
        
        return Response({
            'success': True,
            'bankroll': serialize_bankroll(bankroll),
            'message': 'Bankroll updated successfully'
        })
        
    except UserBankroll.DoesNotExist:
        return Response({
            'error': 'Bankroll not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Failed to update bankroll: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def get_stake_recommendation(request):
    """
    Get stake recommendation for a specific prediction.
    
    Required:
    - fixture_id: Match fixture ID (or prediction data)
    - odds: Odds for the predicted outcome
    - win_probability: Model's win probability
    - confidence: Model confidence
    - session_id: (only for anonymous users)
    """
    try:
        session_id = request.data.get('session_id')
        fixture_id = request.data.get('fixture_id')
        odds = float(request.data.get('odds'))
        win_probability = float(request.data.get('win_probability'))
        confidence = float(request.data.get('confidence'))
        
        # Get user's bankroll (authenticated or session-based)
        bankroll = get_bankroll_for_request(request, session_id)
        
        if not bankroll:
            return Response({
                'error': 'Bankroll not found. Please create a bankroll first.',
                'exists': False
            }, status=status.HTTP_404_NOT_FOUND)
        
        bankroll.check_and_reset_limits()
        
        # Calculate stake recommendation
        stake_calc = calculate_stake_amount(
            bankroll=bankroll.current_bankroll,
            strategy=bankroll.staking_strategy,
            win_probability=win_probability,
            odds=odds,
            confidence=confidence,
            fixed_amount=bankroll.fixed_stake_amount,
            fixed_percentage=bankroll.fixed_stake_percentage,
            max_stake_percentage=bankroll.max_stake_percentage
        )
        
        # Check limits
        can_bet, limit_warnings = check_bankroll_limits(
            bankroll_obj=bankroll,
            stake_amount=stake_calc['recommended_stake']
        )
        
        # Add limit warnings
        all_warnings = stake_calc['warnings'] + limit_warnings
        
        # Simulate outcomes
        simulation = simulate_bet_outcomes(
            stake=stake_calc['recommended_stake'],
            odds=odds,
            win_probability=win_probability,
            num_simulations=1000
        )
        
        # Get or create prediction log if fixture_id provided
        prediction_log = None
        if fixture_id:
            try:
                prediction_log = PredictionLog.objects.get(fixture_id=fixture_id)
                
                # Create stake recommendation record
                stake_rec = StakeRecommendation.objects.create(
                    bankroll=bankroll,
                    prediction_log=prediction_log,
                    recommended_stake_amount=stake_calc['recommended_stake'],
                    recommended_stake_percentage=stake_calc['stake_percentage'],
                    strategy_used=stake_calc['strategy'],
                    kelly_percentage=stake_calc['kelly_info']['kelly_percentage'] if stake_calc['kelly_info'] else None,
                    kelly_full_stake=Decimal(str(
                        float(bankroll.current_bankroll) * stake_calc['kelly_info']['full_kelly'] / 100
                    )) if stake_calc['kelly_info'] else None,
                    risk_level=stake_calc['risk_level'],
                    risk_explanation=stake_calc['risk_explanation'],
                    has_warnings=len(all_warnings) > 0,
                    warnings=all_warnings,
                    bankroll_snapshot=bankroll.current_bankroll,
                    max_stake_allowed=stake_calc['max_stake_allowed']
                )
            except PredictionLog.DoesNotExist:
                pass
        
        return Response({
            'success': True,
            'can_bet': can_bet,
            'recommendation': {
                'stake_amount': float(stake_calc['recommended_stake']),
                'stake_percentage': stake_calc['stake_percentage'],
                'stake_currency': bankroll.currency,
                'strategy': stake_calc['strategy'],
                'risk_level': stake_calc['risk_level'],
                'risk_explanation': stake_calc['risk_explanation'],
                'kelly_info': stake_calc['kelly_info'],
                'max_stake_allowed': float(stake_calc['max_stake_allowed'])
            },
            'warnings': all_warnings,
            'bankroll_status': {
                'current_bankroll': float(bankroll.current_bankroll),
                'daily_loss': float(bankroll.daily_loss_amount),
                'daily_limit': float(bankroll.daily_loss_limit) if bankroll.daily_loss_limit else None,
                'weekly_loss': float(bankroll.weekly_loss_amount),
                'weekly_limit': float(bankroll.weekly_loss_limit) if bankroll.weekly_loss_limit else None,
                'is_daily_limit_reached': bankroll.is_daily_limit_reached,
                'is_weekly_limit_reached': bankroll.is_weekly_limit_reached
            },
            'simulation': simulation
        })
        
    except UserBankroll.DoesNotExist:
        return Response({
            'error': 'Bankroll not found. Please create a bankroll first.',
            'exists': False
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Failed to calculate stake recommendation: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST'])
def record_bet(request):
    """
    Record a bet placed by the user.
    
    Required:
    - session_id
    - fixture_id
    - selected_outcome
    - odds
    - stake_amount
    """
    try:
        session_id = request.data.get('session_id')
        fixture_id = request.data.get('fixture_id')
        selected_outcome = request.data.get('selected_outcome')
        odds = float(request.data.get('odds'))
        stake_amount = Decimal(str(request.data.get('stake_amount')))
        
        # Get bankroll
        bankroll = UserBankroll.objects.get(session_id=session_id)
        bankroll.check_and_reset_limits()
        
        # Check if bet is allowed
        can_bet, reason = bankroll.can_place_bet(stake_amount)
        if not can_bet:
            return Response({
                'error': reason,
                'can_bet': False
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get prediction log if exists
        prediction_log = None
        match_description = request.data.get('match_description', '')
        if fixture_id:
            try:
                prediction_log = PredictionLog.objects.get(fixture_id=fixture_id)
                match_description = f"{prediction_log.home_team} vs {prediction_log.away_team}"
            except PredictionLog.DoesNotExist:
                pass
        
        # Calculate potential return
        potential_return = stake_amount * Decimal(str(odds))
        
        # Create transaction
        transaction = BankrollTransaction.objects.create(
            bankroll=bankroll,
            prediction_log=prediction_log,
            transaction_type='bet_placed',
            fixture_id=fixture_id,
            match_description=match_description,
            selected_outcome=selected_outcome,
            odds=odds,
            stake_amount=stake_amount,
            potential_return=potential_return,
            bankroll_before=bankroll.current_bankroll,
            staking_strategy_used=bankroll.staking_strategy,
            recommended_stake=request.data.get('recommended_stake'),
            status='pending'
        )
        
        # Deduct stake from bankroll
        bankroll.current_bankroll -= stake_amount
        bankroll.total_bets_placed += 1
        bankroll.save()
        
        return Response({
            'success': True,
            'transaction': serialize_transaction(transaction),
            'bankroll': serialize_bankroll(bankroll),
            'message': 'Bet recorded successfully'
        }, status=status.HTTP_201_CREATED)
        
    except UserBankroll.DoesNotExist:
        return Response({
            'error': 'Bankroll not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Failed to record bet: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST'])
def settle_bet(request, transaction_id):
    """
    Settle a pending bet.
    
    Required:
    - won: Boolean indicating if bet won
    - void: Boolean indicating if bet was voided (optional)
    """
    try:
        transaction = BankrollTransaction.objects.get(id=transaction_id)
        
        if transaction.status != 'pending':
            return Response({
                'error': 'Transaction already settled'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        won = request.data.get('won', False)
        void = request.data.get('void', False)
        
        # Settle the transaction
        transaction.settle(won=won, void=void)
        
        # Refresh bankroll
        bankroll = transaction.bankroll
        bankroll.refresh_from_db()
        
        return Response({
            'success': True,
            'transaction': serialize_transaction(transaction),
            'bankroll': serialize_bankroll(bankroll),
            'message': f'Bet settled: {"Won" if won else "Lost" if not void else "Void"}'
        })
        
    except BankrollTransaction.DoesNotExist:
        return Response({
            'error': 'Transaction not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Failed to settle bet: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['GET'])
def get_transactions(request, session_id):
    """Get transaction history for a user."""
    try:
        bankroll = UserBankroll.objects.get(session_id=session_id)
        
        # Get query parameters
        limit = int(request.GET.get('limit', 50))
        status_filter = request.GET.get('status')
        transaction_type = request.GET.get('type')
        
        transactions = BankrollTransaction.objects.filter(bankroll=bankroll)
        
        if status_filter:
            transactions = transactions.filter(status=status_filter)
        
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)
        
        transactions = transactions.order_by('-created_at')[:limit]
        
        return Response({
            'transactions': [serialize_transaction(t) for t in transactions],
            'count': transactions.count()
        })
        
    except UserBankroll.DoesNotExist:
        return Response({
            'error': 'Bankroll not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Failed to get transactions: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['GET'])
def get_bankroll_stats(request, session_id):
    """Get detailed statistics for a user's bankroll."""
    try:
        bankroll = UserBankroll.objects.get(session_id=session_id)
        
        # Get all settled transactions
        settled_transactions = BankrollTransaction.objects.filter(
            bankroll=bankroll,
            status__in=['settled_won', 'settled_lost']
        )
        
        won_bets = settled_transactions.filter(status='settled_won')
        lost_bets = settled_transactions.filter(status='settled_lost')
        
        total_bets = settled_transactions.count()
        wins = won_bets.count()
        losses = lost_bets.count()
        win_rate = (wins / total_bets * 100) if total_bets > 0 else 0
        
        # Calculate profitability
        total_profit = sum(float(t.profit_loss or 0) for t in settled_transactions)
        avg_profit_per_bet = total_profit / total_bets if total_bets > 0 else 0
        
        # Bankroll performance
        bankroll_change = float(bankroll.current_bankroll - bankroll.initial_bankroll)
        bankroll_change_pct = (bankroll_change / float(bankroll.initial_bankroll)) * 100
        
        # Get pending bets
        pending = BankrollTransaction.objects.filter(
            bankroll=bankroll,
            status='pending'
        )
        
        return Response({
            'stats': {
                'total_bets': total_bets,
                'wins': wins,
                'losses': losses,
                'win_rate': round(win_rate, 1),
                'total_profit': round(total_profit, 2),
                'avg_profit_per_bet': round(avg_profit_per_bet, 2),
                'bankroll_change': round(bankroll_change, 2),
                'bankroll_change_pct': round(bankroll_change_pct, 1),
                'roi': round(float(bankroll.roi_percent), 1),
                'pending_bets': pending.count(),
                'pending_exposure': sum(float(t.stake_amount) for t in pending)
            },
            'bankroll': serialize_bankroll(bankroll)
        })
        
    except UserBankroll.DoesNotExist:
        return Response({
            'error': 'Bankroll not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Failed to get stats: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Helper serialization functions
def serialize_bankroll(bankroll: UserBankroll) -> Dict[str, Any]:
    """Serialize bankroll to dictionary."""
    return {
        'session_id': bankroll.session_id,
        'initial_bankroll': float(bankroll.initial_bankroll),
        'current_bankroll': float(bankroll.current_bankroll),
        'currency': bankroll.currency,
        'risk_profile': bankroll.risk_profile,
        'staking_strategy': bankroll.staking_strategy,
        'daily_loss_limit': float(bankroll.daily_loss_limit) if bankroll.daily_loss_limit else None,
        'weekly_loss_limit': float(bankroll.weekly_loss_limit) if bankroll.weekly_loss_limit else None,
        'daily_loss_amount': float(bankroll.daily_loss_amount),
        'weekly_loss_amount': float(bankroll.weekly_loss_amount),
        'is_daily_limit_reached': bankroll.is_daily_limit_reached,
        'is_weekly_limit_reached': bankroll.is_weekly_limit_reached,
        'max_stake_percentage': bankroll.max_stake_percentage,
        'total_bets_placed': bankroll.total_bets_placed,
        'total_wagered': float(bankroll.total_wagered),
        'total_profit_loss': float(bankroll.total_profit_loss),
        'roi_percent': round(bankroll.roi_percent, 2),
        'created_at': bankroll.created_at.isoformat(),
        'updated_at': bankroll.updated_at.isoformat()
    }


def serialize_transaction(transaction: BankrollTransaction) -> Dict[str, Any]:
    """Serialize transaction to dictionary."""
    return {
        'id': transaction.id,
        'transaction_type': transaction.transaction_type,
        'match_description': transaction.match_description,
        'fixture_id': transaction.fixture_id,
        'selected_outcome': transaction.selected_outcome,
        'odds': transaction.odds,
        'stake_amount': float(transaction.stake_amount),
        'potential_return': float(transaction.potential_return),
        'actual_return': float(transaction.actual_return) if transaction.actual_return else None,
        'profit_loss': float(transaction.profit_loss) if transaction.profit_loss else None,
        'status': transaction.status,
        'bankroll_before': float(transaction.bankroll_before),
        'bankroll_after': float(transaction.bankroll_after) if transaction.bankroll_after else None,
        'recommended_stake': float(transaction.recommended_stake) if transaction.recommended_stake else None,
        'staking_strategy_used': transaction.staking_strategy_used,
        'created_at': transaction.created_at.isoformat(),
        'settled_at': transaction.settled_at.isoformat() if transaction.settled_at else None,
        'notes': transaction.notes
    }

