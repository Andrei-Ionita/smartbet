"""
Hardening guarantees for settlement triggering and scheduler observability.

Two unauthenticated write endpoints existed until 2026-08-03:

* ``POST /api/update-fixture-results/`` — no auth at all, csrf_exempt, and the
  PUBLIC /monitoring page fired it on every mount. Each call walked up to 50
  pending predictions, made one SportMonks request per prediction and wrote
  ``actual_outcome``.
* ``POST /api/transparency/update-results/`` — AllowAny, csrf_exempt, ran
  ``ResultUpdaterService`` and returned ``str(e)`` to the caller.

Both are removed. Result recording now has exactly one path:
``run_scheduler → update_results → settle_published_claims``.

These tests exist so neither route can come back unnoticed, and so the
heartbeat that replaced them stays staff-only and honest.
"""
import io
from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import SchedulerHeartbeat
from core.services.scheduler_health import (
    SchedulerAlreadyRunning,
    get_heartbeat,
    record_run,
)

REMOVED_PATHS = [
    '/api/update-fixture-results/',
    '/api/transparency/update-results/',
]


class RemovedSettlementEndpointTests(TestCase):
    """Nobody — anonymous, authenticated or staff — can trigger settlement over HTTP."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('member', 'm@example.com', 'x')
        self.staff = User.objects.create_user('boss', 'b@example.com', 'x', is_staff=True)

    def test_anonymous_post_is_not_found(self):
        for path in REMOVED_PATHS:
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path, {}, format='json').status_code, 404)

    def test_authenticated_non_staff_post_is_not_found(self):
        self.client.force_authenticate(user=self.user)
        for path in REMOVED_PATHS:
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path, {}, format='json').status_code, 404)

    def test_staff_post_is_also_not_found(self):
        """Removed, not merely protected — there is no HTTP trigger at all."""
        self.client.force_authenticate(user=self.staff)
        for path in REMOVED_PATHS:
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path, {}, format='json').status_code, 404)

    def test_get_cannot_trigger_state_changes(self):
        for path in REMOVED_PATHS:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_url_names_no_longer_resolve(self):
        for name in ('update_fixture_results', 'trigger_result_update'):
            with self.subTest(name=name):
                with self.assertRaises(NoReverseMatch):
                    reverse(name)

    def test_view_callables_are_gone(self):
        from core import api_views, transparency_views

        self.assertFalse(hasattr(api_views, 'update_fixture_results'))
        self.assertFalse(hasattr(transparency_views, 'trigger_result_update'))


class SchedulerPipelineIntactTests(TestCase):
    """Removing the endpoints must not change what the scheduler does."""

    def test_scheduler_runs_the_settlement_pipeline_in_order(self):
        from core.management.commands.run_scheduler import Command

        cmd = Command(stdout=io.StringIO(), stderr=io.StringIO())
        with mock.patch(
            'core.management.commands.run_scheduler.call_command'
        ) as call:
            cmd.run_tasks(interval_minutes=60)

        ran = [c.args[0] for c in call.call_args_list]
        self.assertEqual(ran, [
            'log_recommendations_from_homepage',
            'update_results',
            'mark_recommended_predictions',
            'settle_published_claims',
        ])
        # settle_published_claims grades off results that update_results wrote,
        # so the order is a correctness requirement, not a preference.
        self.assertLess(ran.index('update_results'), ran.index('settle_published_claims'))

    def test_a_failing_task_does_not_abort_the_cycle(self):
        """One provider outage must not stop claims whose results already landed."""
        from core.management.commands.run_scheduler import Command

        def flaky(name, *a, **kw):
            if name == 'update_results':
                raise RuntimeError('provider timeout')

        cmd = Command(stdout=io.StringIO(), stderr=io.StringIO())
        with mock.patch(
            'core.management.commands.run_scheduler.call_command', side_effect=flaky
        ) as call:
            cmd.run_tasks(interval_minutes=60)

        ran = [c.args[0] for c in call.call_args_list]
        self.assertIn('settle_published_claims', ran)
        self.assertEqual(get_heartbeat().status, SchedulerHeartbeat.STATUS_SUCCESS)


class SchedulerHeartbeatRecordingTests(TestCase):
    def test_never_run_before_the_first_cycle(self):
        self.assertEqual(get_heartbeat().health(), SchedulerHeartbeat.HEALTH_NEVER_RUN)

    def test_healthy_after_a_successful_run(self):
        with record_run(interval_minutes=60):
            pass

        hb = get_heartbeat()
        self.assertEqual(hb.status, SchedulerHeartbeat.STATUS_SUCCESS)
        self.assertEqual(hb.health(), SchedulerHeartbeat.HEALTH_HEALTHY)
        self.assertIsNotNone(hb.last_success_at)
        self.assertIsNotNone(hb.last_run_completed_at)
        self.assertIsNotNone(hb.last_duration_seconds)
        self.assertEqual(hb.last_failure_code, '')

    def test_failed_after_a_controlled_failure(self):
        with self.assertRaises(ValueError):
            with record_run(interval_minutes=60):
                raise ValueError('boom: secret internal detail')

        hb = get_heartbeat()
        self.assertEqual(hb.status, SchedulerHeartbeat.STATUS_FAILED)
        self.assertEqual(hb.health(), SchedulerHeartbeat.HEALTH_FAILED)
        self.assertIsNotNone(hb.last_failure_at)
        # A short type name, never the message.
        self.assertEqual(hb.last_failure_code, 'ValueError')
        self.assertNotIn('secret internal detail', hb.last_failure_code)

    def test_stale_hourly_execution_reports_delayed(self):
        with record_run(interval_minutes=60):
            pass

        hb = get_heartbeat()
        hb.last_run_started_at = timezone.now() - timedelta(hours=5)
        hb.save(update_fields=['last_run_started_at'])

        self.assertEqual(get_heartbeat().health(), SchedulerHeartbeat.HEALTH_DELAYED)

    def test_one_slow_cycle_does_not_report_delayed(self):
        """Two intervals plus five minutes of grace — no false alarms."""
        with record_run(interval_minutes=60):
            pass

        hb = get_heartbeat()
        hb.last_run_started_at = timezone.now() - timedelta(minutes=90)
        hb.save(update_fields=['last_run_started_at'])

        self.assertEqual(get_heartbeat().health(), SchedulerHeartbeat.HEALTH_HEALTHY)

    def test_counts_are_recorded_as_deltas(self):
        from core.models import PredictionLog

        with record_run(interval_minutes=60):
            PredictionLog.objects.create(
                fixture_id=987654, home_team='A', away_team='B', league='L',
                kickoff=timezone.now(), predicted_outcome='Home', confidence=70.0,
                probability_home=0.7, probability_draw=0.2, probability_away=0.1,
                actual_outcome='Home',
            )

        self.assertEqual(get_heartbeat().results_updated, 1)


class SchedulerConcurrencyTests(TestCase):
    def test_a_second_concurrent_run_is_refused(self):
        """A manual run must not interleave with the worker on the same rows."""
        with record_run(interval_minutes=60):
            with self.assertRaises(SchedulerAlreadyRunning):
                with record_run(interval_minutes=60):
                    self.fail('the inner run should never have started')

    def test_repeated_sequential_runs_are_safe(self):
        for _ in range(3):
            with record_run(interval_minutes=60):
                pass

        hb = get_heartbeat()
        self.assertEqual(hb.status, SchedulerHeartbeat.STATUS_SUCCESS)
        self.assertEqual(SchedulerHeartbeat.objects.count(), 1, 'heartbeat must stay a single row')

    def test_an_abandoned_run_is_taken_over_rather_than_blocking_forever(self):
        """A hard-killed worker must not wedge the lock permanently."""
        with self.assertRaises(ValueError):
            with record_run(interval_minutes=60):
                raise ValueError('killed')

        hb = get_heartbeat()
        hb.status = SchedulerHeartbeat.STATUS_RUNNING
        hb.last_run_started_at = timezone.now() - timedelta(hours=4)
        hb.save(update_fields=['status', 'last_run_started_at'])

        with record_run(interval_minutes=60):
            pass

        self.assertEqual(get_heartbeat().status, SchedulerHeartbeat.STATUS_SUCCESS)


class HeartbeatNeverBlocksSettlementTests(TestCase):
    """Observability must not be able to stop the work it observes.

    The realistic trigger is a fresh deploy: the worker boots with --run-now
    while the web process is still applying migrations, so the heartbeat table
    may not exist yet for the first cycle.
    """

    def test_cycle_still_runs_when_the_heartbeat_cannot_be_written(self):
        ran = []

        with mock.patch(
            'core.services.scheduler_health._begin',
            side_effect=Exception('relation "core_schedulerheartbeat" does not exist'),
        ):
            with record_run(interval_minutes=60):
                ran.append('worked')

        self.assertEqual(ran, ['worked'])

    def test_scheduler_completes_its_pipeline_without_a_heartbeat(self):
        from core.management.commands.run_scheduler import Command

        cmd = Command(stdout=io.StringIO(), stderr=io.StringIO())
        with mock.patch(
            'core.services.scheduler_health._begin', side_effect=Exception('db not ready')
        ):
            with mock.patch(
                'core.management.commands.run_scheduler.call_command'
            ) as call:
                cmd.run_tasks(interval_minutes=60)

        ran = [c.args[0] for c in call.call_args_list]
        self.assertIn('update_results', ran)
        self.assertIn('settle_published_claims', ran)

    def test_a_lock_conflict_still_stops_a_duplicate_run(self):
        """Degrading on DB errors must not swallow the concurrency guard."""
        with record_run(interval_minutes=60):
            with self.assertRaises(SchedulerAlreadyRunning):
                with record_run(interval_minutes=60):
                    self.fail('the inner run should never have started')


class SchedulerHealthEndpointTests(TestCase):
    url = '/api/internal/scheduler-health/'

    def setUp(self):
        self.client = APIClient()
        self.member = User.objects.create_user('member2', 'm2@example.com', 'x')
        self.staff = User.objects.create_user('boss2', 'b2@example.com', 'x', is_staff=True)

    def test_anonymous_is_refused(self):
        self.assertIn(self.client.get(self.url).status_code, (401, 403))

    def test_non_staff_is_refused(self):
        self.client.force_authenticate(user=self.member)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_refusal_leaks_no_scheduler_state(self):
        body = self.client.get(self.url).content.decode().lower()
        for leak in ('last_run', 'results_updated', 'claims_settled', 'run_id', 'healthy'):
            self.assertNotIn(leak, body)

    def test_staff_sees_the_heartbeat(self):
        with record_run(interval_minutes=60):
            pass

        self.client.force_authenticate(user=self.staff)
        resp = self.client.get(self.url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['health'], SchedulerHeartbeat.HEALTH_HEALTHY)
        self.assertEqual(resp.data['interval_minutes'], 60)
        self.assertIn('results_updated', resp.data)

    def test_response_never_carries_a_raw_exception_string(self):
        with self.assertRaises(RuntimeError):
            with record_run(interval_minutes=60):
                raise RuntimeError('psycopg2 connection string password=hunter2')

        self.client.force_authenticate(user=self.staff)
        resp = self.client.get(self.url)

        self.assertEqual(resp.data['health'], SchedulerHeartbeat.HEALTH_FAILED)
        self.assertEqual(resp.data['last_failure_code'], 'RuntimeError')
        body = resp.content.decode()
        self.assertNotIn('hunter2', body)
        self.assertNotIn('psycopg2', body)
        self.assertNotIn('Traceback', body)


class PublicSurfacesUnchangedTests(TestCase):
    """The hardening must not alter what the public can read."""

    def setUp(self):
        self.client = APIClient()

    def test_public_transparency_endpoints_still_serve_anonymously(self):
        for path in (
            '/api/transparency/dashboard/',
            '/api/transparency/recent/',
            '/api/transparency/summary/',
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_public_responses_carry_no_exception_text(self):
        body = self.client.get('/api/transparency/dashboard/').content.decode()
        for leak in ('Traceback', 'psycopg2', 'django.db.utils', 'SPORTMONKS'):
            self.assertNotIn(leak, body)

    def test_scheduler_health_is_not_reachable_without_staff(self):
        """The new internal surface must not become a public one by accident."""
        self.assertNotEqual(self.client.get('/api/internal/scheduler-health/').status_code, 200)
