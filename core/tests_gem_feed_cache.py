from datetime import timedelta
from io import StringIO
from unittest.mock import Mock, patch

import requests
from django.core.management import call_command
from django.test import Client, TestCase
from django.utils import timezone

from core.models import GemFeedCache
from core.services import gem_feed_cache


SECRET = 'gem-feed-test-secret-value'


def feed(*, recommendations=None, updated=None, ranking='gems-v3'):
    recommendations = [] if recommendations is None else recommendations
    updated = updated or timezone.now()
    return {
        'recommendations': recommendations,
        'confidence_threshold': 55,
        'total': len(recommendations),
        'leagues_covered': 27,
        'fixtures_analyzed': 140,
        'fixtures_with_predictions': 90,
        'gem_scan': {
            'fixtures_scanned': 140,
            'fixtures_with_predictions': 90,
            'qualified_fixtures': len(recommendations),
            'displayed_gems': len(recommendations),
            'maximum_gems': 3,
        },
        'lastUpdated': updated.isoformat(),
        'ranking_version': ranking,
        'message': 'Success',
    }


class GemFeedCacheServiceTests(TestCase):
    def test_latest_success_replaces_singleton_atomically(self):
        first = feed(ranking='v1')
        second = feed(recommendations=[{'fixture_id': 12}], ranking='v2')

        gem_feed_cache.store(first)
        gem_feed_cache.store(second)

        self.assertEqual(GemFeedCache.objects.count(), 1)
        cached = gem_feed_cache.latest()
        self.assertEqual(cached.payload, second)
        self.assertEqual(cached.ranking_version, 'v2')
        self.assertEqual(cached.recommendation_count, 1)

    def test_empty_successful_scan_is_a_real_cached_result(self):
        cached = gem_feed_cache.store(feed(recommendations=[]))
        self.assertEqual(cached.recommendation_count, 0)
        self.assertEqual(cached.payload['recommendations'], [])

    def test_invalid_payload_cannot_replace_last_good_scan(self):
        original = feed(ranking='good')
        gem_feed_cache.store(original)

        with self.assertRaises(gem_feed_cache.InvalidGemFeed):
            gem_feed_cache.store({'recommendations': 'not-a-list'})

        self.assertEqual(gem_feed_cache.latest().payload, original)


class GemFeedSnapshotEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = '/api/internal/gem-feed/'

    @patch.dict('os.environ', {'INTERNAL_API_SECRET': SECRET}, clear=False)
    def test_requires_shared_secret(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)
        self.assertEqual(
            self.client.get(self.url, HTTP_X_INTERNAL_AUTH='wrong').status_code,
            401,
        )

    @patch.dict('os.environ', {'INTERNAL_API_SECRET': ''}, clear=False)
    def test_fails_closed_when_unconfigured(self):
        self.assertEqual(
            self.client.get(self.url, HTTP_X_INTERNAL_AUTH='anything').status_code,
            503,
        )

    @patch.dict('os.environ', {'INTERNAL_API_SECRET': SECRET}, clear=False)
    def test_reports_unavailable_before_first_scan(self):
        response = self.client.get(self.url, HTTP_X_INTERNAL_AUTH=SECRET)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['available'])
        self.assertIsNone(response.json()['feed'])

    @patch.dict('os.environ', {'INTERNAL_API_SECRET': SECRET}, clear=False)
    def test_returns_cached_feed_without_shared_caching(self):
        gem_feed_cache.store(
            feed(updated=timezone.now() - timedelta(minutes=5)),
        )
        response = self.client.get(self.url, HTTP_X_INTERNAL_AUTH=SECRET)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['available'])
        self.assertEqual(body['feed']['fixtures_analyzed'], 140)
        self.assertGreaterEqual(body['age_seconds'], 299)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertIn('X-Internal-Auth', response['Vary'])

    @patch.dict('os.environ', {'INTERNAL_API_SECRET': SECRET}, clear=False)
    def test_rejects_writes(self):
        self.assertEqual(
            self.client.post(self.url, HTTP_X_INTERNAL_AUTH=SECRET).status_code,
            405,
        )


class GemFeedSchedulerIntegrationTests(TestCase):
    @patch.dict('os.environ', {'INTERNAL_API_SECRET': SECRET}, clear=False)
    @patch('core.management.commands.log_recommendations_from_homepage.requests.get')
    def test_scheduler_caches_an_empty_successful_scan(self, get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = feed(recommendations=[])
        get.return_value = response

        call_command('log_recommendations_from_homepage', stdout=StringIO())

        self.assertEqual(gem_feed_cache.latest().recommendation_count, 0)

    @patch.dict('os.environ', {'INTERNAL_API_SECRET': SECRET}, clear=False)
    @patch('core.management.commands.log_recommendations_from_homepage.requests.get')
    def test_failed_refresh_keeps_previous_snapshot(self, get):
        original = feed(ranking='last-good')
        gem_feed_cache.store(original)
        response = Mock()
        response.raise_for_status.side_effect = requests.RequestException('upstream failed')
        get.return_value = response

        with self.assertRaises(requests.RequestException):
            call_command('log_recommendations_from_homepage', stdout=StringIO())

        self.assertEqual(gem_feed_cache.latest().payload, original)
