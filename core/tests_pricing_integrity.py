"""
Tests for the public verified universe, pricing-integrity classification and
published-claim immutability.

Context: the 2026-07-29 audit found the public dashboard reading +10.61% ROI
while the defensible figure was -4.90%, because odds were captured from the
wrong SportMonks market and `accuracy_calculator` never excluded quarantined
rows. See docs/audit/gem-selector-diagnostics-2026-07-29.md.
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from core.models import PredictionLog, PublishedClaim
from core.services import public_universe
from core.services.accuracy_calculator import AccuracyCalculator
from core.tests import _verified_pricing, publish_claim


class PublicVerifiedUniverseTests(TestCase):
    """Every public surface must denominate on ONE universe."""

    def _row(self, fixture_id, *, status=None, recommended=True, correct=True,
             confidence=0.64, market='over_under_2.5', league='Test League',
             audit_excluded=False, provenance=True, kickoff_offset_days=1,
             publish=False):
        pred = PredictionLog.objects.create(
            fixture_id=fixture_id, home_team='A', away_team='B', league=league,
            kickoff=timezone.now() - timedelta(days=kickoff_offset_days),
            predicted_outcome='Over 2.5', market_type=market,
            confidence=confidence, odds=1.85,
            probability_home=confidence, probability_draw=(1 - confidence) / 2,
            probability_away=(1 - confidence) / 2,
            actual_outcome='Over 2.5', was_correct=correct,
            profit_loss_10=8.5 if correct else -10.0,
            is_recommended=recommended, is_audit_excluded=audit_excluded,
            odds_provenance=_verified_pricing() if provenance else None,
        )
        PredictionLog.objects.filter(pk=pred.pk).update(
            pricing_integrity_status=status or public_universe.classify_row(pred)
        )
        pred.refresh_from_db()
        if publish:
            publish_claim(pred, pricing_integrity_status=pred.pricing_integrity_status)
        return pred

    def test_all_public_surfaces_share_one_universe(self):
        # Two published claims that belong in public statistics...
        self._row(900001, status=PredictionLog.PRICING_VERIFIED, correct=True, publish=True)
        self._row(900002, status=PredictionLog.PRICING_VERIFIED, correct=False, publish=True)
        # ...and one of every kind that must not.
        self._row(900003, status=PredictionLog.PRICING_LEGACY_UNVERIFIED)
        self._row(900004, status=PredictionLog.PRICING_MISSING_PROVENANCE)
        self._row(900005, status=PredictionLog.PRICING_AUDIT_EXCLUDED,
                  audit_excluded=True)
        self._row(900006, status=PredictionLog.PRICING_VERIFIED, recommended=False)
        self._row(900007, status=PredictionLog.PRICING_VERIFIED, confidence=0.40)

        self.assertEqual(len(public_universe.resolved_claims()), 2)

        calc = AccuracyCalculator()
        self.assertEqual(
            calc.get_overall_accuracy()['overall']['total_predictions'], 2)
        self.assertEqual(calc.get_roi_simulation()['total_bets'], 2)
        self.assertEqual(
            sum(l['total_predictions'] for l in calc.get_accuracy_by_league()), 2)

    def test_legacy_unverified_rows_never_reach_public_roi(self):
        # A large fake winner of exactly the kind the odds defect produced.
        row = self._row(900010, status=PredictionLog.PRICING_LEGACY_UNVERIFIED,
                        publish=True)
        PredictionLog.objects.filter(pk=row.pk).update(profit_loss_10=250.0)

        roi = AccuracyCalculator().get_roi_simulation()
        self.assertEqual(roi['total_bets'], 0)
        self.assertEqual(roi['roi_percent'], 0)

    def test_quarantined_rows_excluded_even_if_marked_verified(self):
        """is_audit_excluded is an independent veto, not merely a status."""
        self._row(900020, status=PredictionLog.PRICING_VERIFIED, audit_excluded=True,
                  publish=True)
        self.assertEqual(public_universe.priced_qs().count(), 0)
        self.assertEqual(len(public_universe.resolved_claims()), 0)

    def test_league_breakdown_returns_one_row_per_league(self):
        """Regression for audit finding F8.

        `PredictionLog.Meta.ordering = ['-kickoff']` leaked `kickoff` into the
        DISTINCT clause, so production returned 241 rows for 25 leagues.
        """
        for i in range(6):
            self._row(900100 + i, status=PredictionLog.PRICING_VERIFIED,
                      league='Eredivisie', kickoff_offset_days=i + 1, publish=True)
        for i in range(3):
            self._row(900200 + i, status=PredictionLog.PRICING_VERIFIED,
                      league='Superliga', kickoff_offset_days=i + 1, publish=True)

        leagues = AccuracyCalculator().get_accuracy_by_league()
        names = [l['league'] for l in leagues]
        self.assertEqual(len(names), len(set(names)), 'duplicate league rows: %s' % names)
        self.assertEqual(sorted(names), ['Eredivisie', 'Superliga'])
        by_name = {l['league']: l for l in leagues}
        self.assertEqual(by_name['Eredivisie']['total_predictions'], 6)
        self.assertEqual(by_name['Superliga']['total_predictions'], 3)


class PricingIntegrityClassificationTests(TestCase):
    """`status_for` is the only place integrity is decided."""

    def setUp(self):
        self.cutoff = public_universe.PRICING_INTEGRITY_CUTOFF

    def test_quarantine_wins_over_everything(self):
        self.assertEqual(
            public_universe.status_for(
                _verified_pricing(), self.cutoff + timedelta(days=1), True, 1.85),
            PredictionLog.PRICING_AUDIT_EXCLUDED,
        )

    def test_before_cutoff_is_legacy_regardless_of_provenance(self):
        self.assertEqual(
            public_universe.status_for(
                _verified_pricing(), self.cutoff - timedelta(seconds=1), False, 1.85),
            PredictionLog.PRICING_LEGACY_UNVERIFIED,
        )

    def test_after_cutoff_with_good_provenance_is_verified(self):
        self.assertEqual(
            public_universe.status_for(
                _verified_pricing(), self.cutoff + timedelta(days=1), False, 1.85),
            PredictionLog.PRICING_VERIFIED,
        )

    def test_missing_or_unrecognised_provenance_is_not_verified(self):
        after = self.cutoff + timedelta(days=1)
        stale_policy = dict(_verified_pricing(), odds_selection_policy='best_price_v0')
        no_market = dict(_verified_pricing(), odds_market_id=None)
        cases = [
            (None, 1.85), ({}, 1.85), (stale_policy, 1.85),
            (no_market, 1.85), (_verified_pricing(), None),
        ]
        for prov, odds in cases:
            self.assertEqual(
                public_universe.status_for(prov, after, False, odds),
                PredictionLog.PRICING_MISSING_PROVENANCE,
            )


class PublishedClaimImmutabilityTests(TestCase):
    """A published claim can never change after it goes public."""

    def _claim(self, fixture_id=910001):
        pred = PredictionLog.objects.create(
            fixture_id=fixture_id,
            home_team='Falkirk', away_team='St. Mirren', league='Premiership',
            kickoff=timezone.now() + timedelta(days=2),
            predicted_outcome='Over 2.5', market_type='over_under_2.5',
            confidence=0.5684, odds=1.78,
            probability_home=0.5, probability_draw=0.25, probability_away=0.25,
            is_recommended=True, odds_provenance=_verified_pricing(1.78),
            pricing_integrity_status=PredictionLog.PRICING_VERIFIED,
        )
        claim = PublishedClaim.objects.create(
            prediction=pred, fixture_id=pred.fixture_id,
            home_team=pred.home_team, away_team=pred.away_team,
            league=pred.league, kickoff=pred.kickoff,
            market_type=pred.market_type, predicted_outcome=pred.predicted_outcome,
            confidence=pred.confidence, odds=pred.odds,
            odds_provenance=pred.odds_provenance,
            prediction_generated_at=pred.prediction_logged_at,
        )
        return pred, claim

    def test_claim_is_hashed_on_insert_and_verifies(self):
        _, claim = self._claim()
        self.assertEqual(len(claim.claim_hash), 64)
        self.assertTrue(claim.verify_integrity())

    def test_updating_a_published_claim_raises(self):
        _, claim = self._claim()
        claim.odds = 3.50
        with self.assertRaises(ValueError):
            claim.save()

    def test_tampering_is_detectable(self):
        _, claim = self._claim()
        # Bypass save() the way a raw SQL edit would.
        PublishedClaim.objects.filter(pk=claim.claim_id).update(odds=3.50)
        claim.refresh_from_db()
        self.assertFalse(claim.verify_integrity())

    def test_live_prediction_can_change_without_altering_the_claim(self):
        """The whole point: the engine keeps improving, the claim does not."""
        pred, claim = self._claim()
        pred.odds = 2.40
        pred.predicted_outcome = 'Under 2.5'
        pred.save()

        claim.refresh_from_db()
        self.assertEqual(claim.odds, 1.78)
        self.assertEqual(claim.predicted_outcome, 'Over 2.5')
        self.assertTrue(claim.verify_integrity())

    def test_result_status_tracks_settlement_without_rewriting_the_claim(self):
        pred, claim = self._claim()
        self.assertEqual(claim.result_status, PublishedClaim.STATUS_PENDING)

        pred.was_correct = True
        pred.save()
        self.assertEqual(claim.result_status, PublishedClaim.STATUS_WON)

        pred.was_correct = False
        pred.save()
        self.assertEqual(claim.result_status, PublishedClaim.STATUS_LOST)

        pred.match_status = 'CANC'
        pred.save()
        self.assertEqual(claim.result_status, PublishedClaim.STATUS_CANCELLED)

        pred.match_status = 'POSTP'
        pred.save()
        self.assertEqual(claim.result_status, PublishedClaim.STATUS_VOID)

        self.assertTrue(claim.verify_integrity())
