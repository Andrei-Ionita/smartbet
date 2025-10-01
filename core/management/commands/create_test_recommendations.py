"""
Command to create test matches, scores, and recommendations for testing purposes.
This version directly inserts test data without complex pipelines.
"""

import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import League, Team, Match, OddsSnapshot, MatchScoreModel

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Create test matches, scores, and recommendations for testing purposes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of test matches to create (default: 5)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=3,
            help='Days in the future for test matches (default: 3)'
        )
        
    def handle(self, *args, **options):
        count = options['count']
        days_ahead = options['days']
        
        self.stdout.write(self.style.NOTICE(f"Creating {count} test matches with their scores and recommendations"))
        
        # Create or get common league and teams
        league, _ = League.objects.get_or_create(
            name_ro="Test League",
            defaults={
                'name_en': "Test League",
                'country': "Test Country",
                'api_id': 123456
            }
        )
        
        now = timezone.now()
        created_matches = []
        
        # Create matches with different betting profiles
        for i in range(count):
            # Create teams
            home_team, _ = Team.objects.get_or_create(
                name_ro=f"Home Team {i+1}",
                defaults={
                    'name_en': f"Home Team {i+1}",
                    'slug': f"home-team-{i+1}"
                }
            )
            
            away_team, _ = Team.objects.get_or_create(
                name_ro=f"Away Team {i+1}",
                defaults={
                    'name_en': f"Away Team {i+1}",
                    'slug': f"away-team-{i+1}"
                }
            )
            
            # Set kickoff time
            kickoff = now + timedelta(days=days_ahead, hours=i)
            
            # Create the match
            match = Match.objects.create(
                league=league,
                home_team=home_team,
                away_team=away_team,
                kickoff=kickoff,
                status="NS",  # Not Started
                api_ref=f"test_match_{i+1}"
            )
            
            self.stdout.write(f"Created match: {match}")
            created_matches.append(match)
            
            # Add odds with different probabilities for different outcomes
            if i % 3 == 0:  # Home team favorite
                odds_home, odds_draw, odds_away = 1.5, 3.5, 6.0
                confidence = "high"
                outcome = "home"
                home_score = 0.7
                away_score = 0.3
                bet = "Home Win"
            elif i % 3 == 1:  # Away team favorite
                odds_home, odds_draw, odds_away = 4.0, 3.5, 1.8
                confidence = "high"
                outcome = "away"
                home_score = 0.3
                away_score = 0.7
                bet = "Away Win"
            else:  # Draw likely
                odds_home, odds_draw, odds_away = 3.5, 2.5, 3.5
                confidence = "medium"
                outcome = "draw"
                home_score = 0.5
                away_score = 0.5
                bet = "Draw"
            
            # Add odds
            odds = OddsSnapshot.objects.create(
                match=match,
                bookmaker="Bet365",
                odds_home=odds_home,
                odds_draw=odds_draw,
                odds_away=odds_away,
                fetched_at=now
            )
            
            self.stdout.write(f"Added odds: H={odds.odds_home}, D={odds.odds_draw}, A={odds.odds_away}")
            
            # Add score directly
            match_score = MatchScoreModel.objects.create(
                match=match,
                fixture_id=match.api_ref,  # Use match.api_ref as fixture_id
                home_team_score=home_score,
                away_team_score=away_score,
                confidence_level=confidence,
                predicted_outcome=outcome,
                recommended_bet=bet,
                source="test_model",
                generated_at=now
            )
            
            self.stdout.write(f"Added score prediction: {outcome} (confidence: {confidence})")
            
        self.stdout.write(self.style.SUCCESS(f"Successfully created {len(created_matches)} test matches with scores"))
        
        # Show how to get recommendations
        self.stdout.write(self.style.NOTICE("\nTo get betting suggestions, run:"))
        self.stdout.write(f"python manage.py get_betting_suggestions --confidence LOW")
        
        # Provide info about the recommendation engine
        self.stdout.write(self.style.NOTICE("\nYou can filter recommendations by:"))
        self.stdout.write("• Confidence level (LOW, MEDIUM, HIGH, VERY_HIGH)")
        self.stdout.write("• League name (--league)")
        self.stdout.write("• Time period (--days)")
        self.stdout.write("• Number of results (--count)")
        self.stdout.write("• Bookmaker (--bookmaker)")
        self.stdout.write("\nExample: python manage.py get_betting_suggestions --confidence HIGH --league Test --days 7 --count 3") 