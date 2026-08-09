"""
Public performance denominates on ONE universe: resolved, integrity-valid,
provenance-complete, non-superseded, non-quarantined PublishedClaims.

Legacy PredictionLog rows were mutable across pipeline re-runs. Grading was
always correct, but a stored predicted_outcome cannot be proven identical to
the one generated at its timestamp — so legacy data may inform internal
diagnostics and must never appear in public performance.
"""
import json
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from core.models import PredictionLog, PublishedClaim
from core.services import public_universe
from core.services.accuracy_calculator import AccuracyCalculator
from core.tests import _verified_pricing, publish_claim, settle_claim


def _pred(fixture_id, *, correct=True, resolved=True, odds=2.0,
          confidence=0.64, league='Test League', market='over_under_2.5',
          status=PredictionLog.PRICING_VERIFIED, audit_excluded=False,
          recommended=True):
    pred = PredictionLog.objects.create(
        fixture_id=fixture_id, home_team='A', away_team='B', league=league,
        kickoff=timezone.now() - timedelta(days=1),
        predicted_outcome='Over 2.5', market_type=market,
        confidence=confidence, odds=odds,
        probability_home=confidence, probability_draw=(1 - confidence) / 2,
        probability_away=(1 - confidence) / 2,
        actual_outcome='Over 2.5' if resolved else None,
        was_correct=correct if resolved else None,
        profit_loss_10=(10.0 if correct else -10.0) if resolved else None,
        is_recommended=recommended, is_audit_excluded=audit_excluded,
        odds_provenance=_verified_pricing(odds),
    )
    PredictionLog.objects.filter(pk=pred.pk).update(pricing_integrity_status=status)
    pred.refresh_from_db()
    return pred


class LegacyNeverEntersPublicPerformanceTests(TestCase):

    def test_legacy_does_not_contribute_to_public_accuracy(self):
        # Ten legacy winners — the flattering kind the odds defect produced.
        for i in range(10):
            publish_claim(
                _pred(940000 + i, correct=True,
                      status=PredictionLog.PRICING_LEGACY_UNVERIFIED),
                pricing_integrity_status=PredictionLog.PRICING_LEGACY_UNVERIFIED,
            )
        overall = AccuracyCalculator().get_overall_accuracy()['overall']
        self.assertEqual(overall['total_predictions'], 0)
        self.assertFalse(overall['has_verified_results'])

    def test_legacy_does_not_contribute_to_public_roi(self):
        for i in range(10):
            publish_claim(
                _pred(941000 + i, correct=True, odds=5.0,
                      status=PredictionLog.PRICING_LEGACY_UNVERIFIED),
                pricing_integrity_status=PredictionLog.PRICING_LEGACY_UNVERIFIED,
            )
        roi = AccuracyCalculator().get_roi_simulation()
        self.assertEqual(roi['total_bets'], 0)
        self.assertFalse(roi['has_verified_results'])

    def test_unpublished_prediction_never_counts(self):
        """A verified PredictionLog with no claim is not public performance."""
        _pred(942001, correct=True)
        self.assertEqual(len(public_universe.resolved_claims()), 0)
        self.assertEqual(
            AccuracyCalculator().get_overall_accuracy()['overall']['total_predictions'], 0)

    def test_unresolved_claim_does_not_enter_resolved_performance(self):
        publish_claim(_pred(943001, resolved=False))
        self.assertEqual(len(public_universe.resolved_claims()), 0)
        self.assertEqual(AccuracyCalculator().get_roi_simulation()['total_bets'], 0)

    def test_quarantined_claim_excluded(self):
        publish_claim(_pred(944001, correct=True, audit_excluded=True))
        self.assertEqual(len(public_universe.resolved_claims()), 0)

    def test_only_resolved_verified_claims_contribute(self):
        publish_claim(_pred(945001, correct=True))                       # counts
        publish_claim(_pred(945002, correct=False))                      # counts
        publish_claim(_pred(945003, resolved=False))                     # pending
        publish_claim(_pred(945004, correct=True, audit_excluded=True))  # quarantined
        publish_claim(                                                   # legacy
            _pred(945005, correct=True,
                  status=PredictionLog.PRICING_LEGACY_UNVERIFIED),
            pricing_integrity_status=PredictionLog.PRICING_LEGACY_UNVERIFIED)
        _pred(945006, correct=True)                                      # unpublished

        self.assertEqual(len(public_universe.resolved_claims()), 2)
        self.assertEqual(AccuracyCalculator().get_roi_simulation()['total_bets'], 2)

    def test_stale_price_claim_remains_public_but_not_in_performance(self):
        now = timezone.now()
        claim = publish_claim(
            _pred(945007, correct=True),
            odds_captured_at=now - timedelta(hours=13),
            published_at=now,
        )

        self.assertTrue(PublishedClaim.objects.filter(pk=claim.pk).exists())
        self.assertEqual(len(public_universe.resolved_claims()), 0)
        self.assertEqual(AccuracyCalculator().get_roi_simulation()['total_bets'], 0)


class TamperedClaimsAreExcludedTests(TestCase):

    def test_tampered_claim_is_excluded_from_public_performance(self):
        pred = _pred(946001, correct=True)
        claim = publish_claim(pred)
        self.assertEqual(len(public_universe.resolved_claims()), 1)

        # Simulate a raw database edit that bypasses save().
        PublishedClaim.objects.filter(pk=claim.claim_id).update(odds=99.0)
        claim.refresh_from_db()
        self.assertFalse(claim.verify_integrity())
        self.assertEqual(len(public_universe.resolved_claims()), 0)
        self.assertEqual(AccuracyCalculator().get_roi_simulation()['total_bets'], 0)

    def test_claim_with_incomplete_provenance_is_excluded(self):
        pred = _pred(946002, correct=True)
        broken = dict(_verified_pricing(2.0))
        broken['odds_bookmaker_name'] = None
        publish_claim(pred, odds_provenance=broken)
        self.assertEqual(len(public_universe.resolved_claims()), 0)


