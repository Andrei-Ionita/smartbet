#!/usr/bin/env python3
"""
Fix League Season Collection
===========================

Properly collect league-specific seasons using the working API patterns
from successful Premier League, Serie A, and La Liga implementations.
"""

import requests
import json
import os
from dotenv import load_dotenv
import time

load_dotenv()

SPORTMONKS_API_TOKEN = os.getenv('SPORTMONKS_API_TOKEN')
BASE_URL = "https://api.sportmonks.com/v3/football"

def get_league_specific_seasons(league_id, league_name):
    """Get seasons specifically for a league using the working pattern"""
    print(f"\n🔍 GETTING SEASONS FOR {league_name.upper()} (ID: {league_id})")
    print("=" * 60)
    
    # Try the approach used in successful implementations
    try:
        # Method 1: Direct league seasons endpoint
        url = f"{BASE_URL}/leagues/{league_id}"
        params = {
            'api_token': SPORTMONKS_API_TOKEN,
            'include': 'seasons'
        }
        
        response = requests.get(url, params=params, timeout=30)
        print(f"📡 Direct league endpoint: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data and 'seasons' in data['data']:
                seasons = data['data']['seasons']
                print(f"✅ Found {len(seasons)} league-specific seasons")
                
                # Sort by most recent first
                seasons_sorted = sorted(seasons, key=lambda x: x.get('name', ''), reverse=True)
                
                print(f"📅 Latest seasons for {league_name}:")
                for i, season in enumerate(seasons_sorted[:5]):
                    season_name = season.get('name', 'Unknown')
                    season_id = season.get('id', 'Unknown')
                    is_current = season.get('is_current', False)
                    starting_at = season.get('starting_at', '')[:10] if season.get('starting_at') else 'Unknown'
                    ending_at = season.get('ending_at', '')[:10] if season.get('ending_at') else 'Unknown'
                    
                    status = "🔴 CURRENT" if is_current else "✅ COMPLETED"
                    print(f"   {i+1}. {season_name} (ID: {season_id}) - {starting_at} to {ending_at} {status}")
                
                return seasons_sorted[:5]  # Return top 5 most recent
                
    except Exception as e:
        print(f"❌ Error getting seasons: {e}")
    
    return None

def test_season_fixtures(season_id, league_id, season_name, league_name):
    """Test if we can get fixtures for a specific season"""
    print(f"\n⚽ TESTING FIXTURES: {season_name} - {league_name}")
    print("=" * 50)
    
    try:
        url = f"{BASE_URL}/fixtures"
        params = {
            'api_token': SPORTMONKS_API_TOKEN,
            'filters': f'fixtureSeasons:{season_id};fixtureLeagues:{league_id}',
            'include': 'participants,scores',
            'per_page': 10
        }
        
        response = requests.get(url, params=params, timeout=30)
        print(f"📡 Fixtures endpoint: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data and data['data']:
                fixtures = data['data']
                print(f"✅ Found {len(fixtures)} fixtures for {season_name}")
                
                # Show sample fixtures
                for i, fixture in enumerate(fixtures[:3]):
                    date = fixture.get('starting_at', '')[:10]
                    participants = fixture.get('participants', [])
                    
                    if len(participants) >= 2:
                        home_team = None
                        away_team = None
                        
                        for participant in participants:
                            location = participant.get('meta', {}).get('location')
                            if location == 'home':
                                home_team = participant.get('name', 'Unknown')
                            elif location == 'away':
                                away_team = participant.get('name', 'Unknown')
                        
                        if home_team and away_team:
                            print(f"   {i+1}. {date}: {home_team} vs {away_team}")
                
                return len(fixtures)
            else:
                print("⚠️ No fixtures found")
                return 0
        else:
            print(f"❌ Error: {response.text[:100]}...")
            return 0
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return 0

def verify_league_correctness(league_id, expected_name):
    """Verify that the league ID corresponds to the expected league"""
    print(f"\n🔍 VERIFYING LEAGUE ID {league_id} = {expected_name}")
    print("=" * 50)
    
    try:
        url = f"{BASE_URL}/leagues/{league_id}"
        params = {
            'api_token': SPORTMONKS_API_TOKEN,
            'include': 'country'
        }
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data:
                league_data = data['data']
                actual_name = league_data.get('name', 'Unknown')
                country_data = league_data.get('country', {})
                country_name = country_data.get('name', 'Unknown') if country_data else 'Unknown'
                active = league_data.get('active', False)
                
                print(f"📋 Actual League: {actual_name}")
                print(f"🌍 Country: {country_name}")
                print(f"✅ Active: {active}")
                
                # Check if this matches expected
                is_correct = expected_name.lower() in actual_name.lower()
                print(f"🎯 Matches Expected: {is_correct}")
                
                if not is_correct:
                    print(f"⚠️ WARNING: Expected '{expected_name}' but got '{actual_name}'")
                
                return {
                    'correct': is_correct,
                    'actual_name': actual_name,
                    'country': country_name,
                    'active': active
                }
                
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return None

# Main execution
if __name__ == "__main__":
    print("🚀 LEAGUE SEASON COLLECTION FIX")
    print("=" * 60)
    
    # Test leagues with verification
    leagues_to_test = [
        (82, "Bundesliga", "Germany"),
        (301, "Ligue 1", "France"),
        (486, "Liga 1", "Romania")  # This might be wrong
    ]
    
    results = {}
    
    for league_id, expected_name, expected_country in leagues_to_test:
        print(f"\n{'='*80}")
        
        # Step 1: Verify league correctness
        league_info = verify_league_correctness(league_id, expected_name)
        
        if not league_info or not league_info['correct']:
            print(f"❌ League ID {league_id} does not match {expected_name}")
            print(f"🔍 Need to find correct league ID for {expected_name}")
            continue
        
        # Step 2: Get league-specific seasons
        seasons = get_league_specific_seasons(league_id, expected_name)
        
        if not seasons:
            print(f"❌ No seasons found for {expected_name}")
            continue
        
        # Step 3: Test fixtures for recent seasons
        fixture_counts = []
        for season in seasons[:3]:  # Test top 3 recent seasons
            season_id = season.get('id')
            season_name = season.get('name')
            
            if season_id and season_name:
                fixture_count = test_season_fixtures(season_id, league_id, season_name, expected_name)
                fixture_counts.append((season_name, fixture_count))
                time.sleep(1)  # Rate limiting
        
        results[expected_name] = {
            'league_info': league_info,
            'seasons': seasons,
            'fixture_counts': fixture_counts
        }
    
    # Final summary
    print(f"\n🎯 FINAL SUMMARY")
    print("=" * 40)
    
    for league_name, result in results.items():
        print(f"\n{league_name}:")
        
        if 'league_info' in result:
            info = result['league_info']
            print(f"  🏆 League: {info['actual_name']} ({info['country']})")
            print(f"  ✅ Active: {info['active']}")
        
        if 'seasons' in result and result['seasons']:
            print(f"  📅 Available Seasons: {len(result['seasons'])}")
            for season in result['seasons'][:3]:
                print(f"     - {season.get('name')} (ID: {season.get('id')})")
        
        if 'fixture_counts' in result:
            print(f"  ⚽ Fixture Counts:")
            for season_name, count in result['fixture_counts']:
                print(f"     - {season_name}: {count} fixtures")
    
    print(f"\n✅ Use the correct league IDs and season IDs from above!") 