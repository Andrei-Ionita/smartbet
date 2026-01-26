
import time
import sys
import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection

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
            self.run_tasks()

        try:
            while True:
                # Calculate seconds to sleep
                sleep_seconds = interval_minutes * 60
                
                self.stdout.write(f'Waiting {interval_minutes} minutes until next run...')
                time.sleep(sleep_seconds)
                
                self.run_tasks()
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n🛑 Scheduler stopped by user.'))
            sys.exit(0)
    
    def run_tasks(self):
        """Execute all scheduled tasks sequentially"""
        self.stdout.write(self.style.SUCCESS(f'\n⏰ Starting scheduled tasks at {datetime.now().strftime("%H:%M:%S")}'))
        
        # Close old db connections to prevent timeouts in long-running script
        connection.close()
        
        # Task 1: Fetch new recommendations
        self.run_task('log_recommendations_from_homepage')
        
        # Task 2: Update finished results
        self.run_task('update_results', **{'max': 100})
        
        # Task 3: Refresh recommendation flags
        self.run_task('mark_recommended_predictions', **{'min_confidence': 60.0, 'min_ev': 15.0})
        
        self.stdout.write(self.style.SUCCESS('✅ All tasks completed successfully.\n'))

    def run_task(self, command_name, **kwargs):
        """Helper to run a single management command"""
        self.stdout.write(f'▶️  Running {command_name}...')
        try:
            call_command(command_name, **kwargs)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error running {command_name}: {e}'))
