"""
The claim-publication lifecycle: eligibility, publication, integrity, settlement.

`publish_prediction_claim` is the ONLY supported way to create a public claim —
the manual staff workflow and the future gem selector both call it, so neither
can drift from these rules.
"""
import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import PredictionLog, PublishedClaim, PublishedClaimResult
from core.services import claim_publication, public_universe
from core.tests import _verified_pricing

User = get_user_model()


def make_prediction(fixture_id=960001, *, odds=1.85, confidence=0.64,
                    kickoff_in=timedelta(days=2), recommended=True,
                    status=PredictionLog.PRICING_VERIFIED, audit_excluded=False,
                    provenance='ok', market='over_under_2.5'):
    prov = None
    if provenance == 'ok':
        prov = _verified_pricing(odds)
        prov['odds_captured_at'] = timezone.now().isoformat()
    elif provenance == 'incomplete':
        prov = dict(_verified_pricing(odds), odds_bookmaker_name=None)

    pred = PredictionLog.objects.create(
        fixture_id=fixture_id, home_team='Falkirk', away_team='St. Mirren',
        league='Premiership', kickoff=timezone.now() + kickoff_in,
        predicted_outcome='Over 2.5', market_type=market,
        confidence=confidence, odds=odds,
        probability_home=0.5, probability_draw=0.25, probability_away=0.25,
        is_recommended=recommended, is_audit_excluded=audit_excluded,
        odds_provenance=prov, prediction_run_id='run-abc',
    )
    PredictionLog.objects.filter(pk=pred.pk).update(pricing_integrity_status=status)
    pred.refresh_from_db()
    return pred


class EligibilityTests(TestCase):

    def test_genuinely_verified_future_prediction_is_accepted(self):
        pred = make_prediction(960010)
        self.assertEqual(claim_publication.check_publication_eligibility(pred), [])
        claim = claim_publication.publish_prediction_claim(pred.pk)
        self.assertIsInstance(claim, PublishedClaim)

    def test_legacy_source_rejected(self):
        pred = make_prediction(960011, status=PredictionLog.PRICING_LEGACY_UNVERIFIED)
        with self.assertRaises(claim_publication.PublicationError) as ctx:
            claim_publication.publish_prediction_claim(pred.pk)
        self.assertEqual(ctx.exception.reason, 'ineligible')
        self.assertIn('pricing_not_verified', ctx.exception.detail)

    def test_audit_excluded_source_rejected(self):
        pred = make_prediction(960012, audit_excluded=True,
                               status=PredictionLog.PRICING_AUDIT_EXCLUDED)
        with self.assertRaises(claim_publication.PublicationError):
            claim_publication.publish_prediction_claim(pred.pk)

    def test_incomplete_provenance_rejected(self):
        pred = make_prediction(960013, provenance='incomplete')
        problems = claim_publication.check_publication_eligibility(pred)
        self.assertTrue(any(p.startswith('incomplete_provenance') for p in problems))
        with self.assertRaises(claim_publication.PublicationError):
            claim_publication.publish_prediction_claim(pred.pk)

    def test_started_fixture_rejected(self):
        pred = make_prediction(960014, kickoff_in=-timedelta(hours=1))
        problems = claim_publication.check_publication_eligibility(pred)
        self.assertIn('fixture_already_started', problems)
        with self.assertRaises(claim_publication.PublicationError):
            claim_publication.publish_prediction_claim(pred.pk)

    def test_non_recommended_source_rejected(self):
        pred = make_prediction(960015, recommended=False)
        self.assertIn('not_recommended',
                      claim_publication.check_publication_eligibility(pred))

    def test_old_row_updated_after_cutoff_is_rejected_while_legacy(self):
        """A pre-cutoff row given fresh provenance is still not publishable.

        Its prediction timestamp predates the cutoff, so pairing it with a
        freshly captured price would itself be a false claim.
        """
        pred = make_prediction(960016, status=PredictionLog.PRICING_LEGACY_UNVERIFIED)
        PredictionLog.objects.filter(pk=pred.pk).update(
            prediction_logged_at=public_universe.PRICING_INTEGRITY_CUTOFF
            - timedelta(days=5)
        )
        pred.refresh_from_db()
        # Even with complete provenance, classification keeps it legacy...
        self.assertEqual(public_universe.classify_row(pred),
                         PredictionLog.PRICING_LEGACY_UNVERIFIED)
        # ...and publication refuses it.
        with self.assertRaises(claim_publication.PublicationError):
            claim_publication.publish_prediction_claim(pred.pk)

    def test_odds_captured_after_kickoff_rejected(self):
        pred = make_prediction(960017)
        prov = dict(pred.odds_provenance)
        prov['odds_captured_at'] = (pred.kickoff + timedelta(hours=1)).isoformat()
        PredictionLog.objects.filter(pk=pred.pk).update(odds_provenance=prov)
        pred.refresh_from_db()
        self.assertIn('odds_captured_after_kickoff',
                      claim_publication.check_publication_eligibility(pred))

    def test_unknown_prediction_reports_not_found(self):
        with self.assertRaises(claim_publication.PublicationError) as ctx:
            claim_publication.publish_prediction_claim(123456789)
        self.assertEqual(ctx.exception.reason, 'prediction_not_found')


