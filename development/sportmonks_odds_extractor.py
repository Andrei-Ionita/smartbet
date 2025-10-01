#!/usr/bin/env python3
"""
SportMonks Odds Extractor - Safe Approach

This script safely extracts odds data from SportMonks API and saves it to a separate CSV file.
Then uses a separate merger script to combine with the training dataset.

Strategy:
1. Extract odds to separate CSV file
2. Keep original training dataset untouched  
3. Merge in separate step
"""

import os
import time
import requests
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

class SportMonksOddsExtractor:
    """Safe odds extractor for SportMonks API"""
    
    def __init__(self):
        """Initialize the odds extractor"""
        self.api_token = self._get_api_token()
        self.base_url = "https://api.sportmonks.com/v3/football"
        self.odds_base_url = "https://api.sportmonks.com/v3/odds"
        self.rate_limit_delay = 1.2
        
        # Target markets from API discovery
        self.target_markets = {
            1: "Fulltime Result",
            2: "Double Chance", 
            4: "Match Goals",
            5: "Alternative Match Goals",
            6: "Asian Handicap",
            7: "Goal Line",
            8: "Final Score",
            9: "3-Way Handicap"
        }
        
        # Priority bookmakers
        self.priority_bookmakers = ["bet365", "betfair", "coral", "betvictor", "888sport"]
        
        self.extracted_odds = []
        self.failed_fixtures = []
        
        print("🎯 SportMonks Odds Extractor initialized")
        print(f"📊 Target markets: {list(self.target_markets.values())}")

    def _get_api_token(self) -> str:
        """Get SportMonks API token"""
        token = os.getenv("SPORTMONKS_TOKEN") or os.getenv("SPORTMONKS_API_TOKEN")
        if not token:
            raise ValueError("❌ SportMonks API token not found. Please set SPORTMONKS_TOKEN in your .env file")
        return token

    def _make_api_request(self, endpoint: str, params: Dict = None, base_url: str = None) -> Optional[Dict]:
        """Make API request with error handling"""
        if base_url is None:
            base_url = self.base_url
            
        url = f"{base_url}/{endpoint}"
        
        if params is None:
            params = {}
        
        params['api_token'] = self.api_token
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                time.sleep(self.rate_limit_delay)
                response = requests.get(url, params=params, timeout=30)
                
                if response.status_code == 429:
                    print("⏱️ Rate limited, waiting 60 seconds...")
                    time.sleep(60)
                    continue
                    
                if response.status_code == 404:
                    return None
                    
                response.raise_for_status()
                data = response.json()
                return data.get("data", data)
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(5 * (attempt + 1))
        
        return None

    def load_fixture_ids(self, training_file: str) -> pd.DataFrame:
        """Load fixture IDs from training dataset"""
        print(f"📂 Loading fixture IDs from {training_file}")
        
        try:
            df = pd.read_csv(training_file)
            print(f"✅ Loaded {len(df)} fixtures")
            
            # Ensure required columns exist
            required_columns = ["fixture_id", "home_team", "away_team", "date"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"❌ Missing required columns: {missing_columns}")
            
            return df[["fixture_id", "home_team", "away_team", "date"]].copy()
            
        except Exception as e:
            print(f"❌ Failed to load training dataset: {e}")
            raise

    def extract_fixture_odds(self, fixture_id: int, home_team: str, away_team: str, date: str) -> List[Dict]:
        """Extract odds for a single fixture"""
        fixture_odds = []
        
        # Try multiple approaches to get odds
        approaches = [
            ("include=odds", f"fixtures/{fixture_id}", {"include": "odds"}),
            ("direct odds", f"fixtures/{fixture_id}/odds", {})
        ]
        
        for approach_name, endpoint, params in approaches:
            try:
                if "odds/" in endpoint:
                    data = self._make_api_request(endpoint, params, base_url=self.odds_base_url)
                else:
                    data = self._make_api_request(endpoint, params)
                
                if data:
                    if isinstance(data, dict) and "odds" in data:
                        odds_list = data["odds"]
                    elif isinstance(data, list):
                        odds_list = data
                    else:
                        continue
                    
                    for odds_entry in odds_list:
                        odds_record = self._parse_odds_entry(odds_entry, fixture_id, home_team, away_team, date)
                        if odds_record:
                            fixture_odds.append(odds_record)
                    
                    if fixture_odds:
                        break  # Found odds, no need to try other approaches
                        
            except Exception as e:
                continue
        
        return fixture_odds

    def _parse_odds_entry(self, odds_entry: Dict, fixture_id: int, home_team: str, away_team: str, date: str) -> Optional[Dict]:
        """Parse a single odds entry"""
        try:
            market_id = odds_entry.get("market_id")
            value = odds_entry.get("value")
            
            if not market_id or not value:
                return None
            
            # Convert value to float
            try:
                odds_value = float(value)
            except (ValueError, TypeError):
                return None
            
            return {
                "fixture_id": fixture_id,
                "home_team": home_team,
                "away_team": away_team,
                "date": date,
                "market_id": market_id,
                "market_name": self.target_markets.get(market_id, f"Market_{market_id}"),
                "bookmaker_id": odds_entry.get("bookmaker_id"),
                "bookmaker_name": odds_entry.get("bookmaker_name", "Unknown"),
                "label": odds_entry.get("label", ""),
                "odds_value": odds_value,
                "probability": odds_entry.get("probability"),
                "fractional": odds_entry.get("fractional"),
                "american": odds_entry.get("american"),
                "handicap": odds_entry.get("handicap"),
                "total": odds_entry.get("total")
            }
            
        except Exception as e:
            return None

    def extract_odds_for_dataset(self, fixtures_df: pd.DataFrame, max_fixtures: int = None) -> pd.DataFrame:
        """Extract odds for all fixtures in the dataset"""
        print("🚀 Starting odds extraction")
        
        if max_fixtures:
            fixtures_df = fixtures_df.head(max_fixtures)
            print(f"🎯 Processing first {max_fixtures} fixtures")
        
        total_fixtures = len(fixtures_df)
        print(f"📊 Processing {total_fixtures} fixtures")
        
        processed_count = 0
        odds_found_count = 0
        
        for idx, row in fixtures_df.iterrows():
            processed_count += 1
            fixture_id = row["fixture_id"]
            home_team = row["home_team"]
            away_team = row["away_team"]
            date = str(row["date"])
            
            if processed_count % 10 == 0:
                print(f"🔄 [{processed_count}/{total_fixtures}] Processing fixture {fixture_id}: {home_team} vs {away_team}")
            
            # Extract odds for this fixture
            fixture_odds = self.extract_fixture_odds(fixture_id, home_team, away_team, date)
            
            if fixture_odds:
                self.extracted_odds.extend(fixture_odds)
                odds_found_count += 1
                print(f"   ✅ Found {len(fixture_odds)} odds entries")
            else:
                self.failed_fixtures.append({
                    "fixture_id": fixture_id,
                    "home_team": home_team,
                    "away_team": away_team,
                    "date": date
                })
                print(f"   ⚠️ No odds found")
            
            # Progress update
            if processed_count % 25 == 0:
                print(f"📈 Progress: {processed_count}/{total_fixtures} processed, {odds_found_count} with odds")
        
        print(f"✅ Odds extraction completed!")
        print(f"📊 Final stats: {processed_count} fixtures processed, {odds_found_count} with odds")
        print(f"📊 Total odds entries: {len(self.extracted_odds)}")
        print(f"📉 Failed fixtures: {len(self.failed_fixtures)}")
        
        # Convert to DataFrame
        if self.extracted_odds:
            odds_df = pd.DataFrame(self.extracted_odds)
            
            # Display summary
            print(f"\n📈 Odds extraction summary:")
            print(f"   - Total odds entries: {len(odds_df)}")
            print(f"   - Unique fixtures: {odds_df['fixture_id'].nunique()}")
            
            if 'market_name' in odds_df.columns:
                print(f"   - Unique markets: {odds_df['market_name'].nunique()}")
                market_counts = odds_df['market_name'].value_counts()
                print("📊 Market breakdown:")
                for market, count in market_counts.head(5).items():
                    print(f"   - {market}: {count} entries")
            
            if 'bookmaker_name' in odds_df.columns:
                print(f"   - Unique bookmakers: {odds_df['bookmaker_name'].nunique()}")
                bookie_counts = odds_df['bookmaker_name'].value_counts()
                print("🏪 Top bookmakers:")
                for bookie, count in bookie_counts.head(5).items():
                    print(f"   - {bookie}: {count} entries")
            
            return odds_df
        else:
            return pd.DataFrame()

    def save_odds_file(self, odds_df: pd.DataFrame) -> str:
        """Save odds data to a separate CSV file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sportmonks_extracted_odds_{timestamp}.csv"
        
        if not odds_df.empty:
            odds_df.to_csv(filename, index=False)
            print(f"💾 Odds data saved to: {filename}")
        else:
            print("⚠️ No odds data to save")
        
        # Save extraction summary
        summary = {
            "extraction_date": timestamp,
            "total_odds_extracted": len(odds_df) if not odds_df.empty else 0,
            "unique_fixtures_with_odds": odds_df['fixture_id'].nunique() if not odds_df.empty else 0,
            "unique_markets": odds_df['market_name'].nunique() if not odds_df.empty and 'market_name' in odds_df.columns else 0,
            "unique_bookmakers": odds_df['bookmaker_name'].nunique() if not odds_df.empty and 'bookmaker_name' in odds_df.columns else 0,
            "failed_fixtures": len(self.failed_fixtures),
            "target_markets": self.target_markets
        }
        
        summary_file = f"sportmonks_extraction_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"📊 Extraction summary saved to: {summary_file}")
        
        # Save failed fixtures if any
        if self.failed_fixtures:
            failed_file = f"sportmonks_failed_fixtures_{timestamp}.json"
            with open(failed_file, 'w') as f:
                json.dump(self.failed_fixtures, f, indent=2, default=str)
            print(f"📝 Failed fixtures saved to: {failed_file}")
        
        return filename

def main():
    """Main execution function"""
    print("🚀 SportMonks Odds Extractor - Safe Mode")
    print("=" * 50)
    print("This script safely extracts odds data to a separate file")
    print("Your original training dataset will NOT be modified")
    print("=" * 50)
    
    # Initialize extractor
    extractor = SportMonksOddsExtractor()
    
    # Find training datasets
    training_datasets = [f for f in os.listdir('.') if f.startswith('premier_league_') and f.endswith('.csv')]
    
    if not training_datasets:
        print("❌ No training datasets found")
        return
    
    # Use the most recent dataset
    latest_dataset = sorted(training_datasets)[-1]
    print(f"📂 Using training dataset: {latest_dataset}")
    
    # Load fixture IDs only
    fixtures_df = extractor.load_fixture_ids(latest_dataset)
    
    # Ask for sample size
    sample_size = input(f"\n🎯 Enter number of fixtures to process (max {len(fixtures_df)}, recommended start: 20): ").strip()
    
    max_fixtures = None
    if sample_size:
        try:
            max_fixtures = int(sample_size)
            max_fixtures = min(max_fixtures, len(fixtures_df))
            print(f"🎯 Will process {max_fixtures} fixtures")
        except ValueError:
            print("⚠️ Invalid number, processing all fixtures")
    
    # Extract odds
    odds_df = extractor.extract_odds_for_dataset(fixtures_df, max_fixtures)
    
    # Save odds file
    odds_filename = extractor.save_odds_file(odds_df)
    
    print("\n✅ Odds extraction completed!")
    
    if not odds_df.empty:
        print(f"📊 Extracted odds for {odds_df['fixture_id'].nunique()} fixtures")
        print(f"📈 Total odds entries: {len(odds_df)}")
        print(f"💾 Odds saved to: {odds_filename}")
        print(f"\n🔄 Next step: Use a merger script to combine with your training dataset")
    else:
        print("❌ No odds data extracted")
        print("💡 Try with more recent fixtures or check your API subscription")

if __name__ == "__main__":
    main()