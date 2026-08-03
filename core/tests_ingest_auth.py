"""
Server-to-server authentication for `POST /api/log-recommendations/`.

Until 2026-08-03 this endpoint was `@csrf_exempt` with no authentication. It
writes PredictionLog rows and appends immutable PredictionSnapshots, and
because it keys on fixture_id and setattr()s the whole payload over any
existing row, an anonymous caller could also **overwrite** existing
predictions — including their recorded odds — and craft `odds_provenance` that
made the result classify as ``verified``, putting attacker-controlled rows into
the publication queue.
"""
import hashlib
import hmac
import json
import time
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from core.models import IngestRequest, PredictionLog, PredictionSnapshot
from core.services import recommendation_ingest

URL = '/api/log-recommendations/'
SECRET = 'test-ingest-secret'


def valid_rec(fixture_id=555001, **over):
    kickoff = timezone.now() + timedelta(days=3)
    rec = {
        'fixture_id': fixture_id,
        'home_team': 'Alpha FC',
        'away_team': 'Beta United',
        'league': 'Test League',
        'kickoff': kickoff.isoformat(),
        'predicted_outcome': 'Home',
        'confidence': 64.0,
        'expected_value': 8.0,
        'odds': 1.95,
        'probabilities': {'home': 64.0, 'draw': 20.0, 'away': 16.0},
        'best_market': {
            'type': '1x2',
            'type_id': 1,
            'odds': 1.95,
            'bookmaker': 'bet365',
        },
        # Field names must match public_universe.REQUIRED_PROVENANCE_FIELDS.
        'odds_provenance': {
            'odds': 1.95,
            'odds_market_id': 1,
            'odds_market_description': 'Fulltime Result',
            'odds_label': 'Home',
            'odds_bookmaker_id': 2,
            'odds_bookmaker_name': 'bet365',
            'odds_captured_at': timezone.now().isoformat(),
            'odds_selection_policy': 'lower_median_v1',
            'quote_count': 5,
        },
    }
    rec.update(over)
    return rec


def signed_headers(body: str, secret=SECRET, request_id='req0001', timestamp=None):
    ts = str(int(timestamp if timestamp is not None else time.time()))
    body_hash = hashlib.sha256(body.encode()).hexdigest()
    sig = hmac.new(
        secret.encode(), f'{ts}.{request_id}.{body_hash}'.encode(), hashlib.sha256
    ).hexdigest()
    return {
        'HTTP_X_BETGLITCH_TIMESTAMP': ts,
        'HTTP_X_BETGLITCH_REQUEST_ID': request_id,
        'HTTP_X_BETGLITCH_SIGNATURE': sig,
    }


class IngestAuthTests(TestCase):
    def setUp(self):
        self.body = json.dumps({'recommendations': [valid_rec()]})
        patcher = self.settings()  # no-op; env patched per test below
        self.addCleanup(lambda: None)

    def _post(self, body=None, **headers):
        body = self.body if body is None else body
        return self.client.post(
            URL, data=body, content_type='application/json', **headers
        )

    # ── fail closed ────────────────────────────────────────────────────────
    def test_no_secret_configured_rejects_even_a_signed_request(self):
        """Production must refuse ingestion rather than fall back to anonymous."""
        import os
        from unittest import mock

        with mock.patch.dict(os.environ, {}, clear=False):
            for k in list(os.environ):
                if k.startswith('RECOMMENDATION_INGEST_SECRET'):
                    os.environ.pop(k)
            resp = self._post(**signed_headers(self.body))

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()['code'], 'recommendation_ingest_unauthorized')
        self.assertEqual(PredictionLog.objects.count(), 0)


