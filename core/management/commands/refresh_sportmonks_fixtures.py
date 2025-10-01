from django.core.management.base import BaseCommand
from django.core.cache import cache
from core.views import fetch_verified_fixtures, MAJOR_LEAGUES
import time


class Command(BaseCommand):
    help = 'Refresh SportMonks fixtures to ensure only real, verified matches are shown'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=14,
            help='Number of days ahead to fetch fixtures (default: 14)'
        )
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear existing fixture cache before refreshing'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 SPORTMONKS FIXTURE VERIFICATION TOOL')
        )
        
        days_ahead = options['days']
        clear_cache = options['clear_cache']
        
        self.stdout.write(f"📅 Fetching fixtures for next {days_ahead} days")
        self.stdout.write(f"🏟️ Monitoring {len(MAJOR_LEAGUES)} major leagues")
        
        # Clear cache if requested
        if clear_cache:
            cache_key = f"verified_fixtures_{days_ahead}"
            cache.delete(cache_key)
            self.stdout.write(
                self.style.WARNING('🧹 Cleared existing fixture cache')
            )
        
        # Fetch fresh fixtures from SportMonks
        start_time = time.time()
        
        try:
            verified_fixtures = fetch_verified_fixtures(days_ahead)
            fetch_time = time.time() - start_time
            
            if not verified_fixtures:
                self.stdout.write(
                    self.style.ERROR('❌ No verified fixtures found!')
                )
                self.stdout.write('This could mean:')
                self.stdout.write('  1. No matches scheduled in the date range')
                self.stdout.write('  2. SportMonks API token issue')
                self.stdout.write('  3. SportMonks API rate limit reached')
                self.stdout.write('  4. Network connectivity issue')
                return
            
            # Group fixtures by league
            league_summary = {}
            for fixture in verified_fixtures:
                league = fixture['league']
                if league not in league_summary:
                    league_summary[league] = []
                league_summary[league].append(fixture)
            
            # Display results
            self.stdout.write(
                self.style.SUCCESS('✅ FIXTURE VERIFICATION COMPLETE')
            )
            self.stdout.write(f"⏱️ Fetch Time: {fetch_time:.2f} seconds")
            self.stdout.write(f"🎮 Total Verified Fixtures: {len(verified_fixtures)}")
            self.stdout.write(f"🏟️ Leagues with Matches: {len(league_summary)}")
            
            # League breakdown
            self.stdout.write("📊 VERIFIED FIXTURES BY LEAGUE:")
            for league, fixtures in sorted(league_summary.items()):
                self.stdout.write(f"   {league}: {len(fixtures)} matches")
                
                # Show first few matches as examples
                for i, fixture in enumerate(fixtures[:3]):
                    kickoff_date = fixture.get('kickoff', '').split('T')[0] if fixture.get('kickoff') else 'TBD'
                    self.stdout.write(
                        f"      → {fixture['home_team']} vs {fixture['away_team']} ({kickoff_date})"
                    )
                
                if len(fixtures) > 3:
                    self.stdout.write(f"      ... and {len(fixtures) - 3} more")
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error fetching fixtures: {str(e)}')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS('🎯 Fixture verification complete! SmartBet will now only show predictions for verified matches.')
        ) 