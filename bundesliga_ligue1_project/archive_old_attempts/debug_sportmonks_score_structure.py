#!/usr/bin/env python3
"""
Debug SportMonks API Score Structure
Diagnose why we're missing home wins - inspect actual API responses
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def inspect_fixture_scores():
    """Inspect actual SportMonks fixture score structure."""
    
    api_token = os.getenv('SPORTMONKS_API_TOKEN')
    if not api_token:
        print("❌ SPORTMONKS_API_TOKEN not found!")
        return
    
    # Get a few recent Bundesliga fixtures
    print("🔍 INSPECTING BUNDESLIGA FIXTURE SCORE STRUCTURE")
    print("=" * 60)
    
    url = "https://api.sportmonks.com/v3/football/fixtures"
    params = {
        'api_token': api_token,
        'filters': f'fixtureLeagues:82',  # Bundesliga
        'include': 'participants;scores;state',
        'per_page': 5  # Just a few samples
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        fixtures = data.get('data', [])
        print(f"📊 Found {len(fixtures)} fixtures to inspect")
        
        for i, fixture in enumerate(fixtures[:3]):  # Inspect first 3
            print(f"\n🏟️  FIXTURE {i+1}: {fixture.get('id')}")
            print("=" * 30)
            
            # Participants
            participants = fixture.get('participants', [])
            print(f"👥 PARTICIPANTS ({len(participants)}):")
            for j, participant in enumerate(participants):
                location = participant.get('meta', {}).get('location', 'unknown')
                name = participant.get('name', 'unknown')
                print(f"   {j}: {name} ({location})")
            
            # State
            state = fixture.get('state', {})
            print(f"📋 STATE: {state.get('state', 'unknown')} (ID: {state.get('id')})")
            
            # Scores - THIS IS THE CRITICAL PART
            scores = fixture.get('scores', [])
            print(f"⚽ SCORES ({len(scores)}):")
            for j, score in enumerate(scores):
                description = score.get('description', 'unknown')
                score_data = score.get('score', {})
                print(f"   Score {j} ({description}):")
                print(f"     Raw score data: {score_data}")
                
                # Check all possible score fields
                for key, value in score_data.items():
                    print(f"     {key}: {value}")
            
            print(f"\n📋 FULL FIXTURE JSON:")
            print(json.dumps(fixture, indent=2)[:1000] + "...")  # First 1000 chars
    
    except Exception as e:
        print(f"❌ Error: {e}")

def inspect_completed_fixtures():
    """Look at completed fixtures specifically."""
    
    api_token = os.getenv('SPORTMONKS_API_TOKEN')
    if not api_token:
        print("❌ SPORTMONKS_API_TOKEN not found!")
        return
    
    print("\n\n🔍 INSPECTING COMPLETED BUNDESLIGA FIXTURES")
    print("=" * 60)
    
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
        completed_fixtures = [f for f in fixtures if f.get('state', {}).get('state') == 'FINISHED']
        
        print(f"📊 Found {len(completed_fixtures)} completed fixtures")
        
        # Analyze score patterns
        outcome_counts = {'home_wins': 0, 'draws': 0, 'away_wins': 0, 'unknown': 0}
        
        for i, fixture in enumerate(completed_fixtures[:5]):
            print(f"\n🏟️  COMPLETED FIXTURE {i+1}")
            print("=" * 30)
            
            participants = fixture.get('participants', [])
            home_team = None
            away_team = None
            
            for participant in participants:
                location = participant.get('meta', {}).get('location')
                if location == 'home':
                    home_team = participant.get('name')
                elif location == 'away':
                    away_team = participant.get('name')
            
            print(f"🏠 Home: {home_team}")
            print(f"✈️  Away: {away_team}")
            
            # Find final score
            scores = fixture.get('scores', [])
            final_score = None
            for score in scores:
                if score.get('description') == 'CURRENT':
                    final_score = score
                    break
            
            if final_score:
                score_data = final_score.get('score', {})
                print(f"⚽ FINAL SCORE DATA: {score_data}")
                
                # Try to interpret scores
                participant_score = score_data.get('participant')
                goals_score = score_data.get('goals')
                
                print(f"   participant: {participant_score}")
                print(f"   goals: {goals_score}")
                
                # Determine outcome with both interpretations
                if participant_score is not None and goals_score is not None:
                    # Current interpretation (wrong?)
                    if participant_score > goals_score:
                        outcome1 = "home_win"
                    elif participant_score < goals_score:
                        outcome1 = "away_win"
                    else:
                        outcome1 = "draw"
                    
                    # Alternative interpretation
                    if goals_score > participant_score:
                        outcome2 = "home_win"
                    elif goals_score < participant_score:
                        outcome2 = "away_win"
                    else:
                        outcome2 = "draw"
                    
                    print(f"   🎯 Current interpretation: {outcome1}")
                    print(f"   🎯 Alternative interpretation: {outcome2}")
                    
                    outcome_counts[outcome1] += 1
                else:
                    outcome_counts['unknown'] += 1
                    print(f"   ❓ Unable to determine score")
        
        print(f"\n📊 OUTCOME DISTRIBUTION (current interpretation):")
        for outcome, count in outcome_counts.items():
            print(f"   {outcome}: {count}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    inspect_fixture_scores()
    inspect_completed_fixtures() 