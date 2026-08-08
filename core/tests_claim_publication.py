"""
The claim lifecycle, now sourced from immutable PredictionSnapshots.

    Prediction run -> PredictionSnapshot (append-only)
                   -> update latest-state PredictionLog
                   -> staff chooses ONE snapshot
                   -> PublishedClaim (immutable)
                   -> PublishedClaimResult (immutable)

`publish_prediction_claim(snapshot_id)` is the ONLY supported way to create a
claim; the future gem selector will call it with a snapshot it ranked.
"""
import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (PredictionLog, PredictionSnapshot, PublishedClaim,
                         PublishedClaimResult)
from core.services import claim_publication, public_universe, snapshot_recording

User = get_user_model()


def provenance(odds=1.85, captured_at=None):
    """Complete provenance, with a capture time coherent with `now`."""
    captured = captured_at or (timezone.now() - timedelta(hours=1))
    return {
        'odds': odds,
        'odds_market_id': 80,
        'odds_market_description': 'Goals Over/Under',
        'odds_line': 2.5,
        'odds_label': 'Over',
        'odds_bookmaker_id': 2,
        'odds_bookmaker_name': 'bet365',
        'odds_bookmaker_count': 5,
        'odds_min': odds - 0.02,
        'odds_max': odds + 0.02,
        'odds_captured_at': captured.isoformat(),
        'odds_fixture_id': None,
        'odds_entry_id': 1,
        'odds_selection_policy': 'lower_median_v1',
    }


def latest_state(fixture_id, *, odds=1.85, confidence=0.64,
                 kickoff_in=timedelta(days=2), market='over_under_2.5',
                 outcome='Over 2.5'):
    """The mutable latest-state row for a fixture."""
    return PredictionLog.objects.create(
        fixture_id=fixture_id, home_team='Falkirk', away_team='St. Mirren',
        league='Premiership', kickoff=timezone.now() + kickoff_in,
        predicted_outcome=outcome, market_type=market,
        confidence=confidence, odds=odds,
        probability_home=0.5, probability_draw=0.25, probability_away=0.25,
        is_recommended=True, odds_provenance=provenance(odds),
    )


def record(pred, *, run_id='run-1', odds=1.85, confidence=0.64,
           generated_at=None, prov='ok', captured_at=None,
           is_recommended=True, audit_excluded=False, outcome=None,
           market=None):
    """Append a snapshot for a run, then classify it."""
    if prov == 'ok':
        prov_dict = provenance(odds, captured_at=captured_at)
    elif prov == 'incomplete':
        prov_dict = dict(provenance(odds, captured_at=captured_at),
                         odds_bookmaker_name=None)
    else:
        prov_dict = None

    snap, created = snapshot_recording.record_snapshot(
        prediction_run_id=run_id,
        prediction=pred,
        fixture_id=pred.fixture_id,
        home_team=pred.home_team, away_team=pred.away_team,
        league=pred.league, league_id=pred.league_id, kickoff=pred.kickoff,
        market_type=market or pred.market_type,
        predicted_outcome=outcome or pred.predicted_outcome,
        confidence=confidence, expected_value=0.05,
        is_recommended=is_recommended, model_version='consensus_ensemble',
        odds=odds, odds_provenance=prov_dict,
        prediction_generated_at=generated_at or timezone.now(),
        is_audit_excluded=audit_excluded,
    )
    return snap, created


