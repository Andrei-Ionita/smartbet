import uuid
from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    FixtureResultObservation,
    GemFeedCache,
    PublicSelection,
    PublicSelectionResult,
    StrategyLabExperiment,
    StrategyLabObservation,
    StrategyLabSettlement,
)
from core.services import public_selections


class PublicSelectionTests(TestCase):
    def setUp(self):
        self.now = timezone.now()

    def selection(self, **changes):
        fields = {
            'category': PublicSelection.CATEGORY_HOMEPAGE,
            'source_key': 'homepage',
            'source_version': 'ranking-test',
            'source_ref': f'test:{uuid.uuid4()}',
            'reason_code': PublicSelection.REASON_VALUE,
            'fixture_id': 700001,
            'home_team': 'Home',
            'away_team': 'Away',
            'league': 'Test League',
            'kickoff': self.now + timedelta(hours=8),
            'market_type': '1x2',
            'predicted_outcome': 'Home',
            'model_score': 0.63,
            'odds': 2.10,
            'bookmaker': 'Test Book',
            'bookmaker_count': 4,
            'odds_captured_at': self.now - timedelta(minutes=10),
            'published_at': self.now,
        }
        fields.update(changes)
        return PublicSelection.objects.create(**fields)

    def result(self, fixture_id=700001, home=2, away=0):
        return FixtureResultObservation.objects.create(
            result_id=uuid.uuid4(), fixture_id=fixture_id,
            home_team='Home', away_team='Away', league='Test League',
            kickoff=self.now - timedelta(hours=3), provider='sportmonks',
            provider_status='FT', home_score=home, away_score=away,
            score_type='CURRENT', is_final=True, is_scoreable=True,
            confirmed=True, result_version=1, captured_at=self.now,
            ingestion_run_id='result-run', source_payload_hash=uuid.uuid4().hex,
        )

    def test_homepage_feed_is_frozen_once_and_is_idempotent(self):
        captured = self.now - timedelta(minutes=5)
        candidate = {
            'fixture_id': 700010, 'home_team': 'Alpha', 'away_team': 'Beta',
            'league': 'League', 'kickoff': (self.now + timedelta(hours=6)).isoformat(),
            'leading_selection': 'Home', 'signal_strength': 0.64,
            'verified_price': 2.05, 'bookmakers_checked': 5,
            'odds_provenance': {
                'odds_captured_at': captured.isoformat(),
                'odds_bookmaker_name': 'Book', 'odds_bookmaker_count': 5,
            },
        }
        GemFeedCache.objects.create(
            key=GemFeedCache.CACHE_KEY,
            payload={'recommendations': [], 'decision_board': {
                'price_watchlist': [candidate], 'strong_signals': [],
            }},
            generated_at=self.now, ranking_version='rank-v1',
            recommendation_count=0,
        )

        first = public_selections.publish_homepage_selections(now=self.now)
        second = public_selections.publish_homepage_selections(now=self.now)
        self.assertEqual(first['published'], 1)
        self.assertEqual(second['published'], 0)
        row = PublicSelection.objects.get()
        self.assertTrue(row.verify_integrity())
        self.assertEqual(row.reason_code, PublicSelection.REASON_VALUE)
        with self.assertRaises(ValueError):
            row.save()

    def test_homepage_selection_settles_at_its_frozen_price(self):
        row = self.selection()
        self.result()
        summary = public_selections.settle_public_selections(now=self.now)
        self.assertEqual(summary['settled'], 1)
        settled = PublicSelectionResult.objects.get(selection=row)
        self.assertEqual(settled.status, PublicSelectionResult.STATUS_WON)
        self.assertAlmostEqual(settled.unit_profit, 1.10)

    def test_strategy_half_win_reuses_exact_lab_settlement(self):
        experiment = StrategyLabExperiment.objects.create(
            strategy_key='asian-handicap-score-distribution', version='test-v1',
            name='AH test', market='asian_handicap', status='shadow',
            rules={}, rules_hash=uuid.uuid4().hex,
        )
        observation = StrategyLabObservation.objects.create(
            experiment=experiment, evidence_phase='forward',
            ingestion_run_id='strategy-run', source_payload_hash=uuid.uuid4().hex,
            fixture_id=700020, home_team='Home', away_team='Away',
            league='League', kickoff=self.now + timedelta(hours=3),
            observed_at=self.now - timedelta(hours=2), hours_to_kickoff=5,
            market='asian_handicap', side='home', handicap=-0.75,
            label='Home -0.75', odds=1.90, bookmaker='Book',
            bookmaker_count=4, price_min=1.85, price_max=1.90,
            odds_captured_at=self.now - timedelta(hours=2), model_mass=0.60,
            expected_return_lower=0.05, expected_return_upper=0.12,
            robust_positive_edge=True,
        )
        row = self.selection(
            category=PublicSelection.CATEGORY_STRATEGY,
            source_key=experiment.strategy_key, source_version=experiment.version,
            source_ref=f'strategy:{observation.observation_id}',
            reason_code=PublicSelection.REASON_STRATEGY,
            source_strategy_observation=observation, fixture_id=700020,
            market_type='asian_handicap', predicted_outcome='Home -0.75',
            side='home', line=-0.75, odds=1.90,
        )
        result = self.result(fixture_id=700020, home=2, away=1)
        StrategyLabSettlement.objects.create(
            observation=observation, result=result, result_version=1,
            home_score=2, away_score=1,
            outcome=StrategyLabSettlement.OUTCOME_HALF_WIN,
            unit_profit=0.45, settlement_hash=uuid.uuid4().hex,
        )
        public_selections.settle_public_selections(now=self.now)
        settled = PublicSelectionResult.objects.get(selection=row)
        self.assertEqual(settled.status, PublicSelectionResult.STATUS_HALF_WON)
        self.assertEqual(settled.unit_profit, 0.45)

    def test_strategy_selection_settles_from_its_frozen_terms_without_lab_row(self):
        experiment = StrategyLabExperiment.objects.create(
            strategy_key='asian-handicap-score-distribution', version='test-v2',
            name='AH test', market='asian_handicap', status='shadow',
            rules={}, rules_hash=uuid.uuid4().hex,
        )
        observation = StrategyLabObservation.objects.create(
            experiment=experiment, evidence_phase='forward',
            ingestion_run_id='strategy-public-run',
            source_payload_hash=uuid.uuid4().hex,
            fixture_id=700021, home_team='Home', away_team='Away',
            league='League', kickoff=self.now + timedelta(hours=3),
            observed_at=self.now - timedelta(hours=2), hours_to_kickoff=5,
            market='asian_handicap', side='home', handicap=-0.75,
            label='Home -0.75', odds=1.90, bookmaker='Book',
            bookmaker_count=4, price_min=1.85, price_max=1.90,
            odds_captured_at=self.now - timedelta(hours=2), model_mass=0.60,
            expected_return_lower=0.05, expected_return_upper=0.12,
            robust_positive_edge=True,
        )
        row = self.selection(
            category=PublicSelection.CATEGORY_STRATEGY,
            source_key=experiment.strategy_key,
            source_version=experiment.version,
            source_ref=f'strategy:{observation.observation_id}',
            reason_code=PublicSelection.REASON_STRATEGY,
            source_strategy_observation=observation, fixture_id=700021,
            market_type='asian_handicap', predicted_outcome='Home -0.75',
            side='home', line=-0.75, odds=1.90,
        )
        self.result(fixture_id=700021, home=2, away=1)

        summary = public_selections.settle_public_selections(now=self.now)

        self.assertEqual(summary['settled'], 1)
        settled = PublicSelectionResult.objects.get(selection=row)
        self.assertEqual(settled.status, PublicSelectionResult.STATUS_HALF_WON)
        self.assertAlmostEqual(settled.unit_profit, 0.45)
        self.assertEqual(StrategyLabSettlement.objects.count(), 0)

    def test_strategy_publication_never_exceeds_five_active_selections(self):
        strategy_key = 'full-time-result-value'
        experiment = StrategyLabExperiment.objects.create(
            strategy_key=strategy_key, version='limit-v1', name='Limit test',
            market='1x2', status='shadow', rules={}, rules_hash=uuid.uuid4().hex,
        )
        for index in range(4):
            self.selection(
                category=PublicSelection.CATEGORY_STRATEGY,
                source_key=strategy_key,
                source_ref=f'existing:{index}', fixture_id=710000 + index,
            )

        fits = []
        for index in range(2):
            fixture_id = 720000 + index
            StrategyLabObservation.objects.create(
                experiment=experiment, evidence_phase='forward',
                ingestion_run_id=f'limit-run-{index}',
                source_payload_hash=uuid.uuid4().hex,
                fixture_id=fixture_id, home_team=f'Home {index}',
                away_team=f'Away {index}', league='League',
                kickoff=self.now + timedelta(hours=6 + index),
                observed_at=self.now - timedelta(minutes=10),
                hours_to_kickoff=6 + index, market='1x2', side='home',
                label='Home', odds=2.0, bookmaker='Book', bookmaker_count=3,
                price_min=1.95, price_max=2.0,
                odds_captured_at=self.now - timedelta(minutes=10),
                model_mass=0.58, expected_return_lower=0.02,
                expected_return_upper=0.08, robust_positive_edge=True,
            )
            fits.append({
                'fixture_id': fixture_id, 'side': 'home',
                'selection': 'Home', 'line': None,
            })

        report = {
            'strategy_key': strategy_key, 'version': experiment.version,
            'fits': fits,
        }
        with mock.patch.object(
            public_selections.strategy_lab, 'STRATEGY_DEFINITIONS',
            [{'strategy_key': strategy_key}],
        ), mock.patch.object(
            public_selections.strategy_lab, 'build_public_current_fits',
            return_value=report,
        ):
            summary = public_selections.publish_strategy_selections(now=self.now)

        self.assertEqual(summary['published'], 1)
        self.assertEqual(PublicSelection.objects.filter(
            category=PublicSelection.CATEGORY_STRATEGY,
            source_key=strategy_key, kickoff__gt=self.now,
        ).count(), 5)

    def test_public_api_filters_without_blending_categories(self):
        self.selection()
        self.selection(
            category=PublicSelection.CATEGORY_STRATEGY,
            source_key='full-time-result-value', source_ref='strategy:test',
            fixture_id=700002,
        )
        response = APIClient().get('/api/results/selections/?category=homepage')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['total'], 1)
        self.assertEqual(body['selections'][0]['category'], 'homepage')
        self.assertTrue(body['policy']['categories_are_separate'])

    def test_public_api_rejects_unknown_filter(self):
        response = APIClient().get('/api/results/selections/?category=combined')
        self.assertEqual(response.status_code, 400)

    def test_public_receipt_is_permanent_and_fixture_filter_is_supported(self):
        row = self.selection()
        self.selection(fixture_id=700002, source_ref='homepage:other')

        filtered = APIClient().get('/api/results/selections/?fixture_id=700001')
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(filtered.json()['total'], 1)

        receipt = APIClient().get(f'/api/results/selections/{row.selection_id}/')
        self.assertEqual(receipt.status_code, 200)
        body = receipt.json()
        self.assertEqual(body['selection']['selection_id'], str(row.selection_id))
        self.assertEqual(
            body['selection']['receipt_url'],
            f'/results/selection/{row.selection_id}',
        )
        self.assertTrue(body['selection']['integrity_ok'])
        self.assertTrue(body['policy']['selection_is_immutable'])
