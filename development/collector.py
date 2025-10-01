import os
import pandas as pd
import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def main():
    print("OddsAPI Historical Odds Collector")
    print("=" * 40)
    
    # Get API key
    api_key = os.getenv('ODDSAPI_KEY')
    if not api_key:
        print("Error: ODDSAPI_KEY not found in .env file")
        return
    
    print(f"API Key found: {api_key[:10]}...")
    
    # Load training dataset
    training_files = [
        'premier_league_complete_4_seasons_20250624_175954.csv',
        'premier_league_comprehensive_training_20250624_172007.csv'
    ]
    
    training_df = None
    for filename in training_files:
        if os.path.exists(filename):
            print(f"Loading: {filename}")
            training_df = pd.read_csv(filename)
            print(f"Loaded {len(training_df)} fixtures")
            break
    
    if training_df is None:
        print("No training dataset found")
        return
    
    # Filter for 2020+ fixtures (OddsAPI coverage)
    training_df['Date'] = pd.to_datetime(training_df['Date'])
    cutoff_date = pd.to_datetime('2020-06-06')
    eligible_df = training_df[training_df['Date'] >= cutoff_date]
    
    print(f"Fixtures eligible for odds: {len(eligible_df)}")
    
    if len(eligible_df) == 0:
        print("No fixtures in OddsAPI coverage period")
        return
    
    # Get unique dates
    dates = eligible_df['Date'].dt.date.unique()
    dates = sorted(dates)
    
    print(f"Unique fixture dates: {len(dates)}")
    print(f"First date: {dates[0]}")
    print(f"Last date: {dates[-1]}")
    
    # Test with first 5 dates
    test_dates = dates[:5]
    print(f"\nTesting with first 5 dates: {test_dates}")
    
    base_url = "https://api.the-odds-api.com/v4"
    odds_data = []
    
    for i, date in enumerate(test_dates):
        print(f"\nProcessing {i+1}/5: {date}")
        
        # Convert to API format
        iso_date = datetime.combine(date, datetime.min.time().replace(hour=12)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        url = f"{base_url}/historical/sports/soccer_epl/odds"
        params = {
            'apiKey': api_key,
            'regions': 'uk',
            'markets': 'h2h',
            'date': iso_date,
            'oddsFormat': 'decimal'
        }
        
        try:
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                cost = response.headers.get('x-requests-last', 'Unknown')
                remaining = response.headers.get('x-requests-remaining', 'Unknown')
                
                print(f"  Success! Cost: {cost}, Remaining: {remaining}")
                
                if 'data' in data and data['data']:
                    matches = data['data']
                    print(f"  Found {len(matches)} matches")
                    odds_data.append({
                        'date': date,
                        'matches': matches
                    })
                else:
                    print(f"  No matches found")
            else:
                print(f"  Error: {response.status_code}")
                
        except Exception as e:
            print(f"  Exception: {e}")
        
        time.sleep(1)
    
    print(f"\n=== Results ===")
    print(f"Collected odds for {len(odds_data)} dates")
    
    # Process collected odds
    if odds_data:
        total_matches = sum(len(d['matches']) for d in odds_data)
        print(f"Total matches with odds: {total_matches}")
        
        # Show sample match
        if odds_data[0]['matches']:
            sample_match = odds_data[0]['matches'][0]
            print(f"\nSample match:")
            print(f"  Home: {sample_match.get('home_team')}")
            print(f"  Away: {sample_match.get('away_team')}")
            print(f"  Bookmakers: {len(sample_match.get('bookmakers', []))}")
            
            if sample_match.get('bookmakers'):
                bm = sample_match['bookmakers'][0]
                print(f"  Sample bookmaker: {bm.get('title')}")
                
        # Save data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"odds_test_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(odds_data, f, indent=2, default=str)
        print(f"\nSaved to: {filename}")
    
    print("\nTest complete!")

if __name__ == "__main__":
    main() 