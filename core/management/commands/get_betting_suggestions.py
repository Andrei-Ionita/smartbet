"""
Command to show top betting suggestions from our prediction models.
"""

import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import League
from suggestions.suggestion_engine import (
    get_top_recommendations,
    format_recommendations_for_display
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Show top betting suggestions for upcoming matches'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--count', '-n',
            type=int,
            default=10,
            help='Number of suggestions to display (default: 10)'
        )
        parser.add_argument(
            '--days', '-d',
            type=int,
            default=7,
            help='Number of days ahead to look for matches (default: 7)'
        )
        parser.add_argument(
            '--confidence', '-c',
            type=str,
            default='MEDIUM',
            choices=['LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH'],
            help='Minimum confidence level (default: MEDIUM)'
        )
        parser.add_argument(
            '--league', '-l',
            type=str,
            help='Filter by league name (partial match)'
        )
        parser.add_argument(
            '--bookmaker', '-b',
            type=str,
            default='Bet365',
            help='Bookmaker to use for odds (default: Bet365)'
        )
        
    def handle(self, *args, **options):
        count = options['count']
        days_ahead = options['days']
        min_confidence = options['confidence']
        league_filter = options['league']
        bookmaker = options['bookmaker']
        
        self.stdout.write(self.style.NOTICE(f"Generating top {count} betting suggestions"))
        
        # Set date range
        from_date = timezone.now()
        to_date = from_date + timedelta(days=days_ahead)
        
        # Find league IDs if league filter is specified
        league_ids = None
        if league_filter:
            leagues = League.objects.filter(
                name_en__icontains=league_filter
            ).order_by('name_en')
            
            if leagues.exists():
                league_ids = list(leagues.values_list('id', flat=True))
                league_names = list(leagues.values_list('name_en', flat=True))
                self.stdout.write(f"Filtering by leagues: {', '.join(league_names)}")
            else:
                self.stdout.write(self.style.WARNING(f"No leagues found matching '{league_filter}'"))
                return
        
        # Get recommendations
        self.stdout.write(f"Looking for matches between {from_date.date()} and {to_date.date()}")
        self.stdout.write(f"Minimum confidence level: {min_confidence}")
        
        try:
            recommendations = get_top_recommendations(
                n=count,
                min_confidence=min_confidence,
                league_ids=league_ids,
                date_from=from_date,
                date_to=to_date,
                bookmaker=bookmaker
            )
            
            # Print formatted recommendations
            formatted_table = format_recommendations_for_display(recommendations)
            self.stdout.write(formatted_table)
            
            if recommendations:
                self.stdout.write(self.style.SUCCESS(f"Found {len(recommendations)} betting suggestions"))
            else:
                self.stdout.write(self.style.WARNING("No betting suggestions found matching your criteria"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error getting suggestions: {e}"))
            logger.error(f"Error in get_betting_suggestions command: {e}") 