"""
Independent anchoring of published claims.

The property under test is not "we wrote a row". It is: a stranger holding
nothing but our PUBLIC claims API can rebuild the exact manifest, recompute
the digest, and find it equal to the digest inside an externally timestamped
proof. If that fails, the anchoring is decoration.

Calendar submission is stubbed — these tests must never depend on the network,
and OpenTimestamps' own serialization is not ours to test.
"""
import hashlib
from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import ClaimAnchor, ClaimAnchorEntry, PublishedClaim
from core.services import claim_anchoring, claim_publication
from core.tests_claim_publication import latest_state, record

FAKE_PROOF = b'\x00OpenTimestamps\x00\x00Proof\x00fake-for-tests'


def publish(fixture_id, **kwargs):
    pred = latest_state(fixture_id, **kwargs)
    snap, _ = record(pred, run_id=f'run-{fixture_id}')
    return claim_publication.publish_prediction_claim(snap.snapshot_id)


def stub_stamp(digest_hex, calendars=None, timeout=None):
    return FAKE_PROOF, ['https://a.pool.opentimestamps.org']


class ManifestTests(TestCase):
    """The manifest must be reproducible from public data alone."""

    def test_manifest_is_sorted_and_order_independent(self):
        pairs = [('b-id', 'hash-b'), ('a-id', 'hash-a')]
        forward = claim_anchoring.build_manifest(pairs)
        backward = claim_anchoring.build_manifest(list(reversed(pairs)))
        self.assertEqual(forward, backward)
        self.assertIn('a-id:hash-a\nb-id:hash-b', forward)

    def test_manifest_is_versioned_and_newline_terminated(self):
        manifest = claim_anchoring.build_manifest([('x', 'y')])
        self.assertTrue(manifest.startswith('betglitch-claim-anchor-v1\n'))
        self.assertTrue(manifest.endswith('\n'))

    def test_digest_is_plain_sha256_of_the_manifest_bytes(self):
        manifest = claim_anchoring.build_manifest([('x', 'y')])
        self.assertEqual(
            claim_anchoring.compute_digest(manifest),
            hashlib.sha256(manifest.encode('utf-8')).hexdigest(),
        )

    def test_a_stranger_can_rebuild_the_digest_from_the_public_api(self):
        """THE test. Public API in, anchored digest out."""
        publish(991001)
        publish(991002)
        with mock.patch.object(claim_anchoring, 'stamp_digest', stub_stamp):
            anchor = claim_anchoring.anchor_pending_claims()

        # Everything below uses ONLY what /api/proof/claims/ serves.
        client = APIClient()
        response = client.get('/api/proof/claims/?limit=200')
        self.assertEqual(response.status_code, 200)
        pairs = [(c['claim_id'], c['claim_hash']) for c in response.json()['claims']]

        rebuilt = claim_anchoring.build_manifest(pairs)
        self.assertEqual(claim_anchoring.compute_digest(rebuilt), anchor.digest)


class AnchoringTests(TestCase):

    def test_anchors_every_unanchored_claim_in_one_batch(self):
        publish(991010)
        publish(991011)
        with mock.patch.object(claim_anchoring, 'stamp_digest', stub_stamp):
            anchor = claim_anchoring.anchor_pending_claims()

        self.assertEqual(anchor.claim_count, 2)
        self.assertEqual(anchor.status, ClaimAnchor.STATUS_PENDING)
        self.assertEqual(ClaimAnchorEntry.objects.count(), 2)

    def test_records_the_hash_as_anchored_alongside_the_claim(self):
        claim = publish(991012)
        with mock.patch.object(claim_anchoring, 'stamp_digest', stub_stamp):
            claim_anchoring.anchor_pending_claims()
        entry = ClaimAnchorEntry.objects.get(claim=claim)
        self.assertEqual(entry.claim_hash, claim.claim_hash)

    def test_a_claim_is_never_anchored_twice(self):
        publish(991013)
        with mock.patch.object(claim_anchoring, 'stamp_digest', stub_stamp):
            claim_anchoring.anchor_pending_claims()
            second = claim_anchoring.anchor_pending_claims()
        self.assertIsNone(second)
        self.assertEqual(ClaimAnchorEntry.objects.count(), 1)

    def test_new_claims_get_their_own_anchor(self):
        publish(991014)
        with mock.patch.object(claim_anchoring, 'stamp_digest', stub_stamp):
            claim_anchoring.anchor_pending_claims()
            publish(991015)
            second = claim_anchoring.anchor_pending_claims()

        self.assertIsNotNone(second)
        self.assertEqual(second.claim_count, 1)
        self.assertEqual(ClaimAnchor.objects.count(), 2)

    def test_nothing_to_anchor_returns_none(self):
        with mock.patch.object(claim_anchoring, 'stamp_digest', stub_stamp):
            self.assertIsNone(claim_anchoring.anchor_pending_claims())

    def test_a_total_calendar_outage_leaves_claims_unanchored_not_faked(self):
        """No calendar, no proof. Never a row claiming a timestamp we lack."""
        publish(991016)

        def refuse(*a, **kw):
            raise claim_anchoring.AnchoringUnavailable('all calendars down')

        with mock.patch.object(claim_anchoring, 'stamp_digest', refuse):
            with self.assertRaises(claim_anchoring.AnchoringUnavailable):
                claim_anchoring.anchor_pending_claims()

        self.assertEqual(ClaimAnchor.objects.count(), 0)
        self.assertEqual(claim_anchoring.unanchored_claims().count(), 1)