# ─────────────────────────────────────────────────────────────────────────────
class SnapshotCreationTests(TestCase):

    def test_new_fixture_creates_a_snapshot(self):
        pred = latest_state(970001)
        snap, created = record(pred, run_id='runA')
        self.assertTrue(created)
        self.assertEqual(PredictionSnapshot.objects.count(), 1)
        self.assertEqual(snap.pricing_integrity_status,
                         PredictionLog.PRICING_VERIFIED)

    def test_existing_fixture_in_a_NEW_run_creates_another_snapshot(self):
        """The blocker this layer exists to solve."""
        pred = latest_state(970002)
        a, _ = record(pred, run_id='runA', odds=1.80)
        b, _ = record(pred, run_id='runB', odds=1.70)

        self.assertNotEqual(a.snapshot_id, b.snapshot_id)
        self.assertEqual(PredictionSnapshot.objects.count(), 2)
        self.assertEqual(a.odds, 1.80)
        self.assertEqual(b.odds, 1.70)

    def test_retrying_the_same_run_is_idempotent(self):
        pred = latest_state(970003)
        first, created1 = record(pred, run_id='runA')
        second, created2 = record(pred, run_id='runA')
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(first.snapshot_id, second.snapshot_id)
        self.assertEqual(PredictionSnapshot.objects.count(), 1)

    def test_same_outcome_from_distinct_runs_is_two_observations(self):
        pred = latest_state(970004)
        record(pred, run_id='r09')
        record(pred, run_id='r14')
        record(pred, run_id='r19')
        self.assertEqual(PredictionSnapshot.objects.count(), 3)

    def test_snapshot_fields_are_internally_coherent(self):
        pred = latest_state(970005, odds=1.9)
        snap, _ = record(pred, run_id='runA', odds=1.9)
        prov = snap.odds_provenance
        self.assertEqual(snap.odds, prov['odds'])
        self.assertEqual(snap.odds_captured_at.isoformat(),
                         prov['odds_captured_at'])
        self.assertLessEqual(snap.odds_captured_at, snap.prediction_generated_at)
        self.assertLess(snap.prediction_generated_at, snap.kickoff)
        self.assertEqual(public_universe.snapshot_timestamp_problems(snap), [])

    def test_incomplete_provenance_creates_a_non_verified_snapshot(self):
        pred = latest_state(970006)
        snap, _ = record(pred, run_id='runA', prov='incomplete')
        self.assertEqual(snap.pricing_integrity_status,
                         PredictionLog.PRICING_MISSING_PROVENANCE)

    def test_pre_cutoff_run_cannot_create_a_verified_snapshot(self):
        pred = latest_state(970007)
        before = public_universe.PRICING_INTEGRITY_CUTOFF - timedelta(days=3)
        snap, _ = record(pred, run_id='old', generated_at=before,
                         captured_at=before - timedelta(hours=1))
        self.assertEqual(snap.pricing_integrity_status,
                         PredictionLog.PRICING_LEGACY_UNVERIFIED)

    def test_audit_excluded_snapshot_is_quarantined(self):
        pred = latest_state(970008)
        snap, _ = record(pred, run_id='runA', audit_excluded=True)
        self.assertEqual(snap.pricing_integrity_status,
                         PredictionLog.PRICING_AUDIT_EXCLUDED)


