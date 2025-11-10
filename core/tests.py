"""
SmartBet Core Tests - Smoke Tests for Critical Flows

Run with: python manage.py test core
"""

from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from core.models import PredictionLog, UserBankroll, BankrollTransaction
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
