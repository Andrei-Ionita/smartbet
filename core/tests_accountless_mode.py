from django.test import SimpleTestCase, override_settings


@override_settings(ACCOUNT_FEATURES_ENABLED=False)
class AccountlessModeTests(SimpleTestCase):
    def test_personal_data_endpoints_are_not_publicly_reachable(self):
        requests = [
            ('post', '/api/auth/register/'),
            ('post', '/api/auth/login/'),
            ('post', '/api/auth/password-reset/request/'),
            ('post', '/api/bankroll/create/'),
            ('post', '/api/subscribe/'),
            ('post', '/api/marketing/events/'),
        ]

        for method, path in requests:
            response = getattr(self.client, method)(path, data={}, content_type='application/json')
            self.assertEqual(response.status_code, 404, path)
            self.assertEqual(response.json(), {'detail': 'Not found.'})

    def test_public_health_route_is_not_guarded(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
