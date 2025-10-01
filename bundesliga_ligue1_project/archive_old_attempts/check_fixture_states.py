#!/usr/bin/env python3
"""
Check Fixture States - Diagnostic
Find out what states the fixtures are actually in
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_fixture_states():
    """Check what states fixtures are in."""
    
    api_token = os.getenv('SPORTMONKS_API_TOKEN')
    if not api_token:
        print("❌ SPORTMONKS_API_TOKEN not found!")
        return
    
    print("🔍 CHECKING FIXTURE STATES")
    print("=" * 40)
    
    # Check Bundesliga 2022/23
    url = "https://api.sportmonks.com/v3/football/fixtures"
    params = {
        'api_token': api_token,
        'filters': f'fixtureLeagues:82;fixtureSeasons:19744',  # Bundesliga 2022/23
        'include': 'participants;scores;state',
        'per_page': 10
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        fixtures = data.get('data', [])
        print(f"📊 Found {len(fixtures)} fixtures")
        
        state_counts = {}
        
        for fixture in fixtures:
            state = fixture.get('state', {})
            state_name = state.get('state', 'UNKNOWN')
            state_id = state.get('id', 'UNKNOWN')
            
            state_key = f"{state_name} (ID: {state_id})"
            state_counts[state_key] = state_counts.get(state_key, 0) + 1
            
            # Show sample data
            if len(state_counts) <= 5:  # First few unique states
                print(f"🏟️  Fixture {fixture.get('id')}: {fixture.get('name', 'Unknown')}")
                print(f"   State: {state_name} (ID: {state_id})")
                if state_name not in ['SCHEDULED', 'NS']:  # If not scheduled
                    scores = fixture.get('scores', [])
                    print(f"   Scores available: {len(scores)}")
                    for score in scores[:2]:  # First 2 scores
                        desc = score.get('description', 'unknown')
                        score_data = score.get('score', {})
                        print(f"     {desc}: {score_data}")
                print()
        
        print(f"📊 STATE DISTRIBUTION:")
        for state, count in sorted(state_counts.items()):
            print(f"   {state}: {count} fixtures")
    
    except Exception as e:
        print(f"❌ Error: {e}")

def check_older_season():
    """Check an older season that should be completed."""
    
    api_token = os.getenv('SPORTMONKS_API_TOKEN')
    if not api_token:
        print("❌ SPORTMONKS_API_TOKEN not found!")
        return
    
    print("\n🔍 CHECKING OLDER SEASON (Should be completed)")
    print("=" * 50)
    
    # Try an older season
    url = "https://api.sportmonks.com/v3/football/fixtures"
    params = {
        'api_token': api_token,
        'filters': f'fixtureLeagues:82;fixtureSeasons:208',  # Much older season
        'include': 'participants;scores;state',
        'per_page': 10
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        fixtures = data.get('data', [])
        print(f"📊 Found {len(fixtures)} fixtures in older season")
        
        completed_count = 0
        state_counts = {}
        
        for fixture in fixtures:
            state = fixture.get('state', {})
            state_name = state.get('state', 'UNKNOWN')
            
            state_counts[state_name] = state_counts.get(state_name, 0) + 1
            
            if state_name in ['FINISHED', 'FT', 'AET', 'PEN']:
                completed_count += 1
                
                # Show one example
                if completed_count == 1:
                    print(f"✅ COMPLETED FIXTURE EXAMPLE:")
                    print(f"   {fixture.get('name', 'Unknown')}")
                    print(f"   State: {state_name}")
                    
                    scores = fixture.get('scores', [])
                    print(f"   Scores ({len(scores)}):")
                    
                    home_goals = None
                    away_goals = None
                    
                    for score in scores:
                        if score.get('description') == 'CURRENT':
                            participant_type = score.get('score', {}).get('participant')
                            goals = score.get('score', {}).get('goals')
                            print(f"     CURRENT {participant_type}: {goals} goals")
                            
                            if participant_type == 'home':
                                home_goals = goals
                            elif participant_type == 'away':
                                away_goals = goals
                    
                    if home_goals is not None and away_goals is not None:
                        if home_goals > away_goals:
                            outcome = "Home Win"
                        elif home_goals < away_goals:
                            outcome = "Away Win"
                        else:
                            outcome = "Draw"
                        print(f"   📊 {home_goals}-{away_goals} → {outcome}")
        
        print(f"\n📊 OLDER SEASON STATE DISTRIBUTION:")
        for state, count in sorted(state_counts.items()):
            print(f"   {state}: {count} fixtures")
        
        print(f"\n✅ Completed fixtures found: {completed_count}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_fixture_states()
    check_older_season() 