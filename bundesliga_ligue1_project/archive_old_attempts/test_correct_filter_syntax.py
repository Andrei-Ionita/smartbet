#!/usr/bin/env python3
"""
Test script to verify correct SportMonks API filter syntax and available seasons
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_api_syntax():
    """Test correct API syntax for filters and includes."""
    
    api_token = os.getenv('SPORTMONKS_API_TOKEN')
    if not api_token:
        print("ERROR: SPORTMONKS_API_TOKEN not found in environment")
        return
    
    print("🧪 TESTING SPORTMONKS API SYNTAX")
    print("=" * 50)
    
    # Test 1: Get available seasons for Bundesliga
    print("\n1️⃣ TESTING BUNDESLIGA SEASONS:")
    seasons_url = f"https://api.sportmonks.com/v3/football/seasons"
    seasons_params = {
        'api_token': api_token,
        'per_page': 50
    }
    
    try:
        response = requests.get(seasons_url, params=seasons_params, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                # Look for Bundesliga seasons (league_id: 82)
                bundesliga_seasons = [s for s in data['data'] if s.get('league_id') == 82]
                print(f"Found {len(bundesliga_seasons)} Bundesliga seasons:")
                for season in bundesliga_seasons[:5]:
                    print(f"   - {season['name']} (ID: {season['id']}) - League: {season.get('league_id')}")
            else:
                print("No seasons data found")
        else:
            print(f"API Error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")
    
    # Test 2: Get available seasons for Ligue 1
    print("\n2️⃣ TESTING LIGUE 1 SEASONS:")
    try:
        response = requests.get(seasons_url, params=seasons_params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                # Look for Ligue 1 seasons (league_id: 301)
                ligue1_seasons = [s for s in data['data'] if s.get('league_id') == 301]
                print(f"Found {len(ligue1_seasons)} Ligue 1 seasons:")
                for season in ligue1_seasons[:5]:
                    print(f"   - {season['name']} (ID: {season['id']}) - League: {season.get('league_id')}")
            else:
                print("No seasons data found")
        else:
            print(f"API Error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")
    
    # Test 3: Try different fixture query methods
    print("\n3️⃣ TESTING FIXTURE QUERIES:")
    
    # Method A: Direct league query
    print("Method A: Direct league query...")
    fixtures_url = f"https://api.sportmonks.com/v3/football/fixtures"
    fixtures_params_a = {
        'api_token': api_token,
        'include': 'participants,scores',
        'per_page': 5
    }
    
    try:
        response = requests.get(fixtures_url, params=fixtures_params_a, timeout=30)
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                print(f"   ✅ Got {len(data['data'])} fixtures")
                # Show first fixture details
                fixture = data['data'][0]
                print(f"   Sample: League {fixture.get('league_id')}, Season {fixture.get('season_id')}")
            else:
                print("   ❌ No fixtures found")
        else:
            print(f"   ❌ API Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Method B: Get fixtures by league (if available)
    print("\nMethod B: Bundesliga league fixtures...")
    bundesliga_fixtures_url = f"https://api.sportmonks.com/v3/football/leagues/82/fixtures"
    bundesliga_params = {
        'api_token': api_token,
        'include': 'participants,scores',
        'per_page': 5
    }
    
    try:
        response = requests.get(bundesliga_fixtures_url, params=bundesliga_params, timeout=30)
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                print(f"   ✅ Got {len(data['data'])} Bundesliga fixtures")
                fixture = data['data'][0]
                print(f"   Sample: {fixture.get('starting_at', 'No date')}")
            else:
                print("   ❌ No Bundesliga fixtures found")
        else:
            print(f"   ❌ API Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    test_api_syntax() 