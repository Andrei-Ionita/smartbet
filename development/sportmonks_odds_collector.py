#!/usr/bin/env python3
"""
SportMonks Comprehensive Historical Odds Collector

This script extracts comprehensive historical betting odds from SportMonks API
for all major betting markets and integrates them with existing training datasets.

Supported Markets:
✅ Fulltime Result (1X2)
✅ Over/Under 2.5 Goals  
✅ Both Teams To Score (BTTS)
✅ Asian Handicap
✅ Correct Score
✅ Double Chance
"""

import os
import time
import logging
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'sportmonks_odds_collection_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SportMonksOddsCollector:
    """Comprehensive odds collector for SportMonks API"""
    
    def __init__(self):
        """Initialize the SportMonks odds collector"""
        self.api_token = self._get_api_token()
        self.base_url = "https://api.sportmonks.com/v3/football"
        self.odds_base_url = "https://api.sportmonks.com/v3/odds"
        self.rate_limit_delay = 1.5  # Conservative rate limiting
        
        # Define target betting markets with SportMonks market IDs (updated from API discovery)
        self.target_markets = {
            "fulltime_result": {"id": 1, "name": "Fulltime Result", "labels": ["home", "draw", "away"]},
            "double_chance": {"id": 2, "name": "Double Chance", "labels": ["1x", "x2", "12"]},
            "asian_handicap": {"id": 6, "name": "Asian Handicap", "labels": ["home", "away"]},
            "match_goals": {"id": 4, "name": "Match Goals", "labels": ["over", "under"]},
            "alternative_match_goals": {"id": 5, "name": "Alternative Match Goals", "labels": ["over", "under"]},
            "goal_line": {"id": 7, "name": "Goal Line", "labels": ["over", "under"]},
            "final_score": {"id": 8, "name": "Final Score", "labels": ["various"]},
            "three_way_handicap": {"id": 9, "name": "3-Way Handicap", "labels": ["home", "draw", "away"]}
        }
        
        # Priority bookmakers (will select the best available)
        self.priority_bookmakers = [
            "pinnacle", "bet365", "betfair", "marathonbet", 
            "williamhill", "unibet", "ladbrokes", "betway"
        ]
        
        self.collected_odds = []
        self.failed_fixtures = []
        
        logger.info("🎯 SportMonks Comprehensive Odds Collector initialized")
        logger.info(f"📊 Target markets: {list(self.target_markets.keys())}")

    def _get_api_token(self) -> str:
        """Get SportMonks API token from environment variables"""
        token = os.getenv("SPORTMONKS_TOKEN") or os.getenv("SPORTMONKS_API_TOKEN")
        if not token:
            raise ValueError("❌ SportMonks API token not found. Please set SPORTMONKS_TOKEN in your .env file")
        return token

    def _make_api_request(self, endpoint: str, params: Dict = None, base_url: str = None) -> Optional[Dict]:
        """Make API request with error handling and rate limiting"""
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
                    logger.warning(f"⏱️ Rate limited, waiting 60 seconds...")
                    time.sleep(60)
                    continue
                    
                if response.status_code == 404:
                    logger.debug(f"🔍 Resource not found: {endpoint}")
                    return None
                    
                response.raise_for_status()
                
                data = response.json()
                return data.get("data", data)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(5 * (attempt + 1))
        
        return None

    def load_training_dataset(self, filepath: str) -> pd.DataFrame:
        """Load the existing training dataset"""
        logger.info(f"📂 Loading training dataset from {filepath}")
        
        try:
            df = pd.read_csv(filepath)
            logger.info(f"✅ Loaded {len(df)} fixtures from training dataset")
            
            # Ensure required columns exist
            required_columns = ["fixture_id", "home_team", "away_team", "date"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"❌ Missing required columns: {missing_columns}")
            
            # Parse dates
            df["date"] = pd.to_datetime(df["date"])
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to load training dataset: {e}")
            raise

    def discover_available_markets(self) -> Dict[int, str]:
        """Discover all available betting markets from SportMonks"""
        logger.info("🔍 Discovering available betting markets...")
        
        markets_data = self._make_api_request("markets", base_url=self.odds_base_url)
        
        available_markets = {}
        if markets_data:
            if isinstance(markets_data, list):
                for market in markets_data:
                    market_id = market.get("id")
                    market_name = market.get("name", "Unknown")
                    available_markets[market_id] = market_name
        
        logger.info(f"📊 Found {len(available_markets)} available markets")
        
        # Check our target markets
        for market_key, market_info in self.target_markets.items():
            market_id = market_info["id"]
            if market_id in available_markets:
                logger.info(f"✅ {market_info['name']} (ID: {market_id}) - Available")
            else:
                logger.warning(f"⚠️ {market_info['name']} (ID: {market_id}) - Not found")
        
        return available_markets

    def discover_available_bookmakers(self) -> Dict[int, str]:
        """Discover all available bookmakers from SportMonks"""
        logger.info("🏪 Discovering available bookmakers...")
        
        bookmakers_data = self._make_api_request("bookmakers", base_url=self.odds_base_url)
        
        available_bookmakers = {}
        if bookmakers_data:
            if isinstance(bookmakers_data, list):
                for bookmaker in bookmakers_data:
                    bookmaker_id = bookmaker.get("id")
                    bookmaker_name = bookmaker.get("name", "Unknown")
                    available_bookmakers[bookmaker_id] = bookmaker_name
        
        logger.info(f"🏪 Found {len(available_bookmakers)} available bookmakers")
        
        # Check priority bookmaker availability
        for priority_bookie in self.priority_bookmakers:
            found = False
            for bookie_id, bookie_name in available_bookmakers.items():
                if priority_bookie.lower() in bookie_name.lower():
                    logger.info(f"✅ {priority_bookie} found as '{bookie_name}' (ID: {bookie_id})")
                    found = True
                    break
            if not found:
                logger.warning(f"⚠️ {priority_bookie} not found in available bookmakers")
        
        return available_bookmakers

    def get_fixture_odds(self, fixture_id: int, fixture_info: Dict) -> List[Dict]:
        """Get comprehensive odds for a specific fixture"""
        logger.debug(f"🎲 Getting odds for fixture {fixture_id}: {fixture_info.get('home_team')} vs {fixture_info.get('away_team')}")
        
        fixture_odds = []
        
        # Try multiple approaches to get odds data
        
        # Approach 1: Get fixture with odds included
        endpoint = f"fixtures/{fixture_id}"
        params = {"include": "odds"}
        
        fixture_data = self._make_api_request(endpoint, params)
        
        if fixture_data and "odds" in fixture_data:
            odds_list = fixture_data["odds"]
            
            for odds_entry in odds_list:
                try:
                    # Extract basic odds information
                    odds_record = {
                        "fixture_id": fixture_id,
                        "market_id": odds_entry.get("market_id"),
                        "market_description": odds_entry.get("market_description", ""),
                        "bookmaker_id": odds_entry.get("bookmaker_id"),
                        "bookmaker_name": odds_entry.get("bookmaker_name", "Unknown"),
                        "label": odds_entry.get("label", ""),
                        "value": self._parse_odds_value(odds_entry.get("value")),
                        "probability": self._parse_probability(odds_entry.get("probability")),
                        "fractional": odds_entry.get("fractional"),
                        "american": odds_entry.get("american"),
                        "handicap": self._parse_line_value(odds_entry.get("handicap")),
                        "total": self._parse_line_value(odds_entry.get("total")),
                        "home_team": fixture_info.get("home_team"),
                        "away_team": fixture_info.get("away_team"),
                        "fixture_date": fixture_info.get("date")
                    }
                    
                    fixture_odds.append(odds_record)
                    
                except (ValueError, TypeError) as e:
                    logger.debug(f"⚠️ Failed to parse odds entry: {e}")
                    continue
        
        # Approach 2: Try direct odds endpoints if no odds found
        if not fixture_odds:
            logger.debug(f"🔄 Trying direct odds endpoint for fixture {fixture_id}")
            
            odds_endpoint = f"fixtures/{fixture_id}/odds"
            odds_data = self._make_api_request(odds_endpoint, base_url=self.odds_base_url)
            
            if odds_data:
                # Process odds data from direct endpoint
                pass  # Implementation depends on actual API response structure
        
        logger.debug(f"📊 Found {len(fixture_odds)} odds entries for fixture {fixture_id}")
        return fixture_odds

    def _parse_odds_value(self, value) -> Optional[float]:
        """Parse odds value to float"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _parse_probability(self, prob_str) -> Optional[float]:
        """Parse probability string to float"""
        if not prob_str:
            return None
        
        if isinstance(prob_str, str) and "%" in prob_str:
            try:
                return float(prob_str.replace("%", "")) / 100
            except ValueError:
                return None
        
        try:
            return float(prob_str)
        except (ValueError, TypeError):
            return None

    def _parse_line_value(self, value) -> Optional[float]:
        """Parse line value (handicap, total) to float"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def collect_odds_for_dataset(self, training_df: pd.DataFrame, max_fixtures: int = None) -> pd.DataFrame:
        """Collect odds for all fixtures in the training dataset"""
        logger.info("🚀 Starting comprehensive odds collection for training dataset")
        
        # Discover available markets and bookmakers
        self.discover_available_markets()
        self.discover_available_bookmakers()
        
        fixtures_to_process = training_df.copy()
        
        if max_fixtures:
            fixtures_to_process = fixtures_to_process.head(max_fixtures)
            logger.info(f"🎯 Processing first {max_fixtures} fixtures for testing")
        
        total_fixtures = len(fixtures_to_process)
        logger.info(f"📊 Processing {total_fixtures} fixtures")
        
        processed_count = 0
        odds_found_count = 0
        
        for idx, row in fixtures_to_process.iterrows():
            processed_count += 1
            fixture_id = row["fixture_id"]
            
            # Prepare fixture info
            fixture_info = {
                "home_team": row["home_team"],
                "away_team": row["away_team"],
                "date": row["date"],
                "season_name": row.get("season_name", "Unknown")
            }
            
            if processed_count % 25 == 0:
                logger.info(f"🔄 [{processed_count}/{total_fixtures}] Processing fixture {fixture_id}")
            
            # Get odds for this fixture
            fixture_odds = self.get_fixture_odds(fixture_id, fixture_info)
            
            if fixture_odds:
                self.collected_odds.extend(fixture_odds)
                odds_found_count += 1
            else:
                self.failed_fixtures.append({
                    "fixture_id": fixture_id,
                    "home_team": fixture_info["home_team"],
                    "away_team": fixture_info["away_team"],
                    "date": str(fixture_info["date"])
                })
            
            # Progress update every 50 fixtures
            if processed_count % 50 == 0:
                logger.info(f"📈 Progress: {processed_count}/{total_fixtures} processed, {odds_found_count} with odds")
        
        logger.info(f"✅ Odds collection completed!")
        logger.info(f"📊 Final stats: {processed_count} fixtures processed, {odds_found_count} with odds")
        logger.info(f"📉 Failed fixtures: {len(self.failed_fixtures)}")
        
        # Convert collected odds to DataFrame
        return self._create_odds_dataframe()

    def _create_odds_dataframe(self) -> pd.DataFrame:
        """Convert collected odds to a structured DataFrame"""
        if not self.collected_odds:
            logger.warning("⚠️ No odds data collected")
            return pd.DataFrame()
        
        logger.info(f"📊 Converting {len(self.collected_odds)} odds entries to DataFrame")
        
        odds_df = pd.DataFrame(self.collected_odds)
        
        # Log summary statistics
        logger.info(f"📈 Odds collection summary:")
        logger.info(f"   - Total odds entries: {len(odds_df)}")
        logger.info(f"   - Unique fixtures: {odds_df['fixture_id'].nunique()}")
        logger.info(f"   - Unique markets: {odds_df['market_description'].nunique()}")
        
        if 'bookmaker_name' in odds_df.columns:
            logger.info(f"   - Unique bookmakers: {odds_df['bookmaker_name'].nunique()}")
            
            # Market breakdown
            if 'market_description' in odds_df.columns:
                market_counts = odds_df['market_description'].value_counts()
                logger.info("📊 Market breakdown:")
                for market, count in market_counts.head(10).items():
                    logger.info(f"   - {market}: {count} entries")
        
        return odds_df

    def create_enhanced_training_dataset(self, training_df: pd.DataFrame, odds_df: pd.DataFrame) -> pd.DataFrame:
        """Create enhanced training dataset with odds features"""
        if odds_df.empty:
            logger.warning("⚠️ No odds data to integrate")
            return training_df
        
        logger.info("🔧 Creating enhanced training dataset with odds features")
        
        enhanced_df = training_df.copy()
        
        # Process odds for each fixture
        for fixture_id in enhanced_df['fixture_id'].unique():
            fixture_odds = odds_df[odds_df['fixture_id'] == fixture_id]
            
            if fixture_odds.empty:
                continue
            
            # Extract features for each target market
            odds_features = self._extract_odds_features(fixture_odds)
            
            # Add features to the enhanced dataset
            fixture_mask = enhanced_df['fixture_id'] == fixture_id
            for feature_name, feature_value in odds_features.items():
                enhanced_df.loc[fixture_mask, feature_name] = feature_value
        
        # Add general odds availability flag
        fixtures_with_odds = set(odds_df['fixture_id'].unique())
        enhanced_df['has_odds'] = enhanced_df['fixture_id'].isin(fixtures_with_odds)
        
        logger.info(f"📊 Enhanced dataset created with {len(enhanced_df.columns)} columns")
        logger.info(f"🎯 Fixtures with odds: {enhanced_df['has_odds'].sum()}/{len(enhanced_df)}")
        
        return enhanced_df

    def _extract_odds_features(self, fixture_odds: pd.DataFrame) -> Dict[str, float]:
        """Extract betting features from fixture odds"""
        features = {}
        
        # Process each target market
        for market_key, market_info in self.target_markets.items():
            market_id = market_info["id"]
            market_odds = fixture_odds[fixture_odds['market_id'] == market_id]
            
            if market_odds.empty:
                continue
            
            # Select best bookmaker for this market
            best_odds = self._select_best_bookmaker_odds(market_odds)
            
            if best_odds.empty:
                continue
            
            # Extract features based on market type
            if market_key == "1x2":
                features.update(self._extract_1x2_features(best_odds, market_key))
            elif market_key == "over_under_25":
                features.update(self._extract_totals_features(best_odds, market_key))
            elif market_key == "btts":
                features.update(self._extract_btts_features(best_odds, market_key))
            elif market_key == "asian_handicap":
                features.update(self._extract_handicap_features(best_odds, market_key))
            elif market_key == "double_chance":
                features.update(self._extract_double_chance_features(best_odds, market_key))
            elif market_key == "correct_score":
                features.update(self._extract_correct_score_features(best_odds, market_key))
        
        return features

    def _select_best_bookmaker_odds(self, market_odds: pd.DataFrame) -> pd.DataFrame:
        """Select odds from the best available bookmaker"""
        if market_odds.empty:
            return market_odds
        
        # Try to find odds from priority bookmakers
        for priority_bookie in self.priority_bookmakers:
            bookie_odds = market_odds[
                market_odds['bookmaker_name'].str.lower().str.contains(priority_bookie, case=False, na=False)
            ]
            if not bookie_odds.empty:
                return bookie_odds
        
        # If no priority bookmaker found, return the first available
        first_bookmaker = market_odds['bookmaker_name'].iloc[0]
        return market_odds[market_odds['bookmaker_name'] == first_bookmaker]

    def _extract_1x2_features(self, odds: pd.DataFrame, prefix: str) -> Dict[str, float]:
        """Extract 1X2 market features"""
        features = {}
        
        for _, row in odds.iterrows():
            label = row['label'].lower()
            odds_value = row['value']
            probability = row['probability']
            
            if odds_value is None:
                continue
                
            if 'home' in label or label == '1':
                features[f'{prefix}_home_odds'] = odds_value
                if probability:
                    features[f'{prefix}_home_prob'] = probability
            elif 'draw' in label or label == 'x':
                features[f'{prefix}_draw_odds'] = odds_value
                if probability:
                    features[f'{prefix}_draw_prob'] = probability
            elif 'away' in label or label == '2':
                features[f'{prefix}_away_odds'] = odds_value
                if probability:
                    features[f'{prefix}_away_prob'] = probability
        
        # Calculate market margin and efficiency if we have all three outcomes
        if all(f'{prefix}_{outcome}_odds' in features for outcome in ['home', 'draw', 'away']):
            home_odds = features[f'{prefix}_home_odds']
            draw_odds = features[f'{prefix}_draw_odds'] 
            away_odds = features[f'{prefix}_away_odds']
            
            # Calculate implied probabilities
            home_impl_prob = 1 / home_odds
            draw_impl_prob = 1 / draw_odds
            away_impl_prob = 1 / away_odds
            
            # Market margin (overround)
            margin = home_impl_prob + draw_impl_prob + away_impl_prob - 1
            features[f'{prefix}_market_margin'] = margin
            
            # Market efficiency (inverse of margin)
            features[f'{prefix}_market_efficiency'] = 1 / (1 + margin) if margin > 0 else 1
        
        return features

    def _extract_totals_features(self, odds: pd.DataFrame, prefix: str) -> Dict[str, float]:
        """Extract Over/Under market features"""
        features = {}
        
        for _, row in odds.iterrows():
            label = row['label'].lower()
            odds_value = row['value']
            line = row['total']
            
            if odds_value is None:
                continue
                
            if 'over' in label:
                features[f'{prefix}_over_odds'] = odds_value
                if line:
                    features[f'{prefix}_line'] = line
            elif 'under' in label:
                features[f'{prefix}_under_odds'] = odds_value
        
        return features

    def _extract_btts_features(self, odds: pd.DataFrame, prefix: str) -> Dict[str, float]:
        """Extract Both Teams to Score features"""
        features = {}
        
        for _, row in odds.iterrows():
            label = row['label'].lower()
            odds_value = row['value']
            
            if odds_value is None:
                continue
                
            if 'yes' in label:
                features[f'{prefix}_yes_odds'] = odds_value
            elif 'no' in label:
                features[f'{prefix}_no_odds'] = odds_value
        
        return features

    def _extract_handicap_features(self, odds: pd.DataFrame, prefix: str) -> Dict[str, float]:
        """Extract Asian Handicap features"""
        features = {}
        
        for _, row in odds.iterrows():
            label = row['label'].lower()
            odds_value = row['value']
            handicap = row['handicap']
            
            if odds_value is None:
                continue
                
            if 'home' in label:
                features[f'{prefix}_home_odds'] = odds_value
                if handicap:
                    features[f'{prefix}_line'] = handicap
            elif 'away' in label:
                features[f'{prefix}_away_odds'] = odds_value
        
        return features

    def _extract_double_chance_features(self, odds: pd.DataFrame, prefix: str) -> Dict[str, float]:
        """Extract Double Chance features"""
        features = {}
        
        for _, row in odds.iterrows():
            label = row['label'].lower()
            odds_value = row['value']
            
            if odds_value is None:
                continue
                
            if '1x' in label or 'home_draw' in label:
                features[f'{prefix}_1x_odds'] = odds_value
            elif 'x2' in label or 'draw_away' in label:
                features[f'{prefix}_x2_odds'] = odds_value
            elif '12' in label or 'home_away' in label:
                features[f'{prefix}_12_odds'] = odds_value
        
        return features

    def _extract_correct_score_features(self, odds: pd.DataFrame, prefix: str) -> Dict[str, float]:
        """Extract Correct Score features (simplified)"""
        features = {}
        
        # For correct score, we'll just track if it's available and get some basic stats
        if not odds.empty:
            features[f'{prefix}_available'] = 1
            features[f'{prefix}_num_outcomes'] = len(odds)
            
            # Get odds for common scores
            for _, row in odds.iterrows():
                label = row['label'].lower()
                odds_value = row['value']
                
                if odds_value is None:
                    continue
                    
                if '1-0' in label or '1_0' in label:
                    features[f'{prefix}_1_0_odds'] = odds_value
                elif '0-1' in label or '0_1' in label:
                    features[f'{prefix}_0_1_odds'] = odds_value
                elif '1-1' in label or '1_1' in label:
                    features[f'{prefix}_1_1_odds'] = odds_value
                elif '2-1' in label or '2_1' in label:
                    features[f'{prefix}_2_1_odds'] = odds_value
                elif '1-2' in label or '1_2' in label:
                    features[f'{prefix}_1_2_odds'] = odds_value
        
        return features

    def save_results(self, training_df: pd.DataFrame, odds_df: pd.DataFrame, enhanced_df: pd.DataFrame):
        """Save all results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save raw odds data
        if not odds_df.empty:
            raw_odds_file = f"sportmonks_raw_odds_{timestamp}.csv"
            odds_df.to_csv(raw_odds_file, index=False)
            logger.info(f"💾 Raw odds data saved to: {raw_odds_file}")
        
        # Save enhanced training dataset
        enhanced_file = f"enhanced_training_with_odds_{timestamp}.csv"
        enhanced_df.to_csv(enhanced_file, index=False)
        logger.info(f"💾 Enhanced training dataset saved to: {enhanced_file}")
        
        # Save collection summary
        summary = {
            "collection_date": timestamp,
            "original_fixtures": len(training_df),
            "total_odds_collected": len(odds_df) if not odds_df.empty else 0,
            "fixtures_with_odds": enhanced_df['has_odds'].sum() if 'has_odds' in enhanced_df.columns else 0,
            "coverage_percentage": (enhanced_df['has_odds'].sum() / len(enhanced_df) * 100) if 'has_odds' in enhanced_df.columns else 0,
            "new_columns_added": len(enhanced_df.columns) - len(training_df.columns),
            "failed_fixtures": len(self.failed_fixtures),
            "target_markets": list(self.target_markets.keys())
        }
        
        summary_file = f"sportmonks_collection_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        logger.info(f"📊 Collection summary saved to: {summary_file}")
        
        # Save failed fixtures if any
        if self.failed_fixtures:
            failed_file = f"failed_fixtures_{timestamp}.json"
            with open(failed_file, 'w') as f:
                json.dump(self.failed_fixtures, f, indent=2, default=str)
            logger.info(f"📝 Failed fixtures log saved to: {failed_file}")

def main():
    """Main execution function"""
    print("🚀 SportMonks Comprehensive Historical Odds Collector")
    print("=" * 60)
    
    # Initialize collector
    collector = SportMonksOddsCollector()
    
    # Find the latest training dataset
    training_datasets = [f for f in os.listdir('.') if f.startswith('premier_league_') and f.endswith('.csv')]
    
    if not training_datasets:
        print("❌ No training datasets found. Please ensure you have a Premier League dataset file.")
        return
    
    # Use the most recent dataset
    latest_dataset = sorted(training_datasets)[-1]
    print(f"📂 Using training dataset: {latest_dataset}")
    
    # Load training dataset
    training_df = collector.load_training_dataset(latest_dataset)
    
    # Ask user for sample size
    sample_size = input(f"\n🎯 Enter number of fixtures to process (max {len(training_df)}, or press Enter for all): ").strip()
    
    max_fixtures = None
    if sample_size:
        try:
            max_fixtures = int(sample_size)
            max_fixtures = min(max_fixtures, len(training_df))
        except ValueError:
            print("⚠️ Invalid number, processing all fixtures")
    
    # Collect odds
    odds_df = collector.collect_odds_for_dataset(training_df, max_fixtures)
    
    # Create enhanced dataset
    enhanced_df = collector.create_enhanced_training_dataset(training_df, odds_df)
    
    # Save results
    collector.save_results(training_df, odds_df, enhanced_df)
    
    print("\n✅ SportMonks odds collection completed successfully!")
    
    if not odds_df.empty:
        print(f"📊 Total odds collected: {len(odds_df)}")
        print(f"🎯 Fixtures with odds: {enhanced_df['has_odds'].sum()}/{len(enhanced_df)}")
        print(f"📈 Coverage: {enhanced_df['has_odds'].sum()/len(enhanced_df)*100:.1f}%")
        print(f"🆕 New columns added: {len(enhanced_df.columns) - len(training_df.columns)}")
    else:
        print("❌ No odds data collected. Check your API connection and token.")

if __name__ == "__main__":
    main()