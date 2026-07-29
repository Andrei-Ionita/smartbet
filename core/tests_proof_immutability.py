"""
The public proof URL may only ever serve an immutable published claim.

A mutable `PredictionLog` row must never be presented as public proof: the
pipeline overwrites odds, confidence and the selection on every re-run, while
`prediction_logged_at` never moves, so serving it publicly would present a
changeable value under "logged before kickoff" language.
"""
import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import PredictionLog, PublishedClaim
from core.services import public_universe
from core.tests import _verified_pricing

User = get_user_model()


class PublicProofNeverServesMutableDataTests(TestCase):

    def _prediction(self, fixture_id=920001, odds=1.78):
        return PredictionLog.objects.create(
            fixture_id=fixture_id, home_team='Falkirk', away_team='St. Mirren',
            league='Premiership', kickoff=timezone.now() + timedelta(days=2),
            predicted_outcome='Over 2.5', market_type='over_under_2.5',
            confidence=0.5684, odds=odds,
            probability_home=0.5, probability_draw=0.25, probability_away=0.25,
            is_recommended=True, odds_provenance=_verified_pricing(odds),
            pricing_integrity_status=PredictionLog.PRICING_VERIFIED,
        )

    def _publish(self, pred):
        return PublishedClaim.objects.create(
            prediction=pred, fixture_id=pred.fixture_id,
            home_team=pred.home_team, away_team=pred.away_team,
            league=pred.league, kickoff=pred.kickoff,
            market_type=pred.market_type, predicted_outcome=pred.predicted_outcome,
            confidence=pred.confidence, odds=pred.odds,
            odds_provenance=pred.odds_provenance,
            prediction_generated_at=pred.prediction_logged_at,
        )

    def _get(self, fixture_id):
        resp = self.client.get(f'/api/proof/{fixture_id}/')
        return resp, json.loads(resp.content)

    def test_fixture_without_a_claim_shows_the_unpublished_state(self):
        self._prediction(920010)
        resp, body = self._get(920010)

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(body['published'])
        self.assertEqual(body['state'], 'unpublished')
        self.assertIn('has not been published', body['message'])

    def test_unpublished_response_leaks_no_mutable_claim_fields(self):
        self._prediction(920011, odds=3.50)
        _, body = self._get(920011)

        self.assertNotIn('pick', body)
        blob = json.dumps(body)
        for leaked in ('3.5', 'Over 2.5', 'Falkirk', '0.5684'):
            self.assertNotIn(leaked, blob,
                             f'unpublished proof leaked mutable value {leaked!r}')

    def test_published_claim_is_served_and_flagged_immutable(self):
        pred = self._prediction(920012)
        claim = self._publish(pred)
        _, body = self._get(920012)

        self.assertTrue(body['published'])
        self.assertEqual(body['state'], 'published')
        self.assertEqual(body['claim_id'], str(claim.claim_id))
        self.assertEqual(body['claim_hash'], claim.claim_hash)
        self.assertEqual(body['pick']['odds'], 1.78)

    def test_changing_the_prediction_cannot_change_published_proof(self):
        pred = self._prediction(920013)
        self._publish(pred)

        # The pipeline re-runs and rewrites every claim field.
        pred.odds = 3.50
        pred.confidence = 0.90
        pred.predicted_outcome = 'Under 2.5'
        pred.market_type = '1x2'
        pred.save()

        _, body = self._get(920013)
        self.assertEqual(body['pick']['odds'], 1.78)
        self.assertEqual(body['pick']['predicted_outcome'], 'Over 2.5')
        self.assertEqual(body['pick']['market_type'], 'over_under_2.5')
        self.assertAlmostEqual(body['pick']['confidence'], 56.8, places=1)

    def test_settlement_updates_result_without_touching_the_claim(self):
        pred = self._prediction(920014)
        self._publish(pred)

        pred.was_correct = True
        pred.actual_score_home, pred.actual_score_away = 2, 1
        pred.save()

        _, body = self._get(920014)
        self.assertEqual(body['result']['status'], 'WON')
        self.assertTrue(body['result']['was_correct'])
        self.assertEqual(body['pick']['odds'], 1.78)  # unchanged

    def test_unknown_fixture_is_unpublished_not_a_leak(self):
        _, body = self._get(999999)
        self.assertFalse(body['published'])
        self.assertNotIn('pick', body)