class PublicationEndpointTests(TestCase):

    def setUp(self):
        self.pred = make_prediction(961001)
        self.url = f'/api/proof/{self.pred.pk}/publish/'

    def _api(self, user=None):
        api = APIClient()
        if user:
            api.force_authenticate(user=user)
        return api

    def test_staff_can_publish(self):
        root = User.objects.create_superuser('root', 'r@e.com', 'pw12345!')
        resp = self._api(root).post(self.url)
        self.assertEqual(resp.status_code, 201)
        body = json.loads(resp.content)
        self.assertTrue(body['success'])
        self.assertIn('/proof/claim/', body['proof_url'])
        self.assertEqual(len(body['claim_hash']), 64)
        self.assertEqual(PublishedClaim.objects.count(), 1)

    def test_anonymous_cannot_publish(self):
        self.assertIn(self._api().post(self.url).status_code, (401, 403))
        self.assertEqual(PublishedClaim.objects.count(), 0)

    def test_non_staff_cannot_publish(self):
        bob = User.objects.create_user('bob', 'b@e.com', 'pw12345!')
        self.assertIn(self._api(bob).post(self.url).status_code, (401, 403))
        self.assertEqual(PublishedClaim.objects.count(), 0)

    def test_get_cannot_create_a_claim(self):
        root = User.objects.create_superuser('root2', 'r2@e.com', 'pw12345!')
        resp = self._api(root).get(self.url)
        self.assertEqual(resp.status_code, 405)
        self.assertEqual(PublishedClaim.objects.count(), 0)

    def test_repeated_post_is_idempotent(self):
        root = User.objects.create_superuser('root3', 'r3@e.com', 'pw12345!')
        api = self._api(root)
        first = json.loads(api.post(self.url).content)
        second = json.loads(api.post(self.url).content)
        self.assertEqual(first['claim_id'], second['claim_id'])
        self.assertEqual(PublishedClaim.objects.count(), 1)

    def test_ineligible_source_returns_a_reason_not_a_claim(self):
        legacy = make_prediction(961002,
                                 status=PredictionLog.PRICING_LEGACY_UNVERIFIED)
        root = User.objects.create_superuser('root4', 'r4@e.com', 'pw12345!')
        resp = self._api(root).post(f'/api/proof/{legacy.pk}/publish/')
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.content)
        self.assertFalse(body['success'])
        self.assertEqual(body['reason'], 'ineligible')
        self.assertEqual(PublishedClaim.objects.count(), 0)

    def test_publication_is_never_automatic(self):
        """Becoming verified must not publish anything on its own."""
        make_prediction(961003)
        self.assertEqual(PublishedClaim.objects.count(), 0)


