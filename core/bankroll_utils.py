"""
Bankroll Management Utilities for SmartBet

Includes Kelly Criterion calculator, staking strategies, and risk assessment.
"""

from decimal import Decimal
from typing import Dict, Tuple, List


def calculate_kelly_criterion(
    win_probability: float,
    odds: float,
    fractional: bool = True,
    fraction: float = 0.25
) -> Dict[str, float]:
    """
    Calculate optimal bet size using Kelly Criterion.
    
    Kelly Formula: f = (bp - q) / b
    Where:
        f = fraction of bankroll to bet
        b = odds - 1 (net odds)
        p = probability of winning
        q = probability of losing (1 - p)
    
    Args:
        win_probability: Model's predicted probability of winning (0-1)
        odds: Decimal odds (e.g., 2.5)
        fractional: Whether to use fractional Kelly (safer)
        fraction: Kelly fraction to use (default 0.25 = 1/4 Kelly)
    
    Returns:
        Dictionary with kelly_percentage, full_kelly, fractional_kelly
    """
    if win_probability <= 0 or win_probability >= 1:
        return {
            'kelly_percentage': 0.0,
            'full_kelly': 0.0,
            'fractional_kelly': 0.0,
            'is_valid': False,
            'reason': 'Invalid probability'
        }
    
    if odds <= 1.0:
        return {
            'kelly_percentage': 0.0,
            'full_kelly': 0.0,
            'fractional_kelly': 0.0,
            'is_valid': False,
            'reason': 'Odds too low'
        }
    
    # Calculate Kelly percentage
    b = odds - 1  # Net odds
    p = win_probability
    q = 1 - p  # Probability of losing
    
    # Full Kelly formula
    kelly_full = (b * p - q) / b
    
    # Kelly should be positive for a value bet
    if kelly_full <= 0:
        return {
            'kelly_percentage': 0.0,
            'full_kelly': 0.0,
            'fractional_kelly': 0.0,
            'is_valid': False,
            'reason': 'No positive expected value'
        }
    
    # Cap at 25% max (safety measure)
    kelly_full = min(kelly_full, 0.25)
    
    # Fractional Kelly (safer, reduces variance)
    kelly_fractional = kelly_full * fraction if fractional else kelly_full
    
    return {
        'kelly_percentage': round(kelly_fractional * 100, 2),
        'full_kelly': round(kelly_full * 100, 2),
        'fractional_kelly': round(kelly_fractional * 100, 2),
        'is_valid': True,
        'fraction_used': fraction
    }


