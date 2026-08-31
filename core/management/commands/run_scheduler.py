
import time
import sys
import logging
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection

from core.services.scheduler_health import SchedulerAlreadyRunning, record_run
from core.services.redaction import redact_exception

# Configure logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# A deployment can replace the worker while the previous cycle still owns the
# database heartbeat. `--run-now` must not overlap it, but a single refusal must
# not turn into the normal 60-minute sleep either. Retry the startup cycle until
# the live run finishes or its 15-minute lease expires.
STARTUP_RETRY_SECONDS = 60

class Command(BaseCommand):
    help = 'Runs a scheduler loop to automatically update predictions and results interactively'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=15,
            help='Interval in minutes between updates (default: 15)'
        )
        parser.add_argument(
            '--run-now',
            action='store_true',
            help='Run tasks immediately on start'
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run one complete scheduler cycle and exit (for Railway Cron)'
        )

    def handle(self, *args, **options):
        interval_minutes = options['interval']
        run_now = options['run_now']
        run_once = options['once']
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('🤖 SMARTBET AUTOMATION SYSTEM'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Interval: Every {interval_minutes} minutes')
        self.stdout.write('Tasks:')
        self.stdout.write('  1. Fetch new recommendations (log_recommendations_from_homepage)')
        self.stdout.write('  2. Update match outcomes (update_results)')
        self.stdout.write('  3. Auto-publish commitments from the versioned feed (auto_publish_claims)')
        self.stdout.write('  4. Settle published claims (settle_published_claims)')
        self.stdout.write('  5. Append signal evidence (capture_signal_evidence)')
        self.stdout.write('  6. Append fixture results (capture_fixture_results)')
        self.stdout.write('  7. Settle private strategy experiments (settle_strategy_lab)')

        if run_once:
            self.stdout.write('Mode: One complete cycle, then exit.\n')
            self.run_startup_cycle(interval_minutes)
            return

        self.stdout.write('\nPress Ctrl+C to stop.\n')

        if run_now:
            self.run_startup_cycle(interval_minutes)

        try:
            while True:
                # Calculate seconds to sleep
                sleep_seconds = interval_minutes * 60

                self.stdout.write(f'Waiting {interval_minutes} minutes until next run...')
                time.sleep(sleep_seconds)

                self.run_tasks(interval_minutes)

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n🛑 Scheduler stopped by user.'))
            sys.exit(0)

    def run_startup_cycle(self, interval_minutes=60):
        """Run once on boot, retrying a temporary overlap instead of sleeping an hour."""
        retry_seconds = min(STARTUP_RETRY_SECONDS, max(1, interval_minutes * 60))
        while not self.run_tasks(interval_minutes):
            self.stdout.write(self.style.WARNING(
                f'Startup cycle deferred; retrying in {retry_seconds} seconds...'
            ))
            time.sleep(retry_seconds)

    def run_tasks(self, interval_minutes=60):
        """Execute all scheduled tasks sequentially, recording a heartbeat.

        The heartbeat exists because settlement is scheduler-only: with no
        public trigger, a dead worker looks exactly like a healthy one with
        nothing to do. It also holds a lock, so a manual run cannot interleave
        with the worker and write contradictory results for the same fixtures.
        """
        self.stdout.write(self.style.SUCCESS(f'\n⏰ Starting scheduled tasks at {datetime.now().strftime("%H:%M:%S")}'))

        # Close old db connections to prevent timeouts in long-running script
        connection.close()

        try:
            # Railway exposes the deployed commit. Recording it makes a stale
            # worker distinguishable from a healthy worker that merely found
            # no new rows, without exposing any credential or provider detail.
            deployed_version = os.environ.get('RAILWAY_GIT_COMMIT_SHA', '')[:40]
            with record_run(
                interval_minutes=interval_minutes,
                version=deployed_version,
            ) as run_id:
                self.stdout.write(f'   run_id={run_id}')
                self._run = run_id
                self._stages = {}
                self.run_all_tasks()
        except SchedulerAlreadyRunning as exc:
            # Not an error: the previous cycle is still working. Skip this tick
            # rather than running the same commands concurrently.
            self.stdout.write(self.style.WARNING(f'⏭️  Skipping run — {exc}'))
            return False

        failed = [k for k, v in (getattr(self, '_stages', None) or {}).items()
                  if v != 'ok']
        if failed:
            self.stdout.write(self.style.WARNING(
                '⚠️  Cycle DEGRADED — stages failed: '
                + ', '.join(failed) + '\n'))
        else:
            self.stdout.write(
                self.style.SUCCESS('✅ All tasks completed successfully.\n'))
        return True

    def run_all_tasks(self):
        # Task 1: Fetch new recommendations
        self.run_task('log_recommendations_from_homepage')

        # Task 2: Update finished results
        self.run_task('update_results', **{'max': 100})

        # Task 3: Automatic public commitment from the versioned strategy feed.
        # Ingestion sets is_recommended=True at the write boundary. Running the
        # retired mark_recommended_predictions command here would apply a second,
        # mixed-scale confidence/EV policy after the versioned decision.
        # Runs ONLY here — after ingestion, before
        # settlement — never manually, so every commitment is attributable to
        # the published policy rather than to a human choice.
        self.run_task('auto_publish_claims')

        # Task 3b: Hand the new claims to an independent timestamp,
        # IMMEDIATELY — while they are still hours from kickoff. Anchoring
        # later (a nightly sweep, say) would prove only that the record
        # existed after the matches were played, which is worthless as
        # evidence of foresight. A calendar outage never blocks publication.
        self.run_task('anchor_published_claims')

        # Task 4: Settle published claims whose fixtures have finished.
        # MUST run after update_results, which is what grades the underlying
        # predictions. Without this the public lifecycle never completes and
        # every published claim stays PENDING forever.
        self.run_task('settle_published_claims')

        # Task 5: Append provider signal evidence. Deliberately after settlement
        # and fully isolated — it writes only SignalObservation rows, publishes
        # nothing, and a failure here must never cost us a settlement.
        self.run_task('capture_signal_evidence')

        # Freeze exactly what the public Homepage and named Strategies are
        # displaying. These broader selections have their own record and never
        # enter or dilute the stricter Gem claim universe.
        self.run_task('publish_public_selections')

        # Task 6: Append provider RESULTS for observed fixtures. Works from the
        # SignalObservation fixture universe, not PredictionLog, so a fixture we
        # observed but never recommended still becomes scoreable.
        self.run_task('capture_fixture_results')

        # Task 7: Grade only fixed-horizon, rule-qualified shadow decisions.
        # This writes private research settlements and cannot publish a Gem.
        self.run_task('settle_strategy_lab')

        # Strategy selections reuse the exact lab settlement, including Asian
        # half-wins, pushes and half-losses. Run only after the lab has graded
        # the latest confirmed fixture-result observations.
        self.run_task('settle_public_selections')

    def run_task(self, command_name, **kwargs):
        """Helper to run a single management command.

        A failing task is logged and the cycle continues — one provider outage
        must not stop settlement of claims whose results already landed. But the
        cycle is then reported as DEGRADED rather than success: an evidence
        outage used to look identical to a clean run, which is how a stage-1
        502 on 2026-08-04 still produced a 'healthy' heartbeat.
        """
        self.stdout.write(f'▶️  Running {command_name}...')
        run = getattr(self, '_run', None)
        try:
            call_command(command_name, **kwargs)
            if run is not None and hasattr(run, 'stage'):
                run.stage(command_name, True)
            self._stages[command_name] = 'ok'
        except Exception as e:
            logger.exception('scheduled task %s failed', command_name)
            # redact_exception, not {e}: a stage that failed inside a provider
            # call carries the resolved request URL in its message, and
            # SportMonks authenticates by query parameter. This line runs on
            # every failure, so it is the most likely place for a token to
            # reach the worker logs.
            self.stdout.write(self.style.ERROR(
                f'❌ Error running {command_name}: {redact_exception(e)}'))
            if run is not None and hasattr(run, 'stage'):
                run.stage(command_name, False)
            self._stages[command_name] = 'failed'
