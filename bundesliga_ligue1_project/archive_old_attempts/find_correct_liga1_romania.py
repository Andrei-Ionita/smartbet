#!/usr/bin/env python3
"""
Find Correct Romanian Liga 1 League ID
======================================

Search SportMonks API for the correct Romanian Liga 1 league.
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

SPORTMONKS_API_TOKEN = os.getenv('SPORTMONKS_API_TOKEN')
BASE_URL = "https://api.sportmonks.com/v3/football"

def search_romanian_leagues():
    """Search for Romanian leagues"""
    print("🔍 SEARCHING FOR ROMANIAN LEAGUES")
    print("=" * 40)
    
    try:
        # Search for leagues with "Romania" in country
        url = f"{BASE_URL}/leagues"
        params = {
            'api_token': SPORTMONKS_API_TOKEN,
            'include': 'country',
            'per_page': 100
        }
        
        response = requests.get(url, params=params, timeout=30)
        print(f"📡 Leagues endpoint: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data:
                leagues = data['data']
                print(f"✅ Found {len(leagues)} total leagues")
                
                romanian_leagues = []
                
                for league in leagues:
                    league_name = league.get('name', '').lower()
                    country_data = league.get('country', {})
                    country_name = country_data.get('name', '') if country_data else ''
                    
                    # Check for Romanian leagues
                    if ('romania' in country_name.lower() or 
                        'romanian' in league_name or
                        'liga' in league_name and 'romania' in str(league).lower()):
                        
                        romanian_leagues.append(league)
                        print(f"🇷🇴 Found: {league.get('name')} (ID: {league.get('id')}) - {country_name}")
                
                return romanian_leagues
                
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return []

def search_liga_leagues():
    """Search for leagues with 'Liga' in the name"""
    print("\n🔍 SEARCHING FOR 'LIGA' LEAGUES")
    print("=" * 40)
    
    try:
        url = f"{BASE_URL}/leagues"
        params = {
            'api_token': SPORTMONKS_API_TOKEN,
            'include': 'country',
            'per_page': 200
        }
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data:
                leagues = data['data']
                
                liga_leagues = []
                
                for league in leagues:
                    league_name = league.get('name', '')
                    country_data = league.get('country', {})
                    country_name = country_data.get('name', '') if country_data else ''
                    
                    # Check for Liga leagues
                    if 'liga' in league_name.lower():
                        liga_leagues.append(league)
                        print(f"📋 {league_name} (ID: {league.get('id')}) - {country_name}")
                
                return liga_leagues
                
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return []

def test_specific_league_ids():
    """Test some specific league IDs that might be Romanian Liga 1"""
    print("\n🔍 TESTING SPECIFIC ROMANIAN LEAGUE IDS")
    print("=" * 50)
    
    # Common Romanian league IDs to test
    ids_to_test = [271, 274, 383, 450, 453, 462, 486, 500, 564]
    
    for league_id in ids_to_test:
        try:
            url = f"{BASE_URL}/leagues/{league_id}"
            params = {
                'api_token': SPORTMONKS_API_TOKEN,
                'include': 'country'
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data:
                    league_data = data['data']
                    league_name = league_data.get('name', 'Unknown')
                    country_data = league_data.get('country', {})
                    country_name = country_data.get('name', 'Unknown') if country_data else 'Unknown'
                    
                    print(f"ID {league_id}: {league_name} ({country_name})")
                    
                    # Check if this looks like Romanian Liga 1
                    if ('romania' in country_name.lower() and 
                        ('liga' in league_name.lower() or 'premier' in league_name.lower())):
                        print(f"   🎯 POTENTIAL MATCH: Romanian league!")
            
        except Exception as e:
            print(f"ID {league_id}: Error - {e}")

if __name__ == "__main__":
    print("🚀 FIND CORRECT ROMANIAN LIGA 1")
    print("=" * 50)
    
    # Method 1: Search Romanian leagues
    romanian_leagues = search_romanian_leagues()
    
    # Method 2: Search Liga leagues  
    liga_leagues = search_liga_leagues()
    
    # Method 3: Test specific IDs
    test_specific_league_ids()
    
    print(f"\n🎯 SUMMARY")
    print("=" * 20)
    
    if romanian_leagues:
        print(f"🇷🇴 Romanian leagues found: {len(romanian_leagues)}")
        for league in romanian_leagues:
            print(f"   - {league.get('name')} (ID: {league.get('id')})")
    
    print(f"\n🔧 RECOMMENDATION:")
    print("Use the league ID that corresponds to the main Romanian football league")
    print("Look for names like 'Liga 1', 'Romanian Premier League', or similar") 