class SnapshotImmutabilityTests(TestCase):

    def test_protected_fields_cannot_be_updated(self):
        pred = latest_state(971001)
        snap, _ = record(pred, run_id='runA')
        snap.odds = 9.99
        with self.assertRaises(ValueError):
            snap.save()

    def test_latest_state_changes_do_not_change_the_snapshot(self):
        pred = latest_state(971002, odds=1.78)
        snap, _ = record(pred, run_id='runA', odds=1.78)

        pred.odds = 3.50
        pred.predicted_outcome = 'Under 2.5'
        pred.confidence = 0.99
        pred.save()

        snap.refresh_from_db()
        self.assertEqual(snap.odds, 1.78)
        self.assertEqual(snap.predicted_outcome, 'Over 2.5')
        self.assertTrue(snap.verify_integrity())

    def test_new_model_output_appends_rather_than_rewrites(self):
        pred = latest_state(971003, odds=1.78)
        old, _ = record(pred, run_id='runA', odds=1.78, confidence=0.64)
        new, _ = record(pred, run_id='runB', odds=2.10, confidence=0.61)

        old.refresh_from_db()
        self.assertEqual(old.odds, 1.78)
        self.assertEqual(old.confidence, 0.64)
        self.assertEqual(new.odds, 2.10)
        self.assertTrue(old.verify_integrity())
        self.assertTrue(new.verify_integrity())

    def test_correction_leaves_the_original_snapshot_intact(self):
        pred = latest_state(971004, odds=1.78)
        original, _ = record(pred, run_id='runA', odds=1.78)
        original_hash = original.snapshot_hash

        corrected = original.correct('price restated', odds=1.72)

        original.refresh_from_db()
        self.assertEqual(original.odds, 1.78)
        self.assertEqual(original.snapshot_hash, original_hash)
        self.assertTrue(original.verify_integrity())
        self.assertEqual(corrected.supersedes_id, original.snapshot_id)
        self.assertTrue(original.is_superseded)

    def test_raw_db_tampering_is_detected(self):
        pred = latest_state(971005)
        snap, _ = record(pred, run_id='runA')
        PredictionSnapshot.objects.filter(pk=snap.snapshot_id).update(odds=42.0)
        snap.refresh_from_db()
        self.assertFalse(snap.verify_integrity())


class TimestampIntegrityTests(TestCase):

    def test_same_run_coherent_timestamps_accepted(self):
        pred = latest_state(972001)
        snap, _ = record(pred, run_id='runA')
        self.assertEqual(public_universe.snapshot_timestamp_problems(snap), [])
        self.assertEqual(snap.pricing_integrity_status,
                         PredictionLog.PRICING_VERIFIED)

    def test_old_prediction_with_fresh_odds_is_rejected(self):
        """The exact pre-cutoff defect: stale prediction, fresh price."""
        pred = latest_state(972002)
        snap = PredictionSnapshot(
            prediction_run_id='bad', prediction=pred,
            fixture_id=pred.fixture_id, home_team=pred.home_team,
            away_team=pred.away_team, league=pred.league, kickoff=pred.kickoff,
            market_type=pred.market_type, predicted_outcome=pred.predicted_outcome,
            confidence=0.64, is_recommended=True, odds=1.85,
            odds_provenance=provenance(1.85, captured_at=timezone.now()),
            odds_captured_at=timezone.now(),
            # Generated 10 days ago, priced now -> incoherent.
            prediction_generated_at=timezone.now() - timedelta(days=10),
        )
        problems = public_universe.snapshot_timestamp_problems(snap)
        self.assertIn('odds_captured_after_prediction', problems)

    def test_stale_odds_with_fresh_prediction_is_rejected(self):
        pred = latest_state(972003)
        snap, _ = record(pred, run_id='runA',
                         captured_at=timezone.now() - timedelta(days=10))
        self.assertIn('odds_stale_relative_to_prediction',
                      public_universe.snapshot_timestamp_problems(snap))
        self.assertEqual(snap.pricing_integrity_status,
                         PredictionLog.PRICING_MISSING_PROVENANCE)

    def test_post_kickoff_snapshot_is_rejected(self):
        pred = latest_state(972004, kickoff_in=timedelta(hours=1))
        snap, _ = record(pred, run_id='runA',
                         generated_at=timezone.now() + timedelta(hours=2))
        problems = public_universe.snapshot_timestamp_problems(snap)
        self.assertIn('prediction_generated_after_kickoff', problems)

    def test_odds_captured_after_kickoff_is_rejected(self):
        pred = latest_state(972005, kickoff_in=timedelta(hours=2))
        snap = PredictionSnapshot(
            prediction_run_id='bad2', prediction=pred,
            fixture_id=pred.fixture_id, home_team=pred.home_team,
            away_team=pred.away_team, league=pred.league, kickoff=pred.kickoff,
            market_type=pred.market_type, predicted_outcome=pred.predicted_outcome,
            confidence=0.64, is_recommended=True, odds=1.85,
            odds_provenance=provenance(1.85),
            odds_captured_at=pred.kickoff + timedelta(hours=1),
            prediction_generated_at=pred.kickoff + timedelta(hours=2),
        )
        self.assertIn('odds_captured_after_kickoff',
                      public_universe.snapshot_timestamp_problems(snap))

    def test_odds_captured_before_prediction_is_normal(self):
        """The documented capture sequence: a price exists before we read it."""
        pred = latest_state(972006)
        snap, _ = record(pred, run_id='runA',
                         captured_at=timezone.now() - timedelta(hours=6))
        self.assertEqual(public_universe.snapshot_timestamp_problems(snap), [])


