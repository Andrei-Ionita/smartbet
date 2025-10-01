"""
Simple command to list matches in the database.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Match, OddsSnapshot, MatchScoreModel

class Command(BaseCommand):
    help = 'List matches in the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Limit the number of matches to display'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Display all matches'
        )
        
    def handle(self, *args, **options):
        limit = options['limit']
        show_all = options['all']
        
        # Basic counts
        total_matches = Match.objects.count()
        matches_with_odds = Match.objects.filter(odds_snapshots__isnull=False).distinct().count()
        matches_with_scores = Match.objects.filter(match_scores__isnull=False).distinct().count()
        future_matches = Match.objects.filter(kickoff__gte=timezone.now()).count()
        
        self.stdout.write("\n=== Match Statistics ===")
        self.stdout.write(f"Total matches: {total_matches}")
        self.stdout.write(f"Matches with odds: {matches_with_odds}")
        self.stdout.write(f"Matches with scores: {matches_with_scores}")
        self.stdout.write(f"Future matches: {future_matches}")
        
        # Get matches to display
        if show_all:
            matches = Match.objects.all().order_by('-kickoff')
            self.stdout.write(f"\n=== All Matches ({total_matches}) ===")
        else:
            matches = Match.objects.all().order_by('-kickoff')[:limit]
            self.stdout.write(f"\n=== Recent Matches (showing {min(limit, total_matches)} of {total_matches}) ===")
        
        # Display matches
        for match in matches:
            has_odds = OddsSnapshot.objects.filter(match=match).exists()
            has_score = MatchScoreModel.objects.filter(match=match).exists()
            
            odds_str = "✅" if has_odds else "❌"
            score_str = "✅" if has_score else "❌"
            future_str = "🔮" if match.kickoff > timezone.now() else "📅"
            
            self.stdout.write(f"{match.id}: {future_str} {match} ({match.kickoff}) - Odds: {odds_str} Score: {score_str}")
            
            # If verbose, show odds and scores
            if has_odds:
                odds = OddsSnapshot.objects.filter(match=match).order_by('-fetched_at').first()
                self.stdout.write(f"   Odds: Home={odds.odds_home}, Draw={odds.odds_draw}, Away={odds.odds_away}")
                
            if has_score:
                score = MatchScoreModel.objects.filter(match=match).order_by('-generated_at').first()
                self.stdout.write(f"   Score: Home={score.home_team_score:.2f}, Away={score.away_team_score:.2f}, " +
                                 f"Confidence={score.confidence_level}, Outcome={score.predicted_outcome}")
                
        self.stdout.write("\nUse --all to see all matches") 