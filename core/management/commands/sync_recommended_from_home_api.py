"""
Management command to sync recommended predictions based on fixture_ids from the home page recommendations API.
This fetches the actual recommendations shown on the home page and marks matching PredictionLog entries.
"""

import os
import sys
import requests
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import PredictionLog


class Command(BaseCommand):
    help = 'Sync recommended predictions from home page recommendations API fixture_ids'

    def add_arguments(self, parser):
        parser.add_argument(
            '--api-url',
            type=str,
            default='http://localhost:3000/api/recommendations',
            help='URL of the recommendations API endpoint (default: http://localhost:3000/api/recommendations)'
        )
        parser.add_argument(
            '--unmark-others',
            action='store_true',
            help='Unmark predictions that are no longer in the recommendations'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be marked without actually marking them'
        )

    def handle(self, *args, **options):
        api_url = options['api_url']
        unmark_others = options['unmark_others']
        dry_run = options['dry_run']

        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('SYNCING RECOMMENDED PREDICTIONS FROM HOME PAGE API'))
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
            
            # Extract fixture_ids from recommendations
            fixture_ids = [rec['fixture_id'] for rec in recommendations]
            
            self.stdout.write(f'Found {len(fixture_ids)} recommendations from API')
            self.stdout.write(f'Fixture IDs: {fixture_ids}\n')
            
            # Find matching PredictionLog entries
            matching_predictions = PredictionLog.objects.filter(fixture_id__in=fixture_ids)
            matching_count = matching_predictions.count()
            
            self.stdout.write(f'Found {matching_count} matching PredictionLog entries\n')
            
            if matching_count == 0:
                self.stdout.write(self.style.WARNING(
                    'No PredictionLog entries found matching the recommendation fixture_ids.\n'
                    'Make sure predictions are logged to the database with the correct fixture_ids.'
                ))
                return
            
            # Show what will be marked
            self.stdout.write(self.style.SUCCESS('Predictions that will be marked as recommended:'))
            self.stdout.write(self.style.SUCCESS('-'*80))
            
            for pred in matching_predictions:
                rec = next((r for r in recommendations if r['fixture_id'] == pred.fixture_id), None)
                self.stdout.write(
                    f'  [*] {pred.home_team} vs {pred.away_team} | '
                    f'{pred.predicted_outcome} (Conf: {pred.confidence:.1f}%, '
                    f'EV: {pred.expected_value:.2f}%) | {pred.league}'
                )
            
            # Check for fixture_ids not found
            found_fixture_ids = set(matching_predictions.values_list('fixture_id', flat=True))
            missing_fixture_ids = set(fixture_ids) - found_fixture_ids
            
            if missing_fixture_ids:
                self.stdout.write(self.style.WARNING(f'\nWarning: {len(missing_fixture_ids)} fixture_ids from API not found in PredictionLog:'))
                for fid in missing_fixture_ids:
                    self.stdout.write(f'  - {fid}')
                self.stdout.write(self.style.WARNING(
                    'These predictions may need to be logged to the database first.'
                ))
            
            if dry_run:
                self.stdout.write(self.style.WARNING('\nDRY RUN - No predictions were actually marked'))
                return
            
            # Unmark others if requested
            if unmark_others:
                unmarked_count = PredictionLog.objects.filter(
                    is_recommended=True
                ).exclude(
                    fixture_id__in=fixture_ids
                ).update(is_recommended=False)
                
                if unmarked_count > 0:
                    self.stdout.write(self.style.WARNING(f'\nUnmarked {unmarked_count} predictions that are no longer in recommendations'))
            
            # Mark the matching predictions as recommended
            updated_count = matching_predictions.update(is_recommended=True)
            
            self.stdout.write(self.style.SUCCESS(f'\nSuccessfully marked {updated_count} predictions as recommended!\n'))
            
            # Show statistics
            total_recommended = PredictionLog.objects.filter(is_recommended=True).count()
            self.stdout.write(f'Total recommended predictions in database: {total_recommended}')
            
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