class PublicationFromSnapshotTests(TestCase):

    def test_verified_snapshot_can_be_published(self):
        pred = latest_state(973001, odds=1.78)
        snap, _ = record(pred, run_id='runA', odds=1.78)
        claim = claim_publication.publish_prediction_claim(snap.snapshot_id)

        self.assertEqual(claim.snapshot_id, snap.snapshot_id)
        self.assertEqual(claim.odds, 1.78)
        self.assertEqual(claim.prediction_generated_at, snap.prediction_generated_at)
        self.assertTrue(claim.verify_integrity())

    def test_source_snapshot_id_is_preserved(self):
        pred = latest_state(973002)
        snap, _ = record(pred, run_id='runA')
        claim = claim_publication.publish_prediction_claim(snap.snapshot_id)
        self.assertEqual(str(claim.snapshot_id), str(snap.snapshot_id))
        self.assertIn(str(snap.snapshot_id),
                      json.dumps(claim.canonical_payload()))

    def test_legacy_snapshot_cannot_be_published(self):
        pred = latest_state(973003)
        before = public_universe.PRICING_INTEGRITY_CUTOFF - timedelta(days=3)
        snap, _ = record(pred, run_id='old', generated_at=before,
                         captured_at=before - timedelta(hours=1))
        with self.assertRaises(claim_publication.PublicationError) as ctx:
            claim_publication.publish_prediction_claim(snap.snapshot_id)
        self.assertIn('pricing_not_verified', ctx.exception.detail)

    def test_incomplete_provenance_snapshot_cannot_be_published(self):
        pred = latest_state(973004)
        snap, _ = record(pred, run_id='runA', prov='incomplete')
        with self.assertRaises(claim_publication.PublicationError):
            claim_publication.publish_prediction_claim(snap.snapshot_id)

    def test_latest_state_mutation_affects_neither_snapshot_nor_claim(self):
        pred = latest_state(973005, odds=1.78)
        snap, _ = record(pred, run_id='runA', odds=1.78)
        claim = claim_publication.publish_prediction_claim(snap.snapshot_id)

        pred.odds = 9.99
        pred.predicted_outcome = 'Under 2.5'
        pred.save()

        snap.refresh_from_db()
        claim.refresh_from_db()
        self.assertEqual(snap.odds, 1.78)
        self.assertEqual(claim.odds, 1.78)
        self.assertEqual(claim.predicted_outcome, 'Over 2.5')
        self.assertTrue(claim.verify_integrity())

    def test_repeated_publication_is_idempotent(self):
        pred = latest_state(973006)
        snap, _ = record(pred, run_id='runA')
        a = claim_publication.publish_prediction_claim(snap.snapshot_id)
        b = claim_publication.publish_prediction_claim(snap.snapshot_id)
        self.assertEqual(a.claim_id, b.claim_id)
        self.assertEqual(PublishedClaim.objects.count(), 1)

    def test_tampered_snapshot_cannot_be_published(self):
        pred = latest_state(973007)
        snap, _ = record(pred, run_id='runA')
        PredictionSnapshot.objects.filter(pk=snap.snapshot_id).update(odds=42.0)
        with self.assertRaises(claim_publication.PublicationError) as ctx:
            claim_publication.publish_prediction_claim(snap.snapshot_id)
        self.assertEqual(ctx.exception.reason, 'snapshot_integrity_failed')

    def test_superseded_snapshot_cannot_be_published(self):
        pred = latest_state(973008)
        snap, _ = record(pred, run_id='runA')
        snap.correct('restated', odds=1.70)
        with self.assertRaises(claim_publication.PublicationError) as ctx:
            claim_publication.publish_prediction_claim(snap.snapshot_id)
        self.assertIn('snapshot_superseded', ctx.exception.detail)

    def test_unknown_snapshot_reports_not_found(self):
        with self.assertRaises(claim_publication.PublicationError) as ctx:
            claim_publication.publish_prediction_claim(
                '00000000-0000-4000-8000-000000000000')
        self.assertEqual(ctx.exception.reason, 'snapshot_not_found')

    def test_publishing_an_OLDER_snapshot_requires_an_explicit_choice(self):
        pred = latest_state(973009)
        older, _ = record(pred, run_id='runA', odds=1.80)
        newer, _ = record(pred, run_id='runB', odds=1.70)

        # The compatibility wrapper refuses to choose between them.
        with self.assertRaises(claim_publication.PublicationError) as ctx:
            claim_publication.publish_for_prediction(pred.pk)
        self.assertEqual(ctx.exception.reason, 'ambiguous_snapshot')

        # An explicit choice of the older snapshot still works.
        claim = claim_publication.publish_prediction_claim(older.snapshot_id)
        self.assertEqual(claim.odds, 1.80)

    def test_compatibility_wrapper_works_when_unambiguous(self):
        pred = latest_state(973010)
        snap, _ = record(pred, run_id='runA')
        claim = claim_publication.publish_for_prediction(pred.pk)
        self.assertEqual(claim.snapshot_id, snap.snapshot_id)

    def test_no_partial_claim_on_failure(self):
        pred = latest_state(973011)
        snap, _ = record(pred, run_id='runA', prov='incomplete')
        with self.assertRaises(claim_publication.PublicationError):
            claim_publication.publish_prediction_claim(snap.snapshot_id)
        self.assertEqual(PublishedClaim.objects.count(), 0)
        self.assertEqual(PublishedClaimResult.objects.count(), 0)


