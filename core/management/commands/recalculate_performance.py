from django.core.management.base import BaseCommand
from core.models import PredictionLog

class Command(BaseCommand):
    help = 'Recalculates performance metrics for all predictions with outcomes'

    def handle(self, *args, **options):
        predictions = PredictionLog.objects.filter(actual_outcome__isnull=False)
        count = predictions.count()
        
        self.stdout.write(f"Found {count} predictions with outcomes. Recalculating...")
        
        updated = 0
        for pred in predictions:
            try:
                # This will run the updated case-insensitive logic
                pred.calculate_performance()
                updated += 1
                if updated % 10 == 0:
                    self.stdout.write(f"Processed {updated}/{count}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing fixture {pred.fixture_id}: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"Successfully recalculated {updated} predictions"))