class IdempotencyAndImmutabilityTests(TestCase):

    def test_source_mutation_after_publication_does_not_affect_the_claim(self):
        pred = make_prediction(962001, odds=1.78)
        claim = claim_publication.publish_prediction_claim(pred.pk)
        original_hash = claim.claim_hash

        pred.odds = 3.50
        pred.predicted_outcome = 'Under 2.5'
        pred.confidence = 0.99
        pred.save()

        claim.refresh_from_db()
        self.assertEqual(claim.odds, 1.78)
        self.assertEqual(claim.predicted_outcome, 'Over 2.5')
        self.assertEqual(claim.claim_hash, original_hash)
        self.assertTrue(claim.verify_integrity())

    def test_republishing_after_source_mutation_returns_the_original(self):
        pred = make_prediction(962002, odds=1.78)
        first = claim_publication.publish_prediction_claim(pred.pk)
        pred.odds = 3.50
        pred.save()
        again = claim_publication.publish_prediction_claim(pred.pk)
        self.assertEqual(first.claim_id, again.claim_id)
        self.assertEqual(again.odds, 1.78)
        self.assertEqual(PublishedClaim.objects.count(), 1)

    def test_duplicate_claim_creation_is_prevented(self):
        pred = make_prediction(962003)
        for _ in range(4):
            claim_publication.publish_prediction_claim(pred.pk)
        self.assertEqual(PublishedClaim.objects.count(), 1)

    def test_ineligible_publication_leaves_no_partial_claim(self):
        pred = make_prediction(962004, provenance=None)
        with self.assertRaises(claim_publication.PublicationError):
            claim_publication.publish_prediction_claim(pred.pk)
        self.assertEqual(PublishedClaim.objects.count(), 0)
        self.assertEqual(PublishedClaimResult.objects.count(), 0)


class CanonicalHashTests(TestCase):

    def test_hash_is_deterministic(self):
        pred = make_prediction(963001)
        claim = claim_publication.publish_prediction_claim(pred.pk)
        self.assertEqual(claim.compute_hash(), claim.compute_hash())
        self.assertEqual(claim.claim_hash_version, 'v1')

    def test_provenance_key_order_does_not_change_the_hash(self):
        pred = make_prediction(963002)
        claim = claim_publication.publish_prediction_claim(pred.pk)
        baseline = claim.compute_hash()
        # Same content, different insertion order.
        claim.odds_provenance = dict(reversed(list(claim.odds_provenance.items())))
        self.assertEqual(claim.compute_hash(), baseline)

    def test_decimal_formatting_is_stable(self):
        pred = make_prediction(963003, odds=1.8)
        claim = claim_publication.publish_prediction_claim(pred.pk)
        baseline = claim.compute_hash()
        claim.odds = 1.80  # same number, different literal
        self.assertEqual(claim.compute_hash(), baseline)

    def test_mutating_any_protected_field_fails_verification(self):
        cases = [
            ('odds', 9.99),
            ('predicted_outcome', 'Under 2.5'),
            ('confidence', 0.99),
            ('market_type', '1x2'),
            ('home_team', 'Someone Else'),
            ('league', 'Другая лига'),
        ]
        for i, (field, value) in enumerate(cases):
            pred = make_prediction(963100 + i)
            claim = claim_publication.publish_prediction_claim(pred.pk)
            self.assertTrue(claim.verify_integrity())

            # A raw UPDATE bypasses save(), the way a direct DB edit would.
            PublishedClaim.objects.filter(pk=claim.claim_id).update(**{field: value})
            claim.refresh_from_db()
            self.assertFalse(claim.verify_integrity(),
                             f'tampering with {field} was not detected')

    def test_settlement_does_not_invalidate_the_claim_hash(self):
        pred = make_prediction(963005)
        claim = claim_publication.publish_prediction_claim(pred.pk)
        before = claim.claim_hash

        pred.was_correct = True
        pred.actual_score_home, pred.actual_score_away = 3, 1
        pred.save()
        claim_publication.settle_published_claim(claim)

        claim.refresh_from_db()
        self.assertEqual(claim.claim_hash, before)
        self.assertTrue(claim.verify_integrity())

    def test_tampered_claim_never_enters_performance(self):
        pred = make_prediction(963006)
        claim = claim_publication.publish_prediction_claim(pred.pk)
        pred.was_correct = True
        pred.save()
        claim_publication.settle_published_claim(claim)
        self.assertEqual(len(public_universe.resolved_claims()), 1)

        PublishedClaim.objects.filter(pk=claim.claim_id).update(odds=50.0)
        self.assertEqual(len(public_universe.resolved_claims()), 0)