class StaffPreviewIsSeparateAndProtectedTests(TestCase):

    def setUp(self):
        self.pred = PredictionLog.objects.create(
            fixture_id=930001, home_team='Aberdeen', away_team='Hearts',
            league='Premiership', kickoff=timezone.now() + timedelta(days=2),
            predicted_outcome='Over 2.5', market_type='over_under_2.5',
            confidence=0.5679, odds=1.67,
            probability_home=0.5, probability_draw=0.25, probability_away=0.25,
            is_recommended=True, odds_provenance=_verified_pricing(1.67),
            pricing_integrity_status=PredictionLog.PRICING_VERIFIED,
        )
        self.url = f'/api/proof/{self.pred.fixture_id}/preview/'

    def test_preview_is_a_different_path_from_public_proof(self):
        self.assertNotEqual(self.url, f'/api/proof/{self.pred.fixture_id}/')

    def test_anonymous_cannot_preview(self):
        self.assertIn(APIClient().get(self.url).status_code, (401, 403))

    def test_non_staff_cannot_preview(self):
        bob = User.objects.create_user('bob', 'bob@example.com', 'pw12345!')
        api = APIClient()
        api.force_authenticate(user=bob)
        self.assertIn(api.get(self.url).status_code, (401, 403))

    def test_staff_preview_returns_live_values_clearly_labelled(self):
        root = User.objects.create_superuser('root', 'root@example.com', 'pw12345!')
        api = APIClient()
        api.force_authenticate(user=root)

        body = json.loads(api.get(self.url).content)
        self.assertEqual(body['state'], 'staff_preview')
        self.assertFalse(body['published'])
        self.assertIn('MUTABLE PREVIEW', body['warning'])
        self.assertEqual(body['pick']['odds'], 1.67)

    def test_public_proof_of_the_same_fixture_stays_unpublished(self):
        body = json.loads(self.client.get(f'/api/proof/{self.pred.fixture_id}/').content)
        self.assertFalse(body['published'])
        self.assertNotIn('pick', body)


class ProvenanceCompletenessTests(TestCase):
    """A record cannot be verified without complete, auditable provenance."""

    def setUp(self):
        self.after = public_universe.PRICING_INTEGRITY_CUTOFF + timedelta(days=1)

    def test_complete_provenance_verifies(self):
        self.assertEqual(
            public_universe.missing_provenance_fields(
                _verified_pricing(), 'over_under_2.5'), [])
        self.assertEqual(
            public_universe.status_for(_verified_pricing(), self.after, False,
                                       1.85, 'over_under_2.5'),
            PredictionLog.PRICING_VERIFIED,
        )

    def test_each_required_field_is_individually_mandatory(self):
        for field in public_universe.REQUIRED_PROVENANCE_FIELDS:
            prov = dict(_verified_pricing())
            prov[field] = None
            self.assertIn(field, public_universe.missing_provenance_fields(
                prov, 'over_under_2.5'), f'{field} was not required')
            self.assertEqual(
                public_universe.status_for(prov, self.after, False, 1.85,
                                           'over_under_2.5'),
                PredictionLog.PRICING_MISSING_PROVENANCE,
                f'row verified despite missing {field}',
            )

    def test_wrong_line_is_rejected_for_a_line_market(self):
        prov = dict(_verified_pricing(), odds_line=3.5)
        problems = public_universe.missing_provenance_fields(prov, 'over_under_2.5')
        self.assertIn('wrong_or_missing_line', problems)

    def test_line_not_required_for_markets_without_one(self):
        prov = dict(_verified_pricing(), odds_line=None)
        self.assertEqual(public_universe.missing_provenance_fields(prov, '1x2'), [])

    def test_unrecognised_selection_policy_is_rejected(self):
        prov = dict(_verified_pricing(), odds_selection_policy='best_price_v0')
        self.assertIn('unrecognised_selection_policy',
                      public_universe.missing_provenance_fields(prov, '1x2'))

    def test_validation_failure_is_explicit_never_silent(self):
        """A missing field must downgrade the status, not pass through."""
        self.assertNotEqual(
            public_universe.status_for({}, self.after, False, 1.85, '1x2'),
            PredictionLog.PRICING_VERIFIED,
        )
