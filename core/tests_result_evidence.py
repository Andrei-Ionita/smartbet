"""Result-evidence and market-derivation contracts (Priority 1C)."""
import uuid
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from core.models import FixtureResultObservation, PredictionLog, SignalObservation
from core.services import market_outcomes, result_evidence


def _obs(fixture_id=7001, hours_ago=3, **kw):
    now = timezone.now()
    kickoff = now - timedelta(hours=hours_ago)
    defaults = dict(
        observation_id=uuid.uuid4(),
        ingestion_run_id='run', source_payload_hash=str(uuid.uuid4()),
        fixture_id=fixture_id, home_team='A', away_team='B', league='L',
        kickoff=kickoff, observed_at=kickoff - timedelta(hours=24),
        hours_to_kickoff=24.0, market='over_under_2.5', outcome='over',
        raw_probability=62.0, normalized_probability=0.62,
        raw_vector={'over': 0.62, 'under': 0.38}, vector_sum=1.0,
        vector_complete=True,
    )
    defaults.update(kw)
    return SignalObservation.objects.create(**defaults)


def _fixture(fixture_id=7001, status='FT', home=2, away=1):
    scores = []
    if home is not None:
        scores = [
            {'description': 'CURRENT', 'score': {'participant': 'home', 'goals': home}},
            {'description': 'CURRENT', 'score': {'participant': 'away', 'goals': away}},
        ]
    return {
        'id': fixture_id,
        'state': {'state': status},
        'scores': scores,
        'participants': [
            {'id': 1, 'name': 'A', 'meta': {'location': 'home'}},
            {'id': 2, 'name': 'B', 'meta': {'location': 'away'}},
        ],
        'league': {'id': 9, 'name': 'L'},
        'starting_at': (timezone.now() - timedelta(hours=3)).isoformat(),
    }


class MarketDerivationTests(TestCase):
    def test_all_four_markets_derive_from_a_score(self):
        self.assertEqual(market_outcomes.derive_outcomes(2, 1), {
            '1x2': 'home', 'btts': 'yes', 'over_under_2.5': 'over',
            'double_chance': {'1x': True, 'x2': False, '12': True},
        })
        self.assertEqual(market_outcomes.derive_outcomes(0, 0), {
            '1x2': 'draw', 'btts': 'no', 'over_under_2.5': 'under',
            'double_chance': {'1x': True, 'x2': True, '12': False},
        })
        self.assertEqual(market_outcomes.derive_outcomes(1, 3)['1x2'], 'away')

    def test_the_2_5_line_cannot_push(self):
        self.assertEqual(market_outcomes.derive_outcomes(1, 1)['over_under_2.5'], 'under')
        self.assertEqual(market_outcomes.derive_outcomes(2, 1)['over_under_2.5'], 'over')

    def test_exactly_two_double_chance_legs_win_every_time(self):
        for home in range(5):
            for away in range(5):
                legs = market_outcomes.derive_outcomes(home, away)['double_chance']
                self.assertEqual(sum(legs.values()), 2)

    def test_double_chance_is_fully_determined_by_the_1x2_result(self):
        seen = {}
        for home in range(4):
            for away in range(4):
                outcomes = market_outcomes.derive_outcomes(home, away)
                key = outcomes['1x2']
                legs = tuple(sorted(outcomes['double_chance'].items()))
                if key in seen:
                    self.assertEqual(seen[key], legs)
                seen[key] = legs
        self.assertEqual(market_outcomes.independent_component_count('double_chance'), 0)

    def test_outcome_vectors_are_one_hot_except_double_chance(self):
        self.assertEqual(market_outcomes.outcome_vector('1x2', 2, 1),
                         {'home': 1, 'draw': 0, 'away': 0})
        self.assertEqual(market_outcomes.outcome_vector('btts', 2, 0),
                         {'yes': 0, 'no': 1})
        self.assertEqual(
            sum(market_outcomes.outcome_vector('double_chance', 2, 1).values()), 2)

    def test_a_missing_or_invalid_score_never_becomes_a_draw(self):
        for bad in (None, -1, 1.5, True, 'two'):
            with self.assertRaises(ValueError):
                market_outcomes.derive_outcomes(bad, 1)


