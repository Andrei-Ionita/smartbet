"""
Standalone script to log predictions to Django database.
Can be called from Next.js API or run independently.

Usage:
  python log_predictions_to_db.py '{"fixture_id": 123, "home_team": "Team A", ...}'
  echo '{"fixture_id": 123, ...}' | python log_predictions_to_db.py
  python log_predictions_to_db.py --file predictions.json
"""

import os
import sys
import json
import django

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartbet.settings')
django.setup()

from django.utils import timezone
from core.models import PredictionLog


def log_single_prediction(prediction_data):
    """Log a single prediction to the database."""
    try:
        # Check if already exists
        if PredictionLog.objects.filter(fixture_id=prediction_data['fixture_id']).exists():
            print(f"SKIP: Prediction for fixture {prediction_data['fixture_id']} already logged")
            return False
        
        prediction_log = PredictionLog.objects.create(
            fixture_id=prediction_data['fixture_id'],
            home_team=prediction_data['home_team'],
            away_team=prediction_data['away_team'],
            league=prediction_data['league'],
            league_id=prediction_data.get('league_id'),
            kickoff=prediction_data['kickoff'],
            
            predicted_outcome=prediction_data['predicted_outcome'],
            confidence=prediction_data['confidence'],
            
            probability_home=prediction_data['probabilities']['home'],
            probability_draw=prediction_data['probabilities']['draw'],
            probability_away=prediction_data['probabilities']['away'],
            
            odds_home=prediction_data.get('odds_data', {}).get('home') if prediction_data.get('odds_data') else None,
            odds_draw=prediction_data.get('odds_data', {}).get('draw') if prediction_data.get('odds_data') else None,
            odds_away=prediction_data.get('odds_data', {}).get('away') if prediction_data.get('odds_data') else None,
            bookmaker=prediction_data.get('odds_data', {}).get('bookmaker') if prediction_data.get('odds_data') else None,
            expected_value=prediction_data.get('ev'),
            
            model_count=prediction_data.get('ensemble_info', {}).get('model_count', 0) if prediction_data.get('ensemble_info') else 0,
            consensus=prediction_data.get('ensemble_info', {}).get('consensus') if prediction_data.get('ensemble_info') else None,
            variance=prediction_data.get('ensemble_info', {}).get('variance') if prediction_data.get('ensemble_info') else None,
            ensemble_strategy=prediction_data.get('ensemble_info', {}).get('strategy', 'consensus_ensemble') if prediction_data.get('ensemble_info') else 'consensus_ensemble',
            
            recommendation_score=prediction_data.get('score')
        )
        
        print(f"SUCCESS: Logged {prediction_log.home_team} vs {prediction_log.away_team} - {prediction_log.predicted_outcome} ({prediction_log.confidence}%)")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return False


def log_batch_predictions(predictions_data):
    """Log multiple predictions in batch."""
    if not isinstance(predictions_data, list):
        print("ERROR: Expected array of predictions for batch logging", file=sys.stderr)
        return
    
    logged = 0
    skipped = 0
    errors = 0
    
    for prediction_data in predictions_data:
        try:
            result = log_single_prediction(prediction_data)
            if result:
                logged += 1
            else:
                skipped += 1
        except Exception as e:
            errors += 1
            print(f"ERROR: {e}", file=sys.stderr)
    
    print(f"\nSummary: {logged} logged | {skipped} skipped | {errors} errors")
    print(f"Total in DB: {PredictionLog.objects.count()}")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Read from command line argument
        if sys.argv[1] == '--file':
            # Read from file
            try:
                with open(sys.argv[2], 'r') as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError, IndexError) as e:
                print(f"ERROR reading file: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            # Read from argument
            try:
                data = json.loads(sys.argv[1])
            except json.JSONDecodeError as e:
                print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
                sys.exit(1)
    else:
        # Read from stdin
        try:
            data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON from stdin: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Process data
    if isinstance(data, list):
        log_batch_predictions(data)
    else:
        log_single_prediction(data)


if __name__ == '__main__':
    main()