class SignedIngestTests(TestCase):
    """Everything below runs with a configured secret."""

    def setUp(self):
        import os
        from unittest import mock

        self.env = mock.patch.dict(
            os.environ, {'RECOMMENDATION_INGEST_SECRET': SECRET}
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        self.body = json.dumps({'recommendations': [valid_rec()]})

    def _post(self, body=None, **headers):
        body = self.body if body is None else body
        return self.client.post(
            URL, data=body, content_type='application/json', **headers
        )

    # ── authentication ─────────────────────────────────────────────────────
    def test_unsigned_request_is_rejected(self):
        resp = self._post()
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(PredictionLog.objects.count(), 0)
        self.assertEqual(PredictionSnapshot.objects.count(), 0)

    def test_missing_timestamp_is_rejected(self):
        h = signed_headers(self.body)
        h.pop('HTTP_X_BETGLITCH_TIMESTAMP')
        self.assertEqual(self._post(**h).status_code, 401)

    def test_missing_request_id_is_rejected(self):
        h = signed_headers(self.body)
        h.pop('HTTP_X_BETGLITCH_REQUEST_ID')
        self.assertEqual(self._post(**h).status_code, 401)

    def test_invalid_signature_is_rejected(self):
        h = signed_headers(self.body)
        h['HTTP_X_BETGLITCH_SIGNATURE'] = 'f' * 64
        self.assertEqual(self._post(**h).status_code, 401)

    def test_wrong_secret_is_rejected(self):
        self.assertEqual(
            self._post(**signed_headers(self.body, secret='not-the-secret')).status_code,
            401,
        )

    def test_altered_body_is_rejected(self):
        """A valid envelope must not carry different content."""
        h = signed_headers(self.body)
        tampered = json.dumps({'recommendations': [valid_rec(fixture_id=999999)]})
        self.assertEqual(self._post(tampered, **h).status_code, 401)
        self.assertEqual(PredictionLog.objects.count(), 0)

    def test_altered_request_id_is_rejected(self):
        h = signed_headers(self.body)
        h['HTTP_X_BETGLITCH_REQUEST_ID'] = 'req0002'
        self.assertEqual(self._post(**h).status_code, 401)

    def test_expired_timestamp_is_rejected(self):
        old = time.time() - 3600
        self.assertEqual(
            self._post(**signed_headers(self.body, timestamp=old)).status_code, 401
        )

    def test_future_timestamp_is_rejected(self):
        ahead = time.time() + 3600
        self.assertEqual(
            self._post(**signed_headers(self.body, timestamp=ahead)).status_code, 401
        )

    def test_valid_signed_request_is_accepted(self):
        resp = self._post(**signed_headers(self.body))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['success'])
        self.assertEqual(PredictionLog.objects.count(), 1)
        self.assertEqual(PredictionSnapshot.objects.count(), 1)

    def test_comparison_uses_constant_time_compare(self):
        from core.services import ingest_auth
        import inspect

        self.assertIn('compare_digest', inspect.getsource(ingest_auth.verify))

    # ── replay and idempotency ─────────────────────────────────────────────
    def test_identical_retry_is_idempotent(self):
        h = signed_headers(self.body)
        first = self._post(**h)
        # A retry re-signs with the SAME request id, so the timestamp differs.
        second = self._post(**signed_headers(self.body, request_id='req0001'))

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(PredictionLog.objects.count(), 1)
        self.assertEqual(PredictionSnapshot.objects.count(), 1)
        self.assertEqual(IngestRequest.objects.count(), 1)

    def test_reused_request_id_with_different_body_is_refused(self):
        self._post(**signed_headers(self.body))

        other = json.dumps({'recommendations': [valid_rec(fixture_id=555002)]})
        resp = self._post(other, **signed_headers(other, request_id='req0001'))

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()['code'], 'recommendation_ingest_replayed')
        self.assertEqual(PredictionLog.objects.count(), 1)

    def test_two_genuinely_different_runs_create_distinct_snapshots(self):
        self._post(**signed_headers(self.body, request_id='runaaaa'))
        self._post(**signed_headers(self.body, request_id='runbbbb'))

        self.assertEqual(PredictionLog.objects.count(), 1, 'latest-state row is updated')
        self.assertEqual(PredictionSnapshot.objects.count(), 2, 'both runs are recorded')
        self.assertEqual(
            PredictionSnapshot.objects.values('prediction_run_id').distinct().count(), 2
        )

    def test_run_id_is_derived_from_the_request_id(self):
        """So a retry lands on the same snapshot uniqueness key."""
        resp = self._post(**signed_headers(self.body, request_id='deadbeef'))
        expected = hashlib.sha256(b'deadbeef').hexdigest()[:32]
        self.assertEqual(resp.json()['prediction_run_id'], expected)

    # ── validation ─────────────────────────────────────────────────────────
    def _reject(self, rec, fragment=None):
        body = json.dumps({'recommendations': [rec]})
        resp = self._post(body, **signed_headers(body, request_id='vreq0001'))
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()['code'], 'recommendation_ingest_invalid')
        self.assertEqual(PredictionLog.objects.count(), 0)
        self.assertEqual(PredictionSnapshot.objects.count(), 0)
        if fragment:
            self.assertIn(fragment, json.dumps(resp.json()['errors']))

    def test_unknown_market_is_rejected(self):
        self._reject(valid_rec(best_market={'type': 'corners', 'odds': 2.0}), 'market_type')

    def test_missing_predicted_outcome_is_rejected(self):
        self._reject(valid_rec(predicted_outcome=''), 'predicted_outcome')

    def test_odds_at_or_below_one_are_rejected(self):
        self._reject(valid_rec(odds=1.0), 'odds')
        self._reject(valid_rec(odds=0.5), 'odds')

    def test_non_numeric_odds_are_rejected(self):
        self._reject(valid_rec(odds='1.95'), 'odds')

    def test_missing_provenance_is_rejected(self):
        self._reject(valid_rec(odds_provenance=None), 'odds_provenance')

    def test_incomplete_provenance_is_rejected(self):
        self._reject(
            valid_rec(odds_provenance={'odds_bookmaker_name': 'bet365'}),
            'odds_provenance',
        )

    def test_post_kickoff_prediction_is_rejected(self):
        past = (timezone.now() - timedelta(hours=2)).isoformat()
        self._reject(valid_rec(kickoff=past), 'kickoff')

    def test_stale_odds_capture_is_rejected(self):
        rec = valid_rec()
        rec['odds_provenance']['odds_captured_at'] = (
            timezone.now() - timedelta(days=5)
        ).isoformat()
        self._reject(rec, 'too old')

    def test_future_odds_capture_is_rejected(self):
        rec = valid_rec()
        rec['odds_provenance']['odds_captured_at'] = (
            timezone.now() + timedelta(hours=2)
        ).isoformat()
        self._reject(rec, 'future')

    def test_oversized_batch_is_rejected(self):
        recs = [valid_rec(fixture_id=600000 + i) for i in range(
            recommendation_ingest.MAX_BATCH_SIZE + 1
        )]
        body = json.dumps({'recommendations': recs})
        resp = self._post(body, **signed_headers(body, request_id='bigreq01'))
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(PredictionLog.objects.count(), 0)

    def test_a_malformed_row_rejects_the_whole_batch(self):
        """No partial acceptance — a run is stored whole or not at all."""
        body = json.dumps({'recommendations': [valid_rec(), valid_rec(
            fixture_id=555003, odds=1.0
        )]})
        resp = self._post(body, **signed_headers(body, request_id='mixreq01'))
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(PredictionLog.objects.count(), 0)
        self.assertEqual(PredictionSnapshot.objects.count(), 0)

    def test_unexpected_fields_do_not_reach_the_database(self):
        rec = valid_rec()
        rec['pricing_integrity_status'] = 'verified'
        rec['is_audit_excluded'] = False
        rec['__proto__'] = {'evil': True}
        body = json.dumps({'recommendations': [rec]})
        resp = self._post(body, **signed_headers(body, request_id='extrafld'))

        self.assertEqual(resp.status_code, 200)
        row = PredictionLog.objects.get()
        # Status is computed by public_universe, never taken from the payload.
        self.assertEqual(row.pricing_integrity_status,
                         PredictionLog.PRICING_VERIFIED)

    # ── error handling ─────────────────────────────────────────────────────
    def test_invalid_json_returns_a_controlled_code(self):
        body = '{not json'
        resp = self._post(body, **signed_headers(body, request_id='badjson1'))
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['code'], 'recommendation_ingest_invalid')

    def test_responses_never_carry_raw_exception_text(self):
        from unittest import mock

        with mock.patch(
            'core.services.recommendation_ingest.ingest_recommendations',
            side_effect=RuntimeError('psycopg2 password=hunter2 api_token=SECRET'),
        ):
            resp = self._post(**signed_headers(self.body, request_id='boomreq1'))

        self.assertEqual(resp.status_code, 500)
        body = resp.content.decode()
        self.assertEqual(resp.json()['code'], 'recommendation_ingest_failed')
        for leak in ('hunter2', 'psycopg2', 'api_token', 'Traceback', 'RuntimeError'):
            self.assertNotIn(leak, body)

    def test_rejection_does_not_reveal_which_header_failed(self):
        h = signed_headers(self.body)
        h['HTTP_X_BETGLITCH_SIGNATURE'] = 'f' * 64
        body = self._post(**h).content.decode()
        for leak in ('signature', 'timestamp', 'secret', 'hmac'):
            self.assertNotIn(leak, body.lower())


