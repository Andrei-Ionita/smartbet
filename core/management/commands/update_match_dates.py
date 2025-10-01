from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import Match
import random

class Command(BaseCommand):
    help = 'Update some matches with realistic future dates for testing'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # Get all matches
        matches = Match.objects.all()[:20]  # Update first 20 matches
        
        if not matches:
            self.stdout.write(self.style.WARNING("No matches found to update"))
            return
        
        updated_count = 0
        
        for i, match in enumerate(matches):
            # Create dates from now to 7 days in the future
            days_ahead = random.randint(0, 7)
            hours_ahead = random.randint(1, 23)
            minutes_ahead = random.randint(0, 59)
            
            future_date = now + timedelta(
                days=days_ahead,
                hours=hours_ahead,
                minutes=minutes_ahead
            )
            
            # Update the match kickoff time
            match.kickoff = future_date
            match.status = 'NS'  # Not started
            match.save()
            
            updated_count += 1
            
            self.stdout.write(
                f"Updated {match.home_team.name_en} vs {match.away_team.name_en} "
                f"-> {future_date.strftime('%Y-%m-%d %H:%M UTC')}"
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated_count} matches with future dates')
        ) 