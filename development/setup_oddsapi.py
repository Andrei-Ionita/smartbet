#!/usr/bin/env python3
"""
OddsAPI Setup and Testing Script
Based on Official Documentation: https://the-odds-api.com/liveapi/guides/v4/

This script helps you:
1. Validate API key setup
2. Test historical odds endpoints
3. Understand costs and coverage
4. Plan your data collection strategy
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_oddsapi_setup():
    """Test OddsAPI setup and capabilities"""
    
    print("🎯 OddsAPI Setup Validator")
    print("=" * 40)
    
    # Check API key
    api_key = os.getenv('ODDSAPI_KEY')
    if not api_key:
        print("❌ ODDSAPI_KEY not found in .env file")
        print("\n📋 Setup Required:")
        print("1. Visit: https://the-odds-api.com/")
        print("2. Subscribe to paid plan (historical data requires subscription)")
        print("3. Add to .env: ODDSAPI_KEY=your_api_key_here")
        return False
    
    print(f"✅ API key found: {api_key[:10]}...")
    
    # Test basic connection
    print("\n📡 Testing API connection...")
    url = "https://api.the-odds-api.com/v4/sports"
    params = {'apiKey': api_key}
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            print("✅ API connection successful!")
            print(f"📊 Requests remaining: {response.headers.get('x-requests-remaining', 'Unknown')}")
            print(f"📈 Requests used: {response.headers.get('x-requests-used', 'Unknown')}")
        else:
            print(f"❌ API error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    
    # Test historical odds endpoint
    print("\n🏆 Testing Premier League historical odds...")
    historical_url = "https://api.the-odds-api.com/v4/historical/sports/soccer_epl/odds"
    historical_params = {
        'apiKey': api_key,
        'regions': 'uk',
        'markets': 'h2h',
        'date': '2022-10-15T12:00:00Z',  # Known Premier League date
        'oddsFormat': 'decimal'
    }
    
    try:
        response = requests.get(historical_url, params=historical_params)
        print(f"📊 Status: {response.status_code}")
        print(f"💰 Cost: {response.headers.get('x-requests-last', 'Unknown')} credits")
        print(f"📈 Remaining: {response.headers.get('x-requests-remaining', 'Unknown')} credits")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Historical odds test successful!")
            print(f"📅 Snapshot timestamp: {data.get('timestamp', 'Unknown')}")
            
            if 'data' in data and data['data']:
                matches = data['data']
                print(f"⚽ Found {len(matches)} Premier League matches")
                
                # Show sample
                if matches:
                    sample = matches[0]
                    print(f"📋 Sample: {sample['home_team']} vs {sample['away_team']}")
                    if sample.get('bookmakers'):
                        print(f"📚 {len(sample['bookmakers'])} bookmakers available")
            else:
                print("⚠️ No match data found for test date")
            
            print("\n🎉 SUCCESS! OddsAPI is properly configured")
            print_summary()
            return True
        else:
            print(f"❌ Historical odds failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Historical odds error: {e}")
        return False

def print_summary():
    """Print implementation summary"""
    print("\n📊 IMPLEMENTATION SUMMARY")
    print("=" * 40)
    
    print("✅ CAPABILITIES:")
    print("   📅 Historical odds from June 6, 2020")
    print("   ⚽ Premier League: soccer_epl")
    print("   🌍 Regions: uk, eu, us")
    print("   📈 Markets: h2h, totals, spreads")
    
    print("\n💰 COSTS (Historical):")
    print("   📊 10 credits per region per market")
    print("   📅 Example: UK bookmakers, h2h = 10 credits per date")
    print("   📊 Your dataset: ~15,000-20,000 credits estimated")
    
    print("\n📅 COVERAGE FOR YOUR DATA:")
    print("   ✅ 2020/21-2023/24 seasons: Good coverage")
    print("   ❌ 2014/15-2019/20 seasons: No historical data")
    print("   📊 ~60-70% of your training data will have odds")
    
    print("\n🚀 RECOMMENDED STRATEGY:")
    print("   1. Focus on seasons 2020/21 onwards")
    print("   2. Start with UK bookmakers (most relevant)")
    print("   3. Begin with h2h (match winner) market")
    print("   4. Add totals (over/under) if budget allows")
    print("   5. Collect 50-100 fixtures as test sample")
    
    print("\n📋 NEXT STEPS:")
    print("   1. Load your training dataset")
    print("   2. Filter fixtures from 2020 onwards")
    print("   3. Implement batch collection script")
    print("   4. Start with small sample (10-20 fixtures)")
    print("   5. Scale up after validating data quality")

if __name__ == "__main__":
    test_oddsapi_setup() 