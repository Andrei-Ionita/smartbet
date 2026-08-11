from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import EmailSubscriber


class PasswordRecoveryTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='reader', email='reader@example.com', password='Old-pass-142!',
        )

    @patch.dict('os.environ', {
        'BREVO_API_KEY': 'test-key',
        'BREVO_SENDER_EMAIL': 'support@betglitch.com',
        'FRONTEND_URL': 'https://www.betglitch.com',
    })
    @patch('core.services.account_email.send_password_reset')
    def test_request_is_non_enumerating(self, sender):
        known = self.client.post(
            '/api/auth/password-reset/request/',
            {'email': self.user.email}, format='json',
        )
        unknown = self.client.post(
            '/api/auth/password-reset/request/',
            {'email': 'nobody@example.com'}, format='json',
        )

        self.assertEqual(known.status_code, 202)
        self.assertEqual(unknown.status_code, 202)
        self.assertEqual(known.json()['message'], unknown.json()['message'])
        sender.assert_called_once()
        self.assertNotIn('token', known.json())

    @patch.dict('os.environ', {}, clear=True)
    def test_unconfigured_transactional_email_fails_visibly(self):
        response = self.client.post(
            '/api/auth/password-reset/request/',
            {'email': self.user.email}, format='json',
        )
        self.assertEqual(response.status_code, 503)

    def test_valid_token_sets_a_new_password_and_invalidates_itself(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        response = self.client.post(
            '/api/auth/password-reset/confirm/',
            {'uid': uid, 'token': token, 'password': 'New-secure-pass-842!'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('New-secure-pass-842!'))
        replay = self.client.post(
            '/api/auth/password-reset/confirm/',
            {'uid': uid, 'token': token, 'password': 'Another-pass-953!'},
            format='json',
        )
        self.assertEqual(replay.status_code, 400)


class AccountDeletionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='delete-me', email='delete@example.com', password='Delete-pass-421!',
        )
        self.subscriber = EmailSubscriber.objects.create(
            email=self.user.email,
            source='account',
            utm_source='private-source',
            interests=['weekly_picks'],
        )
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')

    def test_password_reconfirmation_is_required(self):
        response = self.client.delete(
            '/api/auth/account/',
            {'password': 'wrong', 'confirmation': 'DELETE'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_account_and_personal_marketing_identifier_are_deleted(self):
        response = self.client.delete(
            '/api/auth/account/',
            {'password': 'Delete-pass-421!', 'confirmation': 'DELETE'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.subscriber.refresh_from_db()
        self.assertFalse(self.subscriber.is_active)
        self.assertEqual(self.subscriber.email_platform_status, 'deleted')
        self.assertNotEqual(self.subscriber.email, 'delete@example.com')
        self.assertEqual(self.subscriber.utm_source, '')
        self.assertEqual(self.subscriber.interests, [])


class PublicSurfaceHardeningTests(TestCase):
    def test_database_diagnostics_are_not_publicly_routed(self):
        response = APIClient().get('/api/db-check/')

        self.assertEqual(response.status_code, 404)