def calculate_stake_amount(
    bankroll: Decimal,
    strategy: str,
    win_probability: float,
    odds: float,
    confidence: float,
    fixed_amount: Decimal = None,
    fixed_percentage: float = None,
    max_stake_percentage: float = 5.0
) -> Dict:
    """
    Calculate recommended stake based on selected strategy.
    
    Args:
        bankroll: Current bankroll amount
        strategy: Staking strategy to use
        win_probability: Model's win probability (0-1)
        odds: Decimal odds
        confidence: Model confidence (0-100)
        fixed_amount: For fixed_amount strategy
        fixed_percentage: For fixed_percentage strategy
        max_stake_percentage: Maximum allowed stake as % of bankroll
    
    Returns:
        Dictionary with stake details and risk assessment
    """
    bankroll_float = float(bankroll)
    max_stake = (bankroll_float * max_stake_percentage) / 100
    
    warnings = []
    
    if strategy == 'kelly':
        kelly = calculate_kelly_criterion(win_probability, odds, fractional=False)
        if not kelly['is_valid']:
            return {
                'recommended_stake': Decimal('0.00'),
                'stake_percentage': 0.0,
                'strategy': strategy,
                'kelly_info': kelly,
                'risk_level': 'none',
                'risk_explanation': f"No stake recommended: {kelly['reason']}",
                'warnings': [kelly['reason']]
            }
        
        stake_percentage = kelly['kelly_percentage']
        stake_amount = (bankroll_float * stake_percentage) / 100
        warnings.append("Full Kelly is aggressive - consider Fractional Kelly")
        
    elif strategy == 'kelly_fractional':
        kelly = calculate_kelly_criterion(win_probability, odds, fractional=True, fraction=0.25)
        if not kelly['is_valid']:
            return {
                'recommended_stake': Decimal('0.00'),
                'stake_percentage': 0.0,
                'strategy': strategy,
                'kelly_info': kelly,
                'risk_level': 'none',
                'risk_explanation': f"No stake recommended: {kelly['reason']}",
                'warnings': [kelly['reason']]
            }
        
        stake_percentage = kelly['fractional_kelly']
        stake_amount = (bankroll_float * stake_percentage) / 100
        
    elif strategy == 'fixed_percentage':
        if fixed_percentage is None:
            fixed_percentage = 2.0  # Default 2%
        stake_percentage = fixed_percentage
        stake_amount = (bankroll_float * stake_percentage) / 100
        kelly = None
        
    elif strategy == 'fixed_amount':
        if fixed_amount is None:
            fixed_amount = Decimal('10.00')  # Default $10
        stake_amount = float(fixed_amount)
        stake_percentage = (stake_amount / bankroll_float) * 100
        kelly = None
        
    elif strategy == 'confidence_scaled':
        # Scale stake based on confidence: 1-5% based on confidence 55-100%
        min_stake_pct = 1.0
        max_stake_pct = 5.0
        
        # Map confidence 55-100% to stake 1-5%
        if confidence >= 55:
            normalized_confidence = min((confidence - 55) / 45, 1.0)
            stake_percentage = min_stake_pct + (normalized_confidence * (max_stake_pct - min_stake_pct))
        else:
            stake_percentage = 0.0
            warnings.append("Confidence too low for betting")
        
        stake_amount = (bankroll_float * stake_percentage) / 100
        kelly = None
    else:
        # Default fallback
        stake_percentage = 2.0
        stake_amount = (bankroll_float * stake_percentage) / 100
        kelly = None
    
    # Apply maximum stake limit
    if stake_amount > max_stake:
        warnings.append(f"Stake reduced from ${stake_amount:.2f} to ${max_stake:.2f} (max {max_stake_percentage}% limit)")
        stake_amount = max_stake
        stake_percentage = (stake_amount / bankroll_float) * 100
    
    # Risk level assessment
    risk_level, risk_explanation = assess_risk_level(
        stake_percentage=stake_percentage,
        confidence=confidence,
        odds=odds,
        win_probability=win_probability
    )
    
    return {
        'recommended_stake': Decimal(str(round(stake_amount, 2))),
        'stake_percentage': round(stake_percentage, 2),
        'strategy': strategy,
        'kelly_info': kelly,
        'risk_level': risk_level,
        'risk_explanation': risk_explanation,
        'warnings': warnings,
        'max_stake_allowed': Decimal(str(round(max_stake, 2)))
    }


def assess_risk_level(
    stake_percentage: float,
    confidence: float,
    odds: float,
    win_probability: float
) -> Tuple[str, str]:
    """
    Assess the risk level of a bet.
    
    Returns:
        Tuple of (risk_level, explanation)
    """
    risk_factors = []
    risk_score = 0
    
    # Factor 1: Stake size
    if stake_percentage > 5:
        risk_score += 2
        risk_factors.append(f"Large stake ({stake_percentage:.1f}% of bankroll)")
    elif stake_percentage > 3:
        risk_score += 1
        risk_factors.append(f"Moderate stake ({stake_percentage:.1f}% of bankroll)")
    
    # Factor 2: Confidence level
    if confidence < 60:
        risk_score += 2
        risk_factors.append(f"Lower confidence ({confidence:.1f}%)")
    elif confidence < 70:
        risk_score += 1
        risk_factors.append(f"Moderate confidence ({confidence:.1f}%)")
    
    # Factor 3: Odds (higher odds = more variance)
    if odds > 3.0:
        risk_score += 2
        risk_factors.append(f"High odds ({odds:.2f}) = higher variance")
    elif odds > 2.0:
        risk_score += 1
        risk_factors.append(f"Moderate odds ({odds:.2f})")
    
    # Factor 4: Probability-odds mismatch
    implied_probability = 1 / odds
    edge = win_probability - implied_probability
    if edge < 0.05:
        risk_score += 1
        risk_factors.append("Small edge vs market")
    
    # Determine risk level
    if risk_score == 0:
        risk_level = 'low'
        explanation = "Low risk bet: " + (risk_factors[0] if risk_factors else "Conservative stake, high confidence, good odds")
    elif risk_score <= 2:
        risk_level = 'medium'
        explanation = "Medium risk bet: " + ", ".join(risk_factors)
    else:
        risk_level = 'high'
        explanation = "High risk bet: " + ", ".join(risk_factors)
    
    return risk_level, explanation


