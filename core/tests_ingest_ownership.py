"""
Scheduler ingestion is the single canonical write path.

Before 2026-08-03 one scheduler cycle ingested the same recommendations twice:

    scheduler
      -> GET Next.js /api/recommendations
           -> Next.js background POST /api/log-recommendations/   (run A)
      -> scheduler ingests the returned payload in-process        (run B)

Two prediction runs and two snapshot sets for one calculation, under two
different random run ids. The Next.js side effect is removed; the scheduler's
in-process call now owns the write.
"""
import io
from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from core.models import PredictionLog, PredictionSnapshot
from core.services import recommendation_ingest
from core.tests_ingest_auth import valid_rec


class CanonicalRunIdentityTests(TestCase):
    def test_one_cycle_creates_exactly_one_snapshot_set(self):
        recs = [valid_rec(fixture_id=700001), valid_rec(fixture_id=700002)]

        result = recommendation_ingest.ingest_recommendations(recs)

        self.assertEqual(PredictionSnapshot.objects.count(), 2)
        self.assertEqual(
            PredictionSnapshot.objects.values('prediction_run_id').distinct().count(),
            1,
            'every snapshot from one calculation shares one run identity',
        )
        self.assertEqual(result['snapshots_created'], 2)

    def test_a_retry_of_the_same_run_is_idempotent(self):
        recs = [valid_rec(fixture_id=700001), valid_rec(fixture_id=700002)]

        first = recommendation_ingest.ingest_recommendations(recs)
        second = recommendation_ingest.ingest_recommendations(recs)

        self.assertEqual(first['prediction_run_id'], second['prediction_run_id'])
        self.assertEqual(second['snapshots_created'], 0, 'retry appended nothing')
        self.assertEqual(PredictionSnapshot.objects.count(), 2)
        self.assertEqual(PredictionLog.objects.count(), 2)

    def test_a_genuinely_new_run_creates_new_snapshots(self):
        recs = [valid_rec(fixture_id=700001)]
        first = recommendation_ingest.ingest_recommendations(recs)

        # A real subsequent run re-prices, so the payload differs.
        repriced = [valid_rec(fixture_id=700001, odds=2.10)]
        second = recommendation_ingest.ingest_recommendations(repriced)

        self.assertNotEqual(first['prediction_run_id'], second['prediction_run_id'])
        self.assertEqual(second['snapshots_created'], 1)
        self.assertEqual(PredictionSnapshot.objects.count(), 2)
        self.assertEqual(
            PredictionLog.objects.count(), 1,
            'PredictionLog is the latest-state view, not an append log',
        )

    def test_run_id_is_stable_under_key_ordering(self):
        """Dict ordering must never split one run into two."""
        a = {'fixture_id': 1, 'odds': 2.0, 'league': 'L'}
        b = {'league': 'L', 'odds': 2.0, 'fixture_id': 1}

        self.assertEqual(
            recommendation_ingest.derive_run_id([a]),
            recommendation_ingest.derive_run_id([b]),
        )

    def test_duplicate_ingestion_of_one_payload_no_longer_doubles_snapshots(self):
        """The exact defect: two ingestions of one calculation.

        Previously each got a random run id, so both appended. Now they share a
        content-derived identity and the second is absorbed.
        """
        recs = [valid_rec(fixture_id=700003)]

        recommendation_ingest.ingest_recommendations(recs)   # was "run A"
        recommendation_ingest.ingest_recommendations(recs)   # was "run B"

        self.assertEqual(PredictionSnapshot.objects.count(), 1)
        self.assertEqual(
            PredictionSnapshot.objects.values('prediction_run_id').distinct().count(), 1
        )


class SchedulerNeedsNoIngestSecretTests(TestCase):
    """The canonical path must not depend on RECOMMENDATION_INGEST_SECRET."""

    def test_ingestion_works_with_no_secret_configured(self):
        import os

        with mock.patch.dict(os.environ, {}, clear=False):
            for key in list(os.environ):
                if key.startswith('RECOMMENDATION_INGEST_SECRET'):
                    os.environ.pop(key)

            result = recommendation_ingest.ingest_recommendations(
                [valid_rec(fixture_id=700010)]
            )

        self.assertTrue(result['success'])
        self.assertEqual(PredictionLog.objects.count(), 1)
        self.assertEqual(PredictionSnapshot.objects.count(), 1)

    def test_scheduler_command_calls_the_service_not_the_endpoint(self):
        import inspect
        from core.management.commands import log_recommendations_from_homepage as cmd

        src = inspect.getsource(cmd)
        self.assertIn('recommendation_ingest.ingest_recommendations', src)
        self.assertNotIn('/api/log-recommendations/', src)
        self.assertNotIn('RequestFactory', src)


class NextRouteIsReadOnlyTests(TestCase):
    """A public recommendation GET must create no prediction records."""

    ROUTE = 'smartbet-frontend/app/api/recommendations/route.ts'

    def _source(self):
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        return io.open(root / self.ROUTE, encoding='utf-8').read()

    def test_route_no_longer_posts_to_the_ingest_endpoint(self):
        src = self._source()
        self.assertNotIn('signIngestRequest', src)
        # The only surviving mention is the comment recording why it was removed.
        self.assertNotIn("fetch(`${djangoBaseUrl}/api/log-recommendations/`", src)

    def test_route_makes_no_write_request_at_all(self):
        """No POST/PUT/PATCH/DELETE to our own backend from this route."""
        import re

        src = self._source()
        writes = re.findall(r"method:\s*'(POST|PUT|PATCH|DELETE)'", src)
        self.assertEqual(
            writes, [],
            'the public recommendations route must be read/computation-only',
        )