class CorrectionsAreRecordedSeparatelyTests(TestCase):
    """The architecture must actually enforce the public wording."""

    def test_correction_creates_a_new_claim_and_preserves_the_original(self):
        pred = _pred(947001, correct=True, odds=2.0)
        original = publish_claim(pred)
        original_hash = original.claim_hash

        corrected = original.correct('bookmaker restated the price', odds=1.95)

        original.refresh_from_db()
        self.assertEqual(original.odds, 2.0)               # untouched
        self.assertEqual(original.claim_hash, original_hash)
        self.assertTrue(original.verify_integrity())
        self.assertEqual(corrected.supersedes_id, original.claim_id)
        self.assertEqual(corrected.correction_reason, 'bookmaker restated the price')

    def test_only_the_current_claim_counts_after_a_correction(self):
        pred = _pred(947002, correct=True, odds=2.0)
        original = publish_claim(pred)
        corrected = original.correct('price restated', odds=1.5)
        # Settlement is per-claim: a superseding claim is settled in its own
        # right, so a correction can never inherit a stale result row.
        settle_claim(corrected)

        claims = public_universe.resolved_claims()
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].odds, 1.5)

    def test_a_published_claim_can_never_be_updated_in_place(self):
        claim = publish_claim(_pred(947003, correct=True))
        claim.odds = 9.99
        with self.assertRaises(ValueError):
            claim.save()


class ZeroSampleNeverRendersAsPerformanceTests(TestCase):

    def test_zero_verified_results_flagged_not_zero_percent(self):
        roi = AccuracyCalculator().get_roi_simulation()
        overall = AccuracyCalculator().get_overall_accuracy()['overall']

        self.assertFalse(roi['has_verified_results'])
        self.assertFalse(overall['has_verified_results'])
        self.assertEqual(roi['total_bets'], 0)

    def test_monitoring_reports_null_not_zero_at_empty_sample(self):
        # Legacy rows exist, but public performance must still be empty.
        publish_claim(
            _pred(948001, correct=True,
                  status=PredictionLog.PRICING_LEGACY_UNVERIFIED),
            pricing_integrity_status=PredictionLog.PRICING_LEGACY_UNVERIFIED)

        body = json.loads(self.client.get('/api/recommended-predictions/').content)
        public = body['summary']['verified_public']

        self.assertFalse(public['has_verified_results'])
        self.assertIsNone(public['accuracy'])
        self.assertIsNone(public['roi_percent'])
        self.assertIsNone(public['total_profit_loss'])

    def test_monitoring_keeps_legacy_separate_and_labelled(self):
        publish_claim(
            _pred(948002, correct=True,
                  status=PredictionLog.PRICING_LEGACY_UNVERIFIED),
            pricing_integrity_status=PredictionLog.PRICING_LEGACY_UNVERIFIED)

        summary = json.loads(
            self.client.get('/api/recommended-predictions/').content)['summary']

        self.assertIn('legacy_diagnostics', summary)
        self.assertIn('legacy', summary['legacy_diagnostics']['label'].lower())
        # Legacy figures must not appear inside the public block.
        self.assertNotIn('legacy', json.dumps(summary['verified_public']).lower())


class AllPublicSurfacesShareOneUniverseTests(TestCase):

    def test_dashboard_accuracy_roi_and_leagues_agree(self):
        publish_claim(_pred(949001, correct=True, league='Eredivisie'))
        publish_claim(_pred(949002, correct=False, league='Eredivisie'))
        publish_claim(_pred(949003, correct=True, league='Superliga'))
        # Noise that must not appear anywhere public.
        _pred(949004, correct=True)
        publish_claim(
            _pred(949005, correct=True,
                  status=PredictionLog.PRICING_LEGACY_UNVERIFIED),
            pricing_integrity_status=PredictionLog.PRICING_LEGACY_UNVERIFIED)

        calc = AccuracyCalculator()
        expected = len(public_universe.resolved_claims())
        self.assertEqual(expected, 3)

        self.assertEqual(
            calc.get_overall_accuracy()['overall']['total_predictions'], expected)
        self.assertEqual(calc.get_roi_simulation()['total_bets'], expected)
        self.assertEqual(
            sum(l['total_predictions'] for l in calc.get_accuracy_by_league()), expected)
        self.assertEqual(
            sum(b['total'] for b in calc.get_accuracy_by_confidence()), expected)

        body = json.loads(self.client.get('/api/recommended-predictions/').content)
        self.assertEqual(body['summary']['verified_public']['total'], expected)

    def test_public_roi_uses_the_published_price_not_the_mutable_row(self):
        pred = _pred(949010, correct=True, odds=2.0)
        publish_claim(pred)

        # The pipeline later rewrites the live row's price.
        pred.odds = 10.0
        pred.profit_loss_10 = 900.0
        pred.save()

        roi = AccuracyCalculator().get_roi_simulation(stake_per_bet=10.0)
        # 10 * (2.0 - 1) = 10.0 profit, from the CLAIM price.
        self.assertEqual(roi['total_profit_loss'], 10.0)
        self.assertEqual(roi['roi_percent'], 100.0)
