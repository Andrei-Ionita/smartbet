#!/usr/bin/env python3
"""
Simple test to check if fixtures are available for our verified season IDs
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('SPORTMONKS_API_TOKEN')

def test_season_fixtures(season_id, season_name):
    """Test if fixtures exist for a season"""
    print(f"\n🔍 Testing {season_name} (ID: {season_id})")
    
    url = 'https://api.sportmonks.com/v3/football/fixtures'
    params = {
        'api_token': token,
        'filters': f'fixtureSeasons:{season_id}',
        'per_page': 5
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            fixtures = data.get('data', [])
            print(f"   Fixtures found: {len(fixtures)}")
            
            if fixtures:
                # Show sample fixture
                fixture = fixtures[0]
                print(f"   Sample: {fixture.get('name', 'Unknown')}")
                print(f"   Date: {fixture.get('starting_at', 'Unknown')}")
                
                # Test with includes
                params_with_includes = params.copy()
                params_with_includes['include'] = 'participants;scores'
                
                response2 = requests.get(url, params=params_with_includes, timeout=30)
                if response2.status_code == 200:
                    data2 = response2.json()
                    fixtures2 = data2.get('data', [])
                    print(f"   With includes: {len(fixtures2)} fixtures")
                    
                    if fixtures2:
                        fixture_with_data = fixtures2[0]
                        participants = fixture_with_data.get('participants', [])
                        scores = fixture_with_data.get('scores', [])
                        print(f"   Participants: {len(participants)}")
                        print(f"   Scores: {len(scores)}")
                        
                        # Show team names if available
                        if participants:
                            teams = []
                            for p in participants:
                                teams.append(p.get('name', 'Unknown'))
                            print(f"   Teams: {' vs '.join(teams[:2])}")
                else:
                    print(f"   Include error: {response2.status_code}")
            else:
                print("   ⚠️ No fixtures found")
        else:
            print(f"   ❌ Error: {response.text[:100]}")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    print("🚀 TESTING SEASON FIXTURES")
    print("=" * 40)
    
    # Test verified seasons
    test_seasons = [
        (23744, "Bundesliga 2024/2025"),
        (21795, "Bundesliga 2023/2024"), 
        (19744, "Bundesliga 2022/2023"),
        (23643, "Ligue 1 2024/2025"),
        (21779, "Ligue 1 2023/2024"),
        (19745, "Ligue 1 2022/2023")
    ]
    
    for season_id, season_name in test_seasons:
        test_season_fixtures(season_id, season_name) 