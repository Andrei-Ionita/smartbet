from django.core.management.base import BaseCommand
from core.models import MatchScoreModel
from django.db.models import Q

class Command(BaseCommand):
    help = 'Clean up predictions with invalid odds or negative/zero EV values'

    def handle(self, *args, **options):
        """
        ✅ Step 3: Clean Old Cached Predictions
        Remove or mark predictions that have invalid odds or non-positive EV
        """
        
        # Find predictions with no odds
        predictions_no_odds = MatchScoreModel.objects.filter(
            match__odds_snapshots__isnull=True
        ).distinct()
        
        # Find predictions with invalid odds (≤1.05) - simplified approach
        predictions_invalid_odds = MatchScoreModel.objects.filter(
            Q(match__odds_snapshots__odds_home__lte=1.05) |
            Q(match__odds_snapshots__odds_away__lte=1.05) |
            Q(match__odds_snapshots__odds_draw__lte=1.05)
        ).distinct()
        
        # Find predictions with stored negative/zero EV
        predictions_bad_ev = MatchScoreModel.objects.filter(
            expected_value__lte=0
        )
        
        no_odds_count = predictions_no_odds.count()
        invalid_odds_count = predictions_invalid_odds.count()
        bad_ev_count = predictions_bad_ev.count()
        
        self.stdout.write(f"🔍 CLEANUP ANALYSIS:")
        self.stdout.write(f"   📊 Predictions with no odds: {no_odds_count}")
        self.stdout.write(f"   📊 Predictions with invalid odds (≤1.05): {invalid_odds_count}")
        self.stdout.write(f"   📊 Predictions with non-positive EV: {bad_ev_count}")
        
        if no_odds_count == 0 and invalid_odds_count == 0 and bad_ev_count == 0:
            self.stdout.write(self.style.SUCCESS("✅ No invalid predictions found - database is clean!"))
            return
        
        # Option to set expected_value to None for invalid predictions
        # This marks them as needing recalculation
        total_updated = 0
        
        if bad_ev_count > 0:
            # Reset EV for predictions with non-positive values
            updated = predictions_bad_ev.update(expected_value=None)
            total_updated += updated
            self.stdout.write(f"🔧 Reset EV for {updated} predictions with non-positive values")
        
        # Log problematic matches for manual review
        if no_odds_count > 0:
            self.stdout.write("❌ Matches with no odds (consider removing):")
            for p in predictions_no_odds[:5]:  # Show first 5
                self.stdout.write(f"   - {p.match.home_team.name_en} vs {p.match.away_team.name_en}")
            if no_odds_count > 5:
                self.stdout.write(f"   ... and {no_odds_count - 5} more")
        
        if invalid_odds_count > 0:
            self.stdout.write("❌ Matches with invalid odds (consider fixing odds data):")
            for p in predictions_invalid_odds[:5]:  # Show first 5
                odds = p.match.odds_snapshots.first()
                if odds:
                    self.stdout.write(f"   - {p.match.home_team.name_en} vs {p.match.away_team.name_en} "
                                    f"(H:{odds.odds_home}, D:{odds.odds_draw}, A:{odds.odds_away})")
            if invalid_odds_count > 5:
                self.stdout.write(f"   ... and {invalid_odds_count - 5} more")
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Cleanup completed - reset EV for {total_updated} predictions')
        ) 