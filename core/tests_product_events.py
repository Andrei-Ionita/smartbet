import json
import uuid

from django.core.cache import cache
from django.test import TestCase, override_settings

from core.models import ProductEvent


@override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver'])
class ProductEventEndpointTests(TestCase):
    url = '/api/product-events/'
    origin = 'https://www.betglitch.com'

    def setUp(self):
        cache.clear()

    def payload(self, **changes):
        data = {
            'event_name': 'fixture_opened',
            'session_id': str(uuid.uuid4()),
            'surface': '/prediction/superliga/team-a-v-team-b?secret=no',
        }
        data.update(changes)
        return data

    def post(self, data=None, origin=None):
        return self.client.post(
            self.url,
            data=json.dumps(data or self.payload()),
            content_type='application/json',
            HTTP_ORIGIN=self.origin if origin is None else origin,
        )

    def test_get_is_side_effect_free_readiness_probe(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ready')
        self.assertEqual(
            response.json()['privacy_mode'],
            'session_scoped_pseudonymous',
        )
        self.assertEqual(ProductEvent.objects.count(), 0)

    def test_valid_event_is_hashed_and_normalized(self):
        raw_session = str(uuid.uuid4())
        response = self.post(self.payload(session_id=raw_session))
        self.assertEqual(response.status_code, 201)
        event = ProductEvent.objects.get()
        self.assertEqual(event.surface, '/prediction/:slug')
        self.assertNotEqual(event.session_hash, raw_session)
        self.assertNotIn(raw_session, event.session_hash)

    def test_missing_or_foreign_origin_is_rejected(self):
        response = self.client.post(
            self.url,
            data=json.dumps(self.payload()),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.post(origin='https://attacker.example').status_code, 403)
        self.assertEqual(ProductEvent.objects.count(), 0)

    def test_arbitrary_metadata_and_actions_are_not_accepted(self):
        response = self.post(self.payload(action='email@example.com', arbitrary='private'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ProductEvent.objects.count(), 0)

    def test_allowlisted_boolean_and_duration_are_persisted(self):
        response = self.post(self.payload(
            event_name='explore_search',
            surface='/explore?q=rapid',
            has_results=True,
            duration_bucket='10_to_30s',
        ))
        self.assertEqual(response.status_code, 201)
        event = ProductEvent.objects.get()
        self.assertEqual(event.surface, '/explore')
        self.assertIs(event.has_results, True)
        self.assertEqual(event.duration_bucket, '10_to_30s')
