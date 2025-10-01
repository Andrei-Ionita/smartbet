import logging
import time
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from fixtures.fetch_sportmonks import fetch_and_store_fixtures, enrich_teams_demo_mode
from odds.fetch_oddsapi import fetch_oddsapi_odds
from predictor.scoring_model import generate_match_scores, store_match_scores
from core.models import Match, OddsSnapshot

# Configure logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sync real-time match and odds data from SportMonks and OddsAPI'

    def add_arguments(self, parser):
        parser.add_argument(
            '--leagues',
            nargs='+',
            type=int,
            help='Filter by league IDs (optional)'
        )
        parser.add_argument(
            '--demo',
            action='store_true',
            help='Use demo data for odds'
        )

    def log_with_timestamp(self, message, level='info'):
        """Log message with timestamp."""
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        
        if level == 'info':
            self.stdout.write(self.style.SUCCESS(log_message))
            logger.info(message)
        elif level == 'warning':
            self.stdout.write(self.style.WARNING(log_message))
            logger.warning(message)
        elif level == 'error':
            self.stdout.write(self.style.ERROR(log_message))
            logger.error(message)

    def handle(self, *args, **options):
        start_time = time.time()
        self.log_with_timestamp("Starting real-time data sync...")
        
        # Extract league IDs if provided
        league_ids = options.get('leagues')
        demo_mode = options.get('demo', False)
        
        if league_ids:
            self.log_with_timestamp(f"Filtering by league IDs: {league_ids}")
        if demo_mode:
            self.log_with_timestamp("Demo mode enabled - will use demo data for odds")
        
        # Sync fixtures from SportMonks
        try:
            self.log_with_timestamp("Fetching fixtures from SportMonks...")
            
            # Pass league_ids to fetch_and_store_fixtures
            created, updated, failed = fetch_and_store_fixtures(days_range=3, league_ids=league_ids)
            
            self.log_with_timestamp(f"✅ Matches updated: {created + updated} (created: {created}, updated: {updated})")
            
            # In demo mode, also enrich team data using actual team IDs
            if demo_mode:
                self.log_with_timestamp("Running team enrichment in demo mode...")
                teams_processed = enrich_teams_demo_mode()
                self.log_with_timestamp(f"✅ Teams processed: {teams_processed}")
                
        except Exception as e:
            self.log_with_timestamp(f"Error fetching SportMonks data: {e}", level='error')
        
        # Sync odds from OddsAPI
        try:
            self.log_with_timestamp("Fetching odds from OddsAPI...")
            
            # Pass league_ids to the fetch_oddsapi_odds function
            odds_count = fetch_oddsapi_odds(league_ids=league_ids, demo=demo_mode)
            
            self.log_with_timestamp(f"✅ OddsSnapshots created: {odds_count}")
        except Exception as e:
            self.log_with_timestamp(f"Error fetching OddsAPI data: {e}", level='error')
        
        # Generate ML scores for matches with odds
        try:
            self.log_with_timestamp("Generating ML scores for matches...")
            
            # Find upcoming matches with valid odds
            from_date = timezone.now()
            to_date = from_date + timezone.timedelta(days=7)
            
            matches_with_odds = Match.objects.filter(
                status="NS",  # Not Started
                kickoff__gte=from_date,
                kickoff__lte=to_date,
                odds_snapshots__isnull=False
            ).distinct()
            
            if matches_with_odds.exists():
                # Generate scores for these matches
                match_scores = generate_match_scores(list(matches_with_odds))
                
                if match_scores:
                    # Store the scores
                    store_match_scores(match_scores)
                    self.log_with_timestamp(f"✅ MatchScores generated with ML: {len(match_scores)}")
                else:
                    self.log_with_timestamp("No ML scores generated", level='warning')
            else:
                self.log_with_timestamp("No matches with odds found for ML scoring", level='warning')
                
        except Exception as e:
            self.log_with_timestamp(f"Error generating ML scores: {e}", level='error')
        
        # Calculate and log total execution time
        execution_time = time.time() - start_time
        self.log_with_timestamp(f"Sync completed in {execution_time:.2f} seconds") 