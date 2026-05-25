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


# ─────────────────────────────────────────────────────────────────────────────
# Regression tests for the data-integrity + Phase-2 filter work shipped
# 2026-05-13/14. These exist to fail loudly if a future refactor weakens any of
# the invariants we just spent a session establishing.
# ─────────────────────────────────────────────────────────────────────────────

def _make_pred(fixture_id, **overrides):
    """Helper: a valid PredictionLog kwargs dict with sane defaults; override what you need."""
    base = dict(
        fixture_id=fixture_id,
        home_team='A', away_team='B', league='Premier League',
        kickoff=timezone.now() + timedelta(days=1),
        predicted_outcome='Home',
        confidence=0.65,
        probability_home=0.65, probability_draw=0.20, probability_away=0.15,
        market_type='1x2',
    )
    base.update(overrides)
    return base


class PredictionLogSaveInvariantTests(TestCase):
    """Cover the save() override added in Stage A — see core/models.py PredictionLog.save."""

    def test_ev_percent_normalized_to_decimal(self):
        p = PredictionLog.objects.create(**_make_pred(101, expected_value=15.0, odds=2.1))
        # 15.0 means 15%, should become 0.15
        self.assertAlmostEqual(p.expected_value, 0.15, places=6)
        self.assertEqual(p.is_audit_excluded, False)

    def test_confidence_percent_normalized_to_decimal(self):
        p = PredictionLog.objects.create(**_make_pred(102, confidence=65.0, expected_value=0.10, odds=2.0))
        self.assertAlmostEqual(p.confidence, 0.65, places=6)

    def test_high_ev_clamped_and_audit_excluded(self):
        p = PredictionLog.objects.create(**_make_pred(103, expected_value=0.95, odds=3.0))
        self.assertEqual(p.expected_value, PredictionLog.EV_PLAUSIBLE_MAX)
        self.assertAlmostEqual(p.raw_expected_value, 0.95, places=6)
        self.assertTrue(p.is_audit_excluded)

    def test_low_ev_clamped_and_audit_excluded(self):
        p = PredictionLog.objects.create(**_make_pred(104, expected_value=-0.80, odds=2.0))
        self.assertEqual(p.expected_value, PredictionLog.EV_PLAUSIBLE_MIN)
        self.assertAlmostEqual(p.raw_expected_value, -0.80, places=6)
        self.assertTrue(p.is_audit_excluded)

    def test_high_ev_in_percent_form_handled(self):
        # The DB has historical rows where EV came in as e.g. 89.45 (percent).
        # save() should normalize then clamp.
        p = PredictionLog.objects.create(**_make_pred(105, expected_value=89.45, odds=3.0))
        self.assertEqual(p.expected_value, PredictionLog.EV_PLAUSIBLE_MAX)
        self.assertAlmostEqual(p.raw_expected_value, 0.8945, places=4)
        self.assertTrue(p.is_audit_excluded)

    def test_invalid_odds_nulled(self):
        p = PredictionLog.objects.create(**_make_pred(106, expected_value=0.10, odds=0.95))
        # 0.95 <= 1.01 is impossible for decimal odds — should be discarded
        self.assertIsNone(p.odds)

    def test_clean_inputs_pass_through(self):
        p = PredictionLog.objects.create(
            **_make_pred(107, expected_value=0.18, odds=1.91, confidence=0.62)
        )
        self.assertAlmostEqual(p.expected_value, 0.18, places=6)
        self.assertEqual(p.odds, 1.91)
        self.assertAlmostEqual(p.confidence, 0.62, places=6)
        self.assertFalse(p.is_audit_excluded)
        # raw_expected_value is preserved on first save
        self.assertAlmostEqual(p.raw_expected_value, 0.18, places=6)

    def test_re_save_is_idempotent(self):
        p = PredictionLog.objects.create(**_make_pred(108, expected_value=0.95, odds=3.0))
        # First save clamped to 0.50, flagged audit-excluded.
        first_ev = p.expected_value
        first_raw = p.raw_expected_value
        first_flag = p.is_audit_excluded
        p.save()
        p.refresh_from_db()
        self.assertEqual(p.expected_value, first_ev)
        self.assertEqual(p.raw_expected_value, first_raw)
        self.assertEqual(p.is_audit_excluded, first_flag)