class SettlementTests(TestCase):

    def _published(self, fixture_id):
        pred = make_prediction(fixture_id)
        return pred, claim_publication.publish_prediction_claim(pred.pk)

    def test_pending_until_settled(self):
        _, claim = self._published(964001)
        self.assertEqual(claim.result_status, PublishedClaim.STATUS_PENDING)
        self.assertFalse(claim.is_resolved)

    def test_valid_transitions_from_pending(self):
        cases = [
            (964010, {'was_correct': True}, PublishedClaim.STATUS_WON),
            (964011, {'was_correct': False}, PublishedClaim.STATUS_LOST),
            (964012, {'match_status': 'POSTP'}, PublishedClaim.STATUS_VOID),
            (964013, {'match_status': 'CANC'}, PublishedClaim.STATUS_CANCELLED),
        ]
        for fixture_id, updates, expected in cases:
            pred, claim = self._published(fixture_id)
            for k, v in updates.items():
                setattr(pred, k, v)
            pred.save()
            claim_publication.settle_published_claim(claim)
            self.assertEqual(claim.result_status, expected, f'{fixture_id}')

    def test_settlement_is_idempotent(self):
        pred, claim = self._published(964020)
        pred.was_correct = True
        pred.save()
        first = claim_publication.settle_published_claim(claim)
        second = claim_publication.settle_published_claim(claim)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(PublishedClaimResult.objects.count(), 1)

    def test_contradictory_settlement_is_rejected(self):
        pred, claim = self._published(964021)
        pred.was_correct = True
        pred.save()
        claim_publication.settle_published_claim(claim)

        with self.assertRaises(claim_publication.SettlementError) as ctx:
            claim_publication.settle_published_claim(
                claim, status=PublishedClaim.STATUS_LOST)
        self.assertEqual(ctx.exception.reason, 'contradictory_settlement')
        self.assertEqual(claim.result_status, PublishedClaim.STATUS_WON)

    def test_cannot_settle_back_to_pending(self):
        _, claim = self._published(964022)
        with self.assertRaises(claim_publication.SettlementError):
            claim_publication.settle_published_claim(
                claim, status=PublishedClaim.STATUS_PENDING)

    def test_settling_an_unsettled_fixture_is_refused(self):
        _, claim = self._published(964023)
        with self.assertRaises(claim_publication.SettlementError) as ctx:
            claim_publication.settle_published_claim(claim)
        self.assertEqual(ctx.exception.reason, 'not_settled_yet')

    def test_result_record_is_itself_immutable(self):
        pred, claim = self._published(964024)
        pred.was_correct = True
        pred.save()
        result = claim_publication.settle_published_claim(claim)
        result.status = PublishedClaim.STATUS_LOST
        with self.assertRaises(ValueError):
            result.save()

    def test_settlement_records_the_third_party_source(self):
        pred, claim = self._published(964025)
        pred.was_correct = True
        pred.match_status = 'FT'
        pred.save()
        result = claim_publication.settle_published_claim(claim)
        self.assertEqual(result.result_source, 'sportmonks')
        self.assertIn(str(pred.fixture_id), result.result_reference)

    def test_void_and_cancelled_are_excluded_from_performance(self):
        for fixture_id, status in [(964030, 'POSTP'), (964031, 'CANC')]:
            pred, claim = self._published(fixture_id)
            pred.match_status = status
            pred.save()
            claim_publication.settle_published_claim(claim)
        self.assertEqual(len(public_universe.resolved_claims()), 0)

    def test_original_claim_fields_survive_settlement(self):
        pred, claim = self._published(964040)
        snapshot = {f: getattr(claim, f) for f in
                    ('odds', 'confidence', 'predicted_outcome', 'market_type',
                     'kickoff', 'published_at', 'prediction_generated_at')}
        pred.was_correct = False
        pred.save()
        claim_publication.settle_published_claim(claim)

        claim.refresh_from_db()
        for field, value in snapshot.items():
            self.assertEqual(getattr(claim, field), value, field)

    def test_win_and_loss_receive_equal_treatment(self):
        pred_w, claim_w = self._published(964050)
        pred_w.was_correct = True
        pred_w.save()
        claim_publication.settle_published_claim(claim_w)

        pred_l, claim_l = self._published(964051)
        pred_l.was_correct = False
        pred_l.save()
        claim_publication.settle_published_claim(claim_l)

        won = json.loads(self.client.get(f'/api/proof/claim/{claim_w.claim_id}/').content)
        lost = json.loads(self.client.get(f'/api/proof/claim/{claim_l.claim_id}/').content)

        self.assertEqual(won['result']['status'], 'WON')
        self.assertEqual(lost['result']['status'], 'LOST')
        # Identical shape — a loss is presented exactly like a win.
        self.assertEqual(set(won.keys()), set(lost.keys()))
        self.assertEqual(set(won['pick'].keys()), set(lost['pick'].keys()))
        self.assertEqual(set(won['result'].keys()), set(lost['result'].keys()))


