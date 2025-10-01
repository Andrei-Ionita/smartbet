"""
Management command to fetch odds from OddsAPI.
"""

import logging
from django.core.management.base import BaseCommand
from django.db import transaction

from odds.fetch_oddsapi import fetch_oddsapi_odds
from odds.team_matching import validate_team_matching
from core.models import OddsSnapshot

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetch and store odds from OddsAPI with enhanced fuzzy team matching'

    def add_arguments(self, parser):
        parser.add_argument(
            '--demo',
            action='store_true',
            help='Run in demo mode with mock data',
        )
        parser.add_argument(
            '--league-ids',
            nargs='+',
            type=int,
            help='Specific league IDs to fetch odds for',
        )
        parser.add_argument(
            '--validate',
            action='store_true',
            help='Validate team matching performance before fetching',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔄 Starting enhanced OddsAPI odds ingestion...')
        )
        
        # Validate team matching if requested
        if options.get('validate'):
            self.stdout.write('🧪 Validating team matching performance...')
            stats = validate_team_matching()
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Validation complete: {stats['exact_matches']} exact, "
                    f"{stats['fuzzy_matches']} fuzzy, {stats['no_matches']} unmatched"
                )
            )
        
        try:
            # Run the enhanced odds fetching
            count = fetch_oddsapi_odds(
                league_ids=options.get('league_ids'),
                demo=options.get('demo', False)
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Successfully processed {count} odds snapshots'
                )
            )
            
            if not options.get('demo'):
                self.stdout.write(
                    self.style.WARNING(
                        '📋 Check unmatched_odds.json for any unmatched events'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error during odds ingestion: {e}')
            )
            raise 