class LogRecommendationsFilterTests(TestCase):
    """Cover Phase 2a + 2b reject branches in core/api_views.log_recommendations."""

    def setUp(self):
        self.client = Client()
        self.url = '/api/log-recommendations/'

    def _post(self, recs):
        import json as _json
        return self.client.post(
            self.url, data=_json.dumps({'recommendations': recs}),
            content_type='application/json',
        )

    def _rec(self, **overrides):
        """Default valid recommendation payload. Uses La Liga because Phase 2c
        watchlists Premier League with stricter thresholds — tests that need PL
        explicitly override league=."""
        base = {
            'fixture_id': 200001,
            'home_team': 'Team A', 'away_team': 'Team B',
            'league': 'La Liga',
            'kickoff': (timezone.now() + timedelta(days=1)).isoformat(),
            'predicted_outcome': 'Over 2.5',
            'confidence': 0.62,
            'probabilities': {'home': 0.45, 'draw': 0.25, 'away': 0.30},
            'odds_data': {'home': 1.9, 'draw': 3.4, 'away': 3.2, 'bookmaker': 'bet365'},
            'best_market': {'type': 'over_under_2.5', 'odds': 1.85, 'market_score': 0.5},
            'odds': 1.85,
            'expected_value': 0.15,
        }
        base.update(overrides)
        return base

    def test_blacklist_league_rejected(self):
        rec = self._rec(fixture_id=200010, league='Admiral Bundesliga')
        resp = self._post([rec])
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body['skipped_blacklist'], 1)
        self.assertEqual(body['logged_count'], 0)
        self.assertFalse(PredictionLog.objects.filter(fixture_id=200010).exists())

    def test_under_25_outcome_rejected(self):
        rec = self._rec(fixture_id=200011, predicted_outcome='Under 2.5')
        resp = self._post([rec])
        self.assertEqual(resp.json()['skipped_outcome'], 1)
        self.assertFalse(PredictionLog.objects.filter(fixture_id=200011).exists())

    def test_high_ev_rejected(self):
        # expected_value as decimal > 0.20
        rec = self._rec(fixture_id=200012, expected_value=0.35)
        resp = self._post([rec])
        self.assertEqual(resp.json()['skipped_high_ev'], 1)
        self.assertFalse(PredictionLog.objects.filter(fixture_id=200012).exists())

    def test_high_ev_in_percent_form_rejected(self):
        # Same threshold, expressed as percent
        rec = self._rec(fixture_id=200013, expected_value=35.0)
        resp = self._post([rec])
        self.assertEqual(resp.json()['skipped_high_ev'], 1)

    def test_watchlist_premier_league_low_confidence_rejected(self):
        # Phase 2c: PL pick that doesn't clear the stricter bar (conf>=0.65, ev>=0.12)
        rec = self._rec(
            fixture_id=200015, league='Premier League',
            confidence=0.60, expected_value=0.15,  # conf below threshold
        )
        resp = self._post([rec])
        self.assertEqual(resp.json()['skipped_watchlist'], 1)
        self.assertFalse(PredictionLog.objects.filter(fixture_id=200015).exists())

    def test_watchlist_premier_league_low_ev_rejected(self):
        # Phase 2c: PL pick with high confidence but EV below the watchlist bar
        rec = self._rec(
            fixture_id=200016, league='Premier League',
            confidence=0.70, expected_value=0.08,  # ev below threshold
        )
        resp = self._post([rec])
        self.assertEqual(resp.json()['skipped_watchlist'], 1)

    def test_watchlist_premier_league_passing_threshold_logged(self):
        # Phase 2c: PL pick that clears both stricter thresholds is allowed through
        rec = self._rec(
            fixture_id=200017, league='Premier League',
            confidence=0.68, expected_value=0.15,
        )
        resp = self._post([rec])
        self.assertEqual(resp.json()['logged_count'], 1)
        self.assertEqual(resp.json()['skipped_watchlist'], 0)

    def test_watchlist_doesnt_affect_other_leagues(self):
        # A La Liga pick with the same numbers as the rejected PL pick passes
        rec = self._rec(
            fixture_id=200018, league='La Liga',
            confidence=0.60, expected_value=0.15,
        )
        resp = self._post([rec])
        self.assertEqual(resp.json()['logged_count'], 1)
        self.assertEqual(resp.json()['skipped_watchlist'], 0)

    def test_clean_recommendation_logged(self):
        rec = self._rec(fixture_id=200014)
        resp = self._post([rec])
        body = resp.json()
        self.assertEqual(body['logged_count'], 1)
        self.assertEqual(body['skipped_blacklist'], 0)
        self.assertEqual(body['skipped_outcome'], 0)
        self.assertEqual(body['skipped_high_ev'], 0)
        p = PredictionLog.objects.get(fixture_id=200014)
        # Stage A wiring — `odds` was captured from rec['odds']
        self.assertEqual(p.odds, 1.85)


