#!/usr/bin/env python3
"""
Check detailed subscription information to understand what's actually available
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_subscription_details():
    """Check detailed subscription information."""
    
    api_token = os.getenv('SPORTMONKS_API_TOKEN')
    if not api_token:
        print("ERROR: SPORTMONKS_API_TOKEN not found in environment")
        return
    
    print("🔍 CHECKING SUBSCRIPTION DETAILS")
    print("=" * 50)
    
    # Check subscription info
    print("\n1️⃣ SUBSCRIPTION INFO:")
    sub_url = f"https://api.sportmonks.com/v3/core/subscription"
    sub_params = {'api_token': api_token}
    
    try:
        response = requests.get(sub_url, params=sub_params, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Response:", json.dumps(data, indent=2))
        else:
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Check available leagues (get first page to see which ones work)
    print("\n2️⃣ AVAILABLE LEAGUES SAMPLE:")
    leagues_url = f"https://api.sportmonks.com/v3/football/leagues"
    leagues_params = {
        'api_token': api_token,
        'include': 'country',
        'per_page': 20
    }
    
    try:
        response = requests.get(leagues_url, params=leagues_params, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                print(f"Found {len(data['data'])} leagues in sample:")
                for league in data['data'][:10]:  # Show first 10
                    country_name = "Unknown"
                    if 'country' in league and league['country']:
                        country_name = league['country']['name']
                    print(f"   - {league['name']} (ID: {league['id']}) - {country_name}")
                    
                # Look for Romanian leagues specifically
                romanian_leagues = [l for l in data['data'] if 'country' in l and l['country'] and 'romania' in l['country']['name'].lower()]
                if romanian_leagues:
                    print(f"\n🇷🇴 ROMANIAN LEAGUES FOUND:")
                    for league in romanian_leagues:
                        print(f"   ✅ {league['name']} (ID: {league['id']})")
                else:
                    print(f"\n❌ No Romanian leagues found in this sample")
            else:
                print("❌ No leagues data found")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test a known working league for comparison
    print("\n3️⃣ TESTING KNOWN WORKING LEAGUE (Premier League ID: 8):")
    test_url = f"https://api.sportmonks.com/v3/football/leagues/8"
    test_params = {
        'api_token': api_token,
        'include': 'country'
    }
    
    try:
        response = requests.get(test_url, params=test_params, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                league = data['data']
                print(f"✅ Working: {league['name']} (ID: {league['id']})")
            else:
                print("❌ No data found")
        else:
            print(f"❌ API Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    check_subscription_details() 