class PublicationEndpointTests(TestCase):

    def setUp(self):
        self.pred = latest_state(974001)
        self.snap, _ = record(self.pred, run_id='runA')
        self.url = f'/api/proof/snapshot/{self.snap.snapshot_id}/publish/'

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
        self.assertEqual(body['source_snapshot_id'], str(self.snap.snapshot_id))
        self.assertIn('/proof/claim/', body['proof_url'])

    def test_anonymous_cannot_publish(self):
        self.assertIn(self._api().post(self.url).status_code, (401, 403))
        self.assertEqual(PublishedClaim.objects.count(), 0)

    def test_non_staff_cannot_publish(self):
        bob = User.objects.create_user('bob', 'b@e.com', 'pw12345!')
        self.assertIn(self._api(bob).post(self.url).status_code, (401, 403))
        self.assertEqual(PublishedClaim.objects.count(), 0)

    def test_get_cannot_create_a_claim(self):
        root = User.objects.create_superuser('root2', 'r2@e.com', 'pw12345!')
        self.assertEqual(self._api(root).get(self.url).status_code, 405)
        self.assertEqual(PublishedClaim.objects.count(), 0)

    def test_repeated_post_is_idempotent(self):
        root = User.objects.create_superuser('root3', 'r3@e.com', 'pw12345!')
        api = self._api(root)
        a = json.loads(api.post(self.url).content)
        b = json.loads(api.post(self.url).content)
        self.assertEqual(a['claim_id'], b['claim_id'])
        self.assertEqual(PublishedClaim.objects.count(), 1)

    def test_publication_is_never_automatic(self):
        latest_state(974002)
        self.assertEqual(PublishedClaim.objects.count(), 0)


