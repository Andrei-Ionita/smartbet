
import time
import sys
import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection

from core.services.scheduler_health import SchedulerAlreadyRunning, record_run

# Configure logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

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

    def handle(self, *args, **options):
        interval_minutes = options['interval']
        run_now = options['run_now']
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('🤖 SMARTBET AUTOMATION SYSTEM'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Interval: Every {interval_minutes} minutes')
        self.stdout.write('Tasks:')
        self.stdout.write('  1. Fetch new recommendations (log_recommendations_from_homepage)')
        self.stdout.write('  2. Update match outcomes (update_results)')
        self.stdout.write('  3. Refresh recommendation status (mark_recommended_predictions)')
        self.stdout.write('\nPress Ctrl+C to stop.\n')

        if run_now:
            self.run_tasks(interval_minutes)

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
            with record_run(interval_minutes=interval_minutes) as run_id:
                self.stdout.write(f'   run_id={run_id}')
                self.run_all_tasks()
        except SchedulerAlreadyRunning as exc:
            # Not an error: the previous cycle is still working. Skip this tick
            # rather than running the same commands concurrently.
            self.stdout.write(self.style.WARNING(f'⏭️  Skipping run — {exc}'))
            return

        self.stdout.write(self.style.SUCCESS('✅ All tasks completed successfully.\n'))

    def run_all_tasks(self):
        # Task 1: Fetch new recommendations
        self.run_task('log_recommendations_from_homepage')

        # Task 2: Update finished results
        self.run_task('update_results', **{'max': 100})

        # Task 3: Refresh recommendation flags
        self.run_task('mark_recommended_predictions', **{'min_confidence': 60.0, 'min_ev': 15.0})

        # Task 4: Settle published claims whose fixtures have finished.
        # MUST run after update_results, which is what grades the underlying
        # predictions. Without this the public lifecycle never completes and
        # every published claim stays PENDING forever.
        self.run_task('settle_published_claims')

        # Task 5: Append provider signal evidence. Deliberately LAST and fully
        # isolated — it writes only SignalObservation rows, publishes nothing,
        # and a failure here must never cost us a settlement.
        self.run_task('capture_signal_evidence')

    def run_task(self, command_name, **kwargs):
        """Helper to run a single management command.

        A failing task is logged and the cycle continues — one provider outage
        must not stop settlement of claims whose results already landed. The
        heartbeat therefore reports 'success' for a cycle that completed with
        an individual task error; per-task failures are in the logs.
        """
        self.stdout.write(f'▶️  Running {command_name}...')
        try:
            call_command(command_name, **kwargs)
        except Exception as e:
            logger.exception('scheduled task %s failed', command_name)
            self.stdout.write(self.style.ERROR(f'❌ Error running {command_name}: {e}'))
