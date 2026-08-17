"""Contracts for the private, forward-only Strategies Lab."""
import uuid
from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from core.models import (
    FixtureResultObservation,
    SignalObservation,
    StrategyLabObservation,
    StrategyLabSettlement,
)
from core.services import strategy_lab


def candidate(*, fixture_id=7001, hours=6, odds=1.9, handicap=-.25,
              lower=.05, bookmakers=3, model_mass=.98):
    now = timezone.now()
    kickoff = now + timedelta(hours=hours)
    return {
        'strategy_key': 'asian-handicap-score-distribution',
        'strategy_version': 'v2',
        'strategy_status': 'shadow',
        'fixture_id': fixture_id,
        'home_team': 'Home',
        'away_team': 'Away',
        'league': 'Test League',
        'league_id': 9,
        'kickoff': kickoff.isoformat(),
        'observed_at': now.isoformat(),
        'market': 'asian_handicap',
        'market_id': 6,
        'side': 'home',
        'handicap': handicap,
        'label': f'Home {handicap:+g}',
        'odds': odds,
        'bookmaker': 'Test Book',
        'bookmaker_count': bookmakers,
        'price_min': odds - .05,
        'price_max': odds + .05,
        'captured_at': now.isoformat(),
        'price_provenance': {'market_id': 6, 'selection_policy': 'test'},
        'model_mass': model_mass,
        'expected_return_lower': lower,
        'expected_return_upper': lower + .03,
        'robust_positive_edge': lower > .02,
        'calculation_version': 'test-commit',
    }


def result(fixture_id, home, away, *, version=1, supersedes=None):
    return FixtureResultObservation.objects.create(
        result_id=uuid.uuid4(), fixture_id=fixture_id,
        home_team='Home', away_team='Away', league='Test League', league_id=9,
        kickoff=timezone.now() - timedelta(hours=2), provider_status='FT',
        home_score=home, away_score=away, score_type='CURRENT',
        is_final=True, is_scoreable=True, confirmed=True,
        result_version=version, supersedes=supersedes,
        captured_at=timezone.now(), ingestion_run_id=f'result-{fixture_id}-{version}',
        source_payload_hash=str(uuid.uuid4()),
    )


def signal(*, fixture_id=7301, market='1x2', outcome='home', probability=.6,
           odds=2.0, hours=6, vector=None, vector_sum=1.0):
    now = timezone.now()
    vector = vector or {'home': .6, 'draw': .2, 'away': .2}
    return SignalObservation.objects.create(
        observation_id=uuid.uuid4(), ingestion_run_id=f'signal-{fixture_id}-{outcome}',
        source_payload_hash=str(uuid.uuid4()), fixture_id=fixture_id,
        home_team='Home', away_team='Away', league='Test League', league_id=9,
        kickoff=now + timedelta(hours=hours), observed_at=now,
        hours_to_kickoff=hours, market=market, outcome=outcome,
        raw_probability=probability * 100, normalized_probability=probability,
        raw_vector=vector, vector_sum=vector_sum, vector_complete=True,
        price_status='verified', odds=odds, bookmaker='Test Book',
        odds_captured_at=now,
        odds_provenance={
            'odds_market_id': 1, 'odds_bookmaker_count': 3,
            'odds_min': odds - .05, 'odds_max': odds + .05,
        },
        provenance_complete=True,
        market_price_vector={name: {'odds': 2} for name in vector},
        price_vector_complete=True,
    )