class StaffPreviewShowsSnapshotsTests(TestCase):

    def _staff_api(self, name='root4'):
        root = User.objects.create_superuser(name, f'{name}@e.com', 'pw12345!')
        api = APIClient()
        api.force_authenticate(user=root)
        return api

    def test_multiple_snapshots_are_shown_distinctly(self):
        pred = latest_state(975001)
        # Distinct generation times — otherwise a fast run gives both the same
        # timestamp and "is this the newest?" becomes meaningless.
        older, _ = record(pred, run_id='r09', odds=1.80,
                          generated_at=timezone.now() - timedelta(hours=3),
                          captured_at=timezone.now() - timedelta(hours=4))
        newer, _ = record(pred, run_id='r14', odds=1.70)

        body = json.loads(
            self._staff_api().get(f'/api/proof/{pred.fixture_id}/preview/').content)
        snaps = body['snapshots']
        self.assertEqual(len(snaps), 2)
        ids = {s['snapshot_id'] for s in snaps}
        self.assertEqual(ids, {str(older.snapshot_id), str(newer.snapshot_id)})

        by_id = {s['snapshot_id']: s for s in snaps}
        self.assertTrue(by_id[str(newer.snapshot_id)]['is_newest'])
        self.assertTrue(by_id[str(older.snapshot_id)]['newer_snapshot_exists'])
        # Each row carries what the founder needs to choose.
        for s in snaps:
            for key in ('prediction_run_id', 'prediction_generated_at', 'odds',
                        'bookmaker', 'odds_captured_at', 'model_version',
                        'pricing_integrity_status', 'publication_blockers',
                        'model_score_percent', 'publish_endpoint'):
                self.assertIn(key, s)

    def test_the_exact_snapshot_selected_is_the_one_published(self):
        pred = latest_state(975002)
        older, _ = record(pred, run_id='r09', odds=1.80)
        record(pred, run_id='r14', odds=1.70)

        api = self._staff_api('root5')
        resp = api.post(f'/api/proof/snapshot/{older.snapshot_id}/publish/')
        self.assertEqual(resp.status_code, 201)
        body = json.loads(resp.content)
        self.assertEqual(body['source_snapshot_id'], str(older.snapshot_id))
        self.assertEqual(body['frozen']['odds'], 1.80)

    def test_public_endpoints_do_not_expose_unpublished_snapshots(self):
        pred = latest_state(975003)
        snap, _ = record(pred, run_id='runA')

        body = json.loads(self.client.get(f'/api/proof/{pred.fixture_id}/').content)
        self.assertFalse(body['published'])
        self.assertNotIn('pick', body)
        self.assertNotIn(str(snap.snapshot_id), json.dumps(body))

    def test_preview_is_staff_only(self):
        pred = latest_state(975004)
        record(pred, run_id='runA')
        url = f'/api/proof/{pred.fixture_id}/preview/'
        self.assertIn(APIClient().get(url).status_code, (401, 403))


