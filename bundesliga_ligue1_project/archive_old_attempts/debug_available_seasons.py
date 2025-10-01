#!/usr/bin/env python3
"""
Debug Available Seasons
Check what seasons are actually available and understand filtering
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def debug_seasons():
    """Debug what seasons are available."""
    
    api_token = os.getenv('SPORTMONKS_API_TOKEN')
    if not api_token:
        print("ERROR: SPORTMONKS_API_TOKEN not found in environment")
        return
    
    print("🔍 DEBUGGING AVAILABLE SEASONS")
    print("=" * 50)
    
    # Get all seasons
    seasons_url = f"https://api.sportmonks.com/v3/football/seasons"
    seasons_params = {
        'api_token': api_token,
        'per_page': 100
    }
    
    try:
        response = requests.get(seasons_url, params=seasons_params, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                seasons = data['data']
                print(f"Total seasons found: {len(seasons)}")
                
                # Check what leagues we have seasons for
                league_counts = {}
                for season in seasons:
                    league_id = season.get('league_id')
                    if league_id:
                        league_counts[league_id] = league_counts.get(league_id, 0) + 1
                
                print(f"\nTop 20 leagues by season count:")
                sorted_leagues = sorted(league_counts.items(), key=lambda x: x[1], reverse=True)
                for league_id, count in sorted_leagues[:20]:
                    print(f"   League {league_id}: {count} seasons")
                
                # Specifically check for Bundesliga (82) and Ligue 1 (301)
                print(f"\n🇩🇪 BUNDESLIGA (ID: 82) SEASONS:")
                bundesliga_seasons = [s for s in seasons if s.get('league_id') == 82]
                if bundesliga_seasons:
                    for season in bundesliga_seasons[:10]:
                        print(f"   - {season['name']} (ID: {season['id']})")
                else:
                    print("   ❌ No Bundesliga seasons found")
                
                print(f"\n🇫🇷 LIGUE 1 (ID: 301) SEASONS:")
                ligue1_seasons = [s for s in seasons if s.get('league_id') == 301]
                if ligue1_seasons:
                    for season in ligue1_seasons[:10]:
                        print(f"   - {season['name']} (ID: {season['id']})")
                else:
                    print("   ❌ No Ligue 1 seasons found")
                
                # Check if these leagues exist with different IDs
                print(f"\n🔍 SEARCHING FOR GERMAN LEAGUES:")
                german_leagues = []
                french_leagues = []
                
                for season in seasons:
                    name = season.get('name', '').lower()
                    if 'bundesliga' in name or 'germany' in name:
                        german_leagues.append(season)
                    elif 'ligue' in name or 'france' in name:
                        french_leagues.append(season)
                
                if german_leagues:
                    print("   Found German-related seasons:")
                    for season in german_leagues[:5]:
                        print(f"   - {season['name']} (League: {season.get('league_id')}, ID: {season['id']})")
                
                print(f"\n🔍 SEARCHING FOR FRENCH LEAGUES:")
                if french_leagues:
                    print("   Found French-related seasons:")
                    for season in french_leagues[:5]:
                        print(f"   - {season['name']} (League: {season.get('league_id')}, ID: {season['id']})")
                
            else:
                print("No seasons data found")
        else:
            print(f"API Error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")
    
    # Also check pagination
    print(f"\n📄 CHECKING PAGINATION:")
    try:
        pagination = data.get('pagination', {}) if 'data' in locals() and data else {}
        print(f"   Current page: {pagination.get('current_page', 'unknown')}")
        print(f"   Total pages: {pagination.get('last_page', 'unknown')}")
        print(f"   Has more: {pagination.get('has_more', 'unknown')}")
        print(f"   Total count: {pagination.get('count', 'unknown')}")
        
        if pagination.get('has_more', False):
            print("   ⚠️ More seasons available on additional pages!")
    except:
        print("   Could not check pagination info")

if __name__ == "__main__":
    debug_seasons() 