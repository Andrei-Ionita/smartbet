"""
Training dataset generator for SmartBet ML models.

This module provides functionality to export training data from completed matches 
in the SmartBet database. It queries matches with odds and results, extracts relevant 
features, and saves the data to a CSV file for ML training.
"""

import os
import csv
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import pandas as pd
import numpy as np
from django.db.models import Avg, Q, F, Count
from django.utils import timezone

from core.models import Match, OddsSnapshot, MatchMetadata, Team, League

# Configure logging
logger = logging.getLogger(__name__)

# Constants
BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_FILE = BASE_DIR / "core" / "ml_training_data.csv"

# Feature columns definition
FEATURE_COLUMNS = [
    # Basic odds features
    'odds_home', 'odds_draw', 'odds_away',
    
    # Historical odds features
    'opening_odds_home', 'opening_odds_draw', 'opening_odds_away',
    'closing_odds_home', 'closing_odds_draw', 'closing_odds_away',
    'odds_home_delta', 'odds_draw_delta', 'odds_away_delta',
    
    # Team and league features
    'league_id', 'team_home_rating', 'team_away_rating',
    'team_rating_diff', 'team_rating_ratio',
    
    # Injury features
    'injured_home_starters', 'injured_away_starters', 'injured_starters_diff',
    
    # Form features
    'team_form_home', 'team_form_away', 'team_form_diff',
    'recent_form_diff', 'recent_form_diff_per_match',
    
    # Goal statistics
    'home_goals_avg', 'away_goals_avg', 'goals_avg_diff',
    'home_goals_conceded_avg', 'away_goals_conceded_avg', 'goals_conceded_diff',
    
    # Card statistics
    'home_cards_avg', 'away_cards_avg', 'cards_avg_diff',
    
    # Target variable
    'outcome'
]


def get_completed_matches(months_limit: Optional[int] = None) -> List[Match]:
    """
    Get completed matches with final score and available odds.
    
    Args:
        months_limit: Optional limit to only include matches from the last N months
        
    Returns:
        List of Match objects
    """
    # Base query - completed matches with scores
    query = Q(status='FT') & ~Q(home_score=None) & ~Q(away_score=None)
    
    # Apply time limit if specified
    if months_limit:
        cutoff_date = timezone.now() - timedelta(days=30 * months_limit)
        query &= Q(kickoff__gte=cutoff_date)
    
    # Get matches that also have odds data
    matches = Match.objects.filter(query).filter(
        odds_snapshots__isnull=False
    ).distinct()
    
    logger.info(f"Found {matches.count()} completed matches with scores and odds")
    return list(matches)


def get_team_rating(team: Team, lookback_matches: int = 10) -> int:
    """
    Calculate a simple team rating based on recent performance.
    
    For now, we use a simple formula based on recent goal difference.
    In a production system, this would be replaced with ELO or another rating system.
    
    Args:
        team: The Team model instance
        lookback_matches: Number of past matches to consider
        
    Returns:
        Rating value between 0 and 100
    """
    # Get recent home matches
    home_matches = Match.objects.filter(
        home_team=team,
        status='FT',
        home_score__isnull=False,
        away_score__isnull=False
    ).order_by('-kickoff')[:lookback_matches]
    
    # Get recent away matches
    away_matches = Match.objects.filter(
        away_team=team,
        status='FT', 
        home_score__isnull=False,
        away_score__isnull=False
    ).order_by('-kickoff')[:lookback_matches]
    
    # Calculate total goals for and against
    goals_for = sum([m.home_score or 0 for m in home_matches]) + sum([m.away_score or 0 for m in away_matches])
    goals_against = sum([m.away_score or 0 for m in home_matches]) + sum([m.home_score or 0 for m in away_matches])
    
    # Count matches
    match_count = len(home_matches) + len(away_matches)
    
    if match_count == 0:
        return 75  # Default rating if no matches
    
    # Calculate goal difference per match
    goal_diff_per_match = (goals_for - goals_against) / match_count
    
    # Convert to a rating between 50-100
    # Scale: +1 avg goal diff = +10 rating points, centered at 75
    rating = 75 + (goal_diff_per_match * 10)
    
    # Clamp between 50 and 100
    return max(50, min(100, rating))


