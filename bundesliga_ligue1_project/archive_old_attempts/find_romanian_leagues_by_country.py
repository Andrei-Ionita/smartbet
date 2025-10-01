#!/usr/bin/env python3
"""
Find Romanian leagues using country ID 155
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def find_romanian_leagues():
    """Find Romanian leagues using country ID 155."""
    
    api_token = os.getenv('SPORTMONKS_API_TOKEN')
    if not api_token:
        print("ERROR: SPORTMONKS_API_TOKEN not found in environment")
        return
    
    print("🇷🇴 SEARCHING FOR ROMANIAN LEAGUES (Country ID: 155)")
    print("=" * 60)
    
    # Get leagues by country ID
    leagues_url = f"https://api.sportmonks.com/v3/football/leagues/countries/155"
    leagues_params = {
        'api_token': api_token,
        'include': 'country'
    }
    
    try:
        response = requests.get(leagues_url, params=leagues_params, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                print(f"✅ Found {len(data['data'])} Romanian leagues:")
                print()
                
                for league in data['data']:
                    print(f"🏆 League: {league['name']}")
                    print(f"   ID: {league['id']}")
                    print(f"   Active: {league['active']}")
                    print(f"   Type: {league.get('type', 'Unknown')}")
                    print(f"   Sub-type: {league.get('sub_type', 'Unknown')}")
                    if 'country' in league and league['country']:
                        print(f"   Country: {league['country']['name']}")
                    print()
                
                # Find Liga 1 specifically
                liga1_leagues = [l for l in data['data'] if 'liga' in l['name'].lower() and ('1' in l['name'] or 'i' in l['name'])]
                
                if liga1_leagues:
                    print("🎯 FOUND ROMANIAN LIGA 1:")
                    for league in liga1_leagues:
                        print(f"   ✅ {league['name']} (ID: {league['id']})")
                        
                        # Test this league with seasons and fixtures
                        print(f"   Testing seasons for league {league['id']}...")
                        seasons_url = f"https://api.sportmonks.com/v3/football/seasons"
                        seasons_params = {
                            'api_token': api_token,
                            'filters': f'leagueId:{league["id"]}'
                        }
                        
                        seasons_response = requests.get(seasons_url, params=seasons_params, timeout=30)
                        if seasons_response.status_code == 200:
                            seasons_data = seasons_response.json()
                            if 'data' in seasons_data and len(seasons_data['data']) > 0:
                                print(f"   ✅ Found {len(seasons_data['data'])} seasons")
                                # Show recent seasons
                                for season in seasons_data['data'][:3]:
                                    print(f"      - {season['name']} (ID: {season['id']})")
                            else:
                                print(f"   ❌ No seasons found")
                        else:
                            print(f"   ❌ Seasons API error: {seasons_response.status_code}")
                        print()
                
            else:
                print("❌ No Romanian leagues found")
                print("Raw response:", json.dumps(data, indent=2))
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    find_romanian_leagues() 