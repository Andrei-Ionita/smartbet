"""
Django management command to update match results from SportMonks API
"""

from django.core.management.base import BaseCommand
from core.services.result_updater import ResultUpdaterService


class Command(BaseCommand):
    help = 'Update match results from SportMonks API for transparency tracking'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fixture-id',
            type=int,
            help='Update specific fixture by ID'
        )
        parser.add_argument(
            '--max',
            type=int,
            default=100,
            help='Maximum number of predictions to update (default: 100)'
        )
        parser.add_argument(
            '--hours-after',
            type=int,
            default=3,
            help='Hours after kickoff before checking results (default: 3)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🔄 Starting result update process...\n'))
        
        try:
            updater = ResultUpdaterService()
            
            # Update specific fixture
            if options['fixture_id']:
                fixture_id = options['fixture_id']
                self.stdout.write(f"Updating fixture {fixture_id}...")
                
                result = updater.update_single_fixture(fixture_id)
                
                if result['success']:
                    self.stdout.write(self.style.SUCCESS(f"✅ {result['message']}"))
                    self.stdout.write(f"   Predicted: {result['predicted']}")
                    self.stdout.write(f"   Actual: {result['actual']}")
                    self.stdout.write(f"   Correct: {'✅ YES' if result['was_correct'] else '❌ NO'}")
                else:
                    self.stdout.write(self.style.ERROR(f"❌ {result['message']}"))
                
                return
            
            # Update all pending
            self.stdout.write(f"Checking predictions with kickoff > {options['hours_after']} hours ago...\n")
            
            stats = updater.update_all_pending_results(max_predictions=options['max'])
            
            # Display results
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.SUCCESS('📊 UPDATE SUMMARY'))
            self.stdout.write('='*60)
            self.stdout.write(f"Total Checked:        {stats['total_checked']}")
            self.stdout.write(self.style.SUCCESS(f"✅ Updated:           {stats['updated']}"))
            self.stdout.write(f"⏳ Still Pending:     {stats['still_pending']}")
            self.stdout.write(self.style.ERROR(f"❌ Errors:            {stats['errors']}"))
            self.stdout.write('')
            
            if stats['updated'] > 0:
                self.stdout.write(self.style.SUCCESS('🎯 ACCURACY'))
                self.stdout.write(f"Correct:              {stats['correct_predictions']}")
                self.stdout.write(f"Incorrect:            {stats['incorrect_predictions']}")
                self.stdout.write(self.style.SUCCESS(f"Accuracy:             {stats['accuracy']}%"))
            
            self.stdout.write('='*60 + '\n')
            
            if stats['updated'] > 0:
                self.stdout.write(self.style.SUCCESS(
                    f"✅ Successfully updated {stats['updated']} predictions with {stats['accuracy']}% accuracy!"
                ))
            elif stats['still_pending'] > 0:
                self.stdout.write(self.style.WARNING(
                    f"⏳ {stats['still_pending']} matches still in progress. Check back later."
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    "✅ All predictions are up to date!"
                ))
        
        except ValueError as e:
            self.stdout.write(self.style.ERROR(f"❌ Configuration error: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
            raise