def check_bankroll_limits(
    bankroll_obj,
    stake_amount: Decimal
) -> Tuple[bool, List[str]]:
    """
    Check if bet is allowed given current bankroll limits.
    
    Args:
        bankroll_obj: UserBankroll instance
        stake_amount: Proposed stake amount
    
    Returns:
        Tuple of (is_allowed, reasons)
    """
    reasons = []
    
    # Check basic can_place_bet
    can_bet, reason = bankroll_obj.can_place_bet(stake_amount)
    if not can_bet:
        return False, [reason]
    
    # Check how close to daily limit
    if bankroll_obj.daily_loss_limit:
        remaining_daily = float(bankroll_obj.daily_loss_limit) - float(bankroll_obj.daily_loss_amount)
        if float(stake_amount) > remaining_daily * 0.5:
            reasons.append(f"Bet uses >50% of remaining daily loss limit (${remaining_daily:.2f} left)")
    
    # Check how close to weekly limit
    if bankroll_obj.weekly_loss_limit:
        remaining_weekly = float(bankroll_obj.weekly_loss_limit) - float(bankroll_obj.weekly_loss_amount)
        if float(stake_amount) > remaining_weekly * 0.3:
            reasons.append(f"Bet uses >30% of remaining weekly loss limit (${remaining_weekly:.2f} left)")
    
    # Check bankroll depletion
    bankroll_percentage = (float(stake_amount) / float(bankroll_obj.current_bankroll)) * 100
    if bankroll_percentage > 10:
        reasons.append(f"Warning: Betting {bankroll_percentage:.1f}% of total bankroll on single bet")
    
    # Check if on losing streak
    if bankroll_obj.current_bankroll < bankroll_obj.initial_bankroll * Decimal('0.7'):
        reasons.append("Bankroll down >30% from initial - consider reducing stakes")
    
    return True, reasons


def get_risk_profile_settings(risk_profile: str) -> Dict:
    """
    Get recommended settings for each risk profile.
    
    Args:
        risk_profile: 'conservative', 'balanced', or 'aggressive'
    
    Returns:
        Dictionary with recommended settings
    """
    profiles = {
        'conservative': {
            'max_stake_percentage': 2.0,
            'recommended_strategy': 'kelly_fractional',
            'kelly_fraction': 0.125,  # 1/8 Kelly
            'min_confidence': 70.0,
            'min_expected_value': 0.05,
            'daily_loss_limit_pct': 5.0,  # 5% of bankroll
            'weekly_loss_limit_pct': 15.0,
            'description': 'Safest approach with small stakes and high confidence requirements'
        },
        'balanced': {
            'max_stake_percentage': 5.0,
            'recommended_strategy': 'kelly_fractional',
            'kelly_fraction': 0.25,  # 1/4 Kelly
            'min_confidence': 60.0,
            'min_expected_value': 0.02,
            'daily_loss_limit_pct': 10.0,
            'weekly_loss_limit_pct': 25.0,
            'description': 'Balanced approach suitable for most bettors'
        },
        'aggressive': {
            'max_stake_percentage': 10.0,
            'recommended_strategy': 'kelly',
            'kelly_fraction': 0.5,  # 1/2 Kelly
            'min_confidence': 55.0,
            'min_expected_value': 0.0,
            'daily_loss_limit_pct': 20.0,
            'weekly_loss_limit_pct': 40.0,
            'description': 'Higher risk/reward for experienced bettors'
        }
    }
    
    return profiles.get(risk_profile, profiles['balanced'])


def simulate_bet_outcomes(
    stake: Decimal,
    odds: float,
    win_probability: float,
    num_simulations: int = 100
) -> Dict:
    """
    Simulate potential outcomes of a bet.
    
    Args:
        stake: Bet amount
        odds: Decimal odds
        win_probability: Probability of winning (0-1)
        num_simulations: Number of simulations to run
    
    Returns:
        Dictionary with simulation results
    """
    import random
    
    outcomes = []
    for _ in range(num_simulations):
        if random.random() < win_probability:
            profit = float(stake) * (odds - 1)
            outcomes.append(profit)
        else:
            outcomes.append(-float(stake))
    
    avg_profit = sum(outcomes) / len(outcomes)
    win_count = sum(1 for x in outcomes if x > 0)
    win_rate = (win_count / num_simulations) * 100
    
    return {
        'average_profit': round(avg_profit, 2),
        'win_rate': round(win_rate, 1),
        'best_case': round(max(outcomes), 2),
        'worst_case': round(min(outcomes), 2),
        'expected_value': round(avg_profit, 2)
    }

