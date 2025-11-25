
import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv('smartbet-frontend/.env.local')

API_TOKEN = os.getenv('SPORTMONKS_API_TOKEN')
if not API_TOKEN:
    print("Error: SPORTMONKS_API_TOKEN not found in .env.local")
    exit(1)

def check_any_predictions():
    print("Searching for any fixture with predictions...")
    
    # Search for fixtures in the next 3 days
    # We need a date range. Let's assume today is 2025-11-25 based on the previous log
    start_date = "2025-11-25"
    end_date = "2025-11-28"
    
    url = f"https://api.sportmonks.com/v3/football/fixtures/between/{start_date}/{end_date}"
    params = {
        'api_token': API_TOKEN,
        'include': 'participants;league;predictions',
        'per_page': 10
    }
    
    try:
        print(f"Fetching fixtures from: {url}")
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        fixtures = data.get('data', [])
        print(f"Found {len(fixtures)} fixtures.")
        
        for fixture in fixtures:
            predictions = fixture.get('predictions', [])
            if predictions:
                print(f"SUCCESS: Found predictions for fixture: {fixture['name']} (ID: {fixture['id']})")
                print(f"League: {fixture['league']['name']}")
                print(f"Predictions count: {len(predictions)}")
                print("Sample prediction:", json.dumps(predictions[0], indent=2))
                return
            else:
                print(f"No predictions for: {fixture['name']} (ID: {fixture['id']})")
                
        print("No fixtures with predictions found in this batch.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_any_predictions()