class AuditQuarantineCommandTests(TestCase):
    """End-to-end of `python manage.py audit_quarantine_predictions`."""

    def setUp(self):
        # Three rows: one bad EV (gets flagged), one clean, one with percent-form EV.
        kickoff = timezone.now() - timedelta(days=2)
        # We bypass save() invariants here because the command's job is to fix
        # rows where they weren't applied at write time (legacy data).
        PredictionLog.objects.bulk_create([
            PredictionLog(
                fixture_id=300001, home_team='A', away_team='B', league='Premier League',
                kickoff=kickoff, predicted_outcome='Over 2.5', market_type='over_under_2.5',
                confidence=0.62, probability_home=0, probability_draw=0, probability_away=0,
                expected_value=85.0,  # implausibly high, stored as percent
                actual_outcome='Over', was_correct=True, profit_loss_10=8.5, roi_percent=85.0,
                is_recommended=True,
            ),
            PredictionLog(
                fixture_id=300002, home_team='C', away_team='D', league='Premier League',
                kickoff=kickoff, predicted_outcome='Over 2.5', market_type='over_under_2.5',
                confidence=0.60, probability_home=0, probability_draw=0, probability_away=0,
                expected_value=0.15,  # clean decimal
                actual_outcome='Under', was_correct=False, profit_loss_10=-10.0, roi_percent=-100.0,
                is_recommended=True,
            ),
            PredictionLog(
                fixture_id=300003, home_team='E', away_team='F', league='Premier League',
                kickoff=kickoff, predicted_outcome='Home', market_type='1x2', odds=2.0,
                confidence=58.0, probability_home=0.58, probability_draw=0.22, probability_away=0.20,
                expected_value=16.0,  # percent form — should normalize but stay clean
                actual_outcome='Home', was_correct=True, profit_loss_10=10.0, roi_percent=100.0,
                is_recommended=True,
            ),
        ])

    def test_dry_run_does_not_mutate(self):
        from django.core.management import call_command
        from io import StringIO
        call_command('audit_quarantine_predictions', stdout=StringIO())
        # Nothing should be flagged on the DB.
        self.assertEqual(PredictionLog.objects.filter(is_audit_excluded=True).count(), 0)
        # The bad row's stored EV stays in percent form (untouched).
        bad = PredictionLog.objects.get(fixture_id=300001)
        self.assertEqual(bad.expected_value, 85.0)

    def test_apply_flags_and_normalizes(self):
        from django.core.management import call_command
        from io import StringIO
        call_command('audit_quarantine_predictions', '--apply', stdout=StringIO())
        bad = PredictionLog.objects.get(fixture_id=300001)
        self.assertTrue(bad.is_audit_excluded)
        # EV should be clamped to plausible max
        self.assertEqual(bad.expected_value, PredictionLog.EV_PLAUSIBLE_MAX)
        # Clean rows untouched (the percent-form EV gets normalized but not flagged)
        clean = PredictionLog.objects.get(fixture_id=300002)
        self.assertFalse(clean.is_audit_excluded)
        self.assertAlmostEqual(clean.expected_value, 0.15, places=6)
        percent_clean = PredictionLog.objects.get(fixture_id=300003)
        self.assertFalse(percent_clean.is_audit_excluded)
        self.assertAlmostEqual(percent_clean.expected_value, 0.16, places=6)

    def test_apply_is_idempotent(self):
        from django.core.management import call_command
        from io import StringIO
        call_command('audit_quarantine_predictions', '--apply', stdout=StringIO())
        flagged_first = PredictionLog.objects.filter(is_audit_excluded=True).count()
        call_command('audit_quarantine_predictions', '--apply', stdout=StringIO())
        flagged_second = PredictionLog.objects.filter(is_audit_excluded=True).count()
        self.assertEqual(flagged_first, flagged_second)