class AnonymousInjectionTests(TestCase):
    """The concrete attacks the endpoint previously allowed."""

    def setUp(self):
        import os
        from unittest import mock

        self.env = mock.patch.dict(
            os.environ, {'RECOMMENDATION_INGEST_SECRET': SECRET}
        )
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_anonymous_cannot_create_a_prediction_log(self):
        body = json.dumps({'recommendations': [valid_rec()]})
        self.client.post(URL, data=body, content_type='application/json')
        self.assertEqual(PredictionLog.objects.count(), 0)

    def test_anonymous_cannot_create_a_snapshot(self):
        body = json.dumps({'recommendations': [valid_rec()]})
        self.client.post(URL, data=body, content_type='application/json')
        self.assertEqual(PredictionSnapshot.objects.count(), 0)

    def test_anonymous_cannot_overwrite_an_existing_prediction(self):
        """The original view setattr()d the payload over any existing row."""
        existing = PredictionLog.objects.create(
            fixture_id=555001, home_team='Real', away_team='Teams',
            league='Real League', kickoff=timezone.now() + timedelta(days=2),
            predicted_outcome='Home', confidence=0.62,
            probability_home=0.62, probability_draw=0.2, probability_away=0.18,
            odds=2.5, market_type='1x2',
        )
        body = json.dumps({'recommendations': [valid_rec(
            fixture_id=555001, odds=99.0, home_team='Hacked'
        )]})
        self.client.post(URL, data=body, content_type='application/json')

        existing.refresh_from_db()
        self.assertEqual(existing.home_team, 'Real')
        self.assertEqual(existing.odds, 2.5)

    def test_anonymous_cannot_reach_the_publication_queue(self):
        """Crafted provenance previously classified as verified."""
        body = json.dumps({'recommendations': [valid_rec()]})
        self.client.post(URL, data=body, content_type='application/json')

        self.assertEqual(
            PredictionSnapshot.objects.filter(
                pricing_integrity_status=PredictionLog.PRICING_VERIFIED
            ).count(),
            0,
        )


