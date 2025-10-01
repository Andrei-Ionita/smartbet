#!/usr/bin/env python3
"""
Get All Seasons from All Pages
Find Bundesliga and Ligue 1 seasons by fetching all pages
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_all_seasons():
    """Get ALL seasons from all pages."""
    
    api_token = os.getenv('SPORTMONKS_API_TOKEN')
    if not api_token:
        print("ERROR: SPORTMONKS_API_TOKEN not found in environment")
        return
    
    print("🔍 GETTING ALL SEASONS FROM ALL PAGES")
    print("=" * 50)
    
    all_seasons = []
    page = 1
    
    while True:
        print(f"📄 Fetching page {page}...")
        
        seasons_url = f"https://api.sportmonks.com/v3/football/seasons"
        seasons_params = {
            'api_token': api_token,
            'per_page': 100,
            'page': page
        }
        
        try:
            response = requests.get(seasons_url, params=seasons_params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    page_seasons = data['data']
                    if not page_seasons:
                        print(f"   Empty page {page}")
                        break
                    
                    all_seasons.extend(page_seasons)
                    print(f"   Page {page}: {len(page_seasons)} seasons")
                    
                    # Check pagination
                    pagination = data.get('pagination', {})
                    has_more = pagination.get('has_more', False)
                    
                    if not has_more:
                        print(f"   No more pages")
                        break
                    
                    page += 1
                else:
                    print(f"   No data on page {page}")
                    break
            else:
                print(f"API Error on page {page}: {response.text}")
                break
                
        except Exception as e:
            print(f"Exception on page {page}: {e}")
            break
    
    print(f"\n✅ Total seasons collected: {len(all_seasons)}")
    
    # Now search for Bundesliga and Ligue 1
    print(f"\n🇩🇪 SEARCHING FOR BUNDESLIGA (ID: 82):")
    bundesliga_seasons = [s for s in all_seasons if s.get('league_id') == 82]
    if bundesliga_seasons:
        print(f"   Found {len(bundesliga_seasons)} Bundesliga seasons:")
        for season in bundesliga_seasons:
            print(f"   - {season['name']} (ID: {season['id']})")
    else:
        print("   ❌ Still no Bundesliga seasons found")
    
    print(f"\n🇫🇷 SEARCHING FOR LIGUE 1 (ID: 301):")
    ligue1_seasons = [s for s in all_seasons if s.get('league_id') == 301]
    if ligue1_seasons:
        print(f"   Found {len(ligue1_seasons)} Ligue 1 seasons:")
        for season in ligue1_seasons:
            print(f"   - {season['name']} (ID: {season['id']})")
    else:
        print("   ❌ Still no Ligue 1 seasons found")
    
    # Show all unique league IDs to see what's available
    print(f"\n📊 ALL UNIQUE LEAGUE IDs (showing counts):")
    league_counts = {}
    for season in all_seasons:
        league_id = season.get('league_id')
        if league_id:
            league_counts[league_id] = league_counts.get(league_id, 0) + 1
    
    sorted_leagues = sorted(league_counts.items(), key=lambda x: x[1], reverse=True)
    for league_id, count in sorted_leagues:
        print(f"   League {league_id}: {count} seasons")
    
    # Search for seasons containing German or French leagues by name
    print(f"\n🔍 SEARCHING BY SEASON NAME:")
    german_keywords = ['bundesliga', 'germany', 'deutsch', 'german']
    french_keywords = ['ligue', 'france', 'french', 'français']
    
    print("German-related seasons:")
    for season in all_seasons:
        season_name = season.get('name', '').lower()
        if any(keyword in season_name for keyword in german_keywords):
            print(f"   - {season['name']} (League: {season.get('league_id')}, ID: {season['id']})")
    
    print("French-related seasons:")
    for season in all_seasons:
        season_name = season.get('name', '').lower()
        if any(keyword in season_name for keyword in french_keywords):
            print(f"   - {season['name']} (League: {season.get('league_id')}, ID: {season['id']})")

if __name__ == "__main__":
    get_all_seasons() 