def get_recent_form_diff(home_team: Team, away_team: Team, lookback_matches: int = 5) -> int:
    """
    Calculate the form difference between two teams.
    
    Form is calculated as points in the last N matches (3 for win, 1 for draw, 0 for loss).
    Returns home_team_form - away_team_form.
    
    Args:
        home_team: The home Team model instance
        away_team: The away Team model instance
        lookback_matches: Number of past matches to consider
        
    Returns:
        Form difference value (positive favors home team)
    """
    # Calculate home team's form
    home_team_form = 0
    
    # Home matches where the team was home
    home_as_home = Match.objects.filter(
        home_team=home_team,
        status='FT',
        home_score__isnull=False,
        away_score__isnull=False
    ).order_by('-kickoff')[:lookback_matches]
    
    for match in home_as_home:
        if match.home_score > match.away_score:
            home_team_form += 3  # Win
        elif match.home_score == match.away_score:
            home_team_form += 1  # Draw
    
    # Home matches where the team was away
    home_as_away = Match.objects.filter(
        away_team=home_team,
        status='FT',
        home_score__isnull=False, 
        away_score__isnull=False
    ).order_by('-kickoff')[:lookback_matches - len(home_as_home)]
    
    for match in home_as_away:
        if match.away_score > match.home_score:
            home_team_form += 3  # Win
        elif match.home_score == match.away_score:
            home_team_form += 1  # Draw
    
    # Calculate away team's form (same logic)
    away_team_form = 0
    
    # Away matches where the team was home
    away_as_home = Match.objects.filter(
        home_team=away_team,
        status='FT',
        home_score__isnull=False,
        away_score__isnull=False
    ).order_by('-kickoff')[:lookback_matches]
    
    for match in away_as_home:
        if match.home_score > match.away_score:
            away_team_form += 3  # Win
        elif match.home_score == match.away_score:
            away_team_form += 1  # Draw
    
    # Away matches where the team was away
    away_as_away = Match.objects.filter(
        away_team=away_team,
        status='FT',
        home_score__isnull=False,
        away_score__isnull=False
    ).order_by('-kickoff')[:lookback_matches - len(away_as_home)]
    
    for match in away_as_away:
        if match.away_score > match.home_score:
            away_team_form += 3  # Win
        elif match.home_score == match.away_score:
            away_team_form += 1  # Draw
    
    # Return the form difference
    return home_team_form - away_team_form


def get_team_goals_avg(team: Team, is_home: bool, lookback_matches: int = 10) -> float:
    """
    Calculate the average goals scored per match for a team.
    
    Args:
        team: The Team model instance
        is_home: Whether to calculate for home or away games
        lookback_matches: Number of past matches to consider
        
    Returns:
        Average goals per match
    """
    if is_home:
        matches = Match.objects.filter(
            home_team=team,
            status='FT',
            home_score__isnull=False
        ).order_by('-kickoff')[:lookback_matches]
        
        goal_count = sum(m.home_score for m in matches if m.home_score is not None)
    else:
        matches = Match.objects.filter(
            away_team=team,
            status='FT', 
            away_score__isnull=False
        ).order_by('-kickoff')[:lookback_matches]
        
        goal_count = sum(m.away_score for m in matches if m.away_score is not None)
    
    match_count = len(matches)
    
    if match_count == 0:
        return 1.5 if is_home else 1.0  # Default values
    
    return goal_count / match_count


