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
from rest_framework.test import APIClient

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

    def test_scheduler_publishes_versioned_feed_before_settlement(self):
        """The authenticated feed owns selection; the scheduler must not
        recompute recommendation flags with a second, legacy policy."""
        from pathlib import Path
        source = Path('core/management/commands/run_scheduler.py').read_text(
            encoding='utf-8')
        ingest = source.index("run_task('log_recommendations_from_homepage'")
        auto = source.index("run_task('auto_publish_claims')")
        settle = source.index("run_task('settle_published_claims')")
        self.assertNotIn("run_task('mark_recommended_predictions'", source)
        self.assertTrue(ingest < auto < settle)


class PriceFreshnessTests(TestCase):
    """A price nobody could still get makes the future ROI fiction.

    On 2026-08-08 five of ten live commitments carried prices older than 12
    hours at publication; the worst was 150.7 hours — six days. Every one
    passed the existing gate, because that gate compares the price to its own
    PREDICTION: a six-day-old price beside a six-day-old prediction is
    perfectly coherent, and perfectly worthless as an obtainable quote.
    """

    def test_a_price_stale_at_publication_is_refused(self):
        pred = latest_state(982001, kickoff_in=timedelta(hours=48))
        snap, _ = record(pred, run_id='r1',
                         captured_at=timezone.now() - timedelta(hours=20))

        problems = claim_publication.check_snapshot_publication_eligibility(snap)
        self.assertTrue(any(p.startswith('stale_price_at_publication')
                            for p in problems), problems)

    def test_the_150_hour_case_from_production_is_refused(self):
        pred = latest_state(982002, kickoff_in=timedelta(hours=48))
        snap, _ = record(pred, run_id='r1',
                         generated_at=timezone.now() - timedelta(hours=151),
                         captured_at=timezone.now() - timedelta(hours=152))

        problems = claim_publication.check_snapshot_publication_eligibility(snap)
        self.assertTrue(any(p.startswith('stale_price_at_publication')
                            for p in problems), problems)

    def test_a_fresh_price_still_publishes(self):
        pred = latest_state(982003, kickoff_in=timedelta(hours=48))
        record(pred, run_id='r1',
               captured_at=timezone.now() - timedelta(hours=1))

        run_command()
        self.assertTrue(PublishedClaim.objects.filter(fixture_id=982003).exists())

    def test_auto_publication_skips_the_stale_one(self):
        stale = latest_state(982004, kickoff_in=timedelta(hours=48))
        record(stale, run_id='r-stale',
               captured_at=timezone.now() - timedelta(hours=30))
        fresh = latest_state(982005, kickoff_in=timedelta(hours=48))
        record(fresh, run_id='r-fresh',
               captured_at=timezone.now() - timedelta(minutes=30))

        run_command()

        self.assertFalse(PublishedClaim.objects.filter(fixture_id=982004).exists())
        self.assertTrue(PublishedClaim.objects.filter(fixture_id=982005).exists())

    def test_price_age_is_published_so_nobody_must_subtract_timestamps(self):
        pred = latest_state(982006, kickoff_in=timedelta(hours=48))
        snap, _ = record(pred, run_id='r1',
                         captured_at=timezone.now() - timedelta(hours=3))
        claim = claim_publication.publish_prediction_claim(snap.snapshot_id)

        age = claim_publication.price_age_hours_at_publication(claim)
        self.assertAlmostEqual(age, 3.0, delta=0.2)

        response = APIClient().get(f'/api/proof/claim/{claim.claim_id}/')
        self.assertAlmostEqual(
            response.json()['pick']['price_age_hours_at_publication'],
            3.0, delta=0.2)
