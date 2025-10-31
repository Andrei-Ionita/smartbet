"""
Management command to log predictions to the database.
Can be called from Next.js API or run as a standalone script.
"""

import json
import sys
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import PredictionLog


class Command(BaseCommand):
    help = 'Log a prediction to the database for tracking'

    def add_arguments(self, parser):
        parser.add_argument('--json', type=str, help='JSON string with prediction data')
        parser.add_argument('--file', type=str, help='Path to JSON file with prediction data')

    def handle(self, *args, **options):
        # Get prediction data from JSON input
        prediction_data = None
        
        if options['json']:
            try:
                prediction_data = json.loads(options['json'])
            except json.JSONDecodeError as e:
                self.stdout.write(self.style.ERROR(f'Invalid JSON: {e}'))
                return
        
        elif options['file']:
            try:
                with open(options['file'], 'r') as f:
                    prediction_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                self.stdout.write(self.style.ERROR(f'Error reading file: {e}'))
                return
        
        else:
            # Read from stdin
            try:
                prediction_data = json.load(sys.stdin)
            except json.JSONDecodeError as e:
                self.stdout.write(self.style.ERROR(f'Invalid JSON from stdin: {e}'))
                return
        
        if not prediction_data:
            self.stdout.write(self.style.ERROR('No prediction data provided'))
            return
        
        # Log the prediction
        try:
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
                
                odds_home=prediction_data.get('odds_data', {}).get('home'),
                odds_draw=prediction_data.get('odds_data', {}).get('draw'),
                odds_away=prediction_data.get('odds_data', {}).get('away'),
                bookmaker=prediction_data.get('odds_data', {}).get('bookmaker'),
                expected_value=prediction_data.get('ev'),
                
                model_count=prediction_data.get('ensemble_info', {}).get('model_count', 0),
                consensus=prediction_data.get('ensemble_info', {}).get('consensus'),
                variance=prediction_data.get('ensemble_info', {}).get('variance'),
                ensemble_strategy=prediction_data.get('ensemble_info', {}).get('strategy', 'consensus_ensemble'),
                
                recommendation_score=prediction_data.get('score'),
                is_recommended=prediction_data.get('is_recommended', False)  # Mark as recommended if explicitly set
            )
            
            self.stdout.write(self.style.SUCCESS(
                f'✅ Logged prediction {prediction_log.id}: {prediction_log.home_team} vs {prediction_log.away_team}'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'   Predicted: {prediction_log.predicted_outcome} ({prediction_log.confidence}%)'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'   Timestamp: {prediction_log.prediction_logged_at}'
            ))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error logging prediction: {e}'))
            import traceback
            traceback.print_exc()