def get_injured_starters(match: Match, is_home: bool) -> int:
    """
    Get the number of injured starting players for a team.
    
    In a production system, this would use real injury data from the API.
    For now, we return 0 or extract from metadata if available.
    
    Args:
        match: The Match model instance
        is_home: Whether to get data for home or away team
        
    Returns:
        Number of injured starters
    """
    try:
        # Try to get metadata
        metadata = getattr(match, 'metadata', None)
        
        if metadata and hasattr(metadata, 'data'):
            data = metadata.data
            injuries_key = 'home_injuries' if is_home else 'away_injuries'
            
            if injuries_key in data and isinstance(data[injuries_key], list):
                # Count only starters
                return len([p for p in data[injuries_key] if p.get('is_starter', False)])
    except Exception as e:
        logger.warning(f"Error getting injury data: {e}")
    
    # Default value
    return 0


def get_match_outcome(match: Match) -> str:
    """
    Get the outcome of a match as 'home', 'draw', or 'away'.
    
    Args:
        match: The Match model instance
        
    Returns:
        Outcome string
    """
    if match.home_score is None or match.away_score is None:
        return "unknown"
        
    if match.home_score > match.away_score:
        return "home"
    elif match.home_score < match.away_score:
        return "away"
    else:
        return "draw"


def get_odds_snapshot(match: Match) -> Optional[OddsSnapshot]:
    """
    Get the best odds snapshot for a match.
    
    Prioritizes pre-match odds from reliable bookmakers.
    
    Args:
        match: The Match model instance
        
    Returns:
        OddsSnapshot instance or None
    """
    # Try to get pre-match odds
    cutoff_time = match.kickoff
    
    # Prioritize Pinnacle odds from OddsAPI
    pinnacle_odds = OddsSnapshot.objects.filter(
        match=match,
        bookmaker__startswith="OddsAPI (Pinnacle)",
        fetched_at__lt=cutoff_time
    ).order_by('-fetched_at').first()
    
    if pinnacle_odds:
        return pinnacle_odds
    
    # Then try Bet365 from OddsAPI
    bet365_odds = OddsSnapshot.objects.filter(
        match=match, 
        bookmaker__startswith="OddsAPI (Bet365)",
        fetched_at__lt=cutoff_time
    ).order_by('-fetched_at').first()
    
    if bet365_odds:
        return bet365_odds
    
    # Fallback to any pre-match odds
    any_odds = OddsSnapshot.objects.filter(
        match=match,
        fetched_at__lt=cutoff_time
    ).order_by('-fetched_at').first()
    
    if any_odds:
        return any_odds
    
    # As a last resort, get any odds
    return OddsSnapshot.objects.filter(match=match).order_by('-fetched_at').first()


def get_team_goals_conceded_avg(team: Team, is_home: bool, lookback_matches: int = 10) -> float:
    """
    Calculate the average goals conceded per match for a team.
    
    Args:
        team: The Team model instance
        is_home: Whether to calculate for home or away games
        lookback_matches: Number of past matches to consider
        
    Returns:
        Average goals conceded per match
    """
    if is_home:
        matches = Match.objects.filter(
            home_team=team,
            status='FT',
            away_score__isnull=False
        ).order_by('-kickoff')[:lookback_matches]
        
        goals_conceded = sum(m.away_score for m in matches if m.away_score is not None)
    else:
        matches = Match.objects.filter(
            away_team=team,
            status='FT', 
            home_score__isnull=False
        ).order_by('-kickoff')[:lookback_matches]
        
        goals_conceded = sum(m.home_score for m in matches if m.home_score is not None)
    
    match_count = len(matches)
    
    if match_count == 0:
        return 1.0 if is_home else 1.3  # Default values
    
    return goals_conceded / match_count


def get_team_cards_avg(team: Team, is_home: bool, lookback_matches: int = 10) -> float:
    """
    Calculate the average cards per match for a team.
    
    Args:
        team: The Team model instance
        is_home: Whether to calculate for home or away games
        lookback_matches: Number of past matches to consider
        
    Returns:
        Average cards per match (default to value from Match model field if available)
    """
    # First try to get from match statistics fields if populated
    recent_matches = Match.objects.filter(
        status='FT'
    ).order_by('-kickoff')[:20]
    
    cards_values = []
    
    for match in recent_matches:
        if is_home and match.home_team == team and match.avg_cards_home is not None:
            cards_values.append(match.avg_cards_home)
        elif not is_home and match.away_team == team and match.avg_cards_away is not None:
            cards_values.append(match.avg_cards_away)
    
    if cards_values:
        return sum(cards_values) / len(cards_values)
    
    # Default values if no data available
    return 1.8 if is_home else 2.2


