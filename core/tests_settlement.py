"""
End-to-end settlement: third-party score -> graded prediction -> immutable
PublishedClaimResult.

Grading itself lives in `PredictionLog.calculate_performance` (all four
markets). The settlement command owns NO grading logic — these tests exercise
the real path so a divergence between the two would fail here.
"""
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from core.models import (PredictionLog, PredictionSnapshot, PublishedClaim,
                         PublishedClaimResult)
from core.services import claim_publication, public_universe, snapshot_recording
from core.tests_claim_publication import provenance

MARKET_OUTCOME = {
    'btts': 'Btts yes',
    'over_under_2.5': 'Over 2.5',
    '1x2': 'Home',
    'double_chance': '1X',
}


def published(fixture_id, *, market='btts', outcome=None, odds=1.80):
    """A published claim over a fixture that has not yet kicked off."""
    outcome = outcome or MARKET_OUTCOME[market]
    pred = PredictionLog.objects.create(
        fixture_id=fixture_id, home_team='Cardiff City', away_team='Swindon Town',
        league='Carabao Cup', kickoff=timezone.now() + timedelta(hours=6),
        predicted_outcome=outcome, market_type=market,
        confidence=0.624, odds=odds,
        probability_home=0.5, probability_draw=0.25, probability_away=0.25,
        is_recommended=True, odds_provenance=provenance(odds),
    )
    snap, _ = snapshot_recording.record_snapshot(
        prediction_run_id=f'run-{fixture_id}', prediction=pred,
        fixture_id=pred.fixture_id, home_team=pred.home_team,
        away_team=pred.away_team, league=pred.league, league_id=None,
        kickoff=pred.kickoff, market_type=market, predicted_outcome=outcome,
        confidence=0.624, is_recommended=True, model_version='consensus_ensemble',
        odds=odds, odds_provenance=provenance(odds),
        prediction_generated_at=timezone.now(),
    )
    claim = claim_publication.publish_prediction_claim(snap.snapshot_id)
    return pred, claim


def finish(pred, home, away, status='FT'):
    """Third-party result arrives; grading runs exactly as in production."""
    pred.actual_score_home = home
    pred.actual_score_away = away
    pred.match_status = status
    pred.save()
    pred.calculate_performance()
    pred.refresh_from_db()
    return pred


def run_settlement(**kwargs):
    out = StringIO()
    call_command('settle_published_claims', stdout=out, **kwargs)
    return out.getvalue()


class MarketSettlementTests(TestCase):
    """Every supported market settles to the correct status."""

    def _case(self, fixture_id, market, outcome, score, expected):
        pred, claim = published(fixture_id, market=market, outcome=outcome)
        finish(pred, *score)
        run_settlement()
        claim.refresh_from_db()
        self.assertEqual(claim.result_status, expected,
                         f'{market}/{outcome} {score} -> expected {expected}')
        return claim

    def test_btts_yes_won(self):
        self._case(980001, 'btts', 'Btts yes', (2, 1), PublishedClaim.STATUS_WON)

    def test_btts_yes_lost(self):
        self._case(980002, 'btts', 'Btts yes', (3, 0), PublishedClaim.STATUS_LOST)

    def test_over_25_won(self):
        self._case(980003, 'over_under_2.5', 'Over 2.5', (2, 1),
                   PublishedClaim.STATUS_WON)

    def test_over_25_lost(self):
        self._case(980004, 'over_under_2.5', 'Over 2.5', (1, 1),
                   PublishedClaim.STATUS_LOST)

    def test_under_25_won(self):
        self._case(980005, 'over_under_2.5', 'Under 2.5', (1, 1),
                   PublishedClaim.STATUS_WON)

    def test_under_25_lost(self):
        self._case(980006, 'over_under_2.5', 'Under 2.5', (3, 1),
                   PublishedClaim.STATUS_LOST)

    def test_1x2_home_won_and_lost(self):
        self._case(980007, '1x2', 'Home', (2, 0), PublishedClaim.STATUS_WON)
        self._case(980008, '1x2', 'Home', (0, 2), PublishedClaim.STATUS_LOST)

    def test_double_chance_outcomes(self):
        # 1X wins on a home win and on a draw, loses on an away win.
        self._case(980010, 'double_chance', '1X', (2, 0), PublishedClaim.STATUS_WON)
        self._case(980011, 'double_chance', '1X', (1, 1), PublishedClaim.STATUS_WON)
        self._case(980012, 'double_chance', '1X', (0, 2), PublishedClaim.STATUS_LOST)


