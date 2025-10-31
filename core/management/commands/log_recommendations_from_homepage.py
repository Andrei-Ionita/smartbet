"""
Management command to fetch recommendations from the home page API and log them to the database.
This ensures recommended predictions are tracked for accuracy monitoring.
"""

import os
import sys
import requests
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartbet.settings')
django.setup()

from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import PredictionLog
from datetime import datetime


class Command(BaseCommand):
    help = 'Fetch recommendations from home page API and log them to PredictionLog database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--api-url',
            type=str,
            default='http://localhost:3000/api/recommendations',
            help='URL of the recommendations API endpoint'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be logged without actually logging'
        )

    def handle(self, *args, **options):
        api_url = options['api_url']
        dry_run = options['dry_run']

        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('LOGGING RECOMMENDATIONS FROM HOMEPAGE'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
        self.stdout.write(f'Fetching recommendations from: {api_url}\n')

        try:
            # Fetch recommendations from the home page API
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            recommendations = data.get('recommendations', [])
            
            if not recommendations:
                self.stdout.write(self.style.WARNING('No recommendations found in API response'))
                return
            
            self.stdout.write(f'Found {len(recommendations)} recommendations from homepage\n')
            
            logged_count = 0
            updated_count = 0
            skipped_count = 0
            
            for rec in recommendations:
                fixture_id = rec.get('fixture_id')
                if not fixture_id:
                    continue
                
                # Check if already exists
                existing = PredictionLog.objects.filter(fixture_id=fixture_id).first()
                
                # Prepare prediction data
                kickoff_str = rec.get('kickoff')
                if isinstance(kickoff_str, str):
                    try:
                        # Parse ISO format datetime
                        kickoff = datetime.fromisoformat(kickoff_str.replace('Z', '+00:00'))
                    except:
                        try:
                            from dateutil import parser
                            kickoff = parser.parse(kickoff_str)
                        except:
                            self.stdout.write(self.style.WARNING(f'Could not parse kickoff date for fixture {fixture_id}'))
                            skipped_count += 1
                            continue
                else:
                    kickoff = timezone.now()
                
                # Normalize probabilities
                probabilities = rec.get('probabilities', {})
                prob_home = probabilities.get('home', 0)
                prob_draw = probabilities.get('draw', 0)
                prob_away = probabilities.get('away', 0)
                
                # Normalize confidence - could be percentage (55) or decimal (0.55)
                confidence = rec.get('confidence', 0)
                if confidence > 1:
                    confidence = confidence / 100  # Convert percentage to decimal
                
                # Normalize EV - API returns as percentage (10.0 = 10%), convert to decimal for storage
                expected_value = rec.get('expected_value') or rec.get('ev')
                if expected_value is not None:
                    if expected_value > 1:
                        expected_value = expected_value / 100  # Convert percentage to decimal
                
                # Normalize probabilities - convert percentages to decimals if needed
                if prob_home > 1:
                    prob_home = prob_home / 100
                if prob_draw > 1:
                    prob_draw = prob_draw / 100
                if prob_away > 1:
                    prob_away = prob_away / 100
                
                odds_data = rec.get('odds_data', {})
                
                prediction_data = {
                    'fixture_id': fixture_id,
                    'home_team': rec.get('home_team', 'Unknown'),
                    'away_team': rec.get('away_team', 'Unknown'),
                    'league': rec.get('league', 'Unknown'),
                    'league_id': None,  # Not provided by API
                    'kickoff': kickoff,
                    'predicted_outcome': rec.get('predicted_outcome', 'Home').lower(),
                    'confidence': confidence,
                    'probability_home': prob_home,
                    'probability_draw': prob_draw,
                    'probability_away': prob_away,
                    'odds_home': odds_data.get('home'),
                    'odds_draw': odds_data.get('draw'),
                    'odds_away': odds_data.get('away'),
                    'bookmaker': odds_data.get('bookmaker'),
                    'expected_value': expected_value,
                    'model_count': rec.get('ensemble_info', {}).get('model_count', 0),
                    'consensus': rec.get('ensemble_info', {}).get('consensus'),
                    'variance': rec.get('ensemble_info', {}).get('variance'),
                    'ensemble_strategy': rec.get('ensemble_info', {}).get('strategy', 'consensus_ensemble'),
                    'recommendation_score': rec.get('revenue_vs_risk_score'),
                    'is_recommended': True  # Mark as recommended since they come from homepage
                }
                
                if dry_run:
                    self.stdout.write(
                        f'  [DRY RUN] Would log: {prediction_data["home_team"]} vs {prediction_data["away_team"]} '
                        f'({prediction_data["predicted_outcome"]}, conf: {confidence*100:.1f}%)'
                    )
                    logged_count += 1
                    continue
                
                if existing:
                    # Update existing prediction
                    for key, value in prediction_data.items():
                        setattr(existing, key, value)
                    existing.is_recommended = True  # Ensure it's marked as recommended
                    existing.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  [UPDATED] {existing.home_team} vs {existing.away_team}')
                    )
                else:
                    # Create new prediction
                    prediction_log = PredictionLog.objects.create(**prediction_data)
                    logged_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  [LOGGED] {prediction_log.home_team} vs {prediction_log.away_team}')
                    )
            
            self.stdout.write('\n' + '='*80)
            if dry_run:
                self.stdout.write(self.style.SUCCESS(f'DRY RUN: Would log {logged_count} predictions'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Successfully logged {logged_count} new predictions'))
                self.stdout.write(self.style.SUCCESS(f'Updated {updated_count} existing predictions'))
                if skipped_count > 0:
                    self.stdout.write(self.style.WARNING(f'Skipped {skipped_count} predictions (missing data)'))
                
                total_recommended = PredictionLog.objects.filter(is_recommended=True).count()
                self.stdout.write(f'\nTotal recommended predictions in database: {total_recommended}')
            
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'\nError fetching recommendations from API: {e}'))
            self.stdout.write(self.style.ERROR(
                'Make sure the frontend server is running and the API endpoint is accessible.'
            ))
            sys.exit(1)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\nUnexpected error: {e}'))
            import traceback
            traceback.print_exc()
            sys.exit(1)

