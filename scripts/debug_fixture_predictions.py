import os
import requests
import json
from datetime import datetime, timedelta

def get_api_token():
    # Try to read from smartbet-frontend/.env.local
    try:
        with open('smartbet-frontend/.env.local', 'r') as f:
            for line in f:
                if line.startswith('SPORTMONKS_API_TOKEN='):
                    return line.strip().split('=')[1]
    except Exception as e:
        print(f"Error reading .env.local: {e}")
    return None

def debug_fixture():
    token = get_api_token()
    if not token:
        print("Could not find API token")
        return

    print(f"Using Token: {token[:5]}...")

    # Calculate date range
    now = datetime.now()
    end_date = now + timedelta(days=14)
    start_str = now.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')

    print(f"Searching for 'Inter' in Coppa Italia (ID 390) between {start_str} and {end_str}...")
    
    # Search in Coppa Italia (390)
    url = f"https://api.sportmonks.com/v3/football/fixtures/between/{start_str}/{end_str}"
    params = {
        'api_token': token,
        'include': 'participants;league;predictions;odds',
        'filters': 'fixtureLeagues:390', # Coppa Italia
        'per_page': '50'
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        fixtures = data.get('data', [])
        
        target_fixture = None
        for fixture in fixtures:
            home = fixture.get('participants', [{}, {}])[0].get('name', '')
            away = fixture.get('participants', [{}, {}])[1].get('name', '')
            name = f"{home} vs {away}"
            
            if 'Inter' in home or 'Inter' in away:
                print(f"Found match: {name} (ID: {fixture['id']})")
                target_fixture = fixture
                # Don't break, see all matches
        
        if target_fixture:
            print(f"\nAnalyzing fixture: {target_fixture['name']} (ID: {target_fixture['id']})")
            predictions = target_fixture.get('predictions', [])
            print(f"Predictions count: {len(predictions)}")
            
            for pred in predictions:
                print(f"\nType ID: {pred['type_id']}")
                print(f"Label: {pred.get('label', 'N/A')}")
                print(f"Data: {json.dumps(pred['predictions'], indent=2)}")
                
                if pred['type_id'] in [233, 237, 238]:
                    print(">>> This is a 1x2 prediction candidate")

        else:
            print("Target fixture not found.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_fixture()