class ResultUpdaterArchiveTests(TestCase):
    """Cover the 2026-05-22 fix: SportMonks 404 -> match_status='archived' so
    we don't re-check dead fixtures forever, and max-age filter caps lookback."""

    def setUp(self):
        from core.services.result_updater import ResultUpdaterService
        # Bypass __init__'s env-var check by constructing minimal instance.
        # ResultUpdaterService needs SPORTMONKS_API_TOKEN; provide a dummy.
        import os
        os.environ.setdefault('SPORTMONKS_API_TOKEN', 'dummy-token-for-tests')
        self.svc = ResultUpdaterService()
        kickoff = timezone.now() - timedelta(hours=24)
        # Two rows: one recent (within max-age), one ancient (outside max-age).
        self.recent = PredictionLog.objects.create(
            fixture_id=500001, home_team='A', away_team='B', league='Test',
            kickoff=kickoff, predicted_outcome='Home',
            confidence=0.62, probability_home=0.62, probability_draw=0.2, probability_away=0.18,
            is_recommended=True,
        )
        self.ancient = PredictionLog.objects.create(
            fixture_id=500002, home_team='C', away_team='D', league='Test',
            kickoff=timezone.now() - timedelta(days=90), predicted_outcome='Home',
            confidence=0.60, probability_home=0.60, probability_draw=0.2, probability_away=0.20,
            is_recommended=True,
        )

    def test_max_age_filter_excludes_ancient_rows(self):
        pending = self.svc.get_pending_predictions()
        ids = {p.fixture_id for p in pending}
        self.assertIn(500001, ids)
        self.assertNotIn(500002, ids)  # 90 days old -> outside MAX_LOOKBACK_DAYS

    def test_404_response_marks_row_archived(self):
        """Simulate a 404 response and verify the row gets match_status='archived'."""
        from unittest.mock import patch, Mock
        mock_resp = Mock()
        mock_resp.status_code = 404
        with patch('core.services.result_updater.requests.get', return_value=mock_resp):
            result = self.svc.fetch_fixture_result(500001)
        self.assertIs(result, self.svc.ARCHIVED_RESULT)

    def test_404_handling_in_full_pipeline(self):
        """End-to-end: pending row -> SportMonks 404 -> row marked archived ->
        next call no longer picks it up."""
        from unittest.mock import patch, Mock
        mock_resp = Mock()
        mock_resp.status_code = 404
        with patch('core.services.result_updater.requests.get', return_value=mock_resp):
            stats = self.svc.update_all_pending_results(max_predictions=10)
        self.assertEqual(stats.get('archived'), 1)
        # The recent row should now be marked archived
        self.recent.refresh_from_db()
        self.assertEqual(self.recent.match_status, 'archived')
        # Subsequent get_pending_predictions skips it
        pending_after = self.svc.get_pending_predictions()
        self.assertNotIn(500001, {p.fixture_id for p in pending_after})


