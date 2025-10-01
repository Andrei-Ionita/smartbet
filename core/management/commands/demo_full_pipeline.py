"""
Command to demonstrate the full match scoring and betting suggestion pipeline.
"""

import logging
from django.core.management.base import BaseCommand
from django.core.management import call_command

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Demonstrate the full match scoring and betting suggestion pipeline'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--match-count',
            type=int,
            default=10,
            help='Number of test matches to create (default: 10)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=5,
            help='Days in the future for test matches (default: 5)'
        )
        parser.add_argument(
            '--suggestions',
            type=int,
            default=5,
            help='Number of betting suggestions to show (default: 5)'
        )
        
    def handle(self, *args, **options):
        match_count = options['match_count']
        days_ahead = options['days']
        suggestions_count = options['suggestions']
        
        self.stdout.write(self.style.NOTICE(f"=== SmartBet Pipeline Demo ==="))
        self.stdout.write(f"This command demonstrates the full SmartBet pipeline:")
        self.stdout.write(f"1. Create {match_count} test matches")
        self.stdout.write(f"2. Generate scores for these matches")
        self.stdout.write(f"3. Get top {suggestions_count} betting suggestions")
        self.stdout.write(f"\nPress Enter to start the demo...")
        input()
        
        # Step 1: Create test matches
        self.stdout.write(self.style.NOTICE(f"\n=== Step 1: Creating Test Matches ==="))
        self.stdout.write(f"Creating {match_count} test matches {days_ahead} days in the future...")
        
        try:
            call_command(
                'create_and_score_test_match',
                count=match_count,
                days=days_ahead
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating test matches: {e}"))
            return
            
        self.stdout.write(f"\nPress Enter to continue to step 2...")
        input()
        
        # Step 2: Score matches
        self.stdout.write(self.style.NOTICE(f"\n=== Step 2: Scoring Matches ==="))
        self.stdout.write(f"Running the score_matches command to score all upcoming matches...")
        
        try:
            call_command(
                'score_matches',
                days=days_ahead + 1  # Add buffer to ensure we capture all matches
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error scoring matches: {e}"))
            return
            
        self.stdout.write(f"\nPress Enter to continue to step 3...")
        input()
        
        # Step 3: Get betting suggestions
        self.stdout.write(self.style.NOTICE(f"\n=== Step 3: Generating Betting Suggestions ==="))
        self.stdout.write(f"Getting top {suggestions_count} betting suggestions...")
        
        try:
            call_command(
                'get_betting_suggestions',
                count=suggestions_count,
                days=days_ahead + 1,  # Add buffer to ensure we capture all matches
                confidence='LOW'  # Use low confidence to ensure we get results in the demo
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error getting betting suggestions: {e}"))
            return
            
        # Final message
        self.stdout.write(self.style.SUCCESS(f"\n=== Demo Complete ==="))
        self.stdout.write(f"You have successfully walked through the entire SmartBet pipeline:")
        self.stdout.write(f"1. Created test matches with various odds profiles")
        self.stdout.write(f"2. Generated scores and predictions for these matches")
        self.stdout.write(f"3. Received betting suggestions based on those predictions")
        
        self.stdout.write(f"\nIn a real-world scenario, you would:")
        self.stdout.write(f"1. Fetch real matches and odds from an API")
        self.stdout.write(f"2. Run score_matches daily to update predictions")
        self.stdout.write(f"3. Access betting suggestions through the web interface or API")
        
        self.stdout.write(f"\nType 'python manage.py get_betting_suggestions' anytime to see the latest suggestions.") 