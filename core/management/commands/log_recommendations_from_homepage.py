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
from core.services.redaction import redact, redact_exception
from datetime import datetime


#: Fields the ingest path genuinely requires, and what reads each one.
#:
#: `expected_value`/`ev`      -> PredictionLog.expected_value
#: `best_market.original_ev`  -> PredictionLog.raw_expected_value
#: `best_market.market_score` -> PredictionLog.market_score
#: `best_market.type`         -> PredictionLog.market_type
#: `fixture_id`, `confidence` -> row identity and the frozen score
#:
#: See core/services/recommendation_ingest.py, which is the only write path.
REQUIRED_TOP_LEVEL = ('fixture_id', 'confidence')
REQUIRED_BEST_MARKET = ('type', 'market_score', 'original_ev')

#: How many rows to inspect. Enough to catch a wrong-endpoint payload without
#: turning validation into a second pass over the batch.
SCHEMA_SAMPLE_SIZE = 3


def validate_internal_schema(recommendations):
    """Return a list of human-readable problems; empty means the shape is good.

    Deliberately checks presence, not values: this guards against receiving the
    PUBLIC payload (or a truncated one), which is a wiring fault. It is not a
    data-quality filter — an imperfect but complete row is still classified
    downstream by public_universe.status_for rather than rejected here.
    """
    problems = []
    for index, rec in enumerate(recommendations[:SCHEMA_SAMPLE_SIZE]):
        if not isinstance(rec, dict):
            problems.append(f'row {index} is not an object')
            continue

        for field in REQUIRED_TOP_LEVEL:
            if rec.get(field) is None:
                problems.append(f'row {index}: {field} missing')

        # expected_value and ev are aliases; ingestion accepts either.
        if rec.get('expected_value') is None and rec.get('ev') is None:
            problems.append(f'row {index}: expected_value/ev both missing')

        best_market = rec.get('best_market')
        if not isinstance(best_market, dict):
            problems.append(f'row {index}: best_market missing')
            continue
        for field in REQUIRED_BEST_MARKET:
            if best_market.get(field) is None:
                problems.append(f'row {index}: best_market.{field} missing')

    return problems


class Command(BaseCommand):
    help = 'Fetch recommendations from home page API and log them to PredictionLog database'

    # The default URL must resolve in the deployed environment. Prior default
    # was http://localhost:3000 — local Next.js dev port — which doesn't exist
    # in the Railway container, so the Procfile worker calling this command
    # every 60 minutes was silently 404ing for months. Production picks were
    # only landing in PredictionLog when a user happened to load the homepage
    # and the Next.js endpoint POSTed them back (traffic-coupled persistence).
    # Override via env var for local dev:  RECOMMENDATIONS_API_URL=http://localhost:3000/api/recommendations
    # The INTERNAL feed, not the public one.
    #
    # /api/recommendations serves an allowlisted public DTO with no
    # expected_value, no best_market.original_ev and no market_score, because
    # none of those are defensible publicly. Ingestion writes exactly those
    # fields onto every PredictionLog row, so pointing this command at the
    # public URL would record a null EV against every prediction — silently,
    # behind a 200 OK and a well-formed body.
    DEFAULT_API_URL = os.environ.get(
        'RECOMMENDATIONS_API_URL',
        'https://www.betglitch.com/api/internal/recommendations',
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
            # The internal feed is fail-closed: without the secret it answers
            # 401 and there is nothing to ingest. Check here anyway so the
            # failure names the cause instead of surfacing as an HTTP error.
            internal_secret = os.environ.get('INTERNAL_API_SECRET', '')
            if not internal_secret:
                raise RuntimeError(
                    'INTERNAL_API_SECRET is not set, so the internal '
                    'recommendations feed cannot be reached. Refusing to '
                    'ingest.'
                )

            response = requests.get(
                api_url,
                timeout=90,
                headers={'X-Internal-Auth': internal_secret},
            )
            response.raise_for_status()
            data = response.json()
            
            recommendations = data.get('recommendations', [])
            
            if not recommendations:
                self.stdout.write(self.style.WARNING('No recommendations found in API response'))
                return

            # Validate the payload SHAPE before writing anything.
            #
            # Presenting a secret is not proof of having been trusted. If the
            # two services ever hold different values for INTERNAL_API_SECRET
            # the request is simply refused — but a misconfigured URL pointing
            # back at the public route would answer 200 OK with a well-formed
            # body that is missing every EV field, and ingestion would write a
            # null expected_value onto every row without raising anything.
            #
            # So assert on what arrived, not on what we sent. This is the check
            # that actually protects PredictionLog.
            missing = validate_internal_schema(recommendations)
            if missing:
                raise RuntimeError(
                    'Internal recommendation payload failed schema validation. '
                    'Missing required ingestion fields: '
                    + '; '.join(missing)
                    + '. This usually means the request reached the PUBLIC '
                      'route (which strips EV fields by design) rather than '
                      '/api/internal/recommendations. Refusing to ingest.'
                )
            
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

                # validate=False deliberately. Strict batch validation guards
                # the UNTRUSTED HTTP boundary, where a malformed row means
                # someone is probing us. This path is our own engine, and the
                # pre-existing contract is that an imperfect row is CLASSIFIED
                # (public_universe.status_for marks it missing_provenance and
                # it simply never becomes publishable), not rejected. Batch-
                # rejecting here would let one imperfect row stop the whole
                # hourly run — a much worse failure than one unpublishable row.
                payload = recommendation_ingest.ingest_recommendations(
                    recommendations, validate=False,
                    # Which ranking policy produced this run. Absent on an old
                    # feed; recorded as unreported rather than guessed.
                    ranking_version=data.get('ranking_version'),
                )

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
            
        # Both handlers RE-RAISE. They used to `return`, which meant a total
        # ingestion failure — a 404 from a wrong URL, a 502, a refused
        # credential — was reported to run_scheduler as a completed stage, and
        # the cycle logged "All tasks completed successfully" having ingested
        # nothing. Observed on 2026-08-06: the feed 404'd and the cycle still
        # showed only the evidence stage as failed.
        #
        # A stage that did no work must say so. run_scheduler records the
        # failure, marks the cycle DEGRADED, and continues to settlement — one
        # failed fetch must not stop claims whose results already landed.
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(
                f'\nError fetching recommendations from API: {redact_exception(e)}'))
            self.stdout.write(self.style.ERROR(
                'Make sure the internal recommendations endpoint is reachable '
                'and INTERNAL_API_SECRET matches on both services.'
            ))
            raise
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\nUnexpected error: {redact_exception(e)}'))
            import traceback
            # redact: a traceback frame can quote a provider URL, and
            # SportMonks authenticates by query parameter.
            self.stdout.write(self.style.ERROR(redact(traceback.format_exc())))
            raise

