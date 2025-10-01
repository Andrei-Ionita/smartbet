#!/usr/bin/env python3
"""
Debug Season Discovery for New Leagues
=====================================

Test what seasons are actually available in SportMonks API for:
- Bundesliga (ID: 82)
- Ligue 1 (ID: 301) 
- Liga 1 Romania (ID: 486)
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

SPORTMONKS_API_TOKEN = os.getenv('SPORTMONKS_API_TOKEN')
BASE_URL = "https://api.sportmonks.com/v3/football"

def test_league_seasons(league_id, league_name):
    """Test what seasons are available for a specific league"""
    print(f"\n🔍 TESTING {league_name.upper()} (ID: {league_id})")
    print("=" * 50)
    
    # Test different API endpoints to find seasons
    endpoints_to_test = [
        f"seasons?filter=leagues:{league_id}",
        f"seasons?filters=leagues:{league_id}",
        f"leagues/{league_id}/seasons",
        f"seasons?include=league&filter=leagues:{league_id}",
    ]
    
    for i, endpoint in enumerate(endpoints_to_test):
        print(f"\n📡 Test {i+1}: {endpoint}")
        
        try:
            url = f"{BASE_URL}/{endpoint}"
            params = {
                'api_token': SPORTMONKS_API_TOKEN,
                'per_page': 20
            }
            
            response = requests.get(url, params=params, timeout=30)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and data['data']:
                    seasons = data['data']
                    print(f"   ✅ Found {len(seasons)} seasons")
                    
                    # Show recent seasons
                    for season in seasons[:5]:
                        season_name = season.get('name', 'Unknown')
                        season_id = season.get('id', 'Unknown')
                        is_current = season.get('is_current', False)
                        print(f"      📅 {season_name} (ID: {season_id}) {'🔴 CURRENT' if is_current else ''}")
                    
                    return seasons
                else:
                    print("   ⚠️ No data found")
            else:
                print(f"   ❌ Error: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    return None

def test_direct_league_info(league_id, league_name):
    """Test direct league information"""
    print(f"\n🏆 LEAGUE INFO: {league_name.upper()}")
    print("=" * 30)
    
    try:
        url = f"{BASE_URL}/leagues/{league_id}"
        params = {
            'api_token': SPORTMONKS_API_TOKEN,
            'include': 'seasons'
        }
        
        response = requests.get(url, params=params, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data:
                league_data = data['data']
                print(f"✅ League: {league_data.get('name', 'Unknown')}")
                print(f"   Country: {league_data.get('country', {}).get('name', 'Unknown')}")
                print(f"   Active: {league_data.get('active', 'Unknown')}")
                
                # Check seasons if included
                if 'seasons' in league_data:
                    seasons = league_data['seasons']
                    print(f"   📅 Seasons available: {len(seasons)}")
                    
                    for season in seasons[-5:]:  # Last 5 seasons
                        print(f"      {season.get('name', 'Unknown')} (ID: {season.get('id')})")
                
                return True
        else:
            print(f"❌ Error: {response.text[:100]}...")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    return False

def test_fixtures_for_league(league_id, league_name):
    """Test if we can find recent fixtures for the league"""
    print(f"\n⚽ RECENT FIXTURES: {league_name.upper()}")
    print("=" * 35)
    
    try:
        url = f"{BASE_URL}/fixtures"
        params = {
            'api_token': SPORTMONKS_API_TOKEN,
            'filters': f'fixtureLeagues:{league_id}',
            'per_page': 10
        }
        
        response = requests.get(url, params=params, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data and data['data']:
                fixtures = data['data']
                print(f"✅ Found {len(fixtures)} recent fixtures")
                
                for fixture in fixtures[:3]:
                    date = fixture.get('starting_at', '')[:10]
                    participants = fixture.get('participants', [])
                    if len(participants) >= 2:
                        home = participants[0].get('name', 'Unknown')
                        away = participants[1].get('name', 'Unknown')
                        print(f"   📅 {date}: {home} vs {away}")
                
                return True
            else:
                print("⚠️ No fixtures found")
        else:
            print(f"❌ Error: {response.text[:100]}...")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    return False

# Main testing
if __name__ == "__main__":
    print("🚀 SPORTMONKS API SEASON DISCOVERY DEBUG")
    print("=" * 60)
    print(f"🔑 Using API token: {SPORTMONKS_API_TOKEN[:10]}..." if SPORTMONKS_API_TOKEN else "❌ No API token found")
    
    # Test leagues
    leagues_to_test = [
        (82, "Bundesliga"),
        (301, "Ligue 1"), 
        (486, "Liga 1 Romania")
    ]
    
    results = {}
    
    for league_id, league_name in leagues_to_test:
        # Test league info
        league_valid = test_direct_league_info(league_id, league_name)
        
        # Test seasons
        seasons = test_league_seasons(league_id, league_name)
        
        # Test fixtures
        fixtures_valid = test_fixtures_for_league(league_id, league_name)
        
        results[league_name] = {
            'league_valid': league_valid,
            'seasons_found': len(seasons) if seasons else 0,
            'fixtures_valid': fixtures_valid,
            'seasons': seasons[:3] if seasons else []  # Top 3 seasons
        }
        
        print(f"\n{'='*60}")
    
    # Summary
    print(f"\n🎯 SUMMARY RESULTS")
    print("=" * 30)
    
    for league_name, result in results.items():
        print(f"\n{league_name}:")
        print(f"  ✅ League Valid: {result['league_valid']}")
        print(f"  📅 Seasons Found: {result['seasons_found']}")
        print(f"  ⚽ Recent Fixtures: {result['fixtures_valid']}")
        
        if result['seasons']:
            print(f"  📋 Latest Seasons:")
            for season in result['seasons']:
                print(f"     - {season.get('name')} (ID: {season.get('id')})")
    
    print(f"\n🔧 NEXT STEPS:")
    print("1. Use the working league IDs and season IDs found above")
    print("2. Update the season filtering logic in the main script")
    print("3. Test with the correct API endpoint formats") 