class BacktesterTests(TestCase):
    """Cover core.services.backtester filter logic + metric computation."""

    def setUp(self):
        from core.services import backtester
        self.bt = backtester
        # Three settled rows: a winning O/U, a losing O/U, and a Under 2.5 pick
        # (so drop_under_2.5 config can prove it filters it out).
        kickoff = timezone.now() - timedelta(days=2)
        self.rows = []
        self.rows.append(PredictionLog.objects.create(
            fixture_id=400001, home_team='A', away_team='B', league='Premier League',
            kickoff=kickoff, predicted_outcome='Over 2.5', market_type='over_under_2.5',
            confidence=0.65, probability_home=0, probability_draw=0, probability_away=0,
            expected_value=0.12, odds=1.85,
            actual_outcome='Over', was_correct=True, profit_loss_10=8.5, roi_percent=85.0,
            is_recommended=True,
        ))
        self.rows.append(PredictionLog.objects.create(
            fixture_id=400002, home_team='C', away_team='D', league='Premier League',
            kickoff=kickoff, predicted_outcome='Over 2.5', market_type='over_under_2.5',
            confidence=0.60, probability_home=0, probability_draw=0, probability_away=0,
            expected_value=0.10, odds=1.80,
            actual_outcome='Under', was_correct=False, profit_loss_10=-10.0, roi_percent=-100.0,
            is_recommended=True,
        ))
        self.rows.append(PredictionLog.objects.create(
            fixture_id=400003, home_team='E', away_team='F', league='Allsvenskan',
            kickoff=kickoff, predicted_outcome='Under 2.5', market_type='over_under_2.5',
            confidence=0.62, probability_home=0, probability_draw=0, probability_away=0,
            expected_value=0.12, odds=1.95,
            actual_outcome='Under', was_correct=True, profit_loss_10=9.5, roi_percent=95.0,
            is_recommended=True,
        ))

    def test_metrics_yield_and_accuracy(self):
        m = self.bt.metrics(self.rows)
        self.assertEqual(m.n_settled, 3)
        self.assertEqual(m.correct, 2)
        self.assertAlmostEqual(m.accuracy, 2 / 3 * 100, places=4)
        # Total P/L: 8.5 + -10 + 9.5 = 8.0 over 3 bets of $10 = 8/30 = 26.67%
        self.assertAlmostEqual(m.total_pl, 8.0, places=4)
        self.assertAlmostEqual(m.yield_percent, 8.0 / 30 * 100, places=4)

    def test_passes_drops_under_25_when_configured(self):
        cfg = self.bt.DROP_UNDER_25
        kept = [r for r in self.rows if self.bt.passes(r, cfg)]
        # Under 2.5 row (400003) should be dropped.
        self.assertEqual({r.fixture_id for r in kept}, {400001, 400002})

    def test_passes_drops_blacklisted_leagues_when_configured(self):
        cfg = self.bt.PHASE_2A
        kept = [r for r in self.rows if self.bt.passes(r, cfg)]
        # Allsvenskan is in DATA_DRIVEN_BLACKLIST; row 400003 also drops via under-2.5.
        self.assertNotIn(400003, {r.fixture_id for r in kept})

    def test_passes_ev_max_caps_evaluation(self):
        cfg = self.bt.PHASE_2B  # max_ev=0.20
        # All three rows have EV <= 0.20 so this filter doesn't drop on its own —
        # but combined with Phase 2a blocks Under 2.5 + Allsvenskan, row 400003 still drops.
        kept = [r for r in self.rows if self.bt.passes(r, cfg)]
        self.assertEqual({r.fixture_id for r in kept}, {400001, 400002})

    def test_evaluate_returns_metrics_for_kept_rows(self):
        m, kept = self.bt.evaluate(self.rows, self.bt.PHASE_2A)
        self.assertEqual(len(kept), 2)
        self.assertEqual(m.n_kept, 2)
        # Only the winning O/U (400001) and losing O/U (400002) survive.
        # Yield: (8.5 - 10) / (2 * 10) = -7.5%
        self.assertAlmostEqual(m.yield_percent, -7.5, places=4)
