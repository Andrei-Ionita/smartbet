"""
Result Updater Service - Fetches actual match outcomes from SportMonks API
Updates PredictionLog with real results for transparency and accuracy tracking
"""

import os
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from typing import Dict, List, Optional
import logging

from core.models import PredictionLog

logger = logging.getLogger(__name__)


class ResultUpdaterService:
    """
    Service to update PredictionLog entries with actual match results.
    Fetches completed fixtures from SportMonks and updates outcomes.
    """
    
    def __init__(self):
        self.api_token = os.getenv('SPORTMONKS_API_TOKEN')
        if not self.api_token:
            raise ValueError("SPORTMONKS_API_TOKEN not set in environment")
        
        self.base_url = "https://api.sportmonks.com/v3/football"
    
    # SportMonks archives fixtures after they age out of the live data set
    # (empirically ~30-90 days). Calls for those fixtures 404 indefinitely. We cap
    # the lookback so old never-settled rows don't burn API calls forever. Anything
    # past this is also marked match_status='archived' on the first 404 (see
    # fetch_fixture_result), so even within the window we never re-check a known
    # dead fixture.
    MAX_LOOKBACK_DAYS = 14

    def get_pending_predictions(self, hours_after_kickoff: int = 3) -> List[PredictionLog]:
        """
        Get predictions that need result updates.

        Args:
            hours_after_kickoff: Hours after kickoff before checking (default 3)

        Returns:
            QuerySet of PredictionLog entries needing updates
        """
        now = timezone.now()
        cutoff_time = now - timedelta(hours=hours_after_kickoff)
        max_age_cutoff = now - timedelta(days=self.MAX_LOOKBACK_DAYS)

        pending = PredictionLog.objects.filter(
            actual_outcome__isnull=True,  # No result yet
            kickoff__lt=cutoff_time,      # Match should be finished
            kickoff__gte=max_age_cutoff,  # But not so old SportMonks has archived it
            match_status__isnull=True     # Status not updated
        ).order_by('kickoff')

        logger.info(f"Found {pending.count()} predictions awaiting results (within {self.MAX_LOOKBACK_DAYS}d window)")
        return list(pending)
    
    # Sentinel value returned by fetch_fixture_result when SportMonks no longer
    # serves a fixture (HTTP 404). Caller uses this to mark the prediction
    # match_status='archived' so it never gets re-checked.
    ARCHIVED_RESULT = {'_archived': True}

    def fetch_fixture_result(self, fixture_id: int) -> Optional[Dict]:
        """
        Fetch result for a specific fixture from SportMonks API.

        Args:
            fixture_id: SportMonks fixture ID

        Returns:
            Dictionary with result data or None if not available, or the
            ARCHIVED_RESULT sentinel if SportMonks returns 404 (fixture has
            aged out of their data; we'll never get a result for it).
        """
        try:
            url = f"{self.base_url}/fixtures/{fixture_id}"
            params = {
                'api_token': self.api_token,
                'include': 'scores,state,participants'
            }

            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 404:
                logger.info(f"Fixture {fixture_id} not found in SportMonks (archived)")
                return self.ARCHIVED_RESULT
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' not in data:
                logger.warning(f"No data for fixture {fixture_id}")
                return None
            
            fixture = data['data']
            
            # Check if match is finished
            state = fixture.get('state', {})
            if not state or state.get('state') not in ['FT', 'AET', 'FT_PEN']:
                logger.info(f"Fixture {fixture_id} not finished yet. State: {state.get('state')}")
                return None
            
            # Get scores
            scores = fixture.get('scores', [])
            participants = fixture.get('participants', [])
            
            # Find final score
            home_score = None
            away_score = None
            
            for score in scores:
                if score.get('description') in ['CURRENT', 'FT']:
                    participant_id = score.get('participant_id')
                    score_value = score.get('score', {}).get('goals')
                    
                    # Determine if home or away
                    for participant in participants:
                        if participant.get('id') == participant_id:
                            if participant.get('meta', {}).get('location') == 'home':
                                home_score = score_value
                            elif participant.get('meta', {}).get('location') == 'away':
                                away_score = score_value
            
            if home_score is None or away_score is None:
                logger.warning(f"Could not extract scores for fixture {fixture_id}")
                return None
            
            # Determine outcome
            if home_score > away_score:
                outcome = 'Home'
            elif away_score > home_score:
                outcome = 'Away'
            else:
                outcome = 'Draw'
            
            return {
                'actual_outcome': outcome,
                'actual_score_home': home_score,
                'actual_score_away': away_score,
                'match_status': state.get('state', 'FT')
            }
            
        except requests.RequestException as e:
            logger.error(f"API error fetching fixture {fixture_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing fixture {fixture_id}: {e}")
            return None
    
    def update_prediction_result(self, prediction: PredictionLog, result_data: Dict) -> bool:
        """
        Update a PredictionLog entry with actual result.
        
        Args:
            prediction: PredictionLog instance
            result_data: Dictionary with actual_outcome, scores, etc.
        
        Returns:
            True if updated successfully
        """
        try:
            # Update fields
            prediction.actual_outcome = result_data['actual_outcome']
            prediction.actual_score_home = result_data['actual_score_home']
            prediction.actual_score_away = result_data['actual_score_away']
            prediction.match_status = result_data['match_status']
            
            # Calculate if prediction was correct
            prediction.calculate_performance()
            
            logger.info(
                f"Updated {prediction.home_team} vs {prediction.away_team}: "
                f"Predicted {prediction.predicted_outcome}, Actual {prediction.actual_outcome}, "
                f"Correct: {prediction.was_correct}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating prediction {prediction.id}: {e}")
            return False
    
    def update_all_pending_results(self, max_predictions: int = 100) -> Dict:
        """
        Update all pending predictions with results.
        
        Args:
            max_predictions: Maximum number to update in one run
        
        Returns:
            Dictionary with update statistics
        """
        pending = self.get_pending_predictions()[:max_predictions]
        
        stats = {
            'total_checked': len(pending),
            'updated': 0,
            'still_pending': 0,
            'errors': 0,
            'correct_predictions': 0,
            'incorrect_predictions': 0
        }
        
        stats['archived'] = 0

        for prediction in pending:
            logger.info(f"Checking fixture {prediction.fixture_id}: {prediction.home_team} vs {prediction.away_team}")

            result_data = self.fetch_fixture_result(prediction.fixture_id)

            if result_data is self.ARCHIVED_RESULT:
                # Permanently gone from SportMonks. Mark archived so the pending
                # filter (match_status__isnull=True) drops it from future cycles.
                # Use queryset .update() to bypass the model's save() invariants
                # entirely — we have no reason to re-validate EV/odds on a row
                # we're only flagging.
                PredictionLog.objects.filter(pk=prediction.pk).update(match_status='archived')
                stats['archived'] += 1
            elif result_data:
                if self.update_prediction_result(prediction, result_data):
                    stats['updated'] += 1
                    if prediction.was_correct:
                        stats['correct_predictions'] += 1
                    else:
                        stats['incorrect_predictions'] += 1
                else:
                    stats['errors'] += 1
            else:
                stats['still_pending'] += 1
        
        # Calculate accuracy
        if stats['updated'] > 0:
            accuracy = (stats['correct_predictions'] / stats['updated']) * 100
            stats['accuracy'] = round(accuracy, 1)
        else:
            stats['accuracy'] = None
        
        logger.info(f"Result update complete: {stats}")
        
        return stats
    
    def update_single_fixture(self, fixture_id: int) -> Dict:
        """
        Update result for a single fixture.
        
        Args:
            fixture_id: SportMonks fixture ID
        
        Returns:
            Dictionary with update status
        """
        try:
            prediction = PredictionLog.objects.get(fixture_id=fixture_id)
            
            if prediction.actual_outcome:
                return {
                    'success': False,
                    'message': 'Result already exists',
                    'prediction': prediction.predicted_outcome,
                    'actual': prediction.actual_outcome
                }
            
            result_data = self.fetch_fixture_result(fixture_id)

            if result_data is self.ARCHIVED_RESULT:
                PredictionLog.objects.filter(pk=prediction.pk).update(match_status='archived')
                return {
                    'success': False,
                    'message': f'Fixture {fixture_id} not in SportMonks anymore — marked archived',
                    'archived': True,
                }

            if not result_data:
                return {
                    'success': False,
                    'message': 'Result not available yet or API error'
                }
            
            self.update_prediction_result(prediction, result_data)
            
            return {
                'success': True,
                'message': 'Result updated successfully',
                'fixture_id': fixture_id,
                'predicted': prediction.predicted_outcome,
                'actual': prediction.actual_outcome,
                'was_correct': prediction.was_correct,
                'profit_loss': float(prediction.profit_loss_10) if prediction.profit_loss_10 else None
            }
            
        except PredictionLog.DoesNotExist:
            return {
                'success': False,
                'message': 'Prediction not found in database'
            }
        except Exception as e:
            logger.error(f"Error updating fixture {fixture_id}: {e}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }

