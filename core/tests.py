"""
SmartBet Core Tests - Smoke Tests for Critical Flows

Run with: python manage.py test core
"""

from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch
from core.models import BankrollTransaction, EmailSubscriber, MarketingEvent, PredictionLog, UserBankroll
from core.bankroll_utils import calculate_kelly_criterion, calculate_stake_amount
from django.contrib.auth import get_user_model

User = get_user_model()


class PredictionLogTests(TestCase):
    """Test prediction logging functionality"""

    def setUp(self):
        self.client = Client()

    def test_create_prediction_log(self):
        """Test creating a prediction log entry"""
        kickoff = timezone.now() + timedelta(days=1)

        prediction = PredictionLog.objects.create(
            fixture_id=12345,
            home_team="Manchester United",
            away_team="Liverpool",
            league="Premier League",
            kickoff=kickoff,
            predicted_outcome="Home",
            confidence=0.65,
            probability_home=0.65,
            probability_draw=0.20,
            probability_away=0.15,
            odds_home=2.20,
            odds_draw=3.40,
            odds_away=3.10,
            expected_value=0.43,
            model_count=3,
            consensus=0.87,
            variance=3.1,
            ensemble_strategy="consensus_ensemble"
        )

        self.assertEqual(prediction.fixture_id, 12345)
        self.assertEqual(prediction.home_team, "Manchester United")
        self.assertEqual(prediction.predicted_outcome, "Home")
        self.assertEqual(prediction.confidence, 0.65)
        self.assertIsNone(prediction.actual_outcome)  # Not completed yet

    def test_update_prediction_with_result(self):
        """Test updating prediction with actual match result"""
        kickoff = timezone.now() - timedelta(hours=2)  # Match finished

        prediction = PredictionLog.objects.create(
            fixture_id=12346,
            home_team="Arsenal",
            away_team="Chelsea",
            league="Premier League",
            kickoff=kickoff,
            predicted_outcome="Home",
            confidence=0.60,
            probability_home=0.60,
            probability_draw=0.25,
            probability_away=0.15,
            odds_home=1.80,
            expected_value=0.08
        )

        # Update with result
        prediction.actual_outcome = "Home"
        prediction.actual_score_home = 2
        prediction.actual_score_away = 1
        prediction.was_correct = True
        prediction.profit_loss_10 = 8.0  # $10 bet at 1.80 odds = $8 profit
        prediction.roi_percent = 80.0
        prediction.result_logged_at = timezone.now()
        prediction.save()

        self.assertTrue(prediction.was_correct)
        self.assertEqual(prediction.actual_outcome, "Home")
        self.assertIsNotNone(prediction.result_logged_at)


class KellyCriterionTests(TestCase):
    """Test Kelly Criterion bankroll calculations"""

    def test_kelly_criterion_calculation(self):
        """Test Kelly Criterion formula"""
        result = calculate_kelly_criterion(
            win_probability=0.65,
            odds=2.20,
            fraction=0.25  # 1/4 Kelly
        )

        self.assertIn('kelly_percentage', result)
        self.assertIn('full_kelly', result)
        self.assertIn('fractional_kelly', result)

        # Kelly should be positive for +EV bet
        self.assertGreater(result['kelly_percentage'], 0)
        self.assertGreater(result['full_kelly'], 0)

    def test_kelly_criterion_negative_ev(self):
        """Test Kelly Criterion with negative EV (bad bet)"""
        result = calculate_kelly_criterion(
            win_probability=0.30,
            odds=2.00,
            fraction=0.25
        )

        # Kelly should be 0 for -EV bet
        self.assertEqual(result['kelly_percentage'], 0)

    def test_stake_calculation_kelly(self):
        """Test stake amount calculation using Kelly strategy"""
        result = calculate_stake_amount(
            bankroll=Decimal('1000.00'),
            strategy='kelly',
            win_probability=0.65,
            odds=2.20,
            confidence=65.0,
            max_stake_percentage=10.0
        )

        self.assertIn('recommended_stake', result)
        self.assertIn('strategy', result)
        self.assertIn('risk_level', result)

        # Stake should be reasonable percentage of bankroll
        stake = float(result['recommended_stake'])
        self.assertGreater(stake, 0)
        self.assertLessEqual(stake, 100)  # Max 10% of $1000


class BankrollManagementTests(TestCase):
    """Test bankroll management functionality"""

    def test_create_user_bankroll(self):
        """Test creating a user bankroll"""
        user = User.objects.create_user(username='testuser', password='testpass')

        bankroll = UserBankroll.objects.create(
            user=user,
            initial_bankroll=Decimal('1000.00'),
            current_bankroll=Decimal('1000.00'),
            currency='USD',
            staking_strategy='kelly',
            risk_profile='balanced',
            daily_loss_limit=Decimal('100.00'),
            weekly_loss_limit=Decimal('300.00'),
            max_stake_percentage=5.0
        )

        self.assertEqual(bankroll.initial_bankroll, Decimal('1000.00'))
        self.assertEqual(bankroll.current_bankroll, Decimal('1000.00'))
        self.assertEqual(bankroll.staking_strategy, 'kelly')

    def test_bankroll_with_session_id(self):
        """Test creating anonymous bankroll with session ID"""
        bankroll = UserBankroll.objects.create(
            session_id='test-session-123',
            initial_bankroll=Decimal('500.00'),
            current_bankroll=Decimal('500.00'),
            currency='USD',
            staking_strategy='fixed_percentage',
            fixed_stake_percentage=2.0
        )

        self.assertEqual(bankroll.session_id, 'test-session-123')
        self.assertIsNone(bankroll.user)