class PublicPerformanceStillClaimBasedTests(TestCase):

    def test_snapshots_alone_do_not_enter_performance(self):
        from core.services.accuracy_calculator import AccuracyCalculator

        pred = latest_state(976001, kickoff_in=-timedelta(days=1))
        record(pred, run_id='runA', generated_at=timezone.now() - timedelta(days=2),
               captured_at=timezone.now() - timedelta(days=2, hours=1))
        pred.was_correct = True
        pred.actual_outcome = 'Over 2.5'
        pred.save()

        self.assertEqual(len(public_universe.resolved_claims()), 0)
        self.assertEqual(
            AccuracyCalculator().get_roi_simulation()['total_bets'], 0)

    def test_published_and_settled_claim_enters_performance(self):
        from core.services.accuracy_calculator import AccuracyCalculator

        pred = latest_state(976002, odds=2.0)
        snap, _ = record(pred, run_id='runA', odds=2.0)
        claim = claim_publication.publish_prediction_claim(snap.snapshot_id)

        # Settlement grades the CLAIM's frozen pick against the real score — it
        # no longer trusts the mutable `was_correct` flag.
        pred.actual_score_home, pred.actual_score_away = 2, 1  # Over 2.5 -> WON
        pred.actual_outcome = 'Over 2.5'
        pred.match_status = 'FT'
        pred.save()
        claim_publication.settle_published_claim(claim)

        self.assertEqual(len(public_universe.resolved_claims()), 1)
        roi = AccuracyCalculator().get_roi_simulation(stake_per_bet=10.0)
        self.assertEqual(roi['total_bets'], 1)
        self.assertEqual(roi['total_profit_loss'], 10.0)


