"""
Script to fetch all available prediction types from SportMonks API
This will show us all the markets we can use for recommendations
"""

import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_TOKEN = os.getenv('SPORTMONKS_API_TOKEN')

if not API_TOKEN:
    print("❌ SPORTMONKS_API_TOKEN not found in environment")
    exit(1)

print("🔍 Fetching prediction types from SportMonks API...")
print("=" * 60)

# Fetch fixtures with predictions for the next 7 days to see what types are available
today = datetime.now().strftime('%Y-%m-%d')
end_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')

url = f"https://api.sportmonks.com/v3/football/fixtures/between/{today}/{end_date}?api_token={API_TOKEN}&include=predictions&per_page=50"

try:
    print(f"📅 Fetching fixtures from {today} to {end_date}...")
    response = requests.get(url, timeout=30)
    data = response.json()
    
    if 'data' in data:
        fixtures = data['data']
        print(f"✅ Found {len(fixtures)} fixtures")
        
        # Collect all unique prediction types
        prediction_types = {}
        
        for fixture in fixtures:
            predictions = fixture.get('predictions', [])
            if predictions:
                for pred in predictions:
                    type_id = pred.get('type_id')
                    if type_id and type_id not in prediction_types:
                        prediction_types[type_id] = {
                            'id': type_id,
                            'sample_prediction': pred
                        }
        
        print(f"\n📊 Found {len(prediction_types)} unique prediction types:\n")
        
        # Sort by ID and display
        for type_id in sorted(prediction_types.keys()):
            pred = prediction_types[type_id]['sample_prediction']
            prob = pred.get('predictions', {})
            print(f"  Type ID: {type_id:3}")
            print(f"    Sample probabilities: {prob}")
            print()
        
        # Save raw data
        with open('scripts/prediction_types_found.json', 'w') as f:
            json.dump(prediction_types, f, indent=2, default=str)
        print(f"💾 Raw data saved to scripts/prediction_types_found.json")
        
    else:
        print(f"❌ Unexpected response: {data}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