def get_team_form(team: Team, lookback_matches: int = 5) -> float:
    """
    Calculate the form value for a team.
    
    Args:
        team: The Team model instance
        lookback_matches: Number of past matches to consider
        
    Returns:
        Form value (higher is better)
    """
    # First try to get from match statistics fields if populated
    recent_matches = Match.objects.filter(
        status='FT'
    ).order_by('-kickoff')[:20]
    
    form_values = []
    
    for match in recent_matches:
        if match.home_team == team and match.team_form_home is not None:
            form_values.append(match.team_form_home)
        elif match.away_team == team and match.team_form_away is not None:
            form_values.append(match.team_form_away)
    
    if form_values:
        return sum(form_values) / len(form_values)
    
    # Calculate manually if not available from model fields
    # Home matches where the team was home
    home_as_home = Match.objects.filter(
        home_team=team,
        status='FT',
        home_score__isnull=False,
        away_score__isnull=False
    ).order_by('-kickoff')[:lookback_matches]
    
    # Home matches where the team was away
    home_as_away = Match.objects.filter(
        away_team=team,
        status='FT',
        home_score__isnull=False, 
        away_score__isnull=False
    ).order_by('-kickoff')[:lookback_matches]
    
    total_points = 0
    total_matches = len(home_as_home) + len(home_as_away)
    
    for match in home_as_home:
        if match.home_score > match.away_score:
            total_points += 3  # Win
        elif match.home_score == match.away_score:
            total_points += 1  # Draw
    
    for match in home_as_away:
        if match.away_score > match.home_score:
            total_points += 3  # Win
        elif match.home_score == match.away_score:
            total_points += 1  # Draw
    
    if total_matches == 0:
        return 7.0  # Default value
    
    # Scale to a range from 0-15
    return (total_points / total_matches) * 5


