"""
Odds Collector for Training Dataset Enhancement
Fetches historical odds from OddsAPI for Premier League fixtures
"""

import os
import requests
import pandas as pd
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class OddsCollector:
    def __init__(self):
        self.api_key = os.getenv('ODDSAPI_KEY')
        if not self.api_key:
            print("❌ ODDSAPI_KEY not found. Please add it to your .env file:")
            print("   ODDSAPI_KEY=your_api_key_here")
            raise ValueError("API key required")
        
        self.base_url = "https://api.the-odds-api.com/v4"
        self.sport = "soccer_epl"  # Premier League
        print(f"✅ OddsAPI collector initialized")
    
    def test_connection(self):
        """Test API connection"""
        try:
            url = f"{self.base_url}/sports"
            params = {'apiKey': self.api_key}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                remaining = response.headers.get('x-requests-remaining', 'Unknown')
                print(f"✅ API connection successful. Requests remaining: {remaining}")
                return True
            else:
                print(f"❌ API test failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def load_training_data(self, filepath):
        """Load the training dataset"""
        print(f"📂 Loading training dataset: {filepath}")
        df = pd.read_csv(filepath)
        df['date'] = pd.to_datetime(df['date'])
        
        # Get unique fixtures
        fixtures = df[['fixture_id', 'date', 'home_team', 'away_team', 'season_name']].drop_duplicates()
        fixtures = fixtures.sort_values('date')
        
        print(f"✅ Loaded {len(fixtures)} unique fixtures")
        return fixtures
    
    def get_odds_for_date(self, date_str):
        """Fetch odds for a specific date"""
        try:
            url = f"{self.base_url}/sports/{self.sport}/odds-history"
            params = {
                'apiKey': self.api_key,
                'date': date_str,
                'regions': 'uk,eu',
                'markets': 'h2h,totals,btts',
                'oddsFormat': 'decimal'
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 429:
                print("⏱️ Rate limited, waiting...")
                time.sleep(60)
                return self.get_odds_for_date(date_str)
            
            if response.status_code == 200:
                data = response.json()
                remaining = response.headers.get('x-requests-remaining', 'Unknown')
                print(f"📊 {date_str}: Found {len(data) if isinstance(data, list) else 0} matches. Remaining: {remaining}")
                return data
            else:
                print(f"❌ API error for {date_str}: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error fetching {date_str}: {e}")
            return None
    
    def collect_odds(self, training_file, max_requests=20):
        """Main collection method"""
        print("🚀 Starting odds collection")
        
        # Test connection first
        if not self.test_connection():
            return None
        
        # Load training data
        fixtures = self.load_training_data(training_file)
        
        # Group by date
        date_groups = fixtures.groupby(fixtures['date'].dt.date)
        
        collected_data = []
        requests_made = 0
        
        for match_date, group in date_groups:
            if requests_made >= max_requests:
                print(f"⚠️ Reached request limit ({max_requests})")
                break
            
            date_str = match_date.strftime('%Y-%m-%d')
            print(f"📅 Processing {len(group)} fixtures for {date_str}")
            
            odds_data = self.get_odds_for_date(date_str)
            requests_made += 1
            
            if odds_data and isinstance(odds_data, list):
                for _, fixture in group.iterrows():
                    # Store fixture info with odds availability flag
                    record = {
                        'fixture_id': fixture['fixture_id'],
                        'date': fixture['date'],
                        'home_team': fixture['home_team'],
                        'away_team': fixture['away_team'],
                        'season': fixture['season_name'],
                        'odds_available': len(odds_data) > 0,
                        'odds_count': len(odds_data)
                    }
                    collected_data.append(record)
            
            # Rate limiting
            time.sleep(1.2)
        
        # Save results
        if collected_data:
            df = pd.DataFrame(collected_data)
            output_file = f"odds_collection_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(output_file, index=False)
            
            print(f"✅ Collection complete! {len(collected_data)} records saved to {output_file}")
            print(f"🔥 Used {requests_made} API requests")
            
            # Summary
            odds_available = df['odds_available'].sum()
            print(f"📊 Summary: {odds_available}/{len(df)} fixtures had odds available")
            
            return df
        else:
            print("❌ No data collected")
            return None

def main():
    """Main function"""
    TRAINING_FILE = "premier_league_complete_4_seasons_20250624_175954.csv"
    
    print("🎯 Premier League Odds Collection")
    print("=" * 40)
    
    try:
        collector = OddsCollector()
        results = collector.collect_odds(TRAINING_FILE, max_requests=10)  # Start small
        
        if results is not None:
            print("🎉 Success! Odds collection completed.")
        else:
            print("❌ Collection failed.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 