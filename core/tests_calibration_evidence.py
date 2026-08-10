"""Contracts for the public prediction archive and calibration denominator."""

import uuid
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from core.models import FixtureResultObservation, SignalObservation
from core.services import calibration_evidence


def observation(fixture_id, *, market='1x2', vector=None, hours=6,
                vector_complete=True, observed_offset_minutes=0):
    kickoff = timezone.now() - timedelta(days=2)
    vector = vector or {'home': 0.7, 'draw': 0.2, 'away': 0.1}
    observed_at = kickoff - timedelta(hours=hours, minutes=observed_offset_minutes)
    return SignalObservation.objects.create(
        observation_id=uuid.uuid4(),
        ingestion_run_id=f'run-{fixture_id}-{uuid.uuid4()}',
        source_payload_hash=str(uuid.uuid4()),
        fixture_id=fixture_id,
        home_team=f'Home {fixture_id}',
        away_team=f'Away {fixture_id}',
        league='Evidence League',
        league_id=44,
        kickoff=kickoff,
        observed_at=observed_at,
        hours_to_kickoff=hours + observed_offset_minutes / 60,
        market=market,
        outcome=next(iter(vector)),
        raw_probability=next(iter(vector.values())) * 100,
        normalized_probability=next(iter(vector.values())),
        raw_vector=vector,
        vector_sum=sum(vector.values()),
        vector_complete=vector_complete,
        provider_model_version='provider-v1',
        pipeline_version='pipeline-v1',
        calculation_version='commit-abc',
    )


def confirmed_result(fixture_id, home=2, away=0, *, confirmed=True,
                     scoreable=True, version=1, supersedes=None):
    return FixtureResultObservation.objects.create(
        result_id=uuid.uuid4(),
        fixture_id=fixture_id,
        home_team=f'Home {fixture_id}',
        away_team=f'Away {fixture_id}',
        league='Evidence League',
        league_id=44,
        kickoff=timezone.now() - timedelta(days=2),
        provider_status='FT',
        home_score=home,
        away_score=away,
        score_type='CURRENT',
        is_final=True,
        is_scoreable=scoreable,
        confirmed=confirmed,
        result_version=version,
        supersedes=supersedes,
        captured_at=timezone.now(),
        ingestion_run_id=f'result-{fixture_id}-{version}',
        source_payload_hash=str(uuid.uuid4()),
    )


class DecisionSelectionTests(TestCase):
    def test_uses_closest_complete_vector_outside_fixed_horizon(self):
        observation(1001, vector={'home': .55, 'draw': .25, 'away': .20}, hours=12)
        chosen = observation(1001, vector={'home': .72, 'draw': .18, 'away': .10}, hours=2)
        observation(1001, vector={'home': .95, 'draw': .03, 'away': .02}, hours=.5)
        confirmed_result(1001)

        decisions, coverage = calibration_evidence.collect_decisions()

        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]['observation_id'], str(chosen.observation_id))
        self.assertAlmostEqual(decisions[0]['probabilities']['home'], .72)
        self.assertEqual(coverage['fixture_market_universe'], 1)

    def test_outcome_rows_and_repeated_sweeps_do_not_inflate_sample(self):
        for outcome in ('home', 'draw', 'away'):
            row = observation(1002, hours=4)
            # Bypass insert-only save solely to represent the sibling outcome
            # rows produced by one evidence sweep.
            SignalObservation.objects.filter(pk=row.pk).update(outcome=outcome)
        observation(1002, vector={'home': .65, 'draw': .2, 'away': .15}, hours=2)
        confirmed_result(1002)

        decisions, _ = calibration_evidence.collect_decisions()
        self.assertEqual(len(decisions), 1)

    def test_only_latest_confirmed_scoreable_result_is_evaluated(self):
        observation(1003)
        first = confirmed_result(1003, home=1, away=0, confirmed=True)
        confirmed_result(
            1003, home=1, away=1, confirmed=False, version=2, supersedes=first,
        )

        decisions, _ = calibration_evidence.collect_decisions()
        self.assertEqual(decisions[0]['state'], 'awaiting_confirmation')
        self.assertIsNone(decisions[0]['actual_outcome'])

    def test_incomplete_and_inside_horizon_groups_are_reported(self):
        observation(1004, vector_complete=False, hours=5)
        observation(1005, hours=.5)

        decisions, coverage = calibration_evidence.collect_decisions()
        self.assertEqual(decisions, [])
        self.assertEqual(
            coverage['excluded_before_evaluation'],
            {'incomplete_probability_vector': 1, 'inside_evaluation_horizon': 1},
        )

    def test_double_chance_is_archived_but_not_counted_as_calibration(self):
        observation(
            1006,
            market='double_chance',
            vector={'1x': .76, 'x2': .62, '12': .62},
        )
        confirmed_result(1006, home=2, away=0)

        decisions, _ = calibration_evidence.collect_decisions()
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]['state'], 'evaluated')
        self.assertEqual(decisions[0]['actual_outcome'], '1x + 12')
        self.assertTrue(decisions[0]['correct'])
        self.assertIsNone(decisions[0]['brier_score'])

        report = calibration_evidence.build_report()
        self.assertEqual(report['coverage']['evaluated_market_decisions'], 0)
        self.assertNotIn('double_chance', [row['market'] for row in report['markets']])


