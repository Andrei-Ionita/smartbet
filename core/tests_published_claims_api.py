"""
The public published-claims list endpoint.

WHY THIS EXISTS
---------------
The public "published picks" section used to derive itself from
``/api/transparency/recent/``, which serves PredictionLog rows. That feed can
show predictions which were never published, and it omits actual claims — so
the surface the product uses to demonstrate the live-signal / published-claim
distinction was itself built on the mutable side of that distinction.

These tests pin the correction: PublishedClaim (plus its separate, insert-only
PublishedClaimResult) is the only authority, nothing is filtered out by
outcome, and the endpoint cannot write.
"""
import uuid
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import PredictionLog, PublishedClaim, PublishedClaimResult

LIST_URL = '/api/proof/claims/'


def _prediction(**overrides):
    defaults = dict(
        fixture_id=9001,
        home_team='Cardiff City',
        away_team='Swindon Town',
        league='Carabao Cup',
        kickoff=timezone.now() + timedelta(days=4),
        market_type='btts',
        predicted_outcome='Btts yes',
        confidence=0.62,
        odds=1.8,
        expected_value=0.1,
        probability_home=0.30,
        probability_draw=0.28,
        probability_away=0.42,
        pricing_integrity_status=PredictionLog.PRICING_VERIFIED,
    )
    defaults.update(overrides)
    return PredictionLog.objects.create(**defaults)


def _claim(prediction, **overrides):
    now = timezone.now()
    defaults = dict(
        claim_id=uuid.uuid4(),
        prediction=prediction,
        fixture_id=prediction.fixture_id,
        home_team=prediction.home_team,
        away_team=prediction.away_team,
        league=prediction.league,
        kickoff=prediction.kickoff,
        market_type=prediction.market_type,
        predicted_outcome=prediction.predicted_outcome,
        confidence=prediction.confidence,
        odds=prediction.odds,
        odds_provenance={
            'odds_bookmaker_name': 'BetVictor',
            'odds_market_description': 'Both Teams To Score',
            'odds_captured_at': now.isoformat(),
        },
        odds_captured_at=now,
        prediction_generated_at=now,
        published_at=now,
        pricing_integrity_status=PredictionLog.PRICING_VERIFIED,
    )
    defaults.update(overrides)
    claim = PublishedClaim(**defaults)
    claim.claim_hash = claim.compute_hash()
    claim.save()
    return claim


class PublishedClaimsListTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_returns_published_claims_not_prediction_logs(self):
        pred = _prediction()
        claim = _claim(pred)
        # A second prediction that was NEVER published must not appear.
        _prediction(fixture_id=9002, home_team='Unpublished FC')

        body = self.client.get(LIST_URL).json()

        self.assertTrue(body['success'])
        self.assertEqual(body['count'], 1)
        ids = [c['claim_id'] for c in body['claims']]
        self.assertEqual(ids, [str(claim.claim_id)])
        teams = [c['home_team'] for c in body['claims']]
        self.assertNotIn('Unpublished FC', teams)

    def test_serves_the_frozen_claim_fields_not_the_mutable_prediction(self):
        pred = _prediction()
        claim = _claim(pred)

        # The pipeline rewrites PredictionLog on every run. The claim must not
        # move with it.
        pred.odds = 9.99
        pred.predicted_outcome = 'Btts no'
        pred.save()

        row = self.client.get(LIST_URL).json()['claims'][0]
        self.assertEqual(row['odds'], 1.8)
        self.assertEqual(row['predicted_outcome'], 'Btts yes')
        self.assertEqual(row['claim_hash'], claim.claim_hash)
        self.assertTrue(row['integrity_ok'])

    def test_pending_claim_has_no_result_object(self):
        _claim(_prediction())
        row = self.client.get(LIST_URL).json()['claims'][0]

        self.assertIsNone(row['result'])
        self.assertEqual(row['claim_state'], PublishedClaim.STATUS_PENDING)
        self.assertFalse(row['counts_towards_verified_record'])

    def test_settled_claim_carries_insert_only_result_data(self):
        claim = _claim(_prediction())
        settled = timezone.now()
        PublishedClaimResult.objects.create(
            claim=claim,
            status=PublishedClaim.STATUS_WON,
            actual_score_home=2,
            actual_score_away=1,
            settled_at=settled,
            result_source='sportmonks',
        )

        row = self.client.get(LIST_URL).json()['claims'][0]
        self.assertEqual(row['claim_state'], PublishedClaim.STATUS_WON)
        self.assertEqual(row['result']['status'], PublishedClaim.STATUS_WON)
        self.assertEqual(row['result']['actual_score_home'], 2)
        self.assertEqual(row['result']['actual_score_away'], 1)
        self.assertEqual(row['result']['result_source'], 'sportmonks')
        self.assertTrue(row['counts_towards_verified_record'])

    def test_list_exposes_methodology_and_price_freshness(self):
        claim = _claim(_prediction(), model_version='rank-v1-test')

        row = self.client.get(LIST_URL).json()['claims'][0]

        self.assertEqual(row['ranking_version'], 'rank-v1-test')
        self.assertEqual(row['price_age_hours_at_publication'], 0.0)
        self.assertTrue(row['price_fresh_at_publication'])

    def test_losses_voids_and_cancellations_are_not_filtered_out(self):
        """A record that quietly drops its losses is not a record."""
        wanted = [
            PublishedClaim.STATUS_WON,
            PublishedClaim.STATUS_LOST,
            PublishedClaim.STATUS_VOID,
            PublishedClaim.STATUS_CANCELLED,
        ]
        for i, status in enumerate(wanted):
            claim = _claim(_prediction(fixture_id=9100 + i))
            PublishedClaimResult.objects.create(claim=claim, status=status)

        body = self.client.get(LIST_URL).json()
        self.assertEqual(body['count'], 4)
        self.assertCountEqual([c['claim_state'] for c in body['claims']], wanted)
        by_state = {c['claim_state']: c for c in body['claims']}
        self.assertTrue(by_state[PublishedClaim.STATUS_WON]['counts_towards_verified_record'])
        self.assertTrue(by_state[PublishedClaim.STATUS_LOST]['counts_towards_verified_record'])
        self.assertFalse(by_state[PublishedClaim.STATUS_VOID]['counts_towards_verified_record'])
        self.assertFalse(by_state[PublishedClaim.STATUS_CANCELLED]['counts_towards_verified_record'])

    def test_stale_price_stays_visible_but_does_not_count(self):
        now = timezone.now()
        claim = _claim(
            _prediction(),
            odds_captured_at=now - timedelta(hours=13),
            published_at=now,
        )
        PublishedClaimResult.objects.create(
            claim=claim,
            status=PublishedClaim.STATUS_WON,
        )

        row = self.client.get(LIST_URL).json()['claims'][0]
        self.assertFalse(row['price_fresh_at_publication'])
        self.assertEqual(row['price_age_hours_at_publication'], 13.0)
        self.assertFalse(row['counts_towards_verified_record'])

    def test_superseded_and_correcting_claims_both_stay_visible(self):
        original = _claim(_prediction())
        correction = _claim(
            _prediction(fixture_id=9003),
            supersedes=original,
            correction_reason='price corrected',
        )

        body = self.client.get(LIST_URL).json()
        rows = {c['claim_id']: c for c in body['claims']}

        self.assertEqual(body['count'], 2)
        self.assertTrue(rows[str(original.claim_id)]['superseded'])
        self.assertFalse(rows[str(correction.claim_id)]['superseded'])
        self.assertTrue(rows[str(correction.claim_id)]['is_correction'])
        self.assertEqual(
            rows[str(correction.claim_id)]['supersedes'], str(original.claim_id)
        )

    def test_exposes_no_internal_or_private_fields(self):
        claim = _claim(_prediction(), correction_reason='internal staff note')
        row = self.client.get(LIST_URL).json()['claims'][0]

        for leaked in ('correction_reason', 'prediction', 'prediction_id',
                       'snapshot', 'snapshot_id', 'odds_provenance', 'notes'):
            self.assertNotIn(leaked, row, f'{leaked} must not be public')
        self.assertEqual(row['proof_url'], f'/proof/claim/{claim.claim_id}')

    def test_ordering_is_deterministic_newest_publication_first(self):
        now = timezone.now()
        older = _claim(_prediction(fixture_id=9201),
                       published_at=now - timedelta(hours=2))
        newer = _claim(_prediction(fixture_id=9202), published_at=now)

        ids = [c['claim_id'] for c in self.client.get(LIST_URL).json()['claims']]
        self.assertEqual(ids, [str(newer.claim_id), str(older.claim_id)])

    def test_pagination_is_bounded_and_does_not_repeat_rows(self):
        for i in range(5):
            _claim(_prediction(fixture_id=9300 + i),
                   published_at=timezone.now() - timedelta(minutes=i))

        first = self.client.get(LIST_URL, {'limit': 2, 'offset': 0}).json()
        second = self.client.get(LIST_URL, {'limit': 2, 'offset': 2}).json()

        self.assertEqual(first['count'], 5)
        self.assertEqual(first['limit'], 2)
        self.assertEqual(len(first['claims']), 2)
        self.assertEqual(second['offset'], 2)
        overlap = {c['claim_id'] for c in first['claims']} & {
            c['claim_id'] for c in second['claims']
        }
        self.assertEqual(overlap, set())

    def test_limit_is_capped(self):
        _claim(_prediction())
        body = self.client.get(LIST_URL, {'limit': 100000}).json()
        self.assertEqual(body['limit'], 200)

    def test_non_integer_paging_is_a_controlled_error(self):
        response = self.client.get(LIST_URL, {'limit': 'all'})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])
        self.assertNotIn('Traceback', str(response.content))

    def test_empty_record_is_an_honest_empty_list(self):
        body = self.client.get(LIST_URL).json()
        self.assertTrue(body['success'])
        self.assertEqual(body['count'], 0)
        self.assertEqual(body['claims'], [])


class PublishedClaimsListIsReadOnlyTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_write_methods_are_rejected(self):
        for method in ('post', 'put', 'patch', 'delete'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(LIST_URL)
                self.assertEqual(response.status_code, 405)

    def test_a_get_writes_nothing(self):
        claim = _claim(_prediction())
        before = (
            PublishedClaim.objects.count(),
            PublishedClaimResult.objects.count(),
            PredictionLog.objects.count(),
            claim.claim_hash,
        )

        self.client.get(LIST_URL)
        self.client.get(LIST_URL, {'limit': 10, 'offset': 0})

        claim.refresh_from_db()
        after = (
            PublishedClaim.objects.count(),
            PublishedClaimResult.objects.count(),
            PredictionLog.objects.count(),
            claim.claim_hash,
        )
        self.assertEqual(before, after)


class PublishedClaimsSourceAuthorityTests(TestCase):
    """The endpoint must have no path back to the mutable sources."""

    @staticmethod
    def _code_of(func_name):
        """Executable lines of one view, with comments and docstrings removed.

        The decorated callable is a DRF wrapper, so inspect.getsource would
        return the framework's dispatch shim. Read the module text instead, and
        strip prose so a comment naming a model cannot fail the check.
        """
        import os
        import re
        from pathlib import Path

        path = Path(__file__).resolve().parent / 'transparency_views.py'
        src = path.read_text(encoding='utf-8')
        start = src.index(f'def {func_name}(')
        rest = src[start:]
        end = rest.find(os.linesep.join(['', 'def ']), 1)
        if end == -1:
            end = rest.find('\ndef ', 1)
        body = rest if end == -1 else rest[:end]
        body = re.sub(r'"""[\s\S]*?"""', '', body)
        return re.sub(r'#[^\r\n]*', '', body)

    def test_view_source_never_reads_a_fallback_model(self):
        code = self._code_of('published_claims_list') + self._code_of('_serialize_claim_row')

        for forbidden in ('PredictionLog', 'PredictionSnapshot',
                          'recent_predictions', 'get_recommendations',
                          'actual_outcome', 'was_correct'):
            self.assertNotIn(
                forbidden, code,
                f'{forbidden} must not be reachable from the published-claims '
                'endpoint — PublishedClaim is the sole authority.',
            )
        self.assertIn('PublishedClaim', code)
