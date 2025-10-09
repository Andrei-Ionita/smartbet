#!/usr/bin/env python3
"""
Test script to check SportMonks API predictions availability
"""

import os
import requests
import json
from datetime import datetime, timedelta

# Load environment variables
API_TOKEN = os.getenv('SPORTMONKS_API_TOKEN')
if not API_TOKEN:
    print("ERROR: SPORTMONKS_API_TOKEN not found in environment")
    exit(1)

BASE_URL = "https://api.sportmonks.com/v3/football"
SUPPORTED_LEAGUES = [8, 564, 384, 82, 301]  # Premier League, La Liga, Serie A, Bundesliga, Ligue 1

def test_api_endpoint():
    """Test different API endpoints to see which one works for predictions"""

    print("Testing SportMonks API endpoints...")

    # Test 1: Upcoming fixtures with predictions
    print("\n1. Testing: /fixtures/upcoming with predictions include")
    url1 = f"{BASE_URL}/fixtures/upcoming"
    params1 = {
        'api_token': API_TOKEN,
        'include': 'participants;league;metadata;predictions',
        'filters': f'fixtureLeagues:{",".join(map(str, SUPPORTED_LEAGUES))}',
        'per_page': '10'
    }

    try:
        response = requests.get(url1, params=params1, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            fixtures = data.get('data', [])
            print(f"Fixtures found: {len(fixtures)}")

            for fixture in fixtures[:3]:  # Show first 3 fixtures
                print(f"\n  Match: {fixture.get('name', 'Unknown')}")
                print(f"     League: {fixture.get('league', {}).get('name', 'Unknown')}")
                print(f"     Date: {fixture.get('starting_at', 'Unknown')}")
                print(f"     Predictions: {len(fixture.get('predictions', []))} models")

                for i, pred in enumerate(fixture.get('predictions', [])):
                    predictions = pred.get('predictions', {})
                    print(f"       Model {i+1}: Home={predictions.get('home', 0):.1f}%, Draw={predictions.get('draw', 0):.1f}%, Away={predictions.get('away', 0):.1f}%")
        else:
            print(f"Response: {response.text[:200]}...")

    except Exception as e:
        print(f"Error: {e}")

    # Test 2: Try the markets endpoint (current implementation)
    print("\n2. Testing: /fixtures/upcoming/markets/1 (current implementation)")
    url2 = f"{BASE_URL}/fixtures/upcoming/markets/1"
    params2 = {
        'api_token': API_TOKEN,
        'include': 'participants;league;metadata;predictions',
        'filters': f'fixtureLeagues:{",".join(map(str, SUPPORTED_LEAGUES))}',
        'per_page': '10'
    }

    try:
        response = requests.get(url2, params=params2, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            fixtures = data.get('data', [])
            print(f"Fixtures found: {len(fixtures)}")

            for fixture in fixtures[:3]:  # Show first 3 fixtures
                print(f"\n  Match: {fixture.get('name', 'Unknown')}")
                print(f"     League: {fixture.get('league', {}).get('name', 'Unknown')}")
                print(f"     Date: {fixture.get('starting_at', 'Unknown')}")
                print(f"     Predictions: {len(fixture.get('predictions', []))} models")

                for i, pred in enumerate(fixture.get('predictions', [])):
                    predictions = pred.get('predictions', {})
                    print(f"       Model {i+1}: Home={predictions.get('home', 0):.1f}%, Draw={predictions.get('draw', 0):.1f}%, Away={predictions.get('away', 0):.1f}%")
        else:
            print(f"Response: {response.text[:200]}...")

    except Exception as e:
        print(f"Error: {e}")

    # Test 3: Check if predictions require a separate call
    print("\n3. Testing: /predictions endpoint (if predictions need separate calls)")
    try:
        url3 = f"{BASE_URL}/predictions"
        params3 = {
            'api_token': API_TOKEN,
            'include': 'fixture',
            'per_page': '5'
        }

        response = requests.get(url3, params=params3, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            predictions = data.get('data', [])
            print(f"Predictions found: {len(predictions)}")

            for pred in predictions[:3]:
                fixture = pred.get('fixture', {})
                print(f"\n  Match: {fixture.get('name', 'Unknown')}")
                print(f"     Predictions: {len(pred.get('predictions', []))} models")
        else:
            print(f"Response: {response.text[:200]}...")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Testing SportMonks API for Predictions...")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target Leagues: {SUPPORTED_LEAGUES}")
    print(f"API Token: {API_TOKEN[:10]}...")

    test_api_endpoint()

    print("\nTest completed!")