def extract_match_features(match: Match) -> Optional[Dict[str, Any]]:
    """
    Extract all features for a match needed for the ML model.
    
    Args:
        match: The Match model instance
        
    Returns:
        Dictionary of features or None if required data missing
    """
    try:
        # Get odds snapshot
        odds = get_odds_snapshot(match)
        
        if not odds:
            logger.warning(f"No odds found for match {match.id}: {match}")
            return None
        
        # Base features
        features = {
            # Basic odds
            'odds_home': odds.odds_home,
            'odds_draw': odds.odds_draw,
            'odds_away': odds.odds_away,
            
            # Team and league info
            'league_id': match.league.api_id if match.league and match.league.api_id else match.league.id,
            'team_home_rating': get_team_rating(match.home_team),
            'team_away_rating': get_team_rating(match.away_team),
            
            # Target variable
            'outcome': get_match_outcome(match)
        }
        
        # Add historical odds if available
        features['opening_odds_home'] = odds.opening_odds_home if odds.opening_odds_home else odds.odds_home
        features['opening_odds_draw'] = odds.opening_odds_draw if odds.opening_odds_draw else odds.odds_draw
        features['opening_odds_away'] = odds.opening_odds_away if odds.opening_odds_away else odds.odds_away
        
        features['closing_odds_home'] = odds.closing_odds_home if odds.closing_odds_home else odds.odds_home
        features['closing_odds_draw'] = odds.closing_odds_draw if odds.closing_odds_draw else odds.odds_draw
        features['closing_odds_away'] = odds.closing_odds_away if odds.closing_odds_away else odds.odds_away
        
        # Calculate odds deltas (line movement)
        features['odds_home_delta'] = features['closing_odds_home'] - features['opening_odds_home']
        features['odds_draw_delta'] = features['closing_odds_draw'] - features['opening_odds_draw']
        features['odds_away_delta'] = features['closing_odds_away'] - features['opening_odds_away']
        
        # Team ratings comparisons
        features['team_rating_diff'] = features['team_home_rating'] - features['team_away_rating']
        features['team_rating_ratio'] = features['team_home_rating'] / features['team_away_rating'] if features['team_away_rating'] > 0 else 1.0
        
        # Injuries
        features['injured_home_starters'] = match.injured_starters_home if match.injured_starters_home is not None else get_injured_starters(match, True)
        features['injured_away_starters'] = match.injured_starters_away if match.injured_starters_away is not None else get_injured_starters(match, False)
        features['injured_starters_diff'] = features['injured_home_starters'] - features['injured_away_starters']
        
        # Team form
        features['team_form_home'] = match.team_form_home if match.team_form_home is not None else get_team_form(match.home_team)
        features['team_form_away'] = match.team_form_away if match.team_form_away is not None else get_team_form(match.away_team)
        features['team_form_diff'] = features['team_form_home'] - features['team_form_away']
        
        # Recent form
        recent_form_diff = get_recent_form_diff(match.home_team, match.away_team)
        features['recent_form_diff'] = recent_form_diff
        features['recent_form_diff_per_match'] = recent_form_diff / 5  # Normalize by lookback matches
        
        # Goals statistics
        features['home_goals_avg'] = match.avg_goals_home if match.avg_goals_home is not None else get_team_goals_avg(match.home_team, True)
        features['away_goals_avg'] = match.avg_goals_away if match.avg_goals_away is not None else get_team_goals_avg(match.away_team, False)
        features['goals_avg_diff'] = features['home_goals_avg'] - features['away_goals_avg']
        
        # Goals conceded
        features['home_goals_conceded_avg'] = get_team_goals_conceded_avg(match.home_team, True)
        features['away_goals_conceded_avg'] = get_team_goals_conceded_avg(match.away_team, False)
        features['goals_conceded_diff'] = features['home_goals_conceded_avg'] - features['away_goals_conceded_avg']
        
        # Cards statistics
        features['home_cards_avg'] = match.avg_cards_home if match.avg_cards_home is not None else get_team_cards_avg(match.home_team, True)
        features['away_cards_avg'] = match.avg_cards_away if match.avg_cards_away is not None else get_team_cards_avg(match.away_team, False)
        features['cards_avg_diff'] = features['home_cards_avg'] - features['away_cards_avg']
        
        # Log match included
        logger.debug(f"Extracted features for match {match.id}: {match.home_team} vs {match.away_team}")
        
        return features
    
    except Exception as e:
        logger.error(f"Error extracting features for match {match.id}: {e}")
        return None


