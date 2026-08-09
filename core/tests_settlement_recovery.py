"""
Settlement must not be able to freeze itself shut.

On 2026-08-09 every past-kickoff prediction — all 17, Cardiff included, which
had kicked off the night before — carried `match_status='archived'`. The
pending query excluded archived rows outright, so `update_results` reported
"Found 0 predictions awaiting results" and `settle_published_claims` reported
"16 awaiting a provider result", cycle after cycle. Both lines read like
patience. The verified record was in fact structurally frozen at zero, and the
entire forward-testing proposition with it.

Two independent faults had to line up:

  1. the provider request used comma-separated includes, which SportMonks v3
     rejects, so every fetch failed; and
  2. a failed fetch was recorded as PERMANENT archival, with no regard for
     how recent the fixture was.

These tests pin both, plus the recovery path for rows already poisoned.
"""
from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from core.models import PredictionLog
from core.services.result_updater import ResultUpdaterService
from core.tests_claim_publication import latest_state


def past_fixture(fixture_id, *, hours_ago=12, status=None, outcome=None):
    pred = latest_state(fixture_id, kickoff_in=-timedelta(hours=hours_ago))
    PredictionLog.objects.filter(pk=pred.pk).update(
        match_status=status, actual_outcome=outcome)
    return PredictionLog.objects.get(pk=pred.pk)


class PendingQueryTests(TestCase):

    def test_a_recent_archived_row_is_still_retried(self):
        """THE freeze. An archived flag must never be permanent inside the
        lookback window, or one bad provider call kills settlement forever."""
        past_fixture(970101, hours_ago=12, status='archived')

        pending = ResultUpdaterService().get_pending_predictions()

        self.assertEqual([p.fixture_id for p in pending], [970101])

    def test_an_ungraded_recent_row_is_picked_up(self):
        past_fixture(970102, hours_ago=6)
        pending = ResultUpdaterService().get_pending_predictions()
        self.assertIn(970102, [p.fixture_id for p in pending])

    def test_a_graded_row_is_left_alone(self):
        past_fixture(970103, hours_ago=6, outcome='Home')
        pending = ResultUpdaterService().get_pending_predictions()
        self.assertNotIn(970103, [p.fixture_id for p in pending])

    def test_a_fixture_beyond_the_window_is_not_retried_forever(self):
        past_fixture(970104, hours_ago=24 * (ResultUpdaterService.MAX_LOOKBACK_DAYS + 2))
        pending = ResultUpdaterService().get_pending_predictions()
        self.assertNotIn(970104, [p.fixture_id for p in pending])

    def test_a_match_that_just_kicked_off_is_not_checked_yet(self):
        past_fixture(970105, hours_ago=1)
        pending = ResultUpdaterService().get_pending_predictions()
        self.assertNotIn(970105, [p.fixture_id for p in pending])


class ArchivingPolicyTests(TestCase):

    def _run_with_404(self, fixture_id):
        updater = ResultUpdaterService()
        with mock.patch.object(updater, 'fetch_fixture_result',
                               return_value=ResultUpdaterService.ARCHIVED_RESULT):
            return updater.update_all_pending_results()

    def test_a_recent_404_does_not_archive(self):
        """A fixture that kicked off yesterday cannot have aged out of the
        provider's data. Treat the 404 as transient."""
        past_fixture(970110, hours_ago=12)

        stats = self._run_with_404(970110)

        self.assertEqual(
            PredictionLog.objects.get(fixture_id=970110).match_status, None)
        self.assertEqual(stats['archived'], 0)
        self.assertEqual(stats['still_pending'], 1)

    def test_a_genuinely_old_404_is_archived(self):
        old = 24 * (ResultUpdaterService.MAX_LOOKBACK_DAYS + 1)
        pred = past_fixture(970111, hours_ago=old)
        # Force it into the pending set so the archive branch is reachable.
        updater = ResultUpdaterService()
        with mock.patch.object(updater, 'get_pending_predictions',
                               return_value=[pred]), \
             mock.patch.object(updater, 'fetch_fixture_result',
                               return_value=ResultUpdaterService.ARCHIVED_RESULT):
            stats = updater.update_all_pending_results()

        self.assertEqual(
            PredictionLog.objects.get(fixture_id=970111).match_status, 'archived')
        self.assertEqual(stats['archived'], 1)


class ProviderRequestTests(TestCase):

    def test_includes_are_semicolon_separated(self):
        """SportMonks v3 rejects comma-separated includes. Sending commas is
        what made every fetch fail in the first place."""
        from pathlib import Path
        src = Path('core/services/result_updater.py').read_text(encoding='utf-8')
        self.assertIn("'include': 'scores;state;participants'", src)
        self.assertNotIn("'include': 'scores,state,participants'", src)

    def test_it_matches_the_proven_reader(self):
        """The evidence path has always used the correct syntax; the two must
        not diverge again."""
        from pathlib import Path
        evidence = Path('core/services/result_evidence.py').read_text(encoding='utf-8')
        self.assertIn('include=participants;scores;league;state', evidence)


class UnarchiveCommandTests(TestCase):

    def run_cmd(self, **kwargs):
        out = StringIO()
        call_command('unarchive_recent_predictions', stdout=out, **kwargs)
        return out.getvalue()

    def test_clears_recent_wrongly_archived_rows(self):
        past_fixture(970120, hours_ago=12, status='archived')

        out = self.run_cmd()

        self.assertIn('cleared 1', out)
        self.assertIsNone(
            PredictionLog.objects.get(fixture_id=970120).match_status)

    def test_leaves_genuinely_old_rows_flagged(self):
        old = 24 * (ResultUpdaterService.MAX_LOOKBACK_DAYS + 3)
        past_fixture(970121, hours_ago=old, status='archived')

        self.run_cmd()

        self.assertEqual(
            PredictionLog.objects.get(fixture_id=970121).match_status, 'archived')

    def test_never_touches_a_graded_row(self):
        past_fixture(970122, hours_ago=12, status='archived', outcome='Home')

        self.run_cmd()

        self.assertEqual(
            PredictionLog.objects.get(fixture_id=970122).match_status, 'archived')

    def test_dry_run_writes_nothing(self):
        past_fixture(970123, hours_ago=12, status='archived')

        out = self.run_cmd(dry_run=True)

        self.assertIn('would clear 1', out)
        self.assertEqual(
            PredictionLog.objects.get(fixture_id=970123).match_status, 'archived')
