"""
Django management command to set up scheduled ML model retraining using Django-Q.

This command creates a scheduled task for automated model retraining.
Requires Django-Q to be installed and configured.
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta

# Configure logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Set up scheduled ML model retraining using Django-Q'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=str,
            choices=['daily', 'weekly', 'biweekly'],
            default='weekly',
            help='Retraining interval (default: weekly)',
        )
        parser.add_argument(
            '--hour',
            type=int,
            default=2,
            help='Hour to run retraining (0-23, default: 2)',
        )
        parser.add_argument(
            '--remove',
            action='store_true',
            help='Remove existing scheduled retraining tasks',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List existing scheduled tasks',
        )

    def handle(self, *args, **options):
        # Check if Django-Q is available
        try:
            from django_q.models import Schedule
            from django_q.tasks import schedule
        except ImportError:
            raise CommandError(
                "Django-Q is not installed. Please install it with: pip install django-q\n"
                "Or use the cron job approach instead."
            )

        interval = options.get('interval')
        hour = options.get('hour')
        remove_tasks = options.get('remove')
        list_tasks = options.get('list')

        # List existing tasks
        if list_tasks:
            self.stdout.write(self.style.SUCCESS("📋 Existing scheduled retraining tasks:"))
            
            tasks = Schedule.objects.filter(
                func='core.management.commands.retrain_model.Command.handle'
            )
            
            if not tasks.exists():
                self.stdout.write("❌ No scheduled retraining tasks found")
            else:
                for task in tasks:
                    self.stdout.write(f"🔄 Task ID: {task.id}")
                    self.stdout.write(f"   Name: {task.name}")
                    self.stdout.write(f"   Schedule: {task.schedule_type}")
                    self.stdout.write(f"   Next run: {task.next_run}")
                    self.stdout.write(f"   Repeats: {task.repeats}")
                    self.stdout.write("─" * 40)
            return

        # Remove existing tasks
        if remove_tasks:
            self.stdout.write("🗑️ Removing existing scheduled retraining tasks...")
            
            deleted_count = Schedule.objects.filter(
                func='core.management.commands.retrain_model.Command.handle'
            ).delete()[0]
            
            if deleted_count > 0:
                self.stdout.write(self.style.SUCCESS(f"✅ Removed {deleted_count} scheduled task(s)"))
            else:
                self.stdout.write("❌ No scheduled retraining tasks found to remove")
            return

        # Validate hour
        if not 0 <= hour <= 23:
            raise CommandError("Hour must be between 0 and 23")

        # Remove existing tasks before creating new ones
        existing_count = Schedule.objects.filter(
            func='core.management.commands.retrain_model.Command.handle'
        ).delete()[0]
        
        if existing_count > 0:
            self.stdout.write(f"🔄 Removed {existing_count} existing scheduled task(s)")

        # Create new scheduled task
        self.stdout.write(f"⏰ Setting up {interval} retraining at {hour:02d}:00...")

        try:
            # Determine schedule parameters
            if interval == 'daily':
                schedule_type = Schedule.DAILY
                task_name = f"Daily ML Model Retraining ({hour:02d}:00)"
                repeats = -1  # Infinite repeats
            elif interval == 'weekly':
                schedule_type = Schedule.WEEKLY
                task_name = f"Weekly ML Model Retraining (Sunday {hour:02d}:00)"
                repeats = -1  # Infinite repeats
            elif interval == 'biweekly':
                schedule_type = Schedule.WEEKLY
                task_name = f"Biweekly ML Model Retraining (Sunday {hour:02d}:00)"
                repeats = -1  # Infinite repeats
            
            # Calculate next run time
            now = timezone.now()
            if interval == 'daily':
                next_run = now.replace(hour=hour, minute=0, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
            elif interval == 'weekly':
                # Schedule for next Sunday
                days_until_sunday = (6 - now.weekday()) % 7
                if days_until_sunday == 0 and now.hour >= hour:
                    days_until_sunday = 7
                next_run = (now + timedelta(days=days_until_sunday)).replace(
                    hour=hour, minute=0, second=0, microsecond=0
                )
            elif interval == 'biweekly':
                # Schedule for next Sunday, but only every other week
                days_until_sunday = (6 - now.weekday()) % 7
                if days_until_sunday == 0 and now.hour >= hour:
                    days_until_sunday = 7
                next_run = (now + timedelta(days=days_until_sunday)).replace(
                    hour=hour, minute=0, second=0, microsecond=0
                )

            # Create the scheduled task
            task = Schedule.objects.create(
                name=task_name,
                func='django.core.management.call_command',
                args="'retrain_model', '--save-report', '--months', '24', '--cv', '5'",
                schedule_type=schedule_type,
                next_run=next_run,
                repeats=repeats
            )

            self.stdout.write(self.style.SUCCESS(f"✅ Scheduled task created successfully!"))
            self.stdout.write(f"📋 Task ID: {task.id}")
            self.stdout.write(f"📅 Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            self.stdout.write(f"🔄 Interval: {interval}")
            
            # Additional setup instructions
            self.stdout.write(self.style.WARNING("\n⚠️ Important Setup Notes:"))
            self.stdout.write("1. Make sure Django-Q cluster is running:")
            self.stdout.write("   python manage.py qcluster")
            self.stdout.write("2. Ensure your Django-Q configuration is correct in settings.py")
            self.stdout.write("3. Monitor the Django-Q admin interface for task execution")
            
            # Show how to start the cluster
            self.stdout.write(self.style.SUCCESS("\n🚀 To start the Django-Q cluster:"))
            self.stdout.write("python manage.py qcluster")
            
        except Exception as e:
            raise CommandError(f"Failed to create scheduled task: {e}")

        self.stdout.write(self.style.SUCCESS("\n🎉 Scheduled retraining setup completed!")) 