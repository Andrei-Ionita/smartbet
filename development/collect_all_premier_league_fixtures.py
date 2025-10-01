#!/usr/bin/env python3
"""
CORRECTED Premier League fixtures collector that uses proper pagination.
Based on debugging, we found:
1. API doesn't return last_page/total in pagination
2. Should continue while has_more=True and data is not empty
3. Can get 50 fixtures per page efficiently
"""

import os
import requests
import time
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional

# Configuration
PREMIER_LEAGUE_ID = 8
API_TOKEN = os.getenv('SPORTMONKS_API_TOKEN')

def make_api_request(endpoint: str, params: Dict) -> Optional[Dict]:
    """Make API request with proper error handling."""
    base_url = "https://api.sportmonks.com/v3/football"
    url = f"{base_url}/{endpoint}"
    
    params['api_token'] = API_TOKEN
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ API Error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        return None

def collect_all_season_fixtures(season_id: int, season_name: str) -> List[Dict]:
    """Collect ALL fixtures from a season using corrected pagination logic."""
    print(f"\n🏈 COLLECTING ALL FIXTURES: {season_name} (ID: {season_id})")
    print("=" * 60)
    
    all_fixtures = []
    page = 1
    per_page = 50  # Optimal page size based on testing
    
    while True:
        print(f"📄 Fetching page {page} (per_page={per_page})...")
        
        response = make_api_request("fixtures", {
            'filters': f'fixtureLeagues:{PREMIER_LEAGUE_ID};fixtureSeasons:{season_id}',
            'include': 'participants;scores;state',
            'per_page': per_page,
            'page': page
        })
        
        if not response or 'data' not in response:
            print(f"   ⚠️ No response data on page {page}")
            break
            
        page_fixtures = response['data']
        if not page_fixtures:
            print(f"   ✅ Empty page {page} - end reached")
            break
        
        # Get pagination info
        pagination = response.get('pagination', {})
        has_more = pagination.get('has_more', False)
        
        print(f"   📋 Page {page}: {len(page_fixtures)} fixtures, has_more={has_more}")
        
        # Add fixtures to collection
        all_fixtures.extend(page_fixtures)
        
        # CORRECTED LOGIC: Continue while has_more=True AND we got data
        if not has_more:
            print(f"   🏁 API says no more data (has_more=False)")
            break
            
        page += 1
        time.sleep(0.4)  # Rate limiting
    
    # Filter for completed fixtures
    completed_fixtures = []
    for fixture in all_fixtures:
        if fixture.get('state_id') == 5:  # Completed
            completed_fixtures.append(fixture)
    
    print(f"\n✅ COLLECTION COMPLETE FOR {season_name}:")
    print(f"   🔢 Total fixtures found: {len(all_fixtures)}")
    print(f"   ✅ Completed fixtures: {len(completed_fixtures)}")
    print(f"   📄 Pages processed: {page}")
    print(f"   📈 Fixtures per page avg: {len(all_fixtures)/(page-1):.1f}")
    
    return completed_fixtures

