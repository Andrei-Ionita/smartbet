"""
Management command to fetch odds from Pinnacle Sports API.
"""

import logging
from typing import List, Optional
from django.core.management.base import BaseCommand, CommandError

from odds.fetch_pinnacle import fetch_pinnacle_odds

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fetch and store odds from Pinnacle Sports API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--leagues',
            dest='league_ids',
            nargs='+',
            type=int,
            help='IDs of leagues to fetch odds for (optional, default: all leagues)'
        )
        
    def handle(self, *args, **options):
        league_ids: Optional[List[int]] = options.get('league_ids')
        
        if league_ids:
            self.stdout.write(self.style.NOTICE(f"Fetching Pinnacle odds for leagues: {league_ids}"))
        else:
            self.stdout.write(self.style.NOTICE("Fetching Pinnacle odds for all available leagues"))
        
        try:
            # Call the fetch_pinnacle_odds function with league_ids
            odds_data = fetch_pinnacle_odds(league_ids)
            
            # Log success
            self.stdout.write(
                self.style.SUCCESS(f"Successfully fetched and stored {len(odds_data)} odds from Pinnacle")
            )
            
            # Display odds summary
            if odds_data:
                self.stdout.write(self.style.NOTICE("\nOdds Summary:"))
                self.stdout.write(f"{'Fixture ID':<15} {'Home':<8} {'Draw':<8} {'Away':<8}")
                self.stdout.write("-" * 50)
                
                for odds in odds_data[:10]:  # Show only first 10 for brevity
                    self.stdout.write(
                        f"{odds['fixture_id']:<15} "
                        f"{odds['odds_home']:<8.2f} "
                        f"{odds['odds_draw']:<8.2f} "
                        f"{odds['odds_away']:<8.2f}"
                    )
                
                if len(odds_data) > 10:
                    self.stdout.write(f"... and {len(odds_data) - 10} more")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching Pinnacle odds: {e}"))
            logger.error(f"Error in fetch_pinnacle_odds command: {e}")
            raise CommandError(f"Error fetching Pinnacle odds: {e}") 