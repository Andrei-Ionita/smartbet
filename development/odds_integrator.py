#!/usr/bin/env python3
import os
import requests
import pandas as pd
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class OddsIntegrator:
    def __init__(self):
        self.api_key = os.getenv('ODDSAPI_KEY')
        if not self.api_key:
            raise ValueError("ODDSAPI_KEY required in .env file")
        
        self.base_url = "https://api.the-odds-api.com/v4"
        self.sport = "soccer_epl"
        
    def test_connection(self):
        """Test API connection"""
        url = f"{self.base_url}/sports"
        params = {'apiKey': self.api_key}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                remaining = response.headers.get('x-requests-remaining', 'Unknown')
                print(f"✅ API connected. Requests remaining: {remaining}")
                return True
            else:
                print(f"❌ API error: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def get_odds_for_date(self, date_str):
        """Fetch historical odds for a date"""
        url = f"{self.base_url}/sports/{self.sport}/odds-history"
        params = {
            'apiKey': self.api_key,
            'date': date_str,
            'regions': 'uk,eu',
            'markets': 'h2h,totals,btts',
            'oddsFormat': 'decimal'
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 429:
                print("Rate limited, waiting...")
                time.sleep(60)
                return self.get_odds_for_date(date_str)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error {response.status_code} for {date_str}")
                return None
        except Exception as e:
            print(f"Request failed for {date_str}: {e}")
            return None
    
    def match_teams(self, fixture_home, fixture_away, odds_data):
        """Match fixture teams to odds data"""
        for match in odds_data:
            api_home = match.get('home_team', '').lower()
            api_away = match.get('away_team', '').lower()
            
            if (fixture_home.lower() in api_home or api_home in fixture_home.lower()) and \
               (fixture_away.lower() in api_away or api_away in fixture_away.lower()):
                return match
        return None
    
    def extract_odds(self, odds_data):
        """Extract key odds from API response"""
        extracted = {}
        
        for bookmaker in odds_data.get('bookmakers', []):
            bookie = bookmaker.get('key', '')
            
            for market in bookmaker.get('markets', []):
                market_key = market.get('key', '')
                
                if market_key == 'h2h':  # 1X2
                    for outcome in market.get('outcomes', []):
                        name = outcome.get('name', '').lower()
                        price = outcome.get('price', 0)
                        
                        if 'home' in name or odds_data.get('home_team', '').lower() in name:
                            extracted[f'{bookie}_home'] = price
                        elif 'away' in name or odds_data.get('away_team', '').lower() in name:
                            extracted[f'{bookie}_away'] = price
                        elif 'draw' in name:
                            extracted[f'{bookie}_draw'] = price
                
                elif market_key == 'totals':  # Over/Under
                    for outcome in market.get('outcomes', []):
                        name = outcome.get('name', '').lower()
                        price = outcome.get('price', 0)
                        point = outcome.get('point', 0)
                        
                        if point == 2.5:
                            if 'over' in name:
                                extracted[f'{bookie}_over25'] = price
                            elif 'under' in name:
                                extracted[f'{bookie}_under25'] = price
        
        return extracted
    
    def integrate_dataset(self, training_file, max_requests=20):
        """Main integration method"""
        print("🚀 Starting odds integration")
        
        if not self.test_connection():
            return None
        
        # Load training data
        print(f"📂 Loading {training_file}")
        df = pd.read_csv(training_file)
        df['date'] = pd.to_datetime(df['date'])
        
        # Get unique fixtures
        fixtures = df[['fixture_id', 'date', 'home_team', 'away_team', 'outcome']].drop_duplicates()
        fixtures = fixtures.sort_values('date')
        
        print(f"✅ Processing {len(fixtures)} fixtures")
        
        # Group by date
        date_groups = fixtures.groupby(fixtures['date'].dt.date)
        
        enhanced_data = []
        requests_made = 0
        
        for match_date, group in date_groups:
            if requests_made >= max_requests:
                break
            
            date_str = match_date.strftime('%Y-%m-%d')
            print(f"📅 {date_str}: {len(group)} fixtures")
            
            odds_data = self.get_odds_for_date(date_str)
            requests_made += 1
            
            for _, fixture in group.iterrows():
                record = {
                    'fixture_id': fixture['fixture_id'],
                    'date': fixture['date'],
                    'home_team': fixture['home_team'],
                    'away_team': fixture['away_team'],
                    'outcome': fixture['outcome']
                }
                
                if odds_data:
                    match_odds = self.match_teams(
                        fixture['home_team'], 
                        fixture['away_team'], 
                        odds_data
                    )
                    
                    if match_odds:
                        odds_features = self.extract_odds(match_odds)
                        record.update(odds_features)
                        record['has_odds'] = True
                        print(f"✅ {fixture['home_team']} vs {fixture['away_team']}")
                    else:
                        record['has_odds'] = False
                        print(f"❌ {fixture['home_team']} vs {fixture['away_team']}")
                else:
                    record['has_odds'] = False
                
                enhanced_data.append(record)
            
            time.sleep(1.5)  # Rate limiting
        
        # Create enhanced dataset
        enhanced_df = pd.DataFrame(enhanced_data)
        
        # Save results
        output_file = f"enhanced_training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        enhanced_df.to_csv(output_file, index=False)
        
        odds_count = enhanced_df['has_odds'].sum()
        total_count = len(enhanced_df)
        
        print(f"✅ Integration complete!")
        print(f"📊 {odds_count}/{total_count} fixtures with odds ({odds_count/total_count*100:.1f}%)")
        print(f"💾 Saved to: {output_file}")
        print(f"🔥 Used {requests_made} API requests")
        
        return enhanced_df

def main():
    print("🎯 Odds Integration for Training Dataset")
    print("=" * 45)
    
    try:
        integrator = OddsIntegrator()
        
        result = integrator.integrate_dataset(
            "premier_league_complete_4_seasons_20250624_175954.csv",
            max_requests=15  # Conservative start
        )
        
        if result is not None:
            print("\n🎉 Success! Dataset enhanced with odds data.")
        else:
            print("\n❌ Integration failed.")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 