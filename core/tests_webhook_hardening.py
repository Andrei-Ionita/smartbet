"""
The marketing webhook must fail closed, and no route may fail open.

The previous check was::

    if expected_secret and provided_secret != expected_secret:
        reject()

so an unset ``MARKETING_WEBHOOK_SECRET`` skipped the comparison entirely and
the endpoint was fully public. It **was** unset in production: probed on
2026-08-03, a request with no secret and a request with a wrong secret returned
identical responses, both reaching subscriber lookup.

Reachable side effects for anyone who knew a subscriber's email: deactivate
them, reactivate them, mark ``email_platform_status='paid'``, or append
arbitrary MarketingEvent rows.
"""
import inspect
import json
import re
from unittest import mock

from django.test import TestCase

from core import api_views
from core.models import EmailSubscriber, MarketingEvent

URL = '/api/marketing/webhook/'
SECRET = 'webhook-test-secret'


class MarketingWebhookFailsClosedTests(TestCase):
    def setUp(self):
        self.subscriber = EmailSubscriber.objects.create(
            email='someone@example.com', is_active=True,
        )

    def _post(self, body=None, secret=None):
        body = body or {'email': 'someone@example.com', 'action': 'unsubscribe'}
        headers = {}
        if secret is not None:
            headers['HTTP_X_MARKETING_WEBHOOK_SECRET'] = secret
        return self.client.post(
            URL, data=json.dumps(body), content_type='application/json', **headers
        )

    def _assert_no_side_effects(self):
        self.subscriber.refresh_from_db()
        self.assertTrue(self.subscriber.is_active, 'subscriber was deactivated')
        self.assertEqual(MarketingEvent.objects.count(), 0)

    def test_unset_secret_rejects_every_request(self):
        """An absent secret must DISABLE the webhook, not open it."""
        with mock.patch.dict('os.environ', {}, clear=False):
            import os
            os.environ.pop('MARKETING_WEBHOOK_SECRET', None)
            resp = self._post(secret='anything')

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()['code'], 'webhook_unauthorized')
        self._assert_no_side_effects()

    def test_unset_secret_rejects_even_an_unsigned_request(self):
        with mock.patch.dict('os.environ', {}, clear=False):
            import os
            os.environ.pop('MARKETING_WEBHOOK_SECRET', None)
            resp = self._post()

        self.assertEqual(resp.status_code, 401)
        self._assert_no_side_effects()

    @mock.patch.dict('os.environ', {'MARKETING_WEBHOOK_SECRET': SECRET})
    def test_missing_request_secret_is_rejected(self):
        resp = self._post()
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()['code'], 'webhook_unauthorized')
        self._assert_no_side_effects()

    @mock.patch.dict('os.environ', {'MARKETING_WEBHOOK_SECRET': SECRET})
    def test_wrong_secret_is_rejected(self):
        resp = self._post(secret='not-the-secret')
        self.assertEqual(resp.status_code, 401)
        self._assert_no_side_effects()

    @mock.patch.dict('os.environ', {'MARKETING_WEBHOOK_SECRET': SECRET})
    def test_valid_secret_still_works(self):
        resp = self._post(secret=SECRET)

        self.assertEqual(resp.status_code, 200)
        self.subscriber.refresh_from_db()
        self.assertFalse(self.subscriber.is_active)
        self.assertEqual(self.subscriber.email_platform_status, 'unsubscribed')

    @mock.patch.dict('os.environ', {'MARKETING_WEBHOOK_SECRET': SECRET})
    def test_anonymous_cannot_mark_a_subscriber_as_paid(self):
        self._post({'email': 'someone@example.com', 'action': 'paid_converted'})

        self.subscriber.refresh_from_db()
        self.assertNotEqual(self.subscriber.email_platform_status, 'paid')

    @mock.patch.dict('os.environ', {'MARKETING_WEBHOOK_SECRET': SECRET})
    def test_unconfigured_and_wrong_secret_are_indistinguishable(self):
        """A caller must not be able to tell whether the secret is configured."""
        wrong = self._post(secret='nope')

        with mock.patch.dict('os.environ', {}, clear=False):
            import os
            os.environ.pop('MARKETING_WEBHOOK_SECRET', None)
            unset = self._post(secret='nope')

        self.assertEqual(wrong.status_code, unset.status_code)
        self.assertEqual(wrong.json(), unset.json())

    def test_secret_comparison_is_constant_time(self):
        src = inspect.getsource(api_views.marketing_webhook)
        self.assertIn('hmac.compare_digest', src)
        self.assertNotIn('and provided_secret !=', src)

    @mock.patch.dict('os.environ', {'MARKETING_WEBHOOK_SECRET': SECRET})
    def test_failures_never_leak_internals_or_the_secret(self):
        with mock.patch(
            'core.api_views._record_marketing_event',
            side_effect=RuntimeError('psycopg2 password=hunter2'),
        ):
            resp = self._post(
                {'email': 'someone@example.com', 'action': 'weekly_picks_sent'},
                secret=SECRET,
            )

        self.assertEqual(resp.status_code, 500)
        body = resp.content.decode()
        self.assertEqual(resp.json()['code'], 'webhook_failed')
        for leak in ('hunter2', 'psycopg2', 'Traceback', 'RuntimeError', SECRET):
            self.assertNotIn(leak, body)

    def test_no_response_ever_contains_the_secret(self):
        with mock.patch.dict('os.environ', {'MARKETING_WEBHOOK_SECRET': SECRET}):
            for resp in (self._post(), self._post(secret='wrong'), self._post(secret=SECRET)):
                self.assertNotIn(SECRET, resp.content.decode())


class NoFailOpenSecretChecksTests(TestCase):
    """Static guard against reintroducing the fail-open pattern anywhere."""

    MODULES = (
        'core/api_views.py',
        'core/auth_views.py',
        'core/transparency_views.py',
        'core/bankroll_views.py',
        'core/internal_views.py',
        'core/services/ingest_auth.py',
    )

    # `if <secret> and <something> != <secret>` — the guard makes an absent
    # secret skip the check instead of refusing the request.
    FAIL_OPEN = re.compile(
        r'if\s+\w*(secret|token|key)\w*\s+and\s+.*!=', re.IGNORECASE
    )

    def test_no_module_guards_a_secret_check_on_the_secret_existing(self):
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        offenders = []
        for rel in self.MODULES:
            for i, line in enumerate((root / rel).read_text(encoding='utf-8').splitlines(), 1):
                if line.lstrip().startswith('#'):
                    continue
                if self.FAIL_OPEN.search(line):
                    offenders.append(f'{rel}:{i}: {line.strip()}')

        self.assertEqual(
            offenders, [],
            'Fail-open secret check — an absent secret must REJECT, not skip '
            'the comparison:\n  ' + '\n  '.join(offenders),
        )
