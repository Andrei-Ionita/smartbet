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


class SettlementUsesImmutableClaimFieldsTests(TestCase):
    """RELEASE BLOCKER regression.

    Settlement previously read `PredictionLog.was_correct`, which is graded
    against the row's CURRENT market and selection. A pipeline re-run that
    changed either would have settled a published claim against a bet it never
    made. The BET must come from the frozen claim; only the SCORE and FIXTURE
    STATUS may come from the live row.
    """

    def test_claim_is_graded_on_its_own_market_and_outcome(self):
        # Published as BTTS Yes.
        pred, claim = published(985001, market='btts', outcome='Btts yes')

        # The pipeline re-runs and the live row becomes a DIFFERENT bet that
        # the same scoreline would grade the opposite way.
        pred.market_type = 'over_under_2.5'
        pred.predicted_outcome = 'Over 2.5'
        pred.save()

        # 1-1: BTTS Yes WINS, Over 2.5 LOSES.
        finish(pred, 1, 1)
        self.assertFalse(pred.was_correct, 'live row graded as Over 2.5 -> lost')

        run_settlement()
        claim.refresh_from_db()

        # The claim is settled on ITS bet (BTTS Yes), not the row's new one.
        self.assertEqual(claim.result_status, PublishedClaim.STATUS_WON)
        self.assertEqual(claim.market_type, 'btts')
        self.assertEqual(claim.predicted_outcome, 'Btts yes')
        self.assertTrue(claim.verify_integrity())

    def test_the_opposite_direction_too(self):
        # Published as Over 2.5; the row later becomes BTTS Yes.
        pred, claim = published(985002, market='over_under_2.5',
                                outcome='Over 2.5')
        pred.market_type = 'btts'
        pred.predicted_outcome = 'Btts yes'
        pred.save()

        # 1-1: Over 2.5 LOSES, BTTS Yes WINS.
        finish(pred, 1, 1)
        self.assertTrue(pred.was_correct, 'live row graded as BTTS Yes -> won')

        run_settlement()
        claim.refresh_from_db()
        self.assertEqual(claim.result_status, PublishedClaim.STATUS_LOST)
        self.assertTrue(claim.verify_integrity())

    def test_flipping_only_the_selection_is_also_ignored(self):
        pred, claim = published(985003, market='btts', outcome='Btts yes')
        pred.predicted_outcome = 'Btts no'
        pred.save()

        finish(pred, 2, 1)   # both scored -> claim's "Yes" wins
        run_settlement()
        claim.refresh_from_db()
        self.assertEqual(claim.result_status, PublishedClaim.STATUS_WON)

    def test_confidence_odds_and_bookmaker_cannot_affect_settlement(self):
        pred, claim = published(985004, market='btts', outcome='Btts yes',
                                odds=1.80)
        original_hash = claim.claim_hash

        pred.confidence = 0.99
        pred.odds = 25.0
        pred.bookmaker = 'Some Other Book'
        pred.odds_provenance = dict(provenance(25.0),
                                    odds_bookmaker_name='Some Other Book')
        pred.save()

        finish(pred, 2, 1)
        run_settlement()
        claim.refresh_from_db()

        # Settlement outcome unchanged...
        self.assertEqual(claim.result_status, PublishedClaim.STATUS_WON)
        # ...and the card still shows the ORIGINAL frozen price and score.
        self.assertEqual(claim.odds, 1.80)
        self.assertAlmostEqual(claim.confidence, 0.624, places=3)
        self.assertEqual(
            (claim.odds_provenance or {}).get('odds_bookmaker_name'), 'bet365')
        self.assertEqual(claim.claim_hash, original_hash)
        self.assertTrue(claim.verify_integrity())

    def test_public_pl_uses_the_frozen_price_not_the_mutated_one(self):
        from core.services.accuracy_calculator import AccuracyCalculator

        pred, claim = published(985005, market='btts', outcome='Btts yes',
                                odds=2.0)
        pred.odds = 50.0          # a wildly different live price
        pred.save()
        finish(pred, 2, 1)
        run_settlement()

        roi = AccuracyCalculator().get_roi_simulation(stake_per_bet=10.0)
        # 10 * (2.0 - 1) = 10.0, from the CLAIM price — not 490.0.
        self.assertEqual(roi['total_profit_loss'], 10.0)

    def test_the_public_card_reflects_the_frozen_bet(self):
        import json

        pred, claim = published(985006, market='btts', outcome='Btts yes')
        pred.market_type = 'over_under_2.5'
        pred.predicted_outcome = 'Over 2.5'
        pred.save()
        finish(pred, 1, 1)
        run_settlement()

        body = json.loads(
            self.client.get(f'/api/proof/claim/{claim.claim_id}/').content)
        self.assertEqual(body['pick']['market_type'], 'btts')
        self.assertEqual(body['pick']['predicted_outcome'], 'Btts yes')
        self.assertEqual(body['result']['status'], 'WON')
        self.assertTrue(body['integrity_ok'])

    def test_evaluator_is_pure_and_takes_no_model(self):
        """The shared evaluator cannot accidentally read a mutable row."""
        import inspect

        from core.services import market_evaluation

        sig = inspect.signature(market_evaluation.evaluate_prediction)
        self.assertEqual(
            list(sig.parameters),
            ['market_type', 'predicted_outcome', 'home_score', 'away_score',
             'fixture_status', 'actual_outcome'],
        )
        # Check executable code, not the docstrings (which legitimately name
        # the callers they exist to serve).
        import ast

        tree = ast.parse(inspect.getsource(market_evaluation))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                self.fail('the evaluator must import nothing')
            if isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, ('objects', 'save', 'refresh_from_db'),
                                 'evaluator touches persistence')
