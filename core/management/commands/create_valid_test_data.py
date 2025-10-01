from django.core.management.base import BaseCommand
from core.models import Match, OddsSnapshot, MatchScoreModel
from django.utils import timezone
import random

class Command(BaseCommand):
    help = 'Create valid test data with realistic odds (>1.05) and positive EV values'

    def handle(self, *args, **options):
        """
        Create or update test matches with valid odds and positive EV values
        to demonstrate the enhanced filtering working properly.
        """
        
        updated_count = 0
        now_dt = timezone.now()
        
        # Get future matches that don't have excluded leagues/teams
        EXCLUDED_LEAGUES = ["Test League", "Fake League", "Demo League", "Unknown League"]
        EXCLUDED_TEAMS = ["Team 1", "Team 2", "Team 3", "Team 4", "Team 5", "Test Team", "Fake Team"]
        
        # Get matches that pass basic filtering
        future_matches = Match.objects.filter(
            kickoff__gte=now_dt
        ).exclude(
            league__name_en__in=EXCLUDED_LEAGUES
        ).exclude(
            home_team__name_en__in=EXCLUDED_TEAMS
        ).exclude(
            away_team__name_en__in=EXCLUDED_TEAMS
        )[:5]  # Limit to 5 matches
        
        self.stdout.write(f"🔍 Found {future_matches.count()} eligible future matches")
        
        for match in future_matches:
            # Create or update odds to be realistic (> 1.05)
            odds, created = OddsSnapshot.objects.get_or_create(
                match=match,
                bookmaker="Bet365",
                defaults={
                    'odds_home': round(random.uniform(1.50, 3.50), 2),
                    'odds_draw': round(random.uniform(3.00, 4.50), 2),
                    'odds_away': round(random.uniform(1.80, 4.00), 2),
                    'fetched_at': timezone.now()
                }
            )
            
            if not created:
                # Update existing odds
                odds.odds_home = round(random.uniform(1.50, 3.50), 2)
                odds.odds_draw = round(random.uniform(3.00, 4.50), 2)
                odds.odds_away = round(random.uniform(1.80, 4.00), 2)
                odds.save()
            
            # Create or update prediction with positive EV
            pred, pred_created = MatchScoreModel.objects.get_or_create(
                match=match,
                defaults={
                    'home_team_score': random.uniform(0.2, 0.6),
                    'away_team_score': random.uniform(0.2, 0.6),
                    'predicted_outcome': random.choice(['home', 'away', 'draw']),
                    'confidence_level': random.choice(['Low', 'Medium', 'High']),
                    'source': 'Test Data',
                    'expected_value': round(random.uniform(0.05, 0.30), 4),
                    'generated_at': timezone.now()
                }
            )
            
            if not pred_created:
                # Update existing prediction
                pred.expected_value = round(random.uniform(0.05, 0.30), 4)
                pred.save()
            
            updated_count += 1
            
            self.stdout.write(
                f"✅ Updated: {match.home_team.name_en} vs {match.away_team.name_en} | "
                f"EV: {pred.expected_value*100:.2f}% | "
                f"Odds: H:{odds.odds_home} D:{odds.odds_draw} A:{odds.odds_away}"
            )
        
        if updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Created {updated_count} valid test predictions with realistic odds and positive EV')
            )
            self.stdout.write("🎯 Run the API test now to see valid predictions!")
        else:
            self.stdout.write(
                self.style.WARNING('⚠️ No eligible matches found. Consider checking match data.')
            ) 