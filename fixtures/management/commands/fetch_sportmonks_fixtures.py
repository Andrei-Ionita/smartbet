"""
Command to fetch fixtures from SportMonks API.

This command fetches live and upcoming fixtures for Romanian leagues from SportMonks API, 
along with related data like lineups, injuries, and team stats.
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from fixtures.fetch_sportmonks import fetch_and_store_fixtures, ROMANIAN_LEAGUE_IDS

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetch fixtures from SportMonks API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to fetch fixtures for (before and after today)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )

    def handle(self, *args, **options):
        days_range = options['days']
        verbose = options['verbose']
        
        # Configure logging based on verbosity
        if verbose:
            logger.setLevel(logging.DEBUG)
            # Configure root logger to see all debug messages
            logging.basicConfig(level=logging.DEBUG)
        
        self.stdout.write(self.style.NOTICE(f"Fetching fixtures from SportMonks API for ±{days_range} days"))
        
        # Display leagues we're fetching
        self.stdout.write("Target leagues:")
        for league_name, league_id in ROMANIAN_LEAGUE_IDS.items():
            self.stdout.write(f"  • {league_name} (ID: {league_id})")
        
        try:
            # Fetch and store fixtures
            created, updated, failed = fetch_and_store_fixtures(days_range)
            
            # Display results
            total = created + updated + failed
            
            self.stdout.write(self.style.SUCCESS(f"\nFixture update complete: {total} total fixtures processed"))
            self.stdout.write(f"  ✅ Created: {created}")
            self.stdout.write(f"  🔄 Updated: {updated}")
            
            if failed > 0:
                self.stdout.write(self.style.WARNING(f"  ❌ Failed: {failed}"))
            else:
                self.stdout.write(f"  ❌ Failed: {failed}")
            
            success_rate = ((created + updated) / total * 100) if total > 0 else 0
            
            if success_rate > 90:
                self.stdout.write(self.style.SUCCESS(f"Success rate: {success_rate:.1f}%"))
            elif success_rate > 50:
                self.stdout.write(self.style.WARNING(f"Success rate: {success_rate:.1f}%"))
            else:
                self.stdout.write(self.style.ERROR(f"Success rate: {success_rate:.1f}%"))
                
        except Exception as e:
            logger.exception("Error fetching fixtures")
            raise CommandError(f"Failed to fetch fixtures: {str(e)}") 