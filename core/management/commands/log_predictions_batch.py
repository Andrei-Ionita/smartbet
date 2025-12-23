"""
Management command to log multiple predictions in batch.
Useful for logging all recommendations from the API at once.
"""

import json
import sys
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from core.models import PredictionLog


class Command(BaseCommand):
    help = 'Log multiple predictions to the database in batch'

    def add_arguments(self, parser):
        parser.add_argument('--json', type=str, help='JSON string with array of predictions')
        parser.add_argument('--file', type=str, help='Path to JSON file with array of predictions')

    def handle(self, *args, **options):
        # Get predictions data
        predictions_data = None
        
        if options['json']:
            try:
                predictions_data = json.loads(options['json'])
            except json.JSONDecodeError as e:
                self.stdout.write(self.style.ERROR(f'Invalid JSON: {e}'))
                return
        
        elif options['file']:
            try:
                with open(options['file'], 'r') as f:
                    predictions_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                self.stdout.write(self.style.ERROR(f'Error reading file: {e}'))
                return
        
        else:
            # Read from stdin
            try:
                predictions_data = json.load(sys.stdin)
            except json.JSONDecodeError as e:
                self.stdout.write(self.style.ERROR(f'Invalid JSON from stdin: {e}'))
                return
        
        if not predictions_data:
            self.stdout.write(self.style.ERROR('No predictions data provided'))
            return
        
        # Ensure it's a list
        if not isinstance(predictions_data, list):
            self.stdout.write(self.style.ERROR('Expected array of predictions'))
            return
        
        # Log all predictions in a transaction
        logged_count = 0
        skipped_count = 0
        error_count = 0
        
        with transaction.atomic():
            for prediction_data in predictions_data:
                try:
                    # Check if already logged
                    if PredictionLog.objects.filter(fixture_id=prediction_data['fixture_id']).exists():
                        skipped_count += 1
                        continue
                    
                    PredictionLog.objects.create(
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
                        
                        # Store form data if available
                        home_team_form=prediction_data.get('teams_data', {}).get('home', {}).get('form'),
                        away_team_form=prediction_data.get('teams_data', {}).get('away', {}).get('form'),
                        
                        odds_home=prediction_data.get('odds_data', {}).get('home') if prediction_data.get('odds_data') else None,
                        odds_draw=prediction_data.get('odds_data', {}).get('draw') if prediction_data.get('odds_data') else None,
                        odds_away=prediction_data.get('odds_data', {}).get('away') if prediction_data.get('odds_data') else None,
                        bookmaker=prediction_data.get('odds_data', {}).get('bookmaker') if prediction_data.get('odds_data') else None,
                        expected_value=prediction_data.get('ev'),
                        
                        model_count=prediction_data.get('ensemble_info', {}).get('model_count', 0) if prediction_data.get('ensemble_info') else 0,
                        consensus=prediction_data.get('ensemble_info', {}).get('consensus') if prediction_data.get('ensemble_info') else None,
                        variance=prediction_data.get('ensemble_info', {}).get('variance') if prediction_data.get('ensemble_info') else None,
                        ensemble_strategy=prediction_data.get('ensemble_info', {}).get('strategy', 'consensus_ensemble') if prediction_data.get('ensemble_info') else 'consensus_ensemble',
                        
                        recommendation_score=prediction_data.get('score'),
                        is_recommended=prediction_data.get('is_recommended', False)  # Mark as recommended if explicitly set
                    )
                    
                    logged_count += 1
                    
                except Exception as e:
                    error_count += 1
                    self.stdout.write(self.style.WARNING(
                        f'⚠️  Error logging {prediction_data.get("home_team")} vs {prediction_data.get("away_team")}: {e}'
                    ))
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n📊 Batch Logging Summary:'))
        self.stdout.write(self.style.SUCCESS(f'   ✅ Logged: {logged_count}'))
        self.stdout.write(self.style.WARNING(f'   ⏭️  Skipped (already exists): {skipped_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'   ❌ Errors: {error_count}'))
        self.stdout.write(self.style.SUCCESS(f'   📅 Total predictions in database: {PredictionLog.objects.count()}'))