def clean_dataset(data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Clean and preprocess the extracted dataset.
    
    Args:
        data: List of feature dictionaries
        
    Returns:
        Cleaned pandas DataFrame
    """
    if not data:
        return pd.DataFrame(columns=FEATURE_COLUMNS)
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Fill missing values with appropriate defaults
    # For odds features
    odds_cols = [col for col in df.columns if 'odds' in col]
    for col in odds_cols:
        if col.startswith('odds_') and not col.endswith('delta'):
            # Fill missing basic odds with median
            df[col] = df[col].fillna(df[col].median())
        elif col.endswith('delta'):
            # Fill missing deltas with 0 (no movement)
            df[col] = df[col].fillna(0.0)
    
    # For team stats
    df['team_home_rating'] = df['team_home_rating'].fillna(75)
    df['team_away_rating'] = df['team_away_rating'].fillna(75)
    df['team_rating_diff'] = df['team_rating_diff'].fillna(0)
    df['team_rating_ratio'] = df['team_rating_ratio'].fillna(1.0)
    
    # For injury data
    df['injured_home_starters'] = df['injured_home_starters'].fillna(0)
    df['injured_away_starters'] = df['injured_away_starters'].fillna(0)
    df['injured_starters_diff'] = df['injured_starters_diff'].fillna(0)
    
    # For form data
    df['team_form_home'] = df['team_form_home'].fillna(7.5)
    df['team_form_away'] = df['team_form_away'].fillna(7.5)
    df['team_form_diff'] = df['team_form_diff'].fillna(0)
    df['recent_form_diff'] = df['recent_form_diff'].fillna(0)
    df['recent_form_diff_per_match'] = df['recent_form_diff_per_match'].fillna(0)
    
    # For goal data
    df['home_goals_avg'] = df['home_goals_avg'].fillna(1.5)
    df['away_goals_avg'] = df['away_goals_avg'].fillna(1.0)
    df['goals_avg_diff'] = df['goals_avg_diff'].fillna(0.5)
    df['home_goals_conceded_avg'] = df['home_goals_conceded_avg'].fillna(1.0)
    df['away_goals_conceded_avg'] = df['away_goals_conceded_avg'].fillna(1.3)
    df['goals_conceded_diff'] = df['goals_conceded_diff'].fillna(-0.3)
    
    # For card data
    df['home_cards_avg'] = df['home_cards_avg'].fillna(1.8)
    df['away_cards_avg'] = df['away_cards_avg'].fillna(2.2)
    df['cards_avg_diff'] = df['cards_avg_diff'].fillna(-0.4)
    
    # Standardize league_id to integer
    df['league_id'] = df['league_id'].astype(int)
    
    # Drop rows with missing outcome (target variable)
    df_cleaned = df.dropna(subset=['outcome'])
    
    # Log cleaning results
    missing = len(df) - len(df_cleaned)
    logger.info(f"Cleaned dataset: {len(df_cleaned)} rows kept, {missing} rows dropped due to missing target")
    
    # Check feature columns
    missing_cols = set(FEATURE_COLUMNS) - set(df_cleaned.columns)
    if missing_cols:
        logger.warning(f"Missing columns in dataset: {missing_cols}")
    
    return df_cleaned


def generate_training_dataset(months_limit: Optional[int] = None) -> pd.DataFrame:
    """
    Main function to generate the training dataset.
    
    Args:
        months_limit: Optional limit to only include matches from the last N months
        
    Returns:
        The processed DataFrame
    """
    logger.info(f"Starting training dataset generation{f' (last {months_limit} months)' if months_limit else ''}")
    
    # Get completed matches
    matches = get_completed_matches(months_limit)
    
    if not matches:
        logger.warning("No completed matches found with the required data")
        return pd.DataFrame(columns=FEATURE_COLUMNS)
    
    # Extract features for each match
    feature_data = []
    for match in matches:
        features = extract_match_features(match)
        if features:
            feature_data.append(features)
    
    logger.info(f"Extracted features for {len(feature_data)} matches")
    
    # Clean the dataset
    cleaned_df = clean_dataset(feature_data)
    
    return cleaned_df


def save_training_dataset(df: pd.DataFrame, output_path: str = None) -> str:
    """
    Save the training dataset to CSV.
    
    Args:
        df: The DataFrame to save
        output_path: Optional custom path to save the file
        
    Returns:
        The path where the file was saved
    """
    if df.empty:
        logger.warning("Cannot save empty dataset")
        return None
    
    # Use default or custom path
    filepath = output_path or OUTPUT_FILE
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Save to CSV
    df.to_csv(filepath, index=False)
    
    logger.info(f"Training dataset saved to {filepath} with {len(df)} rows")
    return filepath


def generate_and_save_dataset(months_limit: Optional[int] = None, output_path: str = None) -> str:
    """
    Generate and save the training dataset in one step.
    
    Args:
        months_limit: Optional limit to only include matches from the last N months
        output_path: Optional custom path to save the file
        
    Returns:
        The path where the file was saved or None if failed
    """
    try:
        # Generate the dataset
        df = generate_training_dataset(months_limit)
        
        if df.empty:
            logger.warning("Generated dataset is empty, not saving")
            return None
        
        # Save the dataset
        saved_path = save_training_dataset(df, output_path)
        return saved_path
        
    except Exception as e:
        logger.error(f"Error generating and saving dataset: {e}")
        return None


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Generate and save the dataset
    generate_and_save_dataset() 