class ResultCaptureTests(TestCase):
    def test_fixture_universe_comes_from_observations_not_predictionlog(self):
        _obs(fixture_id=8100)
        self.assertEqual(PredictionLog.objects.count(), 0)
        self.assertIn(8100, result_evidence.fixtures_needing_results())

    def test_future_fixtures_are_not_polled(self):
        _obs(fixture_id=8101, hours_ago=-5)
        self.assertNotIn(8101, result_evidence.fixtures_needing_results())

    def test_replaying_the_same_result_is_idempotent(self):
        _obs(fixture_id=8102)
        first = result_evidence.capture([_fixture(8102)])
        second = result_evidence.capture([_fixture(8102)])
        self.assertEqual(first['written'], 1)
        self.assertEqual(second['written'], 0)
        self.assertEqual(second['duplicate'], 1)

    def test_a_corrected_score_appends_a_new_version(self):
        _obs(fixture_id=8103)
        result_evidence.capture([_fixture(8103, home=2, away=1)])
        result_evidence.capture([_fixture(8103, home=3, away=1)])

        rows = list(FixtureResultObservation.objects
                    .filter(fixture_id=8103).order_by('result_version'))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1].result_version, 2)
        self.assertTrue(rows[1].is_correction)
        self.assertEqual(rows[1].supersedes_id, rows[0].result_id)
        self.assertEqual((rows[0].home_score, rows[0].away_score), (2, 1))

    def test_earlier_result_evidence_cannot_be_overwritten(self):
        _obs(fixture_id=8104)
        result_evidence.capture([_fixture(8104)])
        row = FixtureResultObservation.objects.get()
        row.home_score = 9
        with self.assertRaises(ValueError):
            row.save()

    def test_in_play_and_not_started_are_not_scoreable(self):
        for status in ('INPLAY_2ND_HALF', 'NS', 'HT'):
            with self.subTest(status=status):
                is_final, scoreable, reason = result_evidence.classify(status, 1, 0)
                self.assertFalse(is_final)
                self.assertFalse(scoreable)
                self.assertTrue(reason)

    def test_void_like_states_are_recorded_but_never_scored(self):
        for status in ('POSTP', 'CANCL', 'ABAN', 'SUSP', 'WO', 'AWARDED'):
            with self.subTest(status=status):
                is_final, scoreable, reason = result_evidence.classify(status, 1, 0)
                self.assertFalse(scoreable)
                self.assertTrue(reason.startswith('void_like'))

    def test_extra_time_is_final_but_not_scoreable_for_90_minute_markets(self):
        is_final, scoreable, reason = result_evidence.classify('AET', 3, 2)
        self.assertTrue(is_final)
        self.assertFalse(scoreable)
        self.assertEqual(reason, 'extra_time_not_90min')

    def test_a_final_without_a_score_is_not_scoreable(self):
        is_final, scoreable, reason = result_evidence.classify('FT', None, None)
        self.assertFalse(is_final)
        self.assertFalse(scoreable)
        self.assertEqual(reason, 'final_without_score')

    def test_a_clean_full_time_result_is_scoreable(self):
        is_final, scoreable, reason = result_evidence.classify('FT', 2, 1)
        self.assertTrue(is_final)
        self.assertTrue(scoreable)
        self.assertEqual(reason, '')

    def test_confirmed_finals_stop_being_polled(self):
        _obs(fixture_id=8105)
        result_evidence.capture([_fixture(8105)])
        self.assertIn(8105, result_evidence.fixtures_needing_results())

        row = FixtureResultObservation.objects.get(fixture_id=8105)
        FixtureResultObservation.objects.create(
            result_id=uuid.uuid4(), fixture_id=8105, kickoff=row.kickoff,
            provider_status='FT', home_score=2, away_score=1, score_type='CURRENT',
            is_final=True, is_scoreable=True, confirmed=True, result_version=2,
            supersedes=row, captured_at=timezone.now(), ingestion_run_id='r',
            source_payload_hash=str(uuid.uuid4()),
        )
        self.assertNotIn(8105, result_evidence.fixtures_needing_results())

    def test_void_like_fixtures_stop_being_polled(self):
        _obs(fixture_id=8106)
        result_evidence.capture([_fixture(8106, status='POSTP', home=None, away=None)])
        self.assertNotIn(8106, result_evidence.fixtures_needing_results())

    def test_capture_writes_no_predictions_claims_or_settlements(self):
        from core.models import PredictionSnapshot, PublishedClaim
        _obs(fixture_id=8107)
        before = (PredictionLog.objects.count(), PredictionSnapshot.objects.count(),
                  PublishedClaim.objects.count())
        result_evidence.capture([_fixture(8107)])
        after = (PredictionLog.objects.count(), PredictionSnapshot.objects.count(),
                 PublishedClaim.objects.count())
        self.assertEqual(before, after)