class CalibrationMetricTests(TestCase):
    def test_small_samples_are_archived_but_public_metrics_stay_hidden(self):
        observation(1101)
        confirmed_result(1101)

        report = calibration_evidence.build_report()
        match_result = report['markets'][0]

        self.assertEqual(match_result['fixture_count'], 1)
        self.assertEqual(match_result['evidence_level'], 'collecting')
        self.assertFalse(match_result['metrics_visible'])
        self.assertIsNone(match_result['provider']['brier_score'])

    def test_metrics_unlock_at_declared_fixture_minimum(self):
        for fixture_id in range(1200, 1200 + calibration_evidence.MIN_PUBLIC_FIXTURES):
            observation(fixture_id)
            confirmed_result(fixture_id)

        report = calibration_evidence.build_report()
        match_result = report['markets'][0]

        self.assertTrue(match_result['metrics_visible'])
        self.assertEqual(match_result['fixture_count'], calibration_evidence.MIN_PUBLIC_FIXTURES)
        self.assertLess(
            match_result['provider']['brier_score'],
            match_result['uniform_baseline']['brier_score'],
        )
        self.assertEqual(report['coverage']['evaluated_fixtures'], 30)
        self.assertEqual(report['coverage']['evaluated_market_decisions'], 30)

    def test_multiple_markets_share_one_fixture_count(self):
        observation(1301)
        observation(1301, market='btts', vector={'yes': .6, 'no': .4})
        confirmed_result(1301, home=2, away=1)

        report = calibration_evidence.build_report()
        self.assertEqual(report['coverage']['evaluated_market_decisions'], 2)
        self.assertEqual(report['coverage']['evaluated_fixtures'], 1)


class CalibrationApiTests(TestCase):
    def test_report_is_public_and_states_methodology(self):
        response = self.client.get('/api/transparency/calibration/')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['data']['methodology_version'], 'calibration-evidence-v1')
        self.assertEqual(payload['data']['evaluation_horizon_hours'], 1.0)

    def test_archive_includes_pending_rows_and_paginates(self):
        observation(1401)
        observation(1402)
        confirmed_result(1402)

        response = self.client.get(
            '/api/transparency/prediction-archive/?page_size=1&state=pending_result'
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['pagination']['total'], 1)
        self.assertEqual(payload['decisions'][0]['fixture_id'], 1401)
        self.assertEqual(payload['decisions'][0]['state'], 'pending_result')
        self.assertIn('probabilities', payload['decisions'][0])

    def test_archive_rejects_unknown_filters(self):
        response = self.client.get('/api/transparency/prediction-archive/?market=correct_score')
        self.assertEqual(response.status_code, 400)