class StableClaimUrlTests(TestCase):

    def test_claim_url_serves_only_frozen_fields(self):
        pred = make_prediction(965001, odds=1.78)
        claim = claim_publication.publish_prediction_claim(pred.pk)

        pred.odds = 9.99
        pred.save()

        body = json.loads(
            self.client.get(f'/api/proof/claim/{claim.claim_id}/').content)
        self.assertEqual(body['pick']['odds'], 1.78)
        self.assertTrue(body['integrity_ok'])
        self.assertEqual(body['claim_id'], str(claim.claim_id))

    def test_unknown_claim_uuid_is_unpublished(self):
        resp = self.client.get(
            '/api/proof/claim/00000000-0000-4000-8000-000000000000/')
        self.assertEqual(resp.status_code, 404)
        body = json.loads(resp.content)
        self.assertFalse(body['published'])
        self.assertNotIn('pick', body)

    def test_pending_card_uses_restrained_language(self):
        pred = make_prediction(965002)
        claim = claim_publication.publish_prediction_claim(pred.pk)
        body = json.loads(
            self.client.get(f'/api/proof/claim/{claim.claim_id}/').content)

        self.assertEqual(body['result']['status'], 'PENDING')
        self.assertIn('Published before kickoff', body['note'])
        blob = json.dumps(body).lower()
        for banned in ('proven accuracy', 'guaranteed', 'sure bet',
                       'easy money', 'you need to win'):
            self.assertNotIn(banned, blob)

    def test_pending_card_exposes_the_frozen_price_provenance(self):
        pred = make_prediction(965003)
        claim = claim_publication.publish_prediction_claim(pred.pk)
        pick = json.loads(
            self.client.get(f'/api/proof/claim/{claim.claim_id}/').content)['pick']

        self.assertEqual(pick['bookmaker'], 'bet365')
        self.assertEqual(pick['odds_market'], 'Goals Over/Under')
        self.assertIsNotNone(pick['odds_captured_at'])
        self.assertIsNotNone(pick['published_at'])
        # Model score must be labelled as a score, not a calibrated probability.
        self.assertIn('model_score_percent', pick)

    def test_tampered_claim_returns_a_safe_integrity_error_state(self):
        pred = make_prediction(965004)
        claim = claim_publication.publish_prediction_claim(pred.pk)
        PublishedClaim.objects.filter(pk=claim.claim_id).update(odds=50.0)

        body = json.loads(
            self.client.get(f'/api/proof/claim/{claim.claim_id}/').content)
        self.assertFalse(body['integrity_ok'])
        self.assertIn('integrity check', body['integrity_error'])


class StaffPreviewShowsWhatWillBeFrozenTests(TestCase):

    def test_preview_lists_frozen_fields_and_publish_endpoint(self):
        pred = make_prediction(966001)
        root = User.objects.create_superuser('root5', 'r5@e.com', 'pw12345!')
        api = APIClient()
        api.force_authenticate(user=root)

        body = json.loads(api.get(f'/api/proof/{pred.fixture_id}/preview/').content)
        self.assertEqual(body['state'], 'staff_preview')
        self.assertIn('MUTABLE PREVIEW', body['warning'])
        self.assertTrue(body['publishable'])
        self.assertEqual(body['publication_blockers'], [])
        for field in ('fixture_id', 'market_type', 'predicted_outcome', 'odds',
                      'bookmaker', 'odds_captured_at', 'prediction_generated_at'):
            self.assertIn(field, body['will_freeze'])
        self.assertEqual(body['publish_endpoint'], f'/api/proof/{pred.pk}/publish/')

    def test_preview_reports_blockers_for_an_ineligible_source(self):
        pred = make_prediction(966002,
                               status=PredictionLog.PRICING_LEGACY_UNVERIFIED)
        root = User.objects.create_superuser('root6', 'r6@e.com', 'pw12345!')
        api = APIClient()
        api.force_authenticate(user=root)

        body = json.loads(api.get(f'/api/proof/{pred.fixture_id}/preview/').content)
        self.assertFalse(body['publishable'])
        self.assertTrue(
            any('pricing_not_verified' in b for b in body['publication_blockers']))
