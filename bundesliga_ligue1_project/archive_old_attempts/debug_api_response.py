#!/usr/bin/env python3
"""
Debug script to see raw API response for Romanian Liga 1 (ID 474)
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def debug_api_response():
    """Debug API response for Romanian Liga 1 ID 474."""
    
    api_token = os.getenv('SPORTMONKS_API_TOKEN')
    if not api_token:
        print("ERROR: SPORTMONKS_API_TOKEN not found in environment")
        return
    
    # Test league info
    league_url = f"https://api.sportmonks.com/v3/football/leagues/474"
    league_params = {
        'api_token': api_token
    }
    
    print("Testing Romanian Liga 1 (ID: 474)...")
    print("URL:", league_url)
    print("Params:", league_params)
    print("=" * 50)
    
    try:
        response = requests.get(league_url, params=league_params, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Raw Response Text: {response.text}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"JSON Response: {json.dumps(data, indent=2)}")
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error: {e}")
        
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    debug_api_response() 