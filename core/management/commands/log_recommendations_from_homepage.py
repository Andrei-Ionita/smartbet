"""
Management command to fetch recommendations from the home page API and log them to the database.
This ensures recommended predictions are tracked for accuracy monitoring.
"""

import os
import sys
import json
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

    # The default URL must resolve in the deployed environment. Prior default
    # was http://localhost:3000 — local Next.js dev port — which doesn't exist
    # in the Railway container, so the Procfile worker calling this command
    # every 60 minutes was silently 404ing for months. Production picks were
    # only landing in PredictionLog when a user happened to load the homepage
    # and the Next.js endpoint POSTed them back (traffic-coupled persistence).
    # Override via env var for local dev:  RECOMMENDATIONS_API_URL=http://localhost:3000/api/recommendations
    DEFAULT_API_URL = os.environ.get(
        'RECOMMENDATIONS_API_URL',
        'https://www.betglitch.com/api/recommendations',
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--api-url',
            type=str,
            default=self.DEFAULT_API_URL,
            help='URL of the recommendations API endpoint (override default with RECOMMENDATIONS_API_URL env var)'
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
            # Fetch recommendations from the home page API.
            # The Next.js engine iterates 27 leagues with sequential SportMonks calls,
            # comfortably taking 20-40s. The previous 10s timeout was abandoning the
            # request before any response arrived — yet another silent failure mode.
            response = requests.get(api_url, timeout=90)
            response.raise_for_status()
            data = response.json()
            
            recommendations = data.get('recommendations', [])
            
            if not recommendations:
                self.stdout.write(self.style.WARNING('No recommendations found in API response'))
                return
            
            self.stdout.write(f'Found {len(recommendations)} recommendations from homepage\n')
            
            # ── ONE write path ────────────────────────────────────────────
            # This command previously duplicated ~130 lines of the persistence
            # logic in core.api_views.log_recommendations. The two drifted: when
            # the immutable-snapshot layer landed in the view, this command kept
            # writing PredictionLog rows WITHOUT recording snapshots, so a
            # scheduled run would have produced nothing publishable.
            #
            # It now calls the shared ingest service, so there is exactly one
            # place that decides how a prediction run is persisted.
            if dry_run:
                self.stdout.write(self.style.WARNING(
                    f'DRY RUN: would ingest {len(recommendations)} recommendations '
                    'through core.services.recommendation_ingest'
                ))
                logged_count = updated_count = skipped_count = 0
                snapshots_created = 0
            else:
                # Calls the ingest service directly. It used to build a fake
                # HTTP request and invoke the view; now that the view requires
                # an HMAC signature, that would mean the scheduler signing
                # requests to itself. The service is the shared write path —
                # the view is only the authenticated boundary in front of it.
                from core.services import recommendation_ingest

                try:
                    payload = recommendation_ingest.ingest_recommendations(
                        recommendations
                    )
                except recommendation_ingest.ValidationError as exc:
                    self.stdout.write(self.style.ERROR(
                        f'Ingest rejected {len(recommendations)} recommendations: '
                        f'{exc.errors[:3]}'
                    ))
                    return

                logged_count = payload.get('logged_count', 0)
                updated_count = payload.get('updated_count', 0)
                snapshots_created = payload.get('snapshots_created', 0)
                skipped_count = (
                    payload.get('skipped_blacklist', 0)
                    + payload.get('skipped_outcome', 0)
                    + payload.get('skipped_high_ev', 0)
                    + payload.get('skipped_watchlist', 0)
                )
                self.stdout.write(
                    f"Run {payload.get('prediction_run_id')}: "
                    f'{snapshots_created} immutable snapshots appended'
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
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\nUnexpected error: {e}'))
            import traceback
            traceback.print_exc()
            return

