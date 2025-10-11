"""
Collect match results from SportMonks API and update prediction logs.
Should be run daily (or hourly) to update completed matches.

Usage:
  python collect_match_results.py
  python collect_match_results.py --days 7  # Check last 7 days
  python collect_match_results.py --fixture-id 12345  # Check specific fixture
"""

import os
import sys
import json
import requests
import django
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartbet.settings')
django.setup()

from django.utils import timezone
from core.models import PredictionLog
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SPORTMONKS_API_TOKEN = os.getenv('SPORTMONKS_API_TOKEN')
if not SPORTMONKS_API_TOKEN:
    print("ERROR: SPORTMONKS_API_TOKEN not found in environment", file=sys.stderr)
    sys.exit(1)


def fetch_fixture_result(fixture_id):
    """Fetch fixture result from SportMonks API."""
    try:
        url = f"https://api.sportmonks.com/v3/football/fixtures/{fixture_id}"
        params = {
            'api_token': SPORTMONKS_API_TOKEN,
            'include': 'participants;scores',
            'timezone': 'UTC'
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        if 'data' in data:
            return data['data']
        else:
            print(f"WARNING: No data for fixture {fixture_id}")
            return None
            
    except Exception as e:
        print(f"ERROR fetching fixture {fixture_id}: {e}", file=sys.stderr)
        return None


def determine_outcome(fixture_data):
    """Determine match outcome from fixture data."""
    try:
        # Get final score
        scores = fixture_data.get('scores', [])
        if not scores:
            return None, None, None
        
        # Find full-time score
        home_score = None
        away_score = None
        
        for score in scores:
            if score.get('description') == 'CURRENT' or score.get('type_id') == 1525:  # Full-time score
                participant_id = score.get('participant_id')
                goals = score.get('score', {}).get('goals', 0)
                
                # Match with participants
                participants = fixture_data.get('participants', [])
                for participant in participants:
                    if participant.get('id') == participant_id:
                        if participant.get('meta', {}).get('location') == 'home':
                            home_score = goals
                        else:
                            away_score = goals
        
        if home_score is None or away_score is None:
            return None, None, None
        
        # Determine outcome
        if home_score > away_score:
            outcome = 'Home'
        elif away_score > home_score:
            outcome = 'Away'
        else:
            outcome = 'Draw'
        
        return outcome, home_score, away_score
        
    except Exception as e:
        print(f"ERROR determining outcome: {e}", file=sys.stderr)
        return None, None, None


def update_prediction_with_result(prediction_log, fixture_data):
    """Update prediction log with actual result."""
    try:
        # Get match status
        match_status = fixture_data.get('state', {}).get('short_name', 'UNKNOWN')
        
        # Only process finished matches
        if match_status not in ['FT', 'AET', 'APEN']:
            print(f"SKIP: Match {prediction_log.fixture_id} not finished (status: {match_status})")
            return False
        
        # Determine outcome
        outcome, home_score, away_score = determine_outcome(fixture_data)
        
        if outcome is None:
            print(f"WARNING: Could not determine outcome for fixture {prediction_log.fixture_id}")
            return False
        
        # Update prediction log
        prediction_log.actual_outcome = outcome
        prediction_log.actual_score_home = home_score
        prediction_log.actual_score_away = away_score
        prediction_log.match_status = match_status
        
        # Calculate performance
        prediction_log.calculate_performance()
        
        print(f"SUCCESS: Updated {prediction_log.home_team} vs {prediction_log.away_team}")
        print(f"         Predicted: {prediction_log.predicted_outcome} | Actual: {outcome} ({home_score}-{away_score})")
        print(f"         Result: {'CORRECT' if prediction_log.was_correct else 'INCORRECT'} | P/L: ${prediction_log.profit_loss_10:.2f if prediction_log.profit_loss_10 else 0}")
        
        return True
        
    except Exception as e:
        print(f"ERROR updating prediction {prediction_log.id}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def collect_results(days=3, specific_fixture_id=None):
    """Collect results for predictions."""
    if specific_fixture_id:
        # Process specific fixture
        try:
            prediction_log = PredictionLog.objects.get(fixture_id=specific_fixture_id)
            if prediction_log.actual_outcome:
                print(f"SKIP: Result already collected for fixture {specific_fixture_id}")
                return
            
            print(f"Fetching result for fixture {specific_fixture_id}...")
            fixture_data = fetch_fixture_result(specific_fixture_id)
            if fixture_data:
                update_prediction_with_result(prediction_log, fixture_data)
                
        except PredictionLog.DoesNotExist:
            print(f"ERROR: No prediction log found for fixture {specific_fixture_id}", file=sys.stderr)
            
    else:
        # Process predictions from last N days where result is not collected yet
        cutoff_date = timezone.now() - timedelta(days=days)
        
        predictions = PredictionLog.objects.filter(
            kickoff__gte=cutoff_date,
            kickoff__lte=timezone.now(),
            actual_outcome__isnull=True
        ).order_by('kickoff')
        
        total = predictions.count()
        print(f"\nFound {total} predictions without results from last {days} days")
        print(f"Collecting results...\n")
        
        updated = 0
        skipped = 0
        errors = 0
        
        for prediction_log in predictions:
            try:
                print(f"[{updated + skipped + errors + 1}/{total}] Checking {prediction_log.home_team} vs {prediction_log.away_team}...")
                
                fixture_data = fetch_fixture_result(prediction_log.fixture_id)
                if fixture_data:
                    if update_prediction_with_result(prediction_log, fixture_data):
                        updated += 1
                    else:
                        skipped += 1
                else:
                    errors += 1
                
                print()  # Blank line for readability
                
            except Exception as e:
                errors += 1
                print(f"ERROR: {e}\n", file=sys.stderr)
        
        # Summary
        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"  Updated: {updated}")
        print(f"  Skipped: {skipped}")
        print(f"  Errors: {errors}")
        print(f"{'='*60}\n")
        
        # Overall stats
        total_predictions = PredictionLog.objects.filter(actual_outcome__isnull=False).count()
        correct_predictions = PredictionLog.objects.filter(was_correct=True).count()
        
        if total_predictions > 0:
            accuracy = (correct_predictions / total_predictions) * 100
            print(f"Overall Performance:")
            print(f"  Total Completed: {total_predictions}")
            print(f"  Correct: {correct_predictions}")
            print(f"  Accuracy: {accuracy:.2f}%\n")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Collect match results from SportMonks API')
    parser.add_argument('--days', type=int, default=3, help='Check predictions from last N days')
    parser.add_argument('--fixture-id', type=int, help='Check specific fixture ID')
    
    args = parser.parse_args()
    
    collect_results(days=args.days, specific_fixture_id=args.fixture_id)


if __name__ == '__main__':
    main()

