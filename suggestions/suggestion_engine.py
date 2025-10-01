"""
Suggestion Engine for SmartBet application.

This module provides functions to surface the best betting opportunities based on
match score predictions from our ML models.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from django.utils import timezone
from django.db.models import F, Q

from core.models import MatchScoreModel, Match, OddsSnapshot

logger = logging.getLogger(__name__)

# Confidence level ordering from highest to lowest
CONFIDENCE_LEVELS = {
    'VERY_HIGH': 4,
    'HIGH': 3, 
    'MEDIUM': 2,
    'LOW': 1,
}

def get_top_recommendations(
    n: int = 10, 
    min_confidence: str = 'MEDIUM',
    league_ids: Optional[List[int]] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    bookmaker: str = 'Bet365'
) -> List[Dict[str, Any]]:
    """
    Get top betting recommendations based on match score predictions.
    
    Args:
        n: Number of recommendations to return
        min_confidence: Minimum confidence level ('LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH')
        league_ids: Optional list of league IDs to filter by
        date_from: Optional start date for matches (defaults to now)
        date_to: Optional end date for matches (defaults to 7 days from now)
        bookmaker: Bookmaker to use for odds data
        
    Returns:
        List of dictionaries containing recommendation data
    """
    # Validate inputs
    min_confidence = min_confidence.upper()
    if min_confidence not in CONFIDENCE_LEVELS:
        logger.warning(f"Invalid min_confidence: {min_confidence}. Using 'MEDIUM'")
        min_confidence = 'MEDIUM'
    
    min_confidence_value = CONFIDENCE_LEVELS[min_confidence]
    
    # Set default date range if not provided
    if date_from is None:
        date_from = timezone.now()
    
    if date_to is None:
        date_to = date_from + timedelta(days=7)
    
    # Build base query for match scores
    scores_query = MatchScoreModel.objects.select_related('match').filter(
        # Only include future matches
        match__kickoff__gte=date_from,
        match__kickoff__lte=date_to,
        # Only matches that haven't started
        match__status='NS',
        # Only valid recommendations
        recommended_bet__isnull=False,
        recommended_bet__gt='',
    )
    
    # Filter by confidence level
    confidence_filter = Q()
    for level, value in CONFIDENCE_LEVELS.items():
        if value >= min_confidence_value:
            confidence_filter |= Q(confidence_level__iexact=level)
    
    scores_query = scores_query.filter(confidence_filter)
    
    # Filter by leagues if specified
    if league_ids:
        scores_query = scores_query.filter(match__league_id__in=league_ids)
    
    # Get top N recommendations ordered by confidence level first, then by highest score
    scores = list(scores_query.order_by('-confidence_level', 
                                    -(F('home_team_score') + F('away_team_score')))[:n])
    
    if not scores:
        logger.info("No recommendations found matching criteria")
        return []
    
    # Convert to output format with rich information
    recommendations = []
    
    for score in scores:
        match = score.match
        
        # Get the latest odds for the match
        odds = match.odds_snapshots.filter(
            bookmaker=bookmaker
        ).order_by('-fetched_at').first()
        
        # Determine the odds for the recommended bet
        odds_value = None
        if odds:
            if score.predicted_outcome == 'home':
                odds_value = odds.odds_home
            elif score.predicted_outcome == 'away':
                odds_value = odds.odds_away
            else:  # draw
                odds_value = odds.odds_draw
        
        recommendation = {
            'match_id': match.id,
            'fixture_id': score.fixture_id,
            'home_team': str(match.home_team),
            'away_team': str(match.away_team),
            'kickoff': match.kickoff,
            'league': str(match.league),
            'recommended_bet': score.recommended_bet,
            'predicted_outcome': score.predicted_outcome,
            'confidence_level': score.confidence_level,
            'home_team_score': score.home_team_score,
            'away_team_score': score.away_team_score,
            'odds': odds_value,
            'bookmaker': bookmaker if odds else None,
            'source': score.source,
            'generated_at': score.generated_at,
        }
        
        recommendations.append(recommendation)
    
    logger.info(f"Found {len(recommendations)} recommendations")
    return recommendations

def get_recommendation_by_match(match_id: int) -> Optional[Dict[str, Any]]:
    """
    Get recommendation for a specific match.
    
    Args:
        match_id: ID of the match
        
    Returns:
        Dictionary with recommendation data or None if not found
    """
    try:
        # Get the latest score for the match
        score = MatchScoreModel.objects.filter(
            match_id=match_id
        ).order_by('-generated_at').first()
        
        if not score:
            return None
        
        # Get match details
        match = score.match
        
        # Get the latest odds
        odds = match.odds_snapshots.order_by('-fetched_at').first()
        
        odds_value = None
        if odds:
            if score.predicted_outcome == 'home':
                odds_value = odds.odds_home
            elif score.predicted_outcome == 'away':
                odds_value = odds.odds_away
            else:  # draw
                odds_value = odds.odds_draw
        
        recommendation = {
            'match_id': match.id,
            'fixture_id': score.fixture_id,
            'home_team': str(match.home_team),
            'away_team': str(match.away_team),
            'kickoff': match.kickoff,
            'league': str(match.league),
            'recommended_bet': score.recommended_bet,
            'predicted_outcome': score.predicted_outcome,
            'confidence_level': score.confidence_level,
            'home_team_score': score.home_team_score,
            'away_team_score': score.away_team_score,
            'odds': odds_value,
            'bookmaker': odds.bookmaker if odds else None,
            'source': score.source,
            'generated_at': score.generated_at,
        }
        
        return recommendation
    
    except Exception as e:
        logger.error(f"Error getting recommendation for match {match_id}: {e}")
        return None

def format_recommendations_for_display(recommendations: List[Dict[str, Any]]) -> str:
    """
    Format recommendations as a readable text table.
    
    Args:
        recommendations: List of recommendation dictionaries
        
    Returns:
        Formatted string with recommendations table
    """
    if not recommendations:
        return "No recommendations found."
    
    result = "\n=== SMARTBET TOP RECOMMENDATIONS ===\n\n"
    result += f"{'MATCH':<40} {'KICKOFF':<16} {'PREDICTION':<15} {'CONFIDENCE':<10} {'ODDS':<8}\n"
    result += "-" * 90 + "\n"
    
    for rec in recommendations:
        match_name = f"{rec['home_team']} vs {rec['away_team']}"
        kickoff = rec['kickoff'].strftime("%d-%m-%Y %H:%M")
        prediction = rec['recommended_bet']
        confidence = rec['confidence_level']
        odds = f"{rec['odds']:.2f}" if rec['odds'] else "N/A"
        
        result += f"{match_name:<40} {kickoff:<16} {prediction:<15} {confidence:<10} {odds:<8}\n"
    
    return result 