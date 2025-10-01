#!/usr/bin/env python3
"""
Search for Romanian Liga 1 League ID
===================================
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('SPORTMONKS_API_TOKEN')

def search_specific_ids():
    """Test specific league IDs that might be Romanian Liga 1"""
    print('🎯 TESTING SPECIFIC LEAGUE IDs FOR ROMANIAN LIGA 1')
    print('=' * 55)
    
    # Common IDs that might be Romanian Liga 1
    test_ids = [274, 283, 332, 333, 383, 462, 564, 600, 700, 800, 1000, 1200]
    
    romanian_leagues = []
    
    for league_id in test_ids:
        try:
            url = f'https://api.sportmonks.com/v3/football/leagues/{league_id}'
            params = {
                'api_token': token,
                'include': 'country'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()['data']
                name = data.get('name', 'Unknown')
                country_data = data.get('country', {})
                country = country_data.get('name', 'Unknown') if country_data else 'Unknown'
                
                print(f'ID {league_id}: {name} ({country})')
                
                # Check if this looks like Romanian Liga 1
                if 'romania' in country.lower():
                    romanian_leagues.append({
                        'id': league_id,
                        'name': name,
                        'country': country
                    })
                    print(f'   🇷🇴 ROMANIAN LEAGUE FOUND!')
                    
        except Exception as e:
            print(f'ID {league_id}: Error - {e}')
    
    return romanian_leagues

def test_romanian_league_with_seasons(league_id, league_name):
    """Test if a Romanian league has recent seasons and fixtures"""
    print(f'\n🔍 TESTING {league_name} (ID: {league_id}) FOR RECENT DATA')
    print('=' * 50)
    
    try:
        # Get league with seasons
        url = f'https://api.sportmonks.com/v3/football/leagues/{league_id}'
        params = {
            'api_token': token,
            'include': 'seasons'
        }
        
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()['data']
            seasons = data.get('seasons', [])
            
            print(f'Found {len(seasons)} seasons')
            
            # Look for recent seasons
            recent_seasons = []
            for season in seasons:
                season_name = season.get('name', '')
                if any(year in season_name for year in ['2024', '2023', '2022']):
                    recent_seasons.append(season)
                    print(f'  📅 {season_name} (ID: {season.get("id")})')
            
            # Test fixtures for most recent season
            if recent_seasons:
                latest_season = recent_seasons[0]
                season_id = latest_season.get('id')
                season_name = latest_season.get('name')
                
                print(f'\n⚽ Testing fixtures for {season_name}...')
                
                fixtures_url = 'https://api.sportmonks.com/v3/football/fixtures'
                fixtures_params = {
                    'api_token': token,
                    'filters': f'fixtureSeasons:{season_id}',
                    'per_page': 5
                }
                
                fixtures_response = requests.get(fixtures_url, params=fixtures_params, timeout=30)
                if fixtures_response.status_code == 200:
                    fixtures_data = fixtures_response.json()
                    fixtures = fixtures_data.get('data', [])
                    print(f'  ✅ Found {len(fixtures)} fixtures')
                    
                    if fixtures:
                        # Show sample match
                        fixture = fixtures[0]
                        print(f'  📋 Sample: {fixture.get("name", "Unknown")}')
                        print(f'  📅 Date: {fixture.get("starting_at", "Unknown")}')
                        return True
                else:
                    print(f'  ❌ Fixtures error: {fixtures_response.status_code}')
            else:
                print('  ⚠️ No recent seasons found')
                
        else:
            print(f'Error: {response.status_code}')
            
    except Exception as e:
        print(f'Error: {e}')
    
    return False

if __name__ == "__main__":
    print('🚀 ROMANIAN LIGA 1 SEARCH')
    print('=' * 30)
    
    # Step 1: Find Romanian leagues
    romanian_leagues = search_specific_ids()
    
    print(f'\n📋 SUMMARY: Found {len(romanian_leagues)} Romanian leagues')
    
    # Step 2: Test each Romanian league for data availability
    for league in romanian_leagues:
        has_data = test_romanian_league_with_seasons(league['id'], league['name'])
        if has_data:
            print(f'\n🎯 RECOMMENDED: Use ID {league["id"]} for {league["name"]}')
    
    print(f'\n✅ Search complete!') 