def extract_fixture_features(fixture: Dict) -> Dict:
    """Extract basic features from a fixture."""
    try:
        # Basic fixture info
        fixture_data = {
            'fixture_id': fixture.get('id'),
            'name': fixture.get('name', ''),
            'date': fixture.get('starting_at', ''),
            'state_id': fixture.get('state_id'),
            'round_id': fixture.get('round_id'),
            'stage_id': fixture.get('stage_id'),
        }
        
        # Participants (teams)
        participants = fixture.get('participants', [])
        home_team = None
        away_team = None
        
        for participant in participants:
            if participant.get('meta', {}).get('location') == 'home':
                home_team = participant.get('name', '')
            elif participant.get('meta', {}).get('location') == 'away':
                away_team = participant.get('name', '')
        
        fixture_data['home_team'] = home_team
        fixture_data['away_team'] = away_team
        
        # Scores
        scores = fixture.get('scores', [])
        home_score = None
        away_score = None
        
        for score in scores:
            description = score.get('description', '')
            if 'CURRENT' in description or 'FT' in description:
                participant_id = score.get('participant_id')
                score_value = score.get('score', {}).get('goals', 0)
                
                # Match participant_id to home/away
                for participant in participants:
                    if participant.get('id') == participant_id:
                        location = participant.get('meta', {}).get('location')
                        if location == 'home':
                            home_score = score_value
                        elif location == 'away':
                            away_score = score_value
        
        fixture_data['home_score'] = home_score
        fixture_data['away_score'] = away_score
        
        # Outcome
        if home_score is not None and away_score is not None:
            if home_score > away_score:
                fixture_data['outcome'] = 'home_win'
            elif away_score > home_score:
                fixture_data['outcome'] = 'away_win'
            else:
                fixture_data['outcome'] = 'draw'
        else:
            fixture_data['outcome'] = 'unknown'
        
        return fixture_data
        
    except Exception as e:
        print(f"⚠️ Error extracting fixture {fixture.get('id', 'unknown')}: {str(e)}")
        return None

def main():
    """Collect all fixtures from recent Premier League seasons."""
    if not API_TOKEN:
        print("❌ ERROR: SPORTMONKS_API_TOKEN environment variable not set")
        return
    
    print("🚀 COLLECTING ALL PREMIER LEAGUE FIXTURES")
    print("🔧 Using CORRECTED pagination logic")
    print("=" * 70)
    
    # Test seasons to verify our corrected approach
    test_seasons = [
        (19734, "2022/2023"),  # Should have ~380 fixtures
        (21646, "2023/2024"),  # Should have ~380 fixtures
    ]
    
    all_fixtures_data = []
    total_fixtures = 0
    
    for season_id, season_name in test_seasons:
        try:
            completed_fixtures = collect_all_season_fixtures(season_id, season_name)
            
            # Extract features from each fixture
            print(f"   🔄 Extracting features from {len(completed_fixtures)} fixtures...")
            
            for fixture in completed_fixtures:
                fixture_data = extract_fixture_features(fixture)
                if fixture_data:
                    fixture_data['season_id'] = season_id
                    fixture_data['season_name'] = season_name
                    all_fixtures_data.append(fixture_data)
            
            total_fixtures += len(completed_fixtures)
            print(f"   ✅ Added {len(completed_fixtures)} fixtures from {season_name}")
            
            # Give API a break between seasons
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Error processing {season_name}: {str(e)}")
    
    # Create DataFrame and save
    if all_fixtures_data:
        df = pd.DataFrame(all_fixtures_data)
        
        # Save with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"premier_league_ALL_fixtures_{timestamp}.csv"
        df.to_csv(filename, index=False)
        
        print(f"\n" + "=" * 70)
        print(f"🎉 SUCCESS! CORRECTED APPROACH WORKED!")
        print(f"=" * 70)
        print(f"✅ Total fixtures collected: {total_fixtures}")
        print(f"📊 Seasons processed: {len(test_seasons)}")
        print(f"📈 Average per season: {total_fixtures/len(test_seasons):.1f}")
        print(f"📁 Saved to: {filename}")
        print(f"📋 Dataset shape: {df.shape}")
        
        # Show sample data
        print(f"\n📝 Sample data:")
        print(df[['season_name', 'home_team', 'away_team', 'home_score', 'away_score', 'outcome']].head())
        
        if total_fixtures > 50:
            print(f"\n🎯 BREAKTHROUGH! We got {total_fixtures} fixtures - way more than 25!")
            print(f"✅ The pagination fix WORKED!")
        else:
            print(f"\n🤔 Still only got {total_fixtures} fixtures...")
            print(f"💡 Might need to investigate further")
            
    else:
        print(f"\n❌ No fixtures collected")

if __name__ == "__main__":
    main() 