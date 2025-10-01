#!/usr/bin/env python3
"""
Test script to verify Romanian Liga 1 with official correct league ID 474
Based on official SportMonks European Plan coverage documentation
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_romanian_liga1_474():
    """Test Romanian Liga 1 with official league ID 474."""
    
    api_token = os.getenv('SPORTMONKS_API_TOKEN')
    if not api_token:
        print("ERROR: SPORTMONKS_API_TOKEN not found in environment")
        return
    
    print("🇷🇴 TESTING ROMANIAN LIGA 1 (Official ID: 474)")
    print("=" * 60)
    
    # Test 1: League info
    print("\n1️⃣ TESTING LEAGUE INFO...")
    league_url = f"https://api.sportmonks.com/v3/football/leagues/474"
    league_params = {
        'api_token': api_token,
        'include': 'country'
    }
    
    try:
        response = requests.get(league_url, params=league_params, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                league = data['data']
                print(f"✅ League: {league['name']}")
                print(f"   ID: {league['id']}")
                print(f"   Active: {league['active']}")
                if 'country' in league and league['country']:
                    print(f"   Country: {league['country']['name']}")
            else:
                print("❌ No league data found")
                print("Response:", json.dumps(data, indent=2))
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 2: Seasons
    print("\n2️⃣ TESTING SEASONS...")
    seasons_url = f"https://api.sportmonks.com/v3/football/seasons"
    seasons_params = {
        'api_token': api_token,
        'filters': 'leagueId:474'
    }
    
    try:
        response = requests.get(seasons_url, params=seasons_params, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                print(f"✅ Found {len(data['data'])} seasons:")
                for season in data['data'][:5]:  # Show first 5 seasons
                    print(f"   - {season['name']} (ID: {season['id']})")
            else:
                print("❌ No seasons found")
                print("Response:", json.dumps(data, indent=2))
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 3: Fixtures from latest season (if seasons found)
    print("\n3️⃣ TESTING FIXTURES...")
    fixtures_url = f"https://api.sportmonks.com/v3/football/fixtures"
    fixtures_params = {
        'api_token': api_token,
        'filters': 'leagueId:474',
        'include': 'participants;scores',
        'per_page': 5
    }
    
    try:
        response = requests.get(fixtures_url, params=fixtures_params, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                print(f"✅ Found {len(data['data'])} fixtures:")
                for fixture in data['data']:
                    if 'participants' in fixture and len(fixture['participants']) >= 2:
                        home_team = fixture['participants'][0]['name']
                        away_team = fixture['participants'][1]['name']
                        print(f"   - {home_team} vs {away_team}")
                    else:
                        print(f"   - Fixture ID: {fixture['id']}")
            else:
                print("❌ No fixtures found")
                print("Response:", json.dumps(data, indent=2))
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_romanian_liga1_474() 