class StrategyLabCaptureTests(TestCase):
    def test_capture_is_append_only_and_idempotent(self):
        payload = {'strategy_candidates': [candidate()]}
        first = strategy_lab.capture(payload, 'run-1')
        second = strategy_lab.capture(payload, 'run-2')

        self.assertEqual(first['strategy_written'], 1)
        self.assertEqual(second['strategy_skipped_duplicate'], 1)
        self.assertEqual(StrategyLabObservation.objects.count(), 1)

        row = StrategyLabObservation.objects.get()
        row.odds = 4
        with self.assertRaises(ValueError):
            row.save()

    def test_fixed_horizon_chooses_closest_eligible_observation(self):
        base = timezone.now()
        kickoff = base + timedelta(hours=10)
        payload = {'strategy_candidates': []}
        for hours, odds in ((8, 1.8), (2, 1.9), (.5, 2.1)):
            row = candidate(hours=10, odds=odds)
            row['kickoff'] = kickoff.isoformat()
            row['observed_at'] = (kickoff - timedelta(hours=hours)).isoformat()
            row['captured_at'] = row['observed_at']
            payload['strategy_candidates'].append(row)
        strategy_lab.capture(payload, 'run-horizon')

        decisions = strategy_lab.choose_decisions()
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].odds, 1.9)
        self.assertAlmostEqual(decisions[0].hours_to_kickoff, 2)

    def test_versioned_rules_gate_candidates_without_retroactive_selection(self):
        payload = {'strategy_candidates': [
            candidate(fixture_id=7101, lower=.04, bookmakers=2),
            candidate(fixture_id=7102, lower=.01, bookmakers=5),
            candidate(fixture_id=7103, lower=.08, bookmakers=1),
        ]}
        strategy_lab.capture(payload, 'run-rules')
        decisions = strategy_lab.choose_decisions()

        self.assertEqual({row.fixture_id for row in decisions}, {7101})

    def test_stale_price_cannot_become_a_decision(self):
        row = candidate(fixture_id=7104)
        row['captured_at'] = (
            timezone.now() - timedelta(hours=25)
        ).isoformat()
        strategy_lab.capture({'strategy_candidates': [row]}, 'run-stale-price')

        self.assertEqual(strategy_lab.choose_decisions(), [])

    def test_multiple_qualified_lines_become_one_fixture_decision(self):
        payload = {'strategy_candidates': [
            candidate(fixture_id=7150, handicap=-.25, lower=.04),
            candidate(fixture_id=7150, handicap=-.5, lower=.08),
            candidate(fixture_id=7150, handicap=-.75, lower=.06),
        ]}
        strategy_lab.capture(payload, 'run-one-fixture')

        decisions = strategy_lab.choose_decisions()
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].handicap, -.5)

    def test_goal_line_and_team_total_candidates_enter_distinct_experiments(self):
        goal_line = candidate(fixture_id=7160, handicap=2.25)
        goal_line.update({
            'strategy_key': 'asian-goal-line-score-distribution',
            'market': 'asian_goal_line', 'market_id': 7,
            'side': 'over', 'label': 'Over 2.25',
        })
        team_total = candidate(fixture_id=7161, handicap=1.5)
        team_total.update({
            'strategy_key': 'team-total-score-distribution',
            'market': 'team_total_goals', 'market_id': 86,
            'side': 'home_over', 'label': 'Home Over 1.5',
        })

        summary = strategy_lab.capture(
            {'strategy_candidates': [goal_line, team_total]}, 'run-specialists',
        )

        self.assertEqual(summary['strategy_written'], 2)
        self.assertEqual(
            set(StrategyLabObservation.objects.values_list('market', flat=True)),
            {'asian_goal_line', 'team_total_goals'},
        )


class AsianHandicapSettlementTests(TestCase):
    def test_quarter_lines_split_stake_into_half_win_and_half_loss(self):
        self.assertAlmostEqual(
            strategy_lab.unit_profit('home', -.25, 2.0, 1, 1), -.5,
        )
        self.assertAlmostEqual(
            strategy_lab.unit_profit('home', +.25, 2.0, 1, 1), .5,
        )
        self.assertAlmostEqual(
            strategy_lab.total_unit_profit('over', 2.25, 2.0, 2), -.5,
        )
        self.assertAlmostEqual(
            strategy_lab.total_unit_profit('under', 2.25, 2.0, 2), .5,
        )

    def test_only_qualified_fixed_horizon_decision_is_settled(self):
        now = timezone.now()
        payload = {'strategy_candidates': [candidate(fixture_id=7201, hours=6)]}
        # Make the fixture historical while preserving a six-hour observation horizon.
        payload['strategy_candidates'][0]['kickoff'] = (now - timedelta(hours=2)).isoformat()
        payload['strategy_candidates'][0]['observed_at'] = (now - timedelta(hours=8)).isoformat()
        payload['strategy_candidates'][0]['captured_at'] = (now - timedelta(hours=8)).isoformat()
        strategy_lab.capture(payload, 'run-settle')
        result(7201, 2, 0)

        summary = strategy_lab.settle()
        settlement = StrategyLabSettlement.objects.get()
        self.assertEqual(summary['written'], 1)
        self.assertEqual(settlement.outcome, StrategyLabSettlement.OUTCOME_FULL_WIN)
        self.assertAlmostEqual(settlement.unit_profit, .9)

    def test_result_correction_appends_a_new_settlement_version(self):
        now = timezone.now()
        row = candidate(fixture_id=7202)
        row['kickoff'] = (now - timedelta(hours=2)).isoformat()
        row['observed_at'] = (now - timedelta(hours=8)).isoformat()
        row['captured_at'] = row['observed_at']
        strategy_lab.capture({'strategy_candidates': [row]}, 'run-correction')
        first = result(7202, 2, 0)
        strategy_lab.settle()
        result(7202, 0, 1, version=2, supersedes=first)
        strategy_lab.settle()

        settlements = StrategyLabSettlement.objects.order_by('result_version')
        self.assertEqual(settlements.count(), 2)
        self.assertGreater(settlements[0].unit_profit, 0)
        self.assertLess(settlements[1].unit_profit, 0)


