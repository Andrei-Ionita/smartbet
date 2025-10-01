#!/usr/bin/env python3
"""
Check what leagues are available in the user's European Plan subscription
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_available_leagues():
    """Check what leagues are available in subscription."""
    
    api_token = os.getenv('SPORTMONKS_API_TOKEN')
    if not api_token:
        print("ERROR: SPORTMONKS_API_TOKEN not found in environment")
        return
    
    # Get all available leagues
    leagues_url = f"https://api.sportmonks.com/v3/football/leagues"
    leagues_params = {
        'api_token': api_token,
        'include': 'country',
        'per_page': 100
    }
    
    print("Checking available leagues in subscription...")
    print("=" * 60)
    
    try:
        response = requests.get(leagues_url, params=leagues_params, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                leagues = data['data']
                print(f"✅ Found {len(leagues)} leagues in subscription")
                print()
                
                # Group by country
                countries = {}
                for league in leagues:
                    country_name = "Unknown"
                    if 'country' in league and league['country']:
                        country_name = league['country']['name']
                    
                    if country_name not in countries:
                        countries[country_name] = []
                    countries[country_name].append(league)
                
                # Show available countries and leagues
                for country, country_leagues in sorted(countries.items()):
                    print(f"📍 {country}:")
                    for league in country_leagues:
                        print(f"   - {league['name']} (ID: {league['id']})")
                    print()
                
                # Check specifically for Romania or Eastern European countries
                print("🔍 SEARCHING FOR ROMANIA OR EASTERN EUROPE...")
                romania_found = False
                for country, country_leagues in countries.items():
                    if 'romania' in country.lower() or 'eastern' in country.lower():
                        romania_found = True
                        print(f"✅ Found: {country}")
                        for league in country_leagues:
                            print(f"   - {league['name']} (ID: {league['id']})")
                
                if not romania_found:
                    print("❌ No Romanian leagues found in subscription")
                    print("🔍 Available countries:", sorted(countries.keys()))
                
            else:
                print("❌ No leagues data returned")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    check_available_leagues() 