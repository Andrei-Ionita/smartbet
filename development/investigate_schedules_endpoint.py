#!/usr/bin/env python3
"""
DEEP INVESTIGATION: Why only 240 fixtures instead of 380?
"""

import requests
import json
import os

# Configuration
api_token = os.getenv('SPORTMONKS_API_TOKEN')
if not api_token:
    print("❌ SPORTMONKS_API_TOKEN not found in .env file")
    print("📋 Please add SPORTMONKS_API_TOKEN=your_token_here to your .env file")
    exit(1)

def investigate_schedules_endpoint():
    season_id = 21713  # Premier League 2023/24
    
    print("🔍 DEEP INVESTIGATION: Premier League Schedules")
    print("=" * 60)
    
    # Test the schedules endpoint with different parameters
    base_url = f'https://api.sportmonks.com/v3/football/schedules/seasons/{season_id}'
    
    # 1. Basic endpoint
    print("1️⃣ TESTING BASIC SCHEDULES ENDPOINT")
    url1 = f'{base_url}?api_token={api_token}'
    response1 = requests.get(url1)
    print(f"URL: {url1}")
    print(f"Status: {response1.status_code}")
    
    if response1.status_code == 200:
        data1 = response1.json()
        analyze_schedule_response(data1, "Basic")
    
    # 2. With pagination
    print("\n2️⃣ TESTING WITH PAGINATION")
    url2 = f'{base_url}?api_token={api_token}&per_page=500&page=1'
    response2 = requests.get(url2)
    print(f"URL: {url2}")
    print(f"Status: {response2.status_code}")
    
    if response2.status_code == 200:
        data2 = response2.json()
        analyze_schedule_response(data2, "With Pagination")
    
    # 3. With includes
    print("\n3️⃣ TESTING WITH INCLUDES")
    url3 = f'{base_url}?api_token={api_token}&include=fixtures'
    response3 = requests.get(url3)
    print(f"URL: {url3}")
    print(f"Status: {response3.status_code}")
    
    if response3.status_code == 200:
        data3 = response3.json()
        analyze_schedule_response(data3, "With Includes")
    
    # 4. Check if there are multiple pages
    print("\n4️⃣ CHECKING PAGINATION INFO")
    if response1.status_code == 200:
        check_pagination(data1)

def analyze_schedule_response(data, test_name):
    print(f"\n📊 ANALYSIS: {test_name}")
    print("-" * 40)
    
    if 'data' not in data:
        print("❌ No 'data' field")
        print(f"Available keys: {list(data.keys())}")
        return
    
    stages = data['data']
    print(f"Number of stages: {len(stages)}")
    
    total_fixtures = 0
    for i, stage in enumerate(stages):
        if isinstance(stage, dict):
            stage_name = stage.get('name', f'Stage {i+1}')
            rounds = stage.get('rounds', [])
            print(f"  Stage '{stage_name}': {len(rounds)} rounds")
            
            stage_fixtures = 0
            for j, round_data in enumerate(rounds):
                if isinstance(round_data, dict):
                    fixtures = round_data.get('fixtures', [])
                    round_name = round_data.get('name', f'Round {j+1}')
                    stage_fixtures += len(fixtures)
                    if len(fixtures) > 0:
                        print(f"    Round '{round_name}': {len(fixtures)} fixtures")
            
            print(f"  Total fixtures in '{stage_name}': {stage_fixtures}")
            total_fixtures += stage_fixtures
    
    print(f"🎯 TOTAL FIXTURES: {total_fixtures}")
    print(f"📈 Coverage: {total_fixtures}/380 = {total_fixtures/380*100:.1f}%")
    
    if total_fixtures < 380:
        print(f"❌ MISSING: {380 - total_fixtures} fixtures")
        print("🤔 POSSIBLE REASONS:")
        print("   - API pagination limiting results")
        print("   - Incomplete season data in SportMonks")
        print("   - Wrong endpoint or parameters")
        print("   - Need different includes/filters")

def check_pagination(data):
    print("📄 PAGINATION INFO:")
    
    # Check for pagination metadata
    if 'pagination' in data:
        pagination = data['pagination']
        print(f"  Current page: {pagination.get('current_page', 'N/A')}")
        print(f"  Total pages: {pagination.get('last_page', 'N/A')}")
        print(f"  Per page: {pagination.get('per_page', 'N/A')}")
        print(f"  Total items: {pagination.get('total', 'N/A')}")
        
        if pagination.get('last_page', 1) > 1:
            print(f"🚨 FOUND MULTIPLE PAGES! We need to fetch ALL {pagination.get('last_page')} pages!")
    else:
        print("  No pagination metadata found")
    
    # Check response metadata
    if 'meta' in data:
        meta = data['meta']
        print(f"  Meta info: {meta}")

if __name__ == "__main__":
    investigate_schedules_endpoint() 