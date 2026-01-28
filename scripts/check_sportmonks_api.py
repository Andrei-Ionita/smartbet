"""
SportMonks API Diagnostic Script
Checks what data is available on your current subscription plan
"""

import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv('smartbet-frontend/.env.local')

API_TOKEN = os.getenv('SPORTMONKS_API_TOKEN')
BASE_URL = "https://api.sportmonks.com/v3"

def check_subscription():
    """Check your current subscription details"""
    print("=" * 60)
    print("SPORTMONKS API DIAGNOSTIC")
    print("=" * 60)
    
    if not API_TOKEN:
        print("❌ SPORTMONKS_API_TOKEN not found in .env.local")
        return False
    
    print(f"✓ API Token found: {API_TOKEN[:15]}...")
    
    # Check subscription info
    url = f"{BASE_URL}/my/enrichments"
    params = {'api_token': API_TOKEN}
    
    try:
        response = requests.get(url, params=params)
        print(f"\n📋 Subscription Enrichments Response: {response.status_code}")
        if response.ok:
            data = response.json()
            print(json.dumps(data, indent=2)[:1000])  # First 1000 chars
    except Exception as e:
        print(f"Error checking enrichments: {e}")
    
    return True

def check_available_leagues():
    """Check what leagues are available"""
    print("\n" + "=" * 60)
    print("AVAILABLE LEAGUES")
    print("=" * 60)
    
    url = f"{BASE_URL}/football/leagues"
    params = {
        'api_token': API_TOKEN,
        'per_page': 50
    }
    
    try:
        response = requests.get(url, params=params)
        if response.ok:
            data = response.json()
            leagues = data.get('data', [])
            print(f"✓ Found {len(leagues)} leagues available:")
            for league in leagues[:20]:  # First 20
                print(f"  - {league.get('name', 'Unknown')} (ID: {league.get('id')})")
            if len(leagues) > 20:
                print(f"  ... and {len(leagues) - 20} more")
        else:
            print(f"❌ Error: {response.status_code} - {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

def check_predictions_available():
    """Check if predictions are included in your plan"""
    print("\n" + "=" * 60)
    print("PREDICTIONS CHECK")
    print("=" * 60)
    
    # Get fixtures for the next 3 days
    today = datetime.now()
    start = today.strftime("%Y-%m-%d")
    end = (today + timedelta(days=3)).strftime("%Y-%m-%d")
    
    url = f"{BASE_URL}/football/fixtures/between/{start}/{end}"
    params = {
        'api_token': API_TOKEN,
        'include': 'predictions',
        'per_page': 10
    }
    
    try:
        response = requests.get(url, params=params)
        if response.ok:
            data = response.json()
            fixtures = data.get('data', [])
            print(f"✓ Found {len(fixtures)} fixtures")
            
            fixtures_with_predictions = 0
            for fixture in fixtures:
                preds = fixture.get('predictions', [])
                if preds:
                    fixtures_with_predictions += 1
                    print(f"  ✓ {fixture.get('name', 'Unknown')}: {len(preds)} predictions")
                    
            if fixtures_with_predictions == 0:
                print("  ⚠️ No predictions found - may need paid plan")
            else:
                print(f"\n✓ {fixtures_with_predictions}/{len(fixtures)} fixtures have predictions")
        else:
            error_data = response.json() if response.text else {}
            print(f"❌ Error {response.status_code}: {error_data.get('message', response.text[:200])}")
    except Exception as e:
        print(f"Error: {e}")

def check_odds_available():
    """Check if odds are included in your plan"""
    print("\n" + "=" * 60)
    print("ODDS CHECK")
    print("=" * 60)
    
    today = datetime.now()
    start = today.strftime("%Y-%m-%d")
    end = (today + timedelta(days=3)).strftime("%Y-%m-%d")
    
    url = f"{BASE_URL}/football/fixtures/between/{start}/{end}"
    params = {
        'api_token': API_TOKEN,
        'include': 'odds',
        'per_page': 10
    }
    
    try:
        response = requests.get(url, params=params)
        if response.ok:
            data = response.json()
            fixtures = data.get('data', [])
            
            fixtures_with_odds = 0
            for fixture in fixtures:
                odds = fixture.get('odds', [])
                if odds:
                    fixtures_with_odds += 1
                    print(f"  ✓ {fixture.get('name', 'Unknown')}: {len(odds)} odds entries")
                    
            if fixtures_with_odds == 0:
                print("  ⚠️ No odds found - may need paid plan")
            else:
                print(f"\n✓ {fixtures_with_odds}/{len(fixtures)} fixtures have odds")
        else:
            error_data = response.json() if response.text else {}
            print(f"❌ Error {response.status_code}: {error_data.get('message', response.text[:200])}")
    except Exception as e:
        print(f"Error: {e}")

def main():
    if not check_subscription():
        return
    
    check_available_leagues()
    check_predictions_available()
    check_odds_available()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
If you're missing predictions or odds, you likely need to:
1. Upgrade to a paid SportMonks plan
2. Subscribe to the 'Predictions' add-on
3. Subscribe to the 'Odds' add-on

Check: https://www.sportmonks.com/football-api/pricing/
""")

if __name__ == "__main__":
    main()
