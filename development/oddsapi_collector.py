#!/usr/bin/env python3
"""
OddsAPI Collector for Training Dataset Enhancement
Fetches historical odds from the paid OddsAPI for Premier League fixtures
"""

import os
import sys
import requests
import pandas as pd
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    print("🎯 OddsAPI Collector for Premier League Training Dataset")
    print("=" * 60)
    
    # Check for API key
    api_key = os.getenv('ODDSAPI_KEY')
    if not api_key:
        print("❌ ODDSAPI_KEY not found in environment variables")
        print("💡 Please create a .env file in the project root with:")
        print("   ODDSAPI_KEY=your_actual_api_key_here")
        return False
    
    print("✅ API key found")
    
    # Test API connection
    try:
        test_url = "https://api.the-odds-api.com/v4/sports"
        test_params = {'apiKey': api_key}
        response = requests.get(test_url, params=test_params, timeout=10)
        
        if response.status_code == 200:
            remaining = response.headers.get('x-requests-remaining', 'Unknown')
            print(f"✅ API connection successful")
            print(f"📊 Requests remaining: {remaining}")
        else:
            print(f"❌ API test failed with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ API connection error: {e}")
        return False
    
    # Load training dataset
    training_file = "premier_league_complete_4_seasons_20250624_175954.csv"
    try:
        print(f"📂 Loading training dataset: {training_file}")
        df = pd.read_csv(training_file)
        print(f"✅ Loaded {len(df)} training records")
        
        # Show sample
        print("\n📋 Sample of training data:")
        print(df[['fixture_id', 'date', 'home_team', 'away_team', 'season_name']].head())
        
    except Exception as e:
        print(f"❌ Failed to load training dataset: {e}")
        return False
    
    print("\n🎉 Setup complete! Ready to collect odds data.")
    print("\n💡 Next steps:")
    print("1. The script will fetch historical odds from OddsAPI")
    print("2. Match odds to training dataset fixtures")
    print("3. Create enhanced dataset with odds features")
    print("4. Save results for model training")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1) 