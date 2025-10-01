"""
Test script for the suggestion engine.
"""

import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Match, League
from suggestions.suggestion_engine import (
    get_top_recommendations,
    get_recommendation_by_match,
    format_recommendations_for_display
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test the suggestion engine functionality'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of recommendations to show (default: 5)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days ahead to look for matches (default: 7)'
        )
        parser.add_argument(
            '--confidence',
            type=str,
            default='LOW',
            choices=['LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH'],
            help='Minimum confidence level (default: LOW)'
        )
        parser.add_argument(
            '--league',
            type=str,
            help='Filter by league name (partial match)'
        )
        
    def handle(self, *args, **options):
        count = options['count']
        days_ahead = options['days']
        min_confidence = options['confidence']
        league_filter = options['league']
        
        self.stdout.write(self.style.NOTICE(f"Testing suggestion engine"))
        
        # Set date range
        from_date = timezone.now()
        to_date = from_date + timedelta(days=days_ahead)
        
        # Find league IDs if league filter is specified
        league_ids = None
        if league_filter:
            leagues = League.objects.filter(name_en__icontains=league_filter)
            if leagues.exists():
                league_ids = list(leagues.values_list('id', flat=True))
                league_names = list(leagues.values_list('name_en', flat=True))
                self.stdout.write(f"Filtering by leagues: {', '.join(league_names)}")
            else:
                self.stdout.write(self.style.WARNING(f"No leagues found matching '{league_filter}'"))
        
        # Get recommendations
        self.stdout.write(f"Getting top {count} recommendations with confidence >= {min_confidence}")
        self.stdout.write(f"Date range: {from_date.date()} to {to_date.date()}")
        
        recommendations = get_top_recommendations(
            n=count,
            min_confidence=min_confidence,
            league_ids=league_ids,
            date_from=from_date,
            date_to=to_date
        )
        
        # Print formatted recommendations
        formatted_table = format_recommendations_for_display(recommendations)
        self.stdout.write(formatted_table)
        
        # If we have recommendations, show details for the first one
        if recommendations:
            self.stdout.write(self.style.NOTICE("\nDetailed view of top recommendation:"))
            top_rec = recommendations[0]
            
            match_id = top_rec['match_id']
            detailed_rec = get_recommendation_by_match(match_id)
            
            if detailed_rec:
                match_str = f"{detailed_rec['home_team']} vs {detailed_rec['away_team']}"
                self.stdout.write(f"Match: {match_str}")
                self.stdout.write(f"Kickoff: {detailed_rec['kickoff']}")
                self.stdout.write(f"League: {detailed_rec['league']}")
                self.stdout.write(f"Prediction: {detailed_rec['recommended_bet']}")
                self.stdout.write(f"Confidence: {detailed_rec['confidence_level']}")
                
                odds_str = f"{detailed_rec['odds']:.2f}" if detailed_rec['odds'] else "N/A"
                self.stdout.write(f"Odds: {odds_str} ({detailed_rec['bookmaker'] or 'N/A'})")
                
                self.stdout.write(f"Home team score: {detailed_rec['home_team_score']:.2f}")
                self.stdout.write(f"Away team score: {detailed_rec['away_team_score']:.2f}")
                self.stdout.write(f"Source: {detailed_rec['source']}")
                self.stdout.write(f"Generated: {detailed_rec['generated_at']}")
            
        self.stdout.write(self.style.SUCCESS(f"\nFound {len(recommendations)} recommendations"))
        
        # Provide usage examples
        self.stdout.write(self.style.NOTICE("\nUsage examples in code:"))
        self.stdout.write("1. Get top 5 high confidence recommendations:")
        self.stdout.write('   recommendations = get_top_recommendations(n=5, min_confidence="HIGH")')
        
        self.stdout.write("\n2. Get recommendations for a specific league:")
        self.stdout.write('   recommendations = get_top_recommendations(league_ids=[1, 2])')
        
        self.stdout.write("\n3. Get recommendations for next 3 days only:")
        self.stdout.write('   from django.utils import timezone')
        self.stdout.write('   from datetime import timedelta')
        self.stdout.write('   today = timezone.now()')
        self.stdout.write('   in_3_days = today + timedelta(days=3)')
        self.stdout.write('   recommendations = get_top_recommendations(date_from=today, date_to=in_3_days)') 