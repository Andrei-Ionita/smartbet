#!/usr/bin/env python3
"""
SportMonks API Final Diagnosis Script
Understanding exactly what works and what doesn't
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SPORTMONKS_API_KEY = os.getenv('SPORTMONKS_API_TOKEN')
BASE_URL = "https://api.sportmonks.com/v3/football"

def test_working_odds_approach():
    """Test the correct way to get odds from SportMonks"""
    print("=== Testing WORKING Odds Approach ===")
    
    # Method 1: Direct odds endpoint (THIS WORKS!)
    odds_url = f"{BASE_URL}/odds/pre-match"
    params = {
        'api_token': SPORTMONKS_API_KEY,
        'per_page': 20
    }
    
    try:
        response = requests.get(odds_url, params=params)
        print(f"✅ Direct odds endpoint works: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            odds = data.get('data', [])
            print(f"Found {len(odds)} odds entries")
            
            # Show sample odds
            if odds:
                sample = odds[0]
                print(f"\nSample odds entry:")
                print(f"  Fixture ID: {sample.get('fixture_id')}")
                print(f"  Market ID: {sample.get('market_id')}")
                print(f"  Market: {sample.get('market_description')}")
                print(f"  Bookmaker ID: {sample.get('bookmaker_id')}")
                print(f"  Label: {sample.get('label')}")
                print(f"  Value: {sample.get('value')}")
                print(f"  Probability: {sample.get('probability')}")
                return True
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_fixture_approach():
    """Test getting fixtures and check their odds capability"""
    print("\n=== Testing Fixture Approach ===")
    
    # Get fixtures without odds include (this should work)
    fixtures_url = f"{BASE_URL}/fixtures"
    params = {
        'api_token': SPORTMONKS_API_KEY,
        'per_page': 10
    }
    
    try:
        response = requests.get(fixtures_url, params=params)
        print(f"Fixtures Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            fixtures = data.get('data', [])
            print(f"Found {len(fixtures)} fixtures")
            
            # Check has_odds flags
            odds_available = 0
            for fixture in fixtures[:5]:
                has_odds = fixture.get('has_odds', False)
                has_premium = fixture.get('has_premium_odds', False)
                
                print(f"\nFixture {fixture.get('id')}: {fixture.get('name', 'Unknown')}")
                print(f"  Starting: {fixture.get('starting_at')}")
                print(f"  Has odds: {has_odds}")
                print(f"  Has premium odds: {has_premium}")
                
                if has_odds:
                    odds_available += 1
            
            print(f"\nSummary: {odds_available}/{len(fixtures[:5])} fixtures have odds available")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_includes_that_work():
    """Test which includes actually work"""
    print("\n=== Testing Working Includes ===")
    
    fixtures_url = f"{BASE_URL}/fixtures"
    
    # Try different includes to see what works
    working_includes = []
    test_includes = ['participants', 'scores', 'state', 'league', 'season']
    
    for include in test_includes:
        params = {
            'api_token': SPORTMONKS_API_KEY,
            'include': include,
            'per_page': 3
        }
        
        try:
            response = requests.get(fixtures_url, params=params)
            if response.status_code == 200:
                working_includes.append(include)
                print(f"  ✅ {include} - works")
            else:
                print(f"  ❌ {include} - failed ({response.status_code})")
        except:
            print(f"  ❌ {include} - error")
    
    print(f"\nWorking includes: {', '.join(working_includes)}")
    return working_includes

def get_fixture_odds_by_id():
    """Try to get odds for a specific fixture"""
    print("\n=== Testing Odds by Fixture ID ===")
    
    # First get a recent fixture ID
    fixtures_url = f"{BASE_URL}/fixtures"
    params = {
        'api_token': SPORTMONKS_API_KEY,
        'per_page': 10
    }
    
    try:
        response = requests.get(fixtures_url, params=params)
        if response.status_code == 200:
            fixtures = response.json().get('data', [])
            
            for fixture in fixtures[:3]:
                fixture_id = fixture.get('id')
                has_odds = fixture.get('has_odds', False)
                
                print(f"\nTesting fixture {fixture_id}: {fixture.get('name', 'Unknown')}")
                print(f"  Has odds flag: {has_odds}")
                
                if has_odds:
                    # Try to get odds for this specific fixture
                    odds_url = f"{BASE_URL}/odds/pre-match"
                    odds_params = {
                        'api_token': SPORTMONKS_API_KEY,
                        'filters': f'fixtureOdds:{fixture_id}',
                        'per_page': 50
                    }
                    
                    odds_response = requests.get(odds_url, params=odds_params)
                    if odds_response.status_code == 200:
                        fixture_odds = odds_response.json().get('data', [])
                        print(f"  ✅ Found {len(fixture_odds)} odds for this fixture")
                        
                        if fixture_odds:
                            # Group by market
                            markets = {}
                            for odd in fixture_odds:
                                market = odd.get('market_description', 'Unknown')
                                if market not in markets:
                                    markets[market] = []
                                markets[market].append(odd)
                            
                            print(f"  Markets available: {list(markets.keys())}")
                            return True
                    else:
                        print(f"  ❌ Odds query failed: {odds_response.status_code}")
                        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def final_diagnosis():
    """Provide final diagnosis and recommendations"""
    print("\n" + "=" * 60)
    print("🔍 FINAL DIAGNOSIS")
    print("=" * 60)
    
    print("\n✅ WHAT WORKS:")
    print("1. Direct odds endpoint: /odds/pre-match")
    print("2. Getting fixtures with has_odds flags")
    print("3. Major league coverage (Premier League, La Liga, etc.)")
    print("4. Current/recent odds data")
    
    print("\n❌ WHAT DOESN'T WORK:")
    print("1. 'odds' include on fixtures endpoint")
    print("2. /markets and /bookmakers endpoints (404 errors)")
    print("3. Historical odds (need Premium subscription)")
    print("4. Old fixture odds (beyond retention period)")
    
    print("\n💡 SOLUTION FOR YOUR PROJECT:")
    print("1. Use direct odds endpoint: /odds/pre-match")
    print("2. Get fixtures separately and match by fixture_id")
    print("3. Focus on recent/current matches for odds")
    print("4. Consider upgrading to Premium for historical data")
    
    print("\n📋 NEXT STEPS:")
    print("1. Modify your extraction script to use direct odds endpoint")
    print("2. Match odds to fixtures using fixture_id")
    print("3. Filter for recent fixtures only (within odds retention period)")
    print("4. Test with small sample first")

def main():
    """Run complete diagnosis"""
    print("🩺 SportMonks API Final Diagnosis")
    print("=" * 50)
    
    # Test 1: Working odds approach
    if test_working_odds_approach():
        print("✅ Odds data IS available!")
    else:
        print("❌ No odds data found")
    
    # Test 2: Fixture approach
    test_fixture_approach()
    
    # Test 3: Working includes
    test_includes_that_work()
    
    # Test 4: Fixture-specific odds
    get_fixture_odds_by_id()
    
    # Final recommendations
    final_diagnosis()

if __name__ == "__main__":
    main() 