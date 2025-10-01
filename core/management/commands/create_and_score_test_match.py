"""
Command to create test matches and then generate and store scores for them.
"""

import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Match, Team, League, OddsSnapshot
from predictor.scoring_model import generate_match_scores, store_match_scores

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Create test matches and generate scores for them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=3,
            help='Number of test matches to create (default: 3)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Days in the future for the test matches (default: 1)'
        )
        
    def handle(self, *args, **options):
        count = options['count']
        days_ahead = options['days']
        
        self.stdout.write(self.style.NOTICE(f"Creating {count} test matches and generating scores"))
        
        # Create test matches
        created_matches = self._create_test_matches(count, days_ahead)
        
        if not created_matches:
            self.stdout.write(self.style.ERROR("Failed to create any test matches"))
            return
            
        self.stdout.write(self.style.SUCCESS(f"Created {len(created_matches)} test matches"))
        
        # Generate scores
        self.stdout.write(self.style.NOTICE("\nGenerating scores..."))
        scores = generate_match_scores(created_matches)
        
        if not scores:
            self.stdout.write(self.style.ERROR("No scores were generated!"))
            return
            
        # Print generated scores
        self.stdout.write(self.style.NOTICE("\nGenerated scores:"))
        for i, score in enumerate(scores):
            match = next((m for m in created_matches if m.api_ref == score.fixture_id or str(m.id) == score.fixture_id), None)
            match_str = str(match) if match else f"Unknown match ({score.fixture_id})"
            
            self.stdout.write(f"{i+1}. {match_str}")
            self.stdout.write(f"   Home Score: {score.home_team_score:.2f}")
            self.stdout.write(f"   Away Score: {score.away_team_score:.2f}")
            self.stdout.write(f"   Confidence: {score.confidence_level}")
            
            # Determine outcome
            if score.home_team_score > score.away_team_score:
                outcome = "HOME WIN"
            elif score.away_team_score > score.home_team_score:
                outcome = "AWAY WIN"
            else:
                outcome = "DRAW"
            self.stdout.write(f"   Predicted Outcome: {outcome}")
        
        # Store scores
        self.stdout.write(self.style.NOTICE("\nStoring scores in database..."))
        store_match_scores(scores)
        
        # Try to update the scores
        self.stdout.write(self.style.NOTICE("\nUpdating scores (testing duplicate handling)..."))
        store_match_scores(scores)
        
        self.stdout.write(self.style.SUCCESS("\nTest completed successfully!"))
    
    def _create_test_matches(self, count, days_ahead):
        """Create test matches for scoring."""
        now = timezone.now()
        created_matches = []
        
        # Create or get common league and teams
        league, _ = League.objects.get_or_create(
            name_ro="Test League",
            defaults={
                'name_en': "Test League",
                'country': "Test Country"
            }
        )
        
        home_teams = []
        away_teams = []
        
        for i in range(count):
            home_team, _ = Team.objects.get_or_create(
                name_ro=f"Home Team {i+1}",
                defaults={
                    'name_en': f"Home Team {i+1}",
                    'slug': f"home-team-{i+1}"
                }
            )
            home_teams.append(home_team)
            
            away_team, _ = Team.objects.get_or_create(
                name_ro=f"Away Team {i+1}",
                defaults={
                    'name_en': f"Away Team {i+1}",
                    'slug': f"away-team-{i+1}"
                }
            )
            away_teams.append(away_team)
        
        # Create matches with different kickoff times
        for i in range(count):
            kickoff = now + timedelta(days=days_ahead, hours=i)
            api_ref = f"test_match_{int(now.timestamp())}_{i+1}"
            
            try:
                match = Match.objects.create(
                    league=league,
                    home_team=home_teams[i],
                    away_team=away_teams[i],
                    kickoff=kickoff,
                    status="NS",  # Not Started
                    api_ref=api_ref
                )
                
                self.stdout.write(f"Created match: {match}")
                
                # Add odds with different probabilities for different outcomes
                if i % 3 == 0:  # Home team favorite
                    odds_home, odds_draw, odds_away = 1.5, 3.5, 6.0
                elif i % 3 == 1:  # Away team favorite
                    odds_home, odds_draw, odds_away = 4.0, 3.5, 1.8
                else:  # Draw likely
                    odds_home, odds_draw, odds_away = 3.5, 2.5, 3.5
                
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
                created_matches.append(match)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating match {i+1}: {e}"))
                
        return created_matches 