class VoidAndCancelledTests(TestCase):

    def test_postponed_fixture_is_void(self):
        pred, claim = published(981001)
        finish(pred, None, None, status='POSTP')
        run_settlement()
        claim.refresh_from_db()
        self.assertEqual(claim.result_status, PublishedClaim.STATUS_VOID)
        self.assertFalse(claim.is_resolved)

    def test_cancelled_fixture_is_cancelled(self):
        pred, claim = published(981002)
        finish(pred, None, None, status='CANC')
        run_settlement()
        claim.refresh_from_db()
        self.assertEqual(claim.result_status, PublishedClaim.STATUS_CANCELLED)

    def test_void_and_cancelled_never_reach_performance(self):
        pred_v, _ = published(981003)
        finish(pred_v, None, None, status='ABAN')
        pred_c, _ = published(981004)
        finish(pred_c, None, None, status='CANC')
        run_settlement()
        self.assertEqual(len(public_universe.resolved_claims()), 0)

    def test_cancelled_wins_over_a_stale_was_correct(self):
        """A cancelled fixture is cancelled even if a score was graded first."""
        pred, claim = published(981005)
        finish(pred, 2, 1)                      # graded as a win...
        finish(pred, 2, 1, status='CANC')       # ...then cancelled
        run_settlement()
        claim.refresh_from_db()
        self.assertEqual(claim.result_status, PublishedClaim.STATUS_CANCELLED)


class SchedulerBehaviourTests(TestCase):

    def test_missing_provider_result_leaves_the_claim_pending(self):
        pred, claim = published(982001)
        # No score, no match_status — the provider has not answered yet.
        out = run_settlement()
        claim.refresh_from_db()
        self.assertEqual(claim.result_status, PublishedClaim.STATUS_PENDING)
        self.assertIn('awaiting a provider result', out)
        self.assertEqual(PublishedClaimResult.objects.count(), 0)

    def test_duplicate_scheduler_execution_is_idempotent(self):
        pred, claim = published(982002)
        finish(pred, 2, 1)
        run_settlement()
        run_settlement()
        run_settlement()
        self.assertEqual(PublishedClaimResult.objects.count(), 1)
        claim.refresh_from_db()
        self.assertEqual(claim.result_status, PublishedClaim.STATUS_WON)

    def test_contradictory_provider_data_is_refused_not_applied(self):
        pred, claim = published(982003)
        finish(pred, 2, 1)                 # BTTS yes -> WON
        run_settlement()

        # The provider now reports a contradictory scoreline.
        finish(pred, 3, 0)                 # would grade LOST
        out = run_settlement()

        claim.refresh_from_db()
        self.assertEqual(claim.result_status, PublishedClaim.STATUS_WON)
        self.assertIn('REFUSED', out)
        self.assertEqual(PublishedClaimResult.objects.count(), 1)

    def test_dry_run_writes_nothing(self):
        pred, claim = published(982004)
        finish(pred, 2, 1)
        out = run_settlement(dry_run=True)
        self.assertIn('would settle', out)
        self.assertEqual(PublishedClaimResult.objects.count(), 0)

    def test_claim_integrity_survives_settlement(self):
        pred, claim = published(982005)
        before = claim.claim_hash
        finish(pred, 2, 1)
        run_settlement()
        claim.refresh_from_db()
        self.assertEqual(claim.claim_hash, before)
        self.assertTrue(claim.verify_integrity())

    def test_settled_claim_enters_public_performance(self):
        from core.services.accuracy_calculator import AccuracyCalculator

        pred, claim = published(982006, odds=2.0)
        finish(pred, 2, 1)
        run_settlement()

        self.assertEqual(len(public_universe.resolved_claims()), 1)
        roi = AccuracyCalculator().get_roi_simulation(stake_per_bet=10.0)
        self.assertEqual(roi['total_bets'], 1)
        self.assertEqual(roi['wins'], 1)
        self.assertEqual(roi['total_profit_loss'], 10.0)

    def test_settlement_records_source_and_timestamp(self):
        pred, claim = published(982007)
        finish(pred, 2, 1)
        run_settlement()
        result = PublishedClaimResult.objects.get(claim=claim)
        self.assertEqual(result.result_source, 'sportmonks')
        self.assertIn(str(pred.fixture_id), result.result_reference)
        self.assertIsNotNone(result.settled_at)
        self.assertEqual(result.actual_score_home, 2)
        self.assertEqual(result.actual_score_away, 1)

    def test_no_duplicated_grading_logic_in_the_command(self):
        """The command must delegate; grading lives on the model."""
        import inspect

        from core.management.commands import settle_published_claims as cmd

        source = inspect.getsource(cmd)
        for grading_token in ('total_goals', 'was_correct =', 'both_scored',
                              "== 'over'", 'actual_1x2'):
            self.assertNotIn(grading_token, source,
                             f'grading logic {grading_token!r} duplicated in the command')
