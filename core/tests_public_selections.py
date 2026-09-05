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
    PublicSelectionClosingPrice,
    PublicSelectionResult,
    SignalObservation,
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
            'market_type': 'btts', 'leading_selection': 'BTTS Yes',
            'signal_strength': 0.64,
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
        self.assertEqual(row.source_key, 'portfolio-v4')
        self.assertEqual(row.market_type, 'btts')
        with self.assertRaises(ValueError):
            row.save()

    def test_strong_signal_is_frozen_for_forward_engine_validation(self):
        captured = self.now - timedelta(minutes=5)
        candidate = {
            'fixture_id': 700011, 'home_team': 'Alpha', 'away_team': 'Beta',
            'league': 'League', 'kickoff': (self.now + timedelta(hours=6)).isoformat(),
            'market_type': 'over_under_2.5',
            'leading_selection': 'Over 2.5', 'signal_strength': 0.80,
            'verified_price': 1.30, 'bookmakers_checked': 5,
            'odds_provenance': {
                'odds_captured_at': captured.isoformat(),
                'odds_bookmaker_name': 'Book', 'odds_bookmaker_count': 5,
            },
        }
        GemFeedCache.objects.create(
            key=GemFeedCache.CACHE_KEY,
            payload={'decision_board': {
                'price_watchlist': [], 'strong_signals': [candidate],
            }},
            generated_at=self.now, ranking_version='rank-v3',
            recommendation_count=0,
        )

        summary = public_selections.publish_homepage_selections(now=self.now)

        self.assertEqual(summary['published'], 1)
        row = PublicSelection.objects.get()
        self.assertEqual(row.reason_code, PublicSelection.REASON_STRONG)
        self.assertEqual(row.source_key, 'portfolio-v4')
        self.assertEqual(row.market_type, 'over_under_2.5')

    def test_closing_price_is_append_only_and_exposed_on_receipt(self):
        kickoff = self.now - timedelta(hours=1)
        row = self.selection(
            fixture_id=700012, kickoff=kickoff,
            odds=2.10, published_at=kickoff - timedelta(hours=6),
            odds_captured_at=kickoff - timedelta(hours=6),
        )
        SignalObservation.objects.create(
            observation_id=uuid.uuid4(), ingestion_run_id='closing-run',
            source_payload_hash=uuid.uuid4().hex, fixture_id=row.fixture_id,
            home_team='Home', away_team='Away', league='Test League',
            kickoff=kickoff, observed_at=kickoff - timedelta(minutes=5),
            hours_to_kickoff=5 / 60, market='1x2', outcome='home',
            raw_probability=55, normalized_probability=.55,
            raw_vector={'home': .55, 'draw': .25, 'away': .20},
            vector_sum=1, vector_complete=True, price_status='verified',
            odds=2.0, bookmaker='Closing Book',
            odds_captured_at=kickoff - timedelta(minutes=5),
            odds_provenance={'odds_bookmaker_count': 6},
            provenance_complete=True,
            market_price_vector={
                'home': {'odds': 2.0}, 'draw': {'odds': 3.5},
                'away': {'odds': 4.0},
            },
            price_vector_complete=True,
        )

        first = public_selections.capture_closing_prices(now=self.now)
        second = public_selections.capture_closing_prices(now=self.now)

        self.assertEqual(first['captured'], 1)
        self.assertEqual(second['captured'], 0)
        close = PublicSelectionClosingPrice.objects.get(selection=row)
        self.assertAlmostEqual(close.closing_line_value, .05)
        body = APIClient().get(
            f'/api/results/selections/{row.selection_id}/',
        ).json()['selection']
        self.assertEqual(body['closing_price']['odds'], 2.0)
        self.assertEqual(
            body['closing_price']['closing_line_value_percent'], 5.0,
        )

    def test_homepage_selection_settles_at_its_frozen_price(self):
        row = self.selection()
        self.result()
        summary = public_selections.settle_public_selections(now=self.now)
        self.assertEqual(summary['settled'], 1)
        settled = PublicSelectionResult.objects.get(selection=row)
        self.assertEqual(settled.status, PublicSelectionResult.STATUS_WON)
        self.assertAlmostEqual(settled.unit_profit, 1.10)

    def test_multi_market_portfolio_uses_registered_fulltime_graders(self):
        cases = (
            (700101, 'over_under_1.5', 'Over 1.5', (1, 1), True),
            (700102, 'over_under_3.5', 'Under 3.5', (2, 1), True),
            (700103, 'correct_score', '2-1', (2, 1), True),
            (700104, 'correct_score', '1-1', (2, 1), False),
        )
        rows = []
        for fixture_id, market, outcome, score, _ in cases:
            rows.append(self.selection(
                fixture_id=fixture_id,
                source_key='portfolio-v4',
                source_ref=f'portfolio-v4:test:{fixture_id}',
                market_type=market,
                predicted_outcome=outcome,
            ))
            self.result(fixture_id=fixture_id, home=score[0], away=score[1])

        summary = public_selections.settle_public_selections(now=self.now)

        self.assertEqual(summary['settled'], len(cases))
        for row, case in zip(rows, cases):
            expected_won = case[-1]
            result = PublicSelectionResult.objects.get(selection=row)
            self.assertEqual(
                result.status,
                PublicSelectionResult.STATUS_WON if expected_won
                else PublicSelectionResult.STATUS_LOST,
            )

    def test_unknown_market_stays_pending_instead_of_being_misgraded_as_1x2(self):
        row = self.selection(
            fixture_id=700105,
            source_key='portfolio-v4',
            source_ref='portfolio-v4:test:unknown',
            market_type='half_time_result',
            predicted_outcome='Home at half-time',
        )
        self.result(fixture_id=row.fixture_id, home=2, away=0)

        summary = public_selections.settle_public_selections(now=self.now)

        self.assertEqual(summary['settled'], 0)
        self.assertFalse(PublicSelectionResult.objects.filter(selection=row).exists())

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

    def test_public_api_returns_canonical_performance_and_cohorts(self):
        won = self.selection(fixture_id=700101, source_ref='homepage:won')
        lost = self.selection(
            category=PublicSelection.CATEGORY_STRATEGY,
            source_key='full-time-result-value',
            source_ref='strategy:lost', fixture_id=700102, odds=1.80,
        )
        PublicSelectionResult.objects.create(
            selection=won, status=PublicSelectionResult.STATUS_WON,
            unit_profit=1.10, actual_score_home=2, actual_score_away=0,
            result_source='sportmonks', result_reference='test:won',
        )
        PublicSelectionResult.objects.create(
            selection=lost, status=PublicSelectionResult.STATUS_LOST,
            unit_profit=-1, actual_score_home=0, actual_score_away=1,
            result_source='sportmonks', result_reference='test:lost',
        )

        body = APIClient().get('/api/results/selections/').json()
        summary = body['performance']['overall']
        self.assertEqual(summary['published'], 2)
        self.assertEqual(summary['settled'], 2)
        self.assertEqual(summary['profit_units'], 0.1)
        self.assertEqual(summary['roi_percent'], 5.0)
        self.assertEqual(summary['sample_band'], 'very_early')
        self.assertEqual(
            body['performance']['by_strategy'][0]['key'],
            'full-time-result-value',
        )

    def test_audit_regrades_settlement_without_changing_the_ledger(self):
        row = self.selection(fixture_id=700103, source_ref='homepage:audit')
        result = self.result(fixture_id=700103, home=2, away=0)
        PublicSelectionResult.objects.create(
            selection=row, status=PublicSelectionResult.STATUS_WON,
            unit_profit=1.10, actual_score_home=2, actual_score_away=0,
            result_source=result.provider,
            result_reference=f'fixture-result:{result.result_id}',
        )
        report = public_selections.audit_ledger()
        self.assertEqual(report['checked'], 1)
        self.assertEqual(report['issue_count'], 0)
        self.assertEqual(PublicSelectionResult.objects.count(), 1)

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
