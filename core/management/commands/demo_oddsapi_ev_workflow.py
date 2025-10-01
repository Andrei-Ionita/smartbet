"""
Command to demonstrate the full betting prediction pipeline using live OddsAPI data.
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from core.models import Match, OddsSnapshot, MatchScoreModel
from odds.fetch_oddsapi import fetch_oddsapi_odds
from predictor.scoring_model import generate_match_scores, store_match_scores

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Demonstrate the full betting prediction pipeline using live OddsAPI data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--leagues',
            type=str,
            nargs='+',
            help='Specific league keys to fetch odds for (e.g. romania_liga_1)'
        )
        parser.add_argument(
            '--create-test-match',
            action='store_true',
            help='Create a test match that will match with OddsAPI data'
        )
        parser.add_argument(
            '--demo-mode',
            action='store_true',
            help='Use demo mode with fake OddsAPI data instead of real API calls'
        )
        parser.add_argument(
            '--auto-create-matches',
            action='store_true',
            help='Automatically create matches for OddsAPI data that doesn\'t match existing matches'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting OddsAPI EV workflow demo..."))
        
        # Create a test match if requested
        test_match = None
        if options.get('create_test_match'):
            test_match = self._create_test_match()
        
        # Step 1: Fetch odds from OddsAPI
        self.stdout.write(self.style.NOTICE("\n1️⃣ Fetching odds from OddsAPI..."))
        
        odds_snapshots = []
        raw_api_data = []
        created_matches = []
        
        if options.get('demo_mode'):
            if test_match:
                odds_snapshots = self._create_demo_odds_snapshots(test_match)
                self.stdout.write(self.style.SUCCESS(f"✅ Created fake OddsAPI snapshot for demo mode"))
            else:
                # Create test match if not already created for demo mode
                test_match = self._create_test_match()
                odds_snapshots = self._create_demo_odds_snapshots(test_match)
                self.stdout.write(self.style.SUCCESS(f"✅ Created test match and fake OddsAPI snapshot for demo mode"))
        else:
            # If auto-create-matches is enabled, get the raw API data first
            if options.get('auto_create_matches'):
                from odds.fetch_oddsapi import get_api_key, get_league_keys, fetch_odds_with_retry
                from odds.fetch_oddsapi import ODDSAPI_BASE_URL, ODDSAPI_SPORT, ODDSAPI_REGION, ODDSAPI_MARKET, ODDSAPI_BOOKMAKERS
                
                api_key = get_api_key()
                leagues = get_league_keys(options.get('leagues'))
                
                self.stdout.write(self.style.NOTICE(f"Fetching raw API data for leagues: {', '.join(leagues)}"))
                
                for league in leagues:
                    url = f"{ODDSAPI_BASE_URL}/sports/{ODDSAPI_SPORT}/odds"
                    params = {
                        'apiKey': api_key,
                        'regions': ODDSAPI_REGION,
                        'markets': ODDSAPI_MARKET,
                        'bookmakers': ','.join(ODDSAPI_BOOKMAKERS),
                        'league': league
                    }
                    
                    data = fetch_odds_with_retry(url, params)
                    if data:
                        raw_api_data.extend(data)
                        self.stdout.write(f"  ✅ Fetched {len(data)} matches for league: {league}")
                
                if raw_api_data:
                    self.stdout.write(self.style.SUCCESS(f"✅ Fetched {len(raw_api_data)} total matches from API"))
                    
                    # Create matches for each API match
                    created_matches = self._create_matches_from_api_data(raw_api_data)
                    
                    # Log the API refs of created matches
                    for match in created_matches:
                        self.stdout.write(f"Match {match.id}: {match} - API ref: {match.api_ref}")
                    
                    # Fetch odds with the newly created matches
                    odds_snapshots = fetch_oddsapi_odds(options.get('leagues'))
                else:
                    self.stdout.write(self.style.ERROR("❌ No data fetched from API"))
            else:
                # Standard flow - just fetch odds
                odds_snapshots = fetch_oddsapi_odds(options.get('leagues'))
        
        if not odds_snapshots:
            self.stdout.write(self.style.ERROR("❌ No odds snapshots fetched from OddsAPI"))
            return
            
        self.stdout.write(self.style.SUCCESS(f"✅ Successfully fetched {len(odds_snapshots)} odds snapshots"))
        
        # Step 2: Store the odds in the database
        self.stdout.write(self.style.NOTICE("\n2️⃣ Storing odds snapshots in database..."))
        stored_count = 0
        
        for snapshot_data in odds_snapshots:
            try:
                OddsSnapshot.objects.create(**snapshot_data)
                stored_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error storing odds snapshot: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"✅ Stored {stored_count} out of {len(odds_snapshots)} odds snapshots"))
        
        # Get unique matches from the odds snapshots
        matches = list(set(snapshot['match'] for snapshot in odds_snapshots))
        self.stdout.write(f"📊 Found odds for {len(matches)} unique matches")
        
        # For demo mode, update API refs to match IDs for proper fixture_id matching
        if options.get('demo_mode'):
            for match in matches:
                if not match.api_ref:
                    match.api_ref = f"match_{match.id}"
                    match.save()
                    self.stdout.write(f"Updated API ref for match {match.id} to {match.api_ref}")
        
        # Step 3: Generate match scores
        self.stdout.write(self.style.NOTICE("\n3️⃣ Generating match scores..."))
        
        scores = generate_match_scores(matches)
        
        if not scores:
            self.stdout.write(self.style.ERROR("❌ Failed to generate any scores"))
            return
            
        self.stdout.write(self.style.SUCCESS(f"✅ Generated {len(scores)} match scores"))
        
        # Step 4: Display results
        self.stdout.write(self.style.NOTICE("\n4️⃣ Match Analysis Results:"))
        self.stdout.write("=" * 100)
        
        value_bets = 0
        avoid_bets = 0
        
        for score in scores:
            match = next((m for m in matches if str(m.id) == score.fixture_id), None)
            if not match:
                continue
                
            odds = match.odds_snapshots.latest('fetched_at')
            
            # Determine outcome and odds value
            if score.home_team_score > score.away_team_score:
                outcome = "HOME"
                model_prob = score.home_team_score
                odds_value = odds.odds_home
                bet = f"Home win @ {odds_value:.2f}"
            elif score.away_team_score > score.home_team_score:
                outcome = "AWAY"
                model_prob = score.away_team_score
                odds_value = odds.odds_away
                bet = f"Away win @ {odds_value:.2f}"
            else:
                outcome = "DRAW"
                model_prob = max(score.home_team_score, score.away_team_score)
                odds_value = odds.odds_draw
                bet = f"Draw @ {odds_value:.2f}"
            
            # Determine value status
            if score.expected_value > 0.05:
                value_status = "✅ VALUE BET"
                value_bets += 1
            elif score.expected_value < 0:
                value_status = "❌ AVOID"
                avoid_bets += 1
            else:
                value_status = "⚖️ FAIR"
            
            # Print match analysis
            self.stdout.write(f"\n🏆 {match}")
            self.stdout.write(f"   📊 Model probability: {model_prob:.1%}")
            self.stdout.write(f"   💰 Recommended bet: {bet}")
            self.stdout.write(f"   🏦 Bookmaker: {odds.bookmaker}")
            self.stdout.write(f"   📈 Expected Value: {score.expected_value:.4f}")
            self.stdout.write(f"   🎯 Status: {value_status}")
            
            # Print implied vs model probability
            implied_prob = 1 / odds_value
            edge = model_prob - implied_prob
            self.stdout.write(f"   📊 Probability edge: {edge:.1%}")
        
        # Step 5: Store scores in database
        self.stdout.write(self.style.NOTICE("\n5️⃣ Storing scores in database..."))
        
        with transaction.atomic():
            store_match_scores(scores)
        
        # Print summary
        self.stdout.write(self.style.SUCCESS("\n📊 Summary:"))
        self.stdout.write("=" * 100)
        self.stdout.write(f"Total matches analyzed: {len(scores)}")
        self.stdout.write(f"Value bets found (EV > 0.05): {value_bets} ✅")
        self.stdout.write(f"Matches to avoid (EV < 0): {avoid_bets} ❌")
        self.stdout.write(f"Fair matches: {len(scores) - value_bets - avoid_bets} ⚖️")
        
        self.stdout.write(self.style.SUCCESS("\n✅ OddsAPI EV workflow demo completed successfully"))

    def _create_test_match(self):
        """Create a test match for demonstration purposes."""
        from core.models import League, Team, Match
        from django.utils import timezone
        from datetime import timedelta
        
        self.stdout.write(self.style.NOTICE("Creating test match for OddsAPI integration..."))
        
        # Create or get a test league
        league, _ = League.objects.get_or_create(
            name_en="English Premier League",
            defaults={
                'name_ro': "Premier League",
                'country': "England",
            }
        )
        
        # Create or get test teams
        home_team, _ = Team.objects.get_or_create(
            name_en="Manchester United",
            defaults={
                'name_ro': "Manchester United",
                'slug': "manchester-united"
            }
        )
        
        away_team, _ = Team.objects.get_or_create(
            name_en="Liverpool",
            defaults={
                'name_ro': "Liverpool",
                'slug': "liverpool"
            }
        )
        
        # Create match
        kickoff = timezone.now() + timedelta(days=1)
        
        try:
            match = Match.objects.get(
                home_team=home_team,
                away_team=away_team,
                kickoff__date=kickoff.date()
            )
            self.stdout.write(self.style.SUCCESS(f"Using existing match: {match}"))
        except Match.DoesNotExist:
            match = Match.objects.create(
                league=league,
                home_team=home_team,
                away_team=away_team,
                kickoff=kickoff,
                status="NS"
            )
            self.stdout.write(self.style.SUCCESS(f"Created test match: {match}"))
            
        return match 

    def _create_demo_odds_snapshots(self, match):
        """Create fake OddsAPI odds snapshots for demo mode."""
        from django.utils import timezone
        
        odds_snapshots = []
        
        # Create a Pinnacle odds snapshot
        pinnacle_snapshot = {
            'match': match,
            'bookmaker': 'OddsAPI (Pinnacle)',
            'odds_home': 2.4,  # Value bet scenario
            'odds_draw': 3.5,
            'odds_away': 3.3,
            'fetched_at': timezone.now()
        }
        odds_snapshots.append(pinnacle_snapshot)
        
        # Create a Bet365 odds snapshot
        bet365_snapshot = {
            'match': match,
            'bookmaker': 'OddsAPI (Bet365)',
            'odds_home': 2.3,  # Similar odds but slightly different
            'odds_draw': 3.4,
            'odds_away': 3.4,
            'fetched_at': timezone.now()
        }
        odds_snapshots.append(bet365_snapshot)
        
        return odds_snapshots 

    def _create_matches_from_api_data(self, api_data):
        """Create matches from the OddsAPI data."""
        from core.models import League, Team, Match
        from django.utils import timezone
        from datetime import datetime
        
        created_matches = []
        
        self.stdout.write(self.style.NOTICE(f"Creating matches from {len(api_data)} API matches..."))
        
        for match_data in api_data:
            try:
                # Extract match info
                home_team_name = match_data['home_team']
                away_team_name = match_data['away_team']
                league_name = match_data.get('sport_title', 'Unknown League')
                country = match_data.get('sport_key', '').split('_')[0].capitalize()
                match_id = match_data.get('id')
                
                # Log the API data
                self.stdout.write(f"  Processing match: {home_team_name} vs {away_team_name} (ID: {match_id})")
                
                # Parse kickoff time
                if isinstance(match_data['commence_time'], str):
                    kickoff = datetime.fromisoformat(match_data['commence_time'].replace('Z', '+00:00'))
                    if kickoff.tzinfo is None:
                        kickoff = timezone.make_aware(kickoff)
                else:
                    kickoff = match_data['commence_time']
                    if kickoff.tzinfo is None:
                        kickoff = timezone.make_aware(kickoff)
                
                # Get or create league
                league, _ = League.objects.get_or_create(
                    name_en=league_name,
                    defaults={
                        'name_ro': league_name,
                        'country': country
                    }
                )
                
                # Get or create teams
                home_team, _ = Team.objects.get_or_create(
                    name_en=home_team_name,
                    defaults={
                        'name_ro': home_team_name,
                        'slug': self._create_slug(home_team_name)
                    }
                )
                
                away_team, _ = Team.objects.get_or_create(
                    name_en=away_team_name,
                    defaults={
                        'name_ro': away_team_name,
                        'slug': self._create_slug(away_team_name)
                    }
                )
                
                # Check if match already exists by API ref
                if match_id:
                    existing_match = Match.objects.filter(api_ref=match_id).first()
                    if existing_match:
                        self.stdout.write(f"  ℹ️ Match found by API ref: {existing_match}")
                        created_matches.append(existing_match)
                        continue
                
                # Create match
                match, created = Match.objects.get_or_create(
                    home_team=home_team,
                    away_team=away_team,
                    kickoff=kickoff,
                    defaults={
                        'league': league,
                        'status': "NS",
                        'api_ref': match_id
                    }
                )
                
                if created:
                    self.stdout.write(f"  ✅ Created match: {match} with API ref: {match_id}")
                    created_matches.append(match)
                else:
                    self.stdout.write(f"  ℹ️ Match already exists: {match}")
                    # Update API ref if missing
                    if not match.api_ref and match_id:
                        match.api_ref = match_id
                        match.save()
                        self.stdout.write(f"    ✅ Updated API ref for match: {match.api_ref}")
                    created_matches.append(match)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Error creating match: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"Created {len(created_matches)} new matches"))
        return created_matches
        
    def _create_slug(self, name):
        """Create a slug from a team name."""
        import re
        slug = re.sub(r'[^\w\s-]', '', name.lower())
        slug = re.sub(r'[\s-]+', '-', slug)
        return slug 