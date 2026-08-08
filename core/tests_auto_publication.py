"""
Automatic public commitment — policy v1.

The command must be a thin loop over the SAME gate the manual workflow uses
(`publish_prediction_claim`), plus exactly three policy criteria of its own:
a minimum kickoff lead, one non-superseded commitment per fixture, and
latest-snapshot-per-fixture. Anything beyond that would be an invented
selection rule the public policy does not state.
"""
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from core.models import PredictionLog, PublishedClaim
from core.services import claim_publication
from core.tests_claim_publication import latest_state, record


def run_command(**kwargs):
    out = StringIO()
    call_command('auto_publish_claims', stdout=out, **kwargs)
    return out.getvalue()


class AutoPublicationTests(TestCase):

    def test_publishes_an_eligible_snapshot_with_enough_lead(self):
        pred = latest_state(980001, kickoff_in=timedelta(hours=48))
        snap, _ = record(pred, run_id='runA')

        out = run_command()

        claim = PublishedClaim.objects.get(fixture_id=980001)
        self.assertEqual(claim.snapshot_id, snap.snapshot_id)
        self.assertEqual(claim.predicted_outcome, snap.predicted_outcome)
        self.assertIn('committed 1', out)

    def test_skips_a_fixture_inside_the_kickoff_lead_window(self):
        pred = latest_state(980002, kickoff_in=timedelta(hours=3))
        record(pred, run_id='runA')

        run_command()

        self.assertFalse(
            PublishedClaim.objects.filter(fixture_id=980002).exists())

    def test_lead_window_is_configurable(self):
        pred = latest_state(980003, kickoff_in=timedelta(hours=3))
        record(pred, run_id='runA')

        run_command(min_lead_hours=2.0)

        self.assertTrue(
            PublishedClaim.objects.filter(fixture_id=980003).exists())

    def test_one_commitment_per_fixture_across_hourly_runs(self):
        """The dedup criterion. Hourly runs append a snapshot per run; only
        the FIRST commitment for a fixture may enter the record."""
        pred = latest_state(980004, kickoff_in=timedelta(hours=48))
        record(pred, run_id='runA')
        run_command()

        # An hour later, a new run appends a fresh snapshot for the SAME
        # fixture. It must not become a second commitment.
        record(pred, run_id='runB', odds=1.70)
        run_command()

        self.assertEqual(
            PublishedClaim.objects.filter(fixture_id=980004).count(), 1)

    def test_rerunning_is_idempotent(self):
        pred = latest_state(980005, kickoff_in=timedelta(hours=48))
        record(pred, run_id='runA')

        run_command()
        run_command()

        self.assertEqual(
            PublishedClaim.objects.filter(fixture_id=980005).count(), 1)

    def test_only_the_newest_snapshot_per_fixture_is_considered(self):
        """An older ELIGIBLE snapshot must never be committed over a newer
        signal state whose own snapshot is ineligible — the fixture waits."""
        pred = latest_state(980006, kickoff_in=timedelta(hours=48))
        old = timezone.now() - timedelta(hours=2)
        record(pred, run_id='runOld', generated_at=old,
               captured_at=old - timedelta(minutes=30))
        # Newest snapshot: incomplete provenance -> ineligible.
        record(pred, run_id='runNew', prov='incomplete')

        run_command()

        self.assertFalse(
            PublishedClaim.objects.filter(fixture_id=980006).exists())

    def test_ineligible_snapshots_are_never_committed(self):
        pred = latest_state(980007, kickoff_in=timedelta(hours=48))
        record(pred, run_id='runA', prov='none')  # no price at all

        run_command()

        self.assertFalse(
            PublishedClaim.objects.filter(fixture_id=980007).exists())

    def test_unrecommended_snapshots_are_never_committed(self):
        pred = latest_state(980008, kickoff_in=timedelta(hours=48))
        record(pred, run_id='runA', is_recommended=False)

        run_command()

        self.assertFalse(
            PublishedClaim.objects.filter(fixture_id=980008).exists())

    def test_dry_run_writes_nothing(self):
        pred = latest_state(980009, kickoff_in=timedelta(hours=48))
        record(pred, run_id='runA')

        out = run_command(dry_run=True)

        self.assertIn('would commit 1', out)
        self.assertFalse(PublishedClaim.objects.exists())

    def test_uses_the_shared_gate_not_a_private_one(self):
        """A snapshot the shared gate refuses (kickoff passed between the
        pre-filter and publication) must be refused here too — the command
        owns no eligibility logic."""
        pred = latest_state(980010, kickoff_in=timedelta(hours=48))
        snap, _ = record(pred, run_id='runA')

        problems = claim_publication.check_snapshot_publication_eligibility(
            snap, now=snap.kickoff + timedelta(minutes=1))
        self.assertIn('fixture_already_started', problems)

    def test_manual_and_auto_commitments_share_one_identity_rule(self):
        """Publishing the same snapshot manually first makes the auto pass a
        clean no-op, not a duplicate or an error."""
        pred = latest_state(980011, kickoff_in=timedelta(hours=48))
        snap, _ = record(pred, run_id='runA')
        claim_publication.publish_prediction_claim(snap.snapshot_id)

        out = run_command()

        self.assertEqual(
            PublishedClaim.objects.filter(fixture_id=980011).count(), 1)
        self.assertIn('1 fixtures already hold', out)

    def test_scheduler_runs_the_stage_after_marking_recommendations(self):
        """The stage order is part of the policy: commitments are computed
        from CURRENT recommendation flags, and settlement still runs after."""
        from pathlib import Path
        source = Path('core/management/commands/run_scheduler.py').read_text(
            encoding='utf-8')
        mark = source.index("run_task('mark_recommended_predictions'")
        auto = source.index("run_task('auto_publish_claims')")
        settle = source.index("run_task('settle_published_claims')")
        self.assertTrue(mark < auto < settle)
