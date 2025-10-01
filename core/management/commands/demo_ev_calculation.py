"""
Command to demonstrate Expected Value calculation with test matches.
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from random import uniform

from core.models import Match, Team, League, OddsSnapshot, MatchScoreModel
from predictor.scoring_model import generate_match_scores

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Demonstrate the Expected Value (EV) calculation with test matches'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=3,
            help='Number of test matches to create (default: 3)'
        )
        
    def handle(self, *args, **options):
        count = options['count']
        
        self.stdout.write(self.style.NOTICE(f"Running EV calculation demo with {count} test matches"))
        
        # Clean up any existing test data to avoid conflicts
        self._cleanup_test_data()
        
        # Create/get test data
        test_league = self._get_or_create_league()
        test_teams = self._get_or_create_teams(count * 2)  # Need enough teams for all matches
        test_matches = self._create_test_matches(test_league, test_teams, count)
        
        # Generate match odds with varying values
        self._create_odds_for_matches(test_matches)
        
        # Print odds for reference
        self.stdout.write(self.style.NOTICE("\nMatch odds for reference:"))
        for match in test_matches:
            odds = match.odds_snapshots.latest('fetched_at')
            implied_probabilities = self._calculate_implied_probabilities(odds)
            self.stdout.write(
                f"{match} - {odds.bookmaker}\n"
                f"  Odds: Home={odds.odds_home:.2f}, Draw={odds.odds_draw:.2f}, Away={odds.odds_away:.2f}\n"
                f"  Implied probs: {implied_probabilities['home']:.1%}/{implied_probabilities['draw']:.1%}/{implied_probabilities['away']:.1%}\n"
                f"  Margin: {implied_probabilities['margin']:.1%}"
            )
        
        # Generate scores for these matches
        self.stdout.write(self.style.NOTICE("\nGenerating match scores with EV..."))
        
        scores = generate_match_scores(test_matches)
        
        if not scores:
            self.stdout.write(self.style.ERROR("Failed to generate any scores!"))
            return
        
        # Display the results
        self.stdout.write(self.style.SUCCESS(f"\nGenerated {len(scores)} scores with EV calculations:"))
        self.stdout.write(f"{'Match':<40} {'Outcome':<10} {'Confidence':<10} {'Model Prob':<15} {'Odds':<8} {'EV':<8} {'Value':<10}")
        self.stdout.write("-" * 103)
        
        for score in scores:
            match = next((m for m in test_matches if str(m.id) == score.fixture_id), None)
            match_name = str(match) if match else f"Unknown match ({score.fixture_id})"
            
            # Get the odds used
            odds = match.odds_snapshots.latest('fetched_at')
            
            # Determine outcome and associated odds
            if score.home_team_score > score.away_team_score:
                outcome = "HOME"
                model_prob = score.home_team_score
                odds_value = odds.odds_home
            elif score.away_team_score > score.home_team_score:
                outcome = "AWAY"
                model_prob = score.away_team_score
                odds_value = odds.odds_away
            else:
                outcome = "DRAW"
                model_prob = max(score.home_team_score, score.away_team_score)
                odds_value = odds.odds_draw
            
            # Determine value bet status
            if score.expected_value > 0.05:
                value_status = "VALUE ✅"
            elif score.expected_value < 0:
                value_status = "AVOID ❌"
            else:
                value_status = "FAIR ⚖️"
                    
            self.stdout.write(
                f"{match_name[:40]:<40} "
                f"{outcome:<10} "
                f"{score.confidence_level:<10} "
                f"{model_prob:.4f} ({1/model_prob:.2f})  "
                f"{odds_value:<8.2f} "
                f"{score.expected_value:.4f} "
                f"{value_status:<10}"
            )
            
            # Print additional details
            self.stdout.write(
                f"  Bookmaker: {odds.bookmaker}\n"
                f"  Implied prob: {1/odds_value:.1%}\n"
                f"  Model prob: {model_prob:.1%}\n"
                f"  Edge: {score.expected_value:.1%}"
            )
        
        # Store these scores manually instead of using store_match_scores
        self.stdout.write(self.style.NOTICE("\nStoring scores in database..."))
        
        stored_count = 0
        for score in scores:
            try:
                match = next((m for m in test_matches if str(m.id) == score.fixture_id), None)
                
                if not match:
                    self.stdout.write(self.style.WARNING(f"Match not found for fixture_id: {score.fixture_id}"))
                    continue
                
                # Determine outcome based on scores
                if score.home_team_score > score.away_team_score:
                    outcome = "home"
                    bet = "Home bet"
                elif score.away_team_score > score.home_team_score:
                    outcome = "away"
                    bet = "Away bet"
                else:
                    outcome = "draw"
                    bet = "Draw bet"
                
                # Create the score record
                match_score = MatchScoreModel.objects.create(
                    match=match,
                    fixture_id=score.fixture_id,
                    home_team_score=score.home_team_score,
                    away_team_score=score.away_team_score,
                    confidence_level=score.confidence_level,
                    predicted_outcome=outcome,
                    recommended_bet=bet,
                    source=score.source,
                    generated_at=timezone.now(),  # Use timezone-aware datetime
                    expected_value=score.expected_value
                )
                
                self.stdout.write(self.style.SUCCESS(f"Successfully stored score for {match}"))
                stored_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error storing score: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"Stored {stored_count} out of {len(scores)} scores in the database"))
        
        # Check the stored scores
        self.stdout.write("\nScores in database:")
        for match in test_matches:
            stored_score = match.match_scores.order_by('-generated_at').first()
            if stored_score:
                # Get the odds used
                odds = match.odds_snapshots.latest('fetched_at')
                
                # Determine value bet status
                if stored_score.expected_value > 0.05:
                    value_status = "VALUE BET ✅"
                elif stored_score.expected_value < 0:
                    value_status = "AVOID ❌"
                else:
                    value_status = "FAIR ⚖️"
                        
                self.stdout.write(
                    f"{stored_score.match} - {stored_score.predicted_outcome.upper()} "
                    f"(Confidence: {stored_score.confidence_level})\n"
                    f"  Bookmaker: {odds.bookmaker}\n"
                    f"  EV: {stored_score.expected_value:.4f} {value_status}"
                )
            else:
                self.stdout.write(f"No score found for {match}")
        
        self.stdout.write(self.style.SUCCESS("\nEV calculation demo completed successfully"))
    
    def _cleanup_test_data(self):
        """Clean up any existing test data."""
        # Delete any existing test match scores
        count = MatchScoreModel.objects.filter(source="basic_model_v1").delete()[0]
        if count > 0:
            self.stdout.write(f"Cleaned up {count} existing test match scores")
    
    def _calculate_implied_probabilities(self, odds):
        """Calculate implied probabilities from odds."""
        prob_home = 1 / odds.odds_home
        prob_draw = 1 / odds.odds_draw
        prob_away = 1 / odds.odds_away
        
        # Calculate bookmaker margin
        total_prob = prob_home + prob_draw + prob_away
        margin = total_prob - 1
        
        return {
            'home': prob_home,
            'draw': prob_draw,
            'away': prob_away,
            'margin': margin
        }
        
    def _get_or_create_league(self):
        """Get or create a test league."""
        league, created = League.objects.get_or_create(
            name_en="Test League",
            defaults={
                'name_ro': "Liga Test",
                'country': "Test Country",
            }
        )
        if created:
            self.stdout.write(f"Created test league: {league}")
        else:
            self.stdout.write(f"Using existing league: {league}")
        return league
        
    def _get_or_create_teams(self, count):
        """Get or create test teams."""
        teams = []
        existing_teams = list(Team.objects.filter(name_en__startswith="Test Team").order_by('id')[:count])
        
        # Use existing teams if available
        if len(existing_teams) >= count:
            self.stdout.write(f"Using {count} existing test teams")
            return existing_teams[:count]
        
        # Add any existing teams
        teams.extend(existing_teams)
        
        # Create additional teams as needed
        for i in range(len(teams), count):
            team = Team.objects.create(
                name_en=f"Test Team {i+1}",
                name_ro=f"Echipa Test {i+1}",
                slug=f"test-team-{i+1}"
            )
            teams.append(team)
            self.stdout.write(f"Created test team: {team}")
            
        return teams
        
    def _create_test_matches(self, league, teams, count):
        """Create test matches with the given league and teams."""
        matches = []
        now = timezone.now()
        
        # Create matches
        for i in range(count):
            home_team = teams[i*2]
            away_team = teams[i*2+1]
            
            match = Match.objects.create(
                league=league,
                home_team=home_team,
                away_team=away_team,
                kickoff=now + timedelta(days=1, hours=i),
                status="NS"
            )
            matches.append(match)
            self.stdout.write(f"Created test match: {match} (ID: {match.id})")
            
        return matches
        
    def _create_odds_for_matches(self, matches):
        """Create test odds for the matches."""
        now = timezone.now()
        
        for i, match in enumerate(matches):
            # Create different odds scenarios to demonstrate EV
            if i % 3 == 0:
                # Scenario 1: Value bet - model probability > implied probability
                # Home team is slightly undervalued by the bookmaker
                odds_home = 2.4  # Implied prob: 41.7%
                odds_draw = 3.5  # Implied prob: 28.6% 
                odds_away = 3.3  # Implied prob: 30.3%
                # Our model might think home team has 50% chance to win
                bookmaker = "Pinnacle"
            elif i % 3 == 1:
                # Scenario 2: Fair bet - model probability ≈ implied probability
                odds_home = 1.8  # Implied prob: 55.6%
                odds_draw = 3.8  # Implied prob: 26.3%
                odds_away = 5.0  # Implied prob: 20.0%
                # Our model might think home team has 55% chance to win
                bookmaker = "Bet365"
            else:
                # Scenario 3: Poor value bet - model probability < implied probability
                odds_home = 1.4  # Implied prob: 71.4%
                odds_draw = 4.5  # Implied prob: 22.2%
                odds_away = 9.0  # Implied prob: 11.1%
                # Our model might think home team has only 60% chance to win
                bookmaker = "Pinnacle"
                
            # Add a tiny bit of randomness (not too much to keep the scenarios)
            odds_home = round(odds_home * uniform(0.98, 1.02), 2)
            odds_draw = round(odds_draw * uniform(0.98, 1.02), 2)
            odds_away = round(odds_away * uniform(0.98, 1.02), 2)
            
            # Create odds snapshot
            odds = OddsSnapshot.objects.create(
                match=match,
                bookmaker=bookmaker,
                odds_home=odds_home,
                odds_draw=odds_draw,
                odds_away=odds_away,
                fetched_at=now
            )
            
            # Calculate implied probabilities
            implied_probs = self._calculate_implied_probabilities(odds)
            
            self.stdout.write(
                f"Created odds for {match}: "
                f"Home={odds.odds_home}, Draw={odds.odds_draw}, Away={odds.odds_away} ({bookmaker})"
            ) 