class SchedulerDegradedTests(TestCase):
    def test_a_failed_stage_makes_the_run_degraded_not_successful(self):
        from core.models import SchedulerHeartbeat
        from core.services.scheduler_health import record_run

        with record_run(interval_minutes=60) as run:
            run.stage('capture_signal_evidence', False)
            run.stage('settle_published_claims', True)

        hb = SchedulerHeartbeat.objects.get(key='scheduler')
        self.assertEqual(hb.status, SchedulerHeartbeat.STATUS_DEGRADED)
        self.assertEqual(hb.health(), SchedulerHeartbeat.HEALTH_DEGRADED)
        self.assertEqual(hb.stage_status['capture_signal_evidence'], 'failed')
        self.assertEqual(hb.last_failure_code, 'stage:capture_signal_evidence')
        # A degraded run must not advance "when did everything last work?".
        self.assertIsNone(hb.last_success_at)

    def test_all_stages_ok_is_still_success(self):
        from core.models import SchedulerHeartbeat
        from core.services.scheduler_health import record_run

        with record_run(interval_minutes=60) as run:
            run.stage('capture_signal_evidence', True)

        hb = SchedulerHeartbeat.objects.get(key='scheduler')
        self.assertEqual(hb.status, SchedulerHeartbeat.STATUS_SUCCESS)
        self.assertEqual(hb.health(), SchedulerHeartbeat.HEALTH_HEALTHY)
        self.assertIsNotNone(hb.last_success_at)


class StatisticalUnitTests(TestCase):
    """The resampling unit is the fixture, never the outcome or market row."""

    def test_resampling_draws_whole_fixtures(self):
        from core.management.commands.audit_shadow_variants import (
            fixture_clustered_resample,
        )
        units = {
            101: ['101:1x2', '101:btts', '101:ou'],
            102: ['102:1x2', '102:btts', '102:ou'],
        }
        drawn = fixture_clustered_resample(units, rng_seed=7)

        # Every draw contributes a fixture's markets together — they share one
        # scoreline and are not independent.
        self.assertEqual(len(drawn) % 3, 0)
        for fixture_id in (101, 102):
            present = [d for d in drawn if d.startswith(f'{fixture_id}:')]
            self.assertIn(len(present), (0, 3, 6))

    def test_empty_input_is_safe(self):
        from core.management.commands.audit_shadow_variants import (
            fixture_clustered_resample,
        )
        self.assertEqual(fixture_clustered_resample({}), [])

    def test_markets_from_one_fixture_are_not_independent_units(self):
        from core.services import market_outcomes
        # 1X2 + BTTS + O/U from one fixture = 3 market decisions but ONE fixture.
        components = sum(
            market_outcomes.independent_component_count(m)
            for m in ('1x2', 'btts', 'over_under_2.5', 'double_chance')
        )
        self.assertEqual(components, 3)
        self.assertEqual(market_outcomes.independent_component_count('double_chance'), 0)