class SchedulerPathUnaffectedTests(TestCase):
    """The scheduler ingests in-process and never signs a request to itself."""

    def test_service_ingest_still_creates_rows_and_snapshots(self):
        result = recommendation_ingest.ingest_recommendations([valid_rec()])

        self.assertTrue(result['success'])
        self.assertEqual(result['logged_count'], 1)
        self.assertEqual(result['snapshots_created'], 1)
        self.assertEqual(PredictionLog.objects.count(), 1)
        self.assertEqual(PredictionSnapshot.objects.count(), 1)

    def test_service_ingest_classifies_pricing_correctly(self):
        recommendation_ingest.ingest_recommendations([valid_rec()])
        self.assertEqual(
            PredictionLog.objects.get().pricing_integrity_status,
            PredictionLog.PRICING_VERIFIED,
        )

    def test_command_no_longer_forges_an_http_request(self):
        import inspect
        from core.management.commands import log_recommendations_from_homepage as cmd

        src = inspect.getsource(cmd)
        self.assertNotIn('RequestFactory', src)
        self.assertIn('recommendation_ingest', src)

    def test_service_still_validates_by_default(self):
        with self.assertRaises(recommendation_ingest.ValidationError):
            recommendation_ingest.ingest_recommendations([valid_rec(odds=1.0)])
