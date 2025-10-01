#!/usr/bin/env python3
"""
Test script to verify correct Romanian Liga 1 league ID (474) from official SportMonks documentation.
Based on: https://www.sportmonks.com/football-api/liga-1-api-romania/
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_romanian_liga1():
    """Test Romanian Liga 1 with correct league ID 474."""
    
    api_token = os.getenv('SPORTMONKS_API_TOKEN')
    if not api_token:
        print("ERROR: SPORTMONKS_API_TOKEN not found in environment")
        return
    
    # Test league info first
    league_url = f"https://api.sportmonks.com/v3/football/leagues/474"
    league_params = {
        'api_token': api_token,
        'include': 'country'
    }
    
    print("Testing Romanian Liga 1 (ID: 474)...")
    print("=" * 50)
    
    try:
        response = requests.get(league_url, params=league_params, timeout=30)
        print(f"League API Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                league = data['data']
                print(f"✅ League Name: {league['name']}")
                print(f"✅ League ID: {league['id']}")
                print(f"✅ Active: {league['active']}")
                if 'country' in league:
                    print(f"✅ Country: {league['country']['name']}")
                
                # Test seasons for this league
                seasons_url = f"https://api.sportmonks.com/v3/football/seasons"
                seasons_params = {
                    'api_token': api_token,
                    'filters': f'leagueId:{league["id"]}'
                }
                
                print("\nTesting seasons for Romanian Liga 1...")
                seasons_response = requests.get(seasons_url, params=seasons_params, timeout=30)
                
                if seasons_response.status_code == 200:
                    seasons_data = seasons_response.json()
                    if 'data' in seasons_data and len(seasons_data['data']) > 0:
                        print(f"✅ Found {len(seasons_data['data'])} seasons")
                        
                        # Show recent seasons
                        for season in seasons_data['data'][:3]:
                            print(f"   - {season['name']} (ID: {season['id']})")
                        
                        # Test fixtures for most recent season
                        if len(seasons_data['data']) > 0:
                            latest_season = seasons_data['data'][0]
                            print(f"\nTesting fixtures for latest season: {latest_season['name']}")
                            
                            fixtures_url = f"https://api.sportmonks.com/v3/football/fixtures"
                            fixtures_params = {
                                'api_token': api_token,
                                'filters': f'seasonId:{latest_season["id"]}',
                                'include': 'participants',
                                'per_page': 5
                            }
                            
                            fixtures_response = requests.get(fixtures_url, params=fixtures_params, timeout=30)
                            
                            if fixtures_response.status_code == 200:
                                fixtures_data = fixtures_response.json()
                                if 'data' in fixtures_data and len(fixtures_data['data']) > 0:
                                    print(f"✅ Found {len(fixtures_data['data'])} fixtures")
                                    
                                    # Show some teams
                                    teams_found = set()
                                    for fixture in fixtures_data['data'][:5]:
                                        if 'participants' in fixture:
                                            for participant in fixture['participants']:
                                                teams_found.add(participant['name'])
                                    
                                    print("✅ Romanian Liga 1 Teams Found:")
                                    for team in sorted(list(teams_found)[:8]):
                                        print(f"   - {team}")
                                else:
                                    print("❌ No fixtures found for latest season")
                            else:
                                print(f"❌ Fixtures API error: {fixtures_response.status_code}")
                    else:
                        print("❌ No seasons found")
                else:
                    print(f"❌ Seasons API error: {seasons_response.status_code}")
            else:
                print("❌ No league data returned")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_romanian_liga1() 