#!/usr/bin/env python3
"""
Systematic search for Romanian Liga 1 using multiple approaches
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def search_romania_systematic():
    """Search for Romanian Liga 1 using multiple approaches."""
    
    api_token = os.getenv('SPORTMONKS_API_TOKEN')
    if not api_token:
        print("ERROR: SPORTMONKS_API_TOKEN not found in environment")
        return
    
    print("🔍 SYSTEMATIC SEARCH FOR ROMANIAN LIGA 1")
    print("=" * 60)
    
    # Method 1: Search leagues by name "Romania"
    print("\n1️⃣ SEARCHING BY NAME 'Romania'...")
    search_url = f"https://api.sportmonks.com/v3/football/leagues/search/Romania"
    search_params = {
        'api_token': api_token,
        'include': 'country'
    }
    
    try:
        response = requests.get(search_url, params=search_params, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                print(f"✅ Found {len(data['data'])} results:")
                for league in data['data']:
                    country = league.get('country', {}).get('name', 'Unknown') if league.get('country') else 'Unknown'
                    print(f"   - {league['name']} (ID: {league['id']}) - Country: {country}")
            else:
                print("❌ No results found")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Method 2: Search by name "Liga"
    print("\n2️⃣ SEARCHING BY NAME 'Liga'...")
    search_url2 = f"https://api.sportmonks.com/v3/football/leagues/search/Liga"
    try:
        response = requests.get(search_url2, params=search_params, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                print(f"✅ Found {len(data['data'])} results containing 'Liga':")
                for league in data['data']:
                    country = league.get('country', {}).get('name', 'Unknown') if league.get('country') else 'Unknown'
                    if 'romania' in country.lower() or 'liga 1' in league['name'].lower():
                        print(f"   🎯 {league['name']} (ID: {league['id']}) - Country: {country}")
                    else:
                        print(f"   - {league['name']} (ID: {league['id']}) - Country: {country}")
            else:
                print("❌ No results found")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Method 3: Get all leagues and filter for Romania/Liga 1
    print("\n3️⃣ CHECKING ALL LEAGUES FOR ROMANIA...")
    all_leagues_url = f"https://api.sportmonks.com/v3/football/leagues"
    all_params = {
        'api_token': api_token,
        'include': 'country',
        'per_page': 200  # Get more leagues
    }
    
    try:
        response = requests.get(all_leagues_url, params=all_params, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                print(f"Checking {len(data['data'])} leagues...")
                romania_leagues = []
                liga_leagues = []
                
                for league in data['data']:
                    country = league.get('country', {}).get('name', 'Unknown') if league.get('country') else 'Unknown'
                    league_name = league['name'].lower()
                    
                    if 'romania' in country.lower():
                        romania_leagues.append(league)
                    elif 'liga 1' in league_name or 'liga i' in league_name:
                        liga_leagues.append(league)
                
                if romania_leagues:
                    print(f"✅ Found {len(romania_leagues)} Romanian leagues:")
                    for league in romania_leagues:
                        country = league.get('country', {}).get('name', 'Unknown') if league.get('country') else 'Unknown'
                        print(f"   🎯 {league['name']} (ID: {league['id']}) - Country: {country}")
                else:
                    print("❌ No Romanian leagues found")
                
                if liga_leagues:
                    print(f"\n📋 Found {len(liga_leagues)} 'Liga 1' type leagues:")
                    for league in liga_leagues:
                        country = league.get('country', {}).get('name', 'Unknown') if league.get('country') else 'Unknown'
                        print(f"   - {league['name']} (ID: {league['id']}) - Country: {country}")
            else:
                print("❌ No data returned")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Method 4: Test specific known IDs from research
    print("\n4️⃣ TESTING KNOWN ROMANIAN LIGA 1 IDs...")
    test_ids = [474, 486, 283, 274, 383]  # IDs found in various sources
    
    for league_id in test_ids:
        print(f"\n   Testing ID {league_id}...")
        test_url = f"https://api.sportmonks.com/v3/football/leagues/{league_id}"
        test_params = {
            'api_token': api_token,
            'include': 'country'
        }
        
        try:
            response = requests.get(test_url, params=test_params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    league = data['data']
                    country = league.get('country', {}).get('name', 'Unknown') if league.get('country') else 'Unknown'
                    print(f"   ✅ ID {league_id}: {league['name']} - Country: {country}")
                else:
                    print(f"   ❌ ID {league_id}: No data returned")
            else:
                print(f"   ❌ ID {league_id}: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ ID {league_id}: Exception {e}")

if __name__ == "__main__":
    search_romania_systematic() 