class DirectMarketLabTests(TestCase):
    def test_historical_signal_is_materialised_only_as_retrospective(self):
        row = signal()
        summary = strategy_lab.capture_signal_observations(
            [row], phase=StrategyLabObservation.PHASE_RETROSPECTIVE,
        )
        lab_row = StrategyLabObservation.objects.get(source_signal=row)

        self.assertEqual(summary['signal_strategy_written'], 1)
        self.assertEqual(lab_row.evidence_phase, 'retrospective')
        self.assertAlmostEqual(lab_row.expected_return_lower, .2)

    def test_direct_value_decision_settles_against_confirmed_score(self):
        row = signal(fixture_id=7302)
        # Preserve the six-hour observation horizon while making kickoff past.
        kickoff = timezone.now() - timedelta(hours=2)
        observed = kickoff - timedelta(hours=6)
        SignalObservation.objects.filter(pk=row.pk).update(
            kickoff=kickoff, observed_at=observed,
            odds_captured_at=observed, hours_to_kickoff=6,
        )
        row.refresh_from_db()
        strategy_lab.capture_signal_observations(
            [row], phase=StrategyLabObservation.PHASE_RETROSPECTIVE,
        )
        result(7302, 2, 0)

        summary = strategy_lab.settle()
        settlement = StrategyLabSettlement.objects.get(
            observation__source_signal=row,
        )
        self.assertEqual(summary['written'], 1)
        self.assertEqual(settlement.outcome, 'full_win')
        self.assertAlmostEqual(settlement.unit_profit, 1.0)

    def test_retrospective_profit_never_counts_as_forward_promotion_evidence(self):
        row = signal(fixture_id=7303)
        strategy_lab.capture_signal_observations(
            [row], phase=StrategyLabObservation.PHASE_RETROSPECTIVE,
        )
        report = next(
            item for item in strategy_lab.build_report()['experiments']
            if item['strategy_key'] == 'full-time-result-value'
        )
        self.assertEqual(report['retrospective_backtest']['observations'], 1)
        self.assertEqual(report['forward_validation']['observations'], 0)
        self.assertFalse(report['promotion_ready'])

    def test_phase_is_mandatory_and_validated(self):
        with self.assertRaises(ValueError):
            strategy_lab.capture_signal_observations([signal()], phase='maybe')

    def test_backfill_never_relabels_post_registration_signal_as_retrospective(self):
        experiment = strategy_lab.ensure_experiment(
            strategy_lab.DEFINITION_BY_MARKET['1x2'],
        )
        historical = signal(fixture_id=7310)
        forward = signal(fixture_id=7311)
        SignalObservation.objects.filter(pk=historical.pk).update(
            created_at=experiment.created_at - timedelta(hours=1),
        )

        call_command(
            'backtest_strategy_lab', '--no-settle', '--compact',
            stdout=StringIO(),
        )

        retrospective_sources = set(
            StrategyLabObservation.objects.filter(
                evidence_phase='retrospective',
            ).values_list('source_signal_id', flat=True)
        )
        self.assertEqual(retrospective_sources, {historical.observation_id})
        self.assertNotIn(forward.observation_id, retrospective_sources)


class StrategyLabVisibilityTests(TestCase):
    def test_public_report_is_narrow_read_only_and_anonymous(self):
        before = strategy_lab.StrategyLabExperiment.objects.count()
        response = self.client.get('/api/transparency/strategies/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(strategy_lab.StrategyLabExperiment.objects.count(), before)
        body = response.json()['data']
        self.assertEqual(len(body['strategies']), 12)
        self.assertEqual(body['strategies'][0]['evidence_status'], 'not_started')
        self.assertNotIn('rules_hash', body['strategies'][0])
        self.assertNotIn('retrospective_backtest', body['strategies'][0])
        self.assertFalse(body['policy']['automatic_publication'])

    def test_report_is_staff_only(self):
        self.assertIn(
            self.client.get('/api/internal/strategies-lab/').status_code,
            (401, 403),
        )
        staff = User.objects.create_user('staff', password='safe-test-password', is_staff=True)
        self.client.force_login(staff)
        response = self.client.get('/api/internal/strategies-lab/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['lab_version'], 'strategies-lab-v2')
        self.assertIn('blocked_or_queued', response.json())

    def test_small_sample_can_never_be_promotion_ready(self):
        strategy_lab.ensure_experiment()
        report = strategy_lab.build_report()['experiments'][0]
        self.assertFalse(report['promotion_gates']['minimum_forward_sample'])
        self.assertFalse(report['promotion_ready'])
