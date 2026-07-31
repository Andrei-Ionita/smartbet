"""
Public-beta commercial mode: payments hidden, architecture preserved.

One flag decides whether BetGlitch sells anything. It must fail closed, must
never grant fake paid status, and must not touch the verified-record pipeline.
"""
import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import UserProfile
from core.services import commercial_mode

User = get_user_model()


class FlagFailsClosedTests(TestCase):

    def test_unset_means_public_beta(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('COMMERCIAL_MODE', None)
            self.assertEqual(commercial_mode.commercial_mode(), 'public_beta')
            self.assertFalse(commercial_mode.payments_enabled())
            self.assertTrue(commercial_mode.is_public_beta())

    def test_only_the_exact_string_enables_payments(self):
        for bad in ('', ' ', 'Commercial', 'true', '1', 'yes', 'enabled',
                    'public_beta', 'commercial_mode'):
            with patch.dict(os.environ, {'COMMERCIAL_MODE': bad}):
                self.assertFalse(commercial_mode.payments_enabled(),
                                 f'{bad!r} must not enable payments')

    def test_commercial_enables_payments(self):
        with patch.dict(os.environ, {'COMMERCIAL_MODE': 'commercial'}):
            self.assertTrue(commercial_mode.payments_enabled())

    def test_frontend_and_backend_agree(self):
        """Both halves must accept exactly the same values.

        The frontend compares `=== 'commercial'` with no normalisation; if the
        backend lowercased, 'COMMERCIAL' would enable payments on one side only.
        """
        import re
        ts = open('smartbet-frontend/app/lib/commercialMode.ts',
                  encoding='utf-8').read()
        self.assertIn("=== 'commercial'", ts)
        self.assertNotIn('.toLowerCase()', ts)


class UpgradeTierIsRefusedTests(TestCase):
    """No user may receive paid status while payments are disabled."""

    def setUp(self):
        self.user = User.objects.create_user('beta', 'b@e.com', 'pw12345!')
        self.url = '/api/auth/upgrade-tier/'

    def _post(self):
        return APIClient().post(
            self.url,
            {'user_id': self.user.id, 'tier': 'pro'},
            format='json',
            HTTP_X_INTERNAL_AUTH='whatever',
        )

    def test_upgrade_is_refused_during_the_beta(self):
        with patch.dict(os.environ, {'COMMERCIAL_MODE': 'public_beta',
                                     'INTERNAL_API_SECRET': 'whatever'}):
            resp = self._post()

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.data['code'], 'payments_disabled')

        self.user.refresh_from_db()
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.tier, UserProfile.TIER_FREE,
                         'a user was granted paid status during the beta')

    def test_refusal_precedes_the_shared_secret_check(self):
        """Even a correctly-signed webhook cannot grant a tier."""
        with patch.dict(os.environ, {'COMMERCIAL_MODE': 'public_beta',
                                     'INTERNAL_API_SECRET': 'correct-secret'}):
            resp = APIClient().post(
                self.url, {'user_id': self.user.id, 'tier': 'pro'},
                format='json', HTTP_X_INTERNAL_AUTH='correct-secret',
            )
        self.assertEqual(resp.status_code, 403)


class SubscriptionArchitecturePreservedTests(TestCase):
    """Nothing is deleted — the system stays reactivatable."""

    def test_userprofile_and_tiers_still_exist(self):
        self.assertTrue(hasattr(UserProfile, 'TIER_FREE'))
        self.assertTrue(hasattr(UserProfile, 'TIER_PRO'))
        field_names = {f.name for f in UserProfile._meta.get_fields()}
        self.assertIn('tier', field_names)

    def test_a_users_real_tier_is_preserved_not_faked(self):
        user = User.objects.create_user('real', 'r@e.com', 'pw12345!')
        profile = UserProfile.objects.get(user=user)
        # Free means free. We do not pretend every beta user bought a plan.
        self.assertEqual(profile.tier, UserProfile.TIER_FREE)

    def test_upgrade_tier_endpoint_still_exists(self):
        from core import auth_views
        self.assertTrue(callable(getattr(auth_views, 'upgrade_tier', None)))


class VerifiedRecordUnaffectedTests(TestCase):
    """The beta switch must not touch the pricing-integrity pipeline."""

    def test_public_transparency_endpoints_remain_anonymous(self):
        for url in ('/api/transparency/dashboard/',
                    '/api/transparency/leagues/',
                    '/api/proof/999999/'):
            resp = self.client.get(url)
            self.assertIn(resp.status_code, (200, 404),
                          f'{url} became unavailable')

    def test_staff_only_endpoints_remain_protected(self):
        for url in ('/api/proof/queue/', '/api/proof/1/preview/'):
            resp = APIClient().get(url)
            self.assertIn(resp.status_code, (401, 403),
                          f'{url} lost its staff protection')