class PublicationQueueTests(TestCase):
    """Staff-only list of publishable snapshots. NOT the gem selector."""

    def _staff(self, name='qroot'):
        root = User.objects.create_superuser(name, f'{name}@e.com', 'pw12345!')
        api = APIClient()
        api.force_authenticate(user=root)
        return api

    def _candidate(self, fixture_id, hours_to_kickoff):
        pred = latest_state(fixture_id, kickoff_in=timedelta(hours=hours_to_kickoff))
        snap, _ = record(pred, run_id=f'run-{fixture_id}')
        return pred, snap

    def test_queue_is_staff_only(self):
        self.assertIn(APIClient().get('/api/proof/queue/').status_code, (401, 403))

    def test_lists_only_publishable_verified_snapshots(self):
        _, good = self._candidate(990001, 12)
        # Legacy: not verified.
        legacy_pred = latest_state(990002, kickoff_in=timedelta(hours=12))
        before = public_universe.PRICING_INTEGRITY_CUTOFF - timedelta(days=3)
        record(legacy_pred, run_id='old', generated_at=before,
               captured_at=before - timedelta(hours=1))
        # Already kicked off.
        started = latest_state(990003, kickoff_in=-timedelta(hours=1))
        record(started, run_id='run-started')

        body = json.loads(self._staff().get('/api/proof/queue/').content)
        ids = {c['snapshot_id'] for c in body['candidates']}
        self.assertEqual(ids, {str(good.snapshot_id)})

    def test_already_published_snapshots_drop_out(self):
        _, snap = self._candidate(990010, 12)
        api = self._staff('qroot2')
        self.assertEqual(len(json.loads(api.get('/api/proof/queue/').content)['candidates']), 1)

        claim_publication.publish_prediction_claim(snap.snapshot_id)
        self.assertEqual(len(json.loads(api.get('/api/proof/queue/').content)['candidates']), 0)

    def test_ordering_prefers_the_6_to_24h_window(self):
        self._candidate(990020, 100)   # further out
        self._candidate(990021, 12)    # ideal
        self._candidate(990022, 36)    # 24-48h
        self._candidate(990023, 3)     # 2-6h

        body = json.loads(self._staff('qroot3').get('/api/proof/queue/').content)
        windows = [c['window'] for c in body['candidates']]
        self.assertTrue(windows[0].startswith('6-24h'))
        self.assertEqual(windows[1], '24-48h')
        self.assertTrue(windows[2].startswith('2-6h'))
        self.assertEqual(windows[3], 'further out')

    def test_each_row_carries_what_the_founder_needs(self):
        self._candidate(990030, 12)
        body = json.loads(self._staff('qroot4').get('/api/proof/queue/').content)
        row = body['candidates'][0]
        for key in ('fixture', 'league', 'kickoff', 'hours_to_kickoff',
                    'market_type', 'predicted_outcome', 'model_score_percent',
                    'odds', 'bookmaker', 'odds_captured_at',
                    'prediction_generated_at', 'model_version',
                    'publication_blockers', 'preview_url', 'publish_endpoint'):
            self.assertIn(key, row)
        self.assertEqual(row['publication_blockers'], [])

    def test_queue_makes_no_performance_claim(self):
        self._candidate(990040, 12)
        body = json.loads(self._staff('qroot5').get('/api/proof/queue/').content)
        # Candidate rows must carry no performance framing at all.
        blob = json.dumps(body['candidates']).lower()
        for banned in ('roi', 'proven', 'edge', 'profit', 'best bet', 'rank',
                       'score_rank', 'confidence_rank'):
            self.assertNotIn(banned, blob, f'queue leaked a performance claim: {banned}')
        # And the payload explicitly disclaims being a ranking.
        self.assertIn('not a statistical score', body['note'].lower())

    def test_queue_never_publishes_anything(self):
        self._candidate(990050, 12)
        self._staff('qroot6').get('/api/proof/queue/')
        self.assertEqual(PublishedClaim.objects.count(), 0)

    def test_queue_reports_odds_freshness(self):
        pred = latest_state(991001, kickoff_in=timedelta(hours=12))
        record(pred, run_id='fresh-1',
               captured_at=timezone.now() - timedelta(hours=2))

        body = json.loads(self._staff('qroot7').get('/api/proof/queue/').content)
        row = body['candidates'][0]
        self.assertIsNotNone(row['odds_age_minutes'])
        self.assertGreater(row['odds_age_minutes'], 60)
        self.assertEqual(row['publication_window'], '6-24h — ideal sharing window')

    def test_a_stale_price_is_no_longer_publishable_at_all(self):
        """This used to be a warning a human could read and override. Auto-
        publication has no human, and it committed a price 150 hours old."""
        pred = latest_state(991009, kickoff_in=timedelta(hours=12))
        record(pred, run_id='stale-1',
               captured_at=timezone.now() - timedelta(hours=20))

        body = json.loads(self._staff('qroot7b').get('/api/proof/queue/').content)
        self.assertEqual(body['candidates'], [])

    def test_queue_flags_when_a_newer_snapshot_exists(self):
        pred = latest_state(991002, kickoff_in=timedelta(hours=12))
        # Coherent timestamps: the price must be captured BEFORE the run that
        # used it, so an older run needs an older capture time too.
        older, _ = record(pred, run_id='r-old',
                          generated_at=timezone.now() - timedelta(hours=3),
                          captured_at=timezone.now() - timedelta(hours=4))
        newer, _ = record(pred, run_id='r-new')

        body = json.loads(self._staff('qroot8').get('/api/proof/queue/').content)
        by_id = {r['snapshot_id']: r for r in body['candidates']}
        self.assertIn(str(older.snapshot_id), by_id,
                      'the older snapshot should still be publishable')
        self.assertIn(str(newer.snapshot_id), by_id)

        self.assertTrue(by_id[str(older.snapshot_id)]['newer_snapshot_exists'])
        self.assertTrue(any('newer snapshot exists' in w
                            for w in by_id[str(older.snapshot_id)]['warnings']))
        self.assertFalse(by_id[str(newer.snapshot_id)]['newer_snapshot_exists'])
        self.assertIsNotNone(by_id[str(older.snapshot_id)]['latest_snapshot_generated_at'])

    def test_fresher_odds_come_first_within_a_window(self):
        stale = latest_state(991010, kickoff_in=timedelta(hours=12))
        record(stale, run_id='s1', captured_at=timezone.now() - timedelta(hours=30))
        fresh = latest_state(991011, kickoff_in=timedelta(hours=13))
        record(fresh, run_id='f1', captured_at=timezone.now() - timedelta(minutes=20))

        body = json.loads(self._staff('qroot9').get('/api/proof/queue/').content)
        first = body['candidates'][0]
        self.assertEqual(first['fixture_id'], 991011)
        self.assertLess(first['odds_age_minutes'], 60)
