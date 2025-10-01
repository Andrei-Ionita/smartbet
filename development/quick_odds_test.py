import os
import pandas as pd
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

print("OddsAPI Historical Odds Test")
print("=" * 30)

# Check API key
api_key = os.getenv('ODDSAPI_KEY')
if not api_key:
    print("No API key found")
    exit()

print(f"API Key: {api_key[:10]}...")

# Load dataset
df = pd.read_csv('premier_league_complete_4_seasons_20250624_175954.csv')
print(f"Loaded {len(df)} fixtures")

# Filter for 2020+
df['date'] = pd.to_datetime(df['date'])
eligible_df = df[df['date'] >= '2020-06-06']
print(f"Eligible fixtures: {len(eligible_df)}")

if len(eligible_df) == 0:
    print("No eligible fixtures")
    exit()

# Get test date
dates = eligible_df['date'].dt.date.unique()
test_date = sorted(dates)[0]
print(f"Testing with date: {test_date}")

# API call
iso_date = datetime.combine(test_date, datetime.min.time().replace(hour=12)).strftime('%Y-%m-%dT%H:%M:%SZ')

url = "https://api.the-odds-api.com/v4/historical/sports/soccer_epl/odds"
params = {
    'apiKey': api_key,
    'regions': 'uk',
    'markets': 'h2h',
    'date': iso_date,
    'oddsFormat': 'decimal'
}

print(f"Requesting: {iso_date}")

try:
    response = requests.get(url, params=params)
    print(f"Response: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        cost = response.headers.get('x-requests-last', 'Unknown')
        remaining = response.headers.get('x-requests-remaining', 'Unknown')
        print(f"Cost: {cost}, Remaining: {remaining}")
        
        if 'data' in data and data['data']:
            matches = data['data']
            print(f"Matches found: {len(matches)}")
            
            if matches:
                sample_match = matches[0]
                home_team = sample_match.get('home_team')
                away_team = sample_match.get('away_team')
                bookmakers = sample_match.get('bookmakers', [])
                
                print(f"Sample: {home_team} vs {away_team}")
                print(f"Bookmakers: {len(bookmakers)}")
                
                if bookmakers:
                    bm = bookmakers[0]
                    title = bm.get('title')
                    markets = bm.get('markets', [])
                    print(f"Sample bookmaker: {title}")
                    
                    if markets:
                        market = markets[0]
                        outcomes = market.get('outcomes', [])
                        print(f"Outcomes: {len(outcomes)}")
                        
                        for outcome in outcomes:
                            name = outcome.get('name')
                            price = outcome.get('price')
                            print(f"  {name}: {price}")
                            
                print("\nSuccess! OddsAPI working correctly.")
        else:
            print("No matches found for this date")
    else:
        print(f"Error {response.status_code}: {response.text}")
        
except Exception as e:
    print(f"Exception: {e}") 