class AnchorCommandTests(TestCase):

    def run_cmd(self, **kwargs):
        out = StringIO()
        call_command('anchor_published_claims', stdout=out, **kwargs)
        return out.getvalue()

    def test_command_anchors_pending_claims(self):
        publish(991020)
        with mock.patch.object(claim_anchoring, 'stamp_digest', stub_stamp):
            out = self.run_cmd()
        self.assertIn('anchored 1 claims', out)
        self.assertEqual(ClaimAnchor.objects.count(), 1)

    def test_dry_run_contacts_nothing_and_writes_nothing(self):
        publish(991021)
        with mock.patch.object(claim_anchoring, 'stamp_digest') as stamp:
            out = self.run_cmd(dry_run=True)
            stamp.assert_not_called()
        self.assertIn('would anchor 1 claims', out)
        self.assertEqual(ClaimAnchor.objects.count(), 0)

    def test_calendar_outage_is_reported_not_raised(self):
        """A scheduler stage must not die because a calendar is down."""
        publish(991022)

        def refuse(*a, **kw):
            raise claim_anchoring.AnchoringUnavailable('down')

        with mock.patch.object(claim_anchoring, 'stamp_digest', refuse):
            out = self.run_cmd()
        self.assertIn('anchoring unavailable', out)

    def test_anchoring_runs_immediately_after_publication(self):
        """Timing IS the proof. A nightly anchor would date the record after
        kickoff and demonstrate nothing about foresight."""
        from pathlib import Path
        src = Path('core/management/commands/run_scheduler.py').read_text(
            encoding='utf-8')
        publish_at = src.index("run_task('auto_publish_claims')")
        anchor_at = src.index("run_task('anchor_published_claims')")
        settle_at = src.index("run_task('settle_published_claims')")
        self.assertTrue(publish_at < anchor_at < settle_at)


class AnchorApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        publish(991030)
        with mock.patch.object(claim_anchoring, 'stamp_digest', stub_stamp):
            self.anchor = claim_anchoring.anchor_pending_claims()

    def test_list_is_public_and_explains_how_to_verify(self):
        response = self.client.get('/api/proof/anchors/')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['count'], 1)
        self.assertIn('ots verify', body['how_to_verify'])
        self.assertEqual(body['anchors'][0]['digest'], self.anchor.digest)

    def test_detail_serves_the_exact_manifest_that_was_hashed(self):
        response = self.client.get(f'/api/proof/anchors/{self.anchor.digest}/')
        self.assertEqual(response.status_code, 200)
        manifest = response.json()['anchor']['manifest']
        self.assertEqual(
            claim_anchoring.compute_digest(manifest), self.anchor.digest)

    def test_proof_endpoint_serves_the_raw_ots_bytes(self):
        response = self.client.get(
            f'/api/proof/anchors/{self.anchor.digest}/proof/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, FAKE_PROOF)
        self.assertIn('.ots', response['Content-Disposition'])

    def test_unknown_digest_is_404_not_a_server_error(self):
        self.assertEqual(self.client.get('/api/proof/anchors/deadbeef/').status_code, 404)
        self.assertEqual(
            self.client.get('/api/proof/anchors/deadbeef/proof/').status_code, 404)