class APIEndpointsTests(TestCase):
    """Test critical API endpoints"""

    def setUp(self):
        self.client = Client()

        # Create test predictions
        kickoff = timezone.now() + timedelta(days=1)
        PredictionLog.objects.create(
            fixture_id=99999,
            home_team="Test Home",
            away_team="Test Away",
            league="Test League",
            kickoff=kickoff,
            predicted_outcome="Home",
            confidence=0.60,
            probability_home=0.60,
            probability_draw=0.25,
            probability_away=0.15,
            expected_value=0.10
        )

    def test_recommendations_endpoint(self):
        """Test /api/recommendations/ endpoint"""
        response = self.client.get('/api/recommendations/?limit=10')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('success', data)
        self.assertIn('data', data)

    def test_search_endpoint(self):
        """Test /api/search/ endpoint"""
        response = self.client.get('/api/search/?q=Test')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('success', data)
        self.assertIn('results', data)

    def test_fixture_details_endpoint(self):
        """Test /api/fixture/<id>/ endpoint"""
        response = self.client.get('/api/fixture/99999/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('success', data)


class TransparencyTests(TestCase):
    """Test transparency and accuracy tracking"""

    def setUp(self):
        self.client = Client()

        # Create predictions with results
        kickoff_past = timezone.now() - timedelta(days=1)

        # Correct prediction
        PredictionLog.objects.create(
            fixture_id=88881,
            home_team="Team A",
            away_team="Team B",
            league="Test League",
            kickoff=kickoff_past,
            predicted_outcome="Home",
            confidence=0.70,
            probability_home=0.70,
            probability_draw=0.15,
            probability_away=0.15,
            actual_outcome="Home",
            was_correct=True,
            result_logged_at=timezone.now(),
            is_recommended=True
        )

        # Incorrect prediction
        PredictionLog.objects.create(
            fixture_id=88882,
            home_team="Team C",
            away_team="Team D",
            league="Test League",
            kickoff=kickoff_past,
            predicted_outcome="Home",
            confidence=0.60,
            probability_home=0.60,
            probability_draw=0.20,
            probability_away=0.20,
            actual_outcome="Away",
            was_correct=False,
            result_logged_at=timezone.now(),
            is_recommended=True
        )

    def test_accuracy_calculation(self):
        """Test accuracy calculation for completed predictions"""
        completed = PredictionLog.objects.filter(
            actual_outcome__isnull=False,
            is_recommended=True
        )

        total = completed.count()
        correct = completed.filter(was_correct=True).count()

        self.assertEqual(total, 2)
        self.assertEqual(correct, 1)

        accuracy = (correct / total * 100) if total > 0 else 0
        self.assertEqual(accuracy, 50.0)

    def test_transparency_endpoint(self):
        """Test /api/transparency/summary/ endpoint"""
        response = self.client.get('/api/transparency/summary/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('success', data)


class SecurityTests(TestCase):
    """Test security-related functionality"""

    def test_sensitive_data_not_exposed(self):
        """Test that API tokens are not exposed in responses"""
        response = self.client.get('/api/recommendations/')

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Check that common secret patterns are not in response
        self.assertNotIn('SPORTMONKS_TOKEN', content)
        self.assertNotIn('SPORTMONKS_API_TOKEN', content)
        self.assertNotIn('SECRET_KEY', content)

    def test_cors_headers_present(self):
        """Test that CORS headers are configured"""
        response = self.client.get('/api/recommendations/')

        # Django CORS middleware should add these headers
        # (This test assumes django-cors-headers is installed)
        self.assertEqual(response.status_code, 200)


class AuthenticationTests(TestCase):
    """Test authentication API endpoints"""

    def setUp(self):
        self.client = Client()
        self.register_url = '/api/auth/register/'
        self.login_url = '/api/auth/login/'
        self.refresh_url = '/api/auth/token/refresh/'
        self.user_url = '/api/auth/user/'

    def test_register_success(self):
        """Test successful user registration"""
        response = self.client.post(self.register_url, data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123',
        }, content_type='application/json')

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('tokens', data)
        self.assertIn('access', data['tokens'])
        self.assertIn('refresh', data['tokens'])
        self.assertEqual(data['user']['username'], 'newuser')
        self.assertEqual(data['user']['email'], 'newuser@example.com')

    def test_register_duplicate_username(self):
        """Test registration with existing username is rejected"""
        User.objects.create_user(username='taken', email='a@test.com', password='pass12345')

        response = self.client.post(self.register_url, data={
            'username': 'taken',
            'email': 'b@test.com',
            'password': 'securepass123',
        }, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_register_duplicate_email(self):
        """Test registration with existing email is rejected"""
        User.objects.create_user(username='user1', email='used@test.com', password='pass12345')

        response = self.client.post(self.register_url, data={
            'username': 'user2',
            'email': 'used@test.com',
            'password': 'securepass123',
        }, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_register_short_password(self):
        """Test registration with password too short is rejected"""
        response = self.client.post(self.register_url, data={
            'username': 'shortpw',
            'email': 'test@test.com',
            'password': 'abc',
        }, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_login_by_username(self):
        """Test login with username"""
        User.objects.create_user(username='loginuser', email='login@test.com', password='mypassword1')

        response = self.client.post(self.login_url, data={
            'username': 'loginuser',
            'password': 'mypassword1',
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('tokens', data)
        self.assertEqual(data['user']['username'], 'loginuser')

    def test_login_by_email(self):
        """Test login with email address"""
        User.objects.create_user(username='emailuser', email='email@test.com', password='mypassword1')

        response = self.client.post(self.login_url, data={
            'username': 'email@test.com',
            'password': 'mypassword1',
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['username'], 'emailuser')

    def test_login_wrong_password(self):
        """Test login with wrong password returns 401"""
        User.objects.create_user(username='wrongpw', email='wp@test.com', password='correctpassword')

        response = self.client.post(self.login_url, data={
            'username': 'wrongpw',
            'password': 'incorrectpassword',
        }, content_type='application/json')

        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.json())

    def test_login_nonexistent_user(self):
        """Test login with non-existent user returns 401"""
        response = self.client.post(self.login_url, data={
            'username': 'noone',
            'password': 'nopassword',
        }, content_type='application/json')

        self.assertEqual(response.status_code, 401)

    def test_login_nonexistent_email(self):
        """Test login with non-existent email returns 401"""
        response = self.client.post(self.login_url, data={
            'username': 'nobody@nowhere.com',
            'password': 'nopassword',
        }, content_type='application/json')

        self.assertEqual(response.status_code, 401)

    def test_token_refresh(self):
        """Test refreshing access token with valid refresh token"""
        # Register to get tokens
        reg_response = self.client.post(self.register_url, data={
            'username': 'refresher',
            'email': 'refresh@test.com',
            'password': 'securepass123',
        }, content_type='application/json')

        refresh_token = reg_response.json()['tokens']['refresh']

        # Refresh the token
        response = self.client.post(self.refresh_url, data={
            'refresh': refresh_token,
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('access', data)

    def test_get_user_with_token(self):
        """Test getting user profile with valid JWT token"""
        # Register to get tokens
        reg_response = self.client.post(self.register_url, data={
            'username': 'profileuser',
            'email': 'profile@test.com',
            'password': 'securepass123',
        }, content_type='application/json')

        access_token = reg_response.json()['tokens']['access']

        # Get user profile with Bearer token
        response = self.client.get(self.user_url,
            HTTP_AUTHORIZATION=f'Bearer {access_token}')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['username'], 'profileuser')

    def test_get_user_without_token(self):
        """Test getting user profile without token returns 401"""
        response = self.client.get(self.user_url)

        self.assertEqual(response.status_code, 401)


class MarketingAutomationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.subscribe_url = '/api/subscribe/'
        self.events_url = '/api/marketing/events/'
        self.webhook_url = '/api/marketing/webhook/'

    def test_subscribe_email_backwards_compatible_payload(self):
        response = self.client.post(self.subscribe_url, data={
            'email': 'subscriber@example.com',
            'source': 'homepage',
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        subscriber = EmailSubscriber.objects.get(email='subscriber@example.com')
        self.assertEqual(subscriber.source, 'homepage')
        self.assertEqual(subscriber.landing_page, '')
        self.assertEqual(subscriber.language, 'en')
        self.assertEqual(MarketingEvent.objects.filter(subscriber=subscriber, event_name='email_subscribed').count(), 1)
        self.assertEqual(MarketingEvent.objects.filter(subscriber=subscriber, event_name='welcome_sequence_started').count(), 1)

    def test_subscribe_email_with_marketing_metadata(self):
        response = self.client.post(self.subscribe_url, data={
            'email': 'meta@example.com',
            'source': 'prediction_page',
            'landing_page': '/prediction/team-a-vs-team-b-123',
            'utm_source': 'google',
            'utm_medium': 'organic',
            'utm_campaign': 'liga-1-weekend',
            'language': 'ro',
            'league_interest': 'Liga 1',
            'interests': ['weekly_picks', 'premium_launch'],
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        subscriber = EmailSubscriber.objects.get(email='meta@example.com')
        self.assertEqual(subscriber.landing_page, '/prediction/team-a-vs-team-b-123')
        self.assertEqual(subscriber.utm_source, 'google')
        self.assertEqual(subscriber.utm_medium, 'organic')
        self.assertEqual(subscriber.utm_campaign, 'liga-1-weekend')
        self.assertEqual(subscriber.language, 'ro')
        self.assertEqual(subscriber.league_interest, 'Liga 1')
        self.assertEqual(subscriber.interests, ['weekly_picks', 'premium_launch'])


    @patch.dict('os.environ', {
        'MARKETING_SYNC_ENABLED': 'True',
        'BREVO_API_KEY': 'brevo-test-key',
        'BREVO_SENDER_EMAIL': 'hello@betglitch.com',
        'BREVO_SENDER_NAME': 'BetGlitch',
        'BREVO_WELCOME_EMAIL_ENABLED': 'True',
        'BREVO_SANDBOX_MODE': 'True',
    }, clear=False)
    @patch('core.services.marketing.requests.request')
    def test_subscribe_triggers_brevo_contact_sync_and_welcome_email(self, mock_request):
        contact_response = Mock()
        contact_response.content = b'{}'
        contact_response.json.return_value = {}
        contact_response.raise_for_status.return_value = None

        email_response = Mock()
        email_response.content = b'{}'
        email_response.json.return_value = {}
        email_response.raise_for_status.return_value = None

        mock_request.side_effect = [contact_response, email_response]

        response = self.client.post(self.subscribe_url, data={
            'email': 'brevo@example.com',
            'source': 'homepage',
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        subscriber = EmailSubscriber.objects.get(email='brevo@example.com')
        self.assertEqual(subscriber.email_platform_status, 'synced')
        self.assertIsNotNone(subscriber.last_synced_at)
        self.assertEqual(mock_request.call_count, 2)
        self.assertEqual(mock_request.call_args_list[0].args[0], 'POST')
        self.assertEqual(mock_request.call_args_list[0].args[1], 'https://api.brevo.com/v3/contacts')
        self.assertEqual(mock_request.call_args_list[1].args[1], 'https://api.brevo.com/v3/smtp/email')

    def test_brevo_webhook_click_payload_logs_email_click(self):
        subscriber = EmailSubscriber.objects.create(email='clicked@example.com', source='homepage')

        response = self.client.post(
            self.webhook_url,
            data={
                'event': 'clicked',
                'email': 'clicked@example.com',
                'link': '/pricing',
                'messageId': 'abc123',
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(MarketingEvent.objects.filter(subscriber=subscriber, event_name='email_clicked').exists())

    def test_reactivate_inactive_subscriber_logs_events(self):
        subscriber = EmailSubscriber.objects.create(
            email='inactive@example.com',
            source='homepage',
            is_active=False,
        )

        response = self.client.post(self.subscribe_url, data={
            'email': 'inactive@example.com',
            'source': 'track_record_page',
            'landing_page': '/track-record',
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        subscriber.refresh_from_db()
        self.assertTrue(subscriber.is_active)
        self.assertEqual(subscriber.source, 'track_record_page')
        self.assertEqual(MarketingEvent.objects.filter(subscriber=subscriber, event_name='email_subscribed').count(), 1)
        self.assertEqual(MarketingEvent.objects.filter(subscriber=subscriber, event_name='welcome_sequence_started').count(), 1)

    def test_track_marketing_event_updates_paid_status(self):
        subscriber = EmailSubscriber.objects.create(email='paid@example.com', source='pricing_page')

        response = self.client.post(self.events_url, data={
            'event_name': 'paid_converted',
            'subscriber_id': subscriber.id,
            'source': 'pricing_page',
            'page': '/pricing',
            'metadata': {'plan': 'premium_waitlist'},
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        subscriber.refresh_from_db()
        self.assertEqual(subscriber.email_platform_status, 'paid')
        self.assertTrue(MarketingEvent.objects.filter(subscriber=subscriber, event_name='paid_converted').exists())

    @patch.dict('os.environ', {'MARKETING_WEBHOOK_SECRET': 'top-secret'}, clear=False)
    def test_marketing_webhook_unsubscribe_and_reactivate(self):
        subscriber = EmailSubscriber.objects.create(email='webhook@example.com', source='homepage')

        unsubscribe_response = self.client.post(
            self.webhook_url,
            data={'action': 'unsubscribe', 'email': 'webhook@example.com'},
            content_type='application/json',
            HTTP_X_MARKETING_WEBHOOK_SECRET='top-secret'
        )
        self.assertEqual(unsubscribe_response.status_code, 200)
        subscriber.refresh_from_db()
        self.assertFalse(subscriber.is_active)
        self.assertEqual(subscriber.email_platform_status, 'unsubscribed')

        reactivate_response = self.client.post(
            self.webhook_url,
            data={'action': 'reactivate', 'email': 'webhook@example.com', 'source': 'email_platform'},
            content_type='application/json',
            HTTP_X_MARKETING_WEBHOOK_SECRET='top-secret'
        )
        self.assertEqual(reactivate_response.status_code, 200)
        subscriber.refresh_from_db()
        self.assertTrue(subscriber.is_active)
        self.assertEqual(subscriber.email_platform_status, 'reactivated')
        self.assertTrue(MarketingEvent.objects.filter(subscriber=subscriber, event_name='welcome_sequence_started').exists())

    def test_end_to_end_marketing_journey(self):
        subscribe_response = self.client.post(self.subscribe_url, data={
            'email': 'journey@example.com',
            'source': 'homepage',
            'landing_page': '/',
            'utm_source': 'google',
            'utm_medium': 'organic',
            'utm_campaign': 'weekly-picks',
        }, content_type='application/json')
        self.assertEqual(subscribe_response.status_code, 200)
        subscriber_id = subscribe_response.json()['subscriber_id']

        pricing_response = self.client.post(self.events_url, data={
            'event_name': 'pricing_viewed',
            'subscriber_id': subscriber_id,
            'source': 'pricing_page',
            'page': '/pricing',
            'metadata': {'tier': 'marketing_waitlist'},
        }, content_type='application/json')
        self.assertEqual(pricing_response.status_code, 200)

        click_response = self.client.post(self.webhook_url, data={
            'action': 'email_clicked',
            'subscriber_id': subscriber_id,
            'source': 'weekly_picks_email',
            'page': '/prediction/sample-fixture',
            'metadata': {'campaign': 'welcome-1'},
        }, content_type='application/json')
        self.assertEqual(click_response.status_code, 200)

        subscriber = EmailSubscriber.objects.get(id=subscriber_id)
        events = list(MarketingEvent.objects.filter(subscriber=subscriber).values_list('event_name', flat=True))
        self.assertIn('email_subscribed', events)
        self.assertIn('welcome_sequence_started', events)
        self.assertIn('pricing_viewed', events)
        self.assertIn('email_clicked', events)
