#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OddsAPI Historical Odds Collector
Specifically designed for Premier League training dataset enhancement

This script:
1. Loads your existing training dataset
2. Filters fixtures from 2020 onwards (OddsAPI coverage period)
3. Collects historical odds for each fixture date
4. Merges odds data with existing features
5. Creates enhanced training dataset
"""

import os
import pandas as pd
import requests
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class OddsAPIHistoricalCollector:
    def __init__(self):
        self.api_key = os.getenv('ODDSAPI_KEY')
        self.base_url = "https://api.the-odds-api.com/v4"
        
        if not self.api_key:
            raise ValueError("ODDSAPI_KEY not found in .env file")
        
        print(f"Initialized with API key: {self.api_key[:10]}...")
    
    def load_training_dataset(self):
        """Load the existing training dataset"""
        print("\n=== Loading Training Dataset ===")
        
        training_files = [
            'premier_league_complete_4_seasons_20250624_175954.csv',
            'premier_league_comprehensive_training_20250624_172007.csv',
            'premier_league_final_clean_training_20250624_154624.csv'
        ]
        
        for filename in training_files:
            if os.path.exists(filename):
                print(f"Loading: {filename}")
                df = pd.read_csv(filename)
                print(f"Loaded {len(df)} fixtures")
                print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
                return df, filename
        
        print("No training dataset found.")
        return None, None
    
    def filter_odds_eligible_fixtures(self, df):
        """Filter fixtures that are eligible for odds collection (2020 onwards)"""
        print("\n=== Filtering Odds-Eligible Fixtures ===")
        
        df['Date'] = pd.to_datetime(df['Date'])
        cutoff_date = pd.to_datetime('2020-06-06')
        eligible_df = df[df['Date'] >= cutoff_date].copy()
        
        print(f"Total fixtures: {len(df)}")
        print(f"Eligible for odds (2020+): {len(eligible_df)}")
        print(f"Coverage: {len(eligible_df)/len(df)*100:.1f}%")
        
        return eligible_df
    
    def get_unique_fixture_dates(self, df):
        """Get unique fixture dates for efficient API calls"""
        print("\n=== Analyzing Fixture Dates ===")
        
        dates = df['Date'].dt.date.unique()
        dates = sorted(dates)
        
        print(f"Unique fixture dates: {len(dates)}")
        print(f"Estimated cost: {len(dates)*10} credits")
        
        return dates
    
    def collect_odds_for_date(self, date):
        """Collect odds for a specific date"""
        
        iso_date = datetime.combine(date, datetime.min.time().replace(hour=12)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        url = f"{self.base_url}/historical/sports/soccer_epl/odds"
        params = {
            'apiKey': self.api_key,
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
                
                print(f"  {date}: Success! Cost: {cost}, Remaining: {remaining}")
                
                if 'data' in data and data['data']:
                    matches = data['data']
                    print(f"    Found {len(matches)} matches")
                    return {
                        'date': date,
                        'matches': matches,
                        'cost': cost,
                        'remaining': remaining
                    }
                else:
                    print(f"    No matches found")
                    return None
            else:
                print(f"  {date}: Error {response.status_code}")
                return None
                
        except Exception as e:
            print(f"  {date}: Exception {e}")
            return None
    
    def collect_historical_odds(self, dates, max_dates=None):
        """Collect historical odds for multiple dates"""
        print(f"\n=== Collecting Historical Odds ===")
        
        if max_dates:
            dates = dates[:max_dates]
            print(f"Collecting for {len(dates)} dates (sample)")
        
        odds_data = []
        
        for i, date in enumerate(dates):
            print(f"\nProcessing {i+1}/{len(dates)}: {date}")
            
            result = self.collect_odds_for_date(date)
            if result:
                odds_data.append(result)
            
            time.sleep(1)
        
        return odds_data
    
    def extract_odds_features(self, odds_data):
        """Extract odds features for matching with training data"""
        print("\n=== Extracting Odds Features ===")
        
        odds_features = []
        
        for date_data in odds_data:
            date = date_data['date']
            matches = date_data.get('matches', [])
            
            for match in matches:
                home_team = match.get('home_team')
                away_team = match.get('away_team')
                
                match_odds = {
                    'match_date': date,
                    'api_home_team': home_team,
                    'api_away_team': away_team
                }
                
                bookmakers = match.get('bookmakers', [])
                
                home_odds = []
                away_odds = []
                draw_odds = []
                
                for bookmaker in bookmakers:
                    markets = bookmaker.get('markets', [])
                    
                    for market in markets:
                        if market.get('key') == 'h2h':
                            outcomes = market.get('outcomes', [])
                            
                            for outcome in outcomes:
                                name = outcome.get('name')
                                price = outcome.get('price')
                                
                                if name == home_team:
                                    home_odds.append(price)
                                elif name == away_team:
                                    away_odds.append(price)
                                elif name == 'Draw':
                                    draw_odds.append(price)
                
                if home_odds:
                    match_odds['avg_home_odds'] = sum(home_odds) / len(home_odds)
                if away_odds:
                    match_odds['avg_away_odds'] = sum(away_odds) / len(away_odds)
                if draw_odds:
                    match_odds['avg_draw_odds'] = sum(draw_odds) / len(draw_odds)
                
                if home_odds:
                    match_odds['implied_prob_home'] = 1 / match_odds['avg_home_odds']
                if away_odds:
                    match_odds['implied_prob_away'] = 1 / match_odds['avg_away_odds']
                if draw_odds:
                    match_odds['implied_prob_draw'] = 1 / match_odds['avg_draw_odds']
                
                odds_features.append(match_odds)
        
        return pd.DataFrame(odds_features)
    
    def merge_with_training_data(self, training_df, odds_df):
        """Merge odds features with training dataset"""
        print("\n=== Merging with Training Data ===")
        
        training_df['match_date'] = pd.to_datetime(training_df['Date']).dt.date
        
        print(f"Training fixtures: {len(training_df)}")
        print(f"Odds data: {len(odds_df)}")
        
        merged_df = training_df.merge(odds_df, on='match_date', how='left')
        
        print(f"After merge: {len(merged_df)}")
        print(f"Fixtures with odds: {len(merged_df.dropna(subset=['avg_home_odds']))}")
        
        merged_df = merged_df.drop(['match_date'], axis=1)
        
        return merged_df

def main():
    """Main execution function"""
    print("OddsAPI Historical Odds Collector")
    print("=" * 40)
    
    try:
        # Initialize collector
        collector = OddsAPIHistoricalCollector()
        
        # Load training dataset
        training_df, training_file = collector.load_training_dataset()
        if training_df is None:
            return
        
        # Filter fixtures eligible for odds collection
        eligible_df = collector.filter_odds_eligible_fixtures(training_df)
        if len(eligible_df) == 0:
            print("No fixtures eligible for odds collection.")
            return
        
        # Get unique fixture dates
        dates = collector.get_unique_fixture_dates(eligible_df)
        
        # Ask user for collection scope
        print(f"\nCollection Options:")
        print(f"1. Test sample (5 dates): ~50 credits")
        print(f"2. Small batch (20 dates): ~200 credits")
        print(f"3. Medium batch (50 dates): ~500 credits")
        print(f"4. Full collection ({len(dates)} dates): ~{len(dates)*10} credits")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == '1':
            max_dates = 5
        elif choice == '2':
            max_dates = 20
        elif choice == '3':
            max_dates = 50
        elif choice == '4':
            max_dates = None
        else:
            print("Using test sample.")
            max_dates = 5
        
        # Collect historical odds
        odds_data = collector.collect_historical_odds(dates, max_dates=max_dates)
        
        if not odds_data:
            print("No odds data collected.")
            return
        
        # Extract odds features
        odds_df = collector.extract_odds_features(odds_data)
        
        # Merge with training data
        enhanced_df = collector.merge_with_training_data(training_df, odds_df)
        
        # Save enhanced dataset
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"premier_league_enhanced_with_odds_{timestamp}.csv"
        enhanced_df.to_csv(output_filename, index=False)
        
        print(f"\n=== Collection Complete ===")
        print(f"Enhanced dataset saved: {output_filename}")
        print(f"Total fixtures: {len(enhanced_df)}")
        print(f"Fixtures with odds: {len(enhanced_df.dropna(subset=['avg_home_odds']))}")
        print(f"Original features: {len(training_df.columns)}")
        print(f"Enhanced features: {len(enhanced_df.columns)}")
        
        odds_columns = [col for col in enhanced_df.columns if 'odds' in col.lower() or 'prob' in col.lower()]
        if odds_columns:
            print(f"\nNew odds features: {odds_columns}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 