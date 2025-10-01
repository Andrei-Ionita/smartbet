"""
Set up instructions for scheduling tasks without Django-Q.
"""

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Instructions for setting up scheduled tasks without Django-Q'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up scheduled tasks - Alternative Methods'))
        self.stdout.write('Django-Q is not installed. Here are alternative ways to schedule tasks:')
        
        self.stdout.write('\n1. Using Windows Task Scheduler (Windows):')
        self.stdout.write('   - Open Task Scheduler')
        self.stdout.write('   - Create a new Basic Task')
        self.stdout.write('   - Set it to run every 6 hours')
        self.stdout.write('   - Action: Start a program')
        self.stdout.write('   - Program/script: python')
        self.stdout.write('   - Arguments: manage.py sync_realtime_data --leagues 274 332')
        self.stdout.write('   - Start in: ' + str(self.get_project_dir()))
        
        self.stdout.write('\n2. Using Cron (Linux/macOS):')
        self.stdout.write('   Add this line to crontab:')
        self.stdout.write('   0 */6 * * * cd ' + str(self.get_project_dir()) + 
                         ' && python manage.py sync_realtime_data --leagues 274 332')
        
        self.stdout.write('\n3. Manual scheduling:')
        self.stdout.write('   - Run this command manually when needed:')
        self.stdout.write('     python manage.py sync_realtime_data --leagues 274 332')
        
        self.stdout.write(self.style.WARNING('\nNote: The original setup used Django-Q which is not installed.'))
        self.stdout.write(self.style.WARNING('To use Django-Q instead, install it with: pip install django-q'))
    
    def get_project_dir(self):
        """Get the project directory path."""
        import os
        from django.conf import settings
        return os.path.dirname(settings.BASE_DIR) 