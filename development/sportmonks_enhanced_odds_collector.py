#!/usr/bin/env python3
"""
SportMonks Enhanced Historical Odds Collector

Enhanced version based on API discovery results.
Uses correct market IDs and improved extraction logic.

Supported Markets (based on API discovery):
✅ Fulltime Result (ID: 1)
✅ Double Chance (ID: 2)  
✅ Match Goals (ID: 4)
✅ Alternative Match Goals (ID: 5)
✅ Asian Handicap (ID: 6)
✅ Goal Line (ID: 7)
✅ Final Score (ID: 8)
✅ 3-Way Handicap (ID: 9)
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
        logging.FileHandler(f'sportmonks_enhanced_odds_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SportMonksEnhancedOddsCollector:
    """Enhanced odds collector using discovered SportMonks market IDs"""
    
    def __init__(self):
        """Initialize the enhanced SportMonks odds collector"""
        self.api_token = self._get_api_token()
        self.base_url = "https://api.sportmonks.com/v3/football"
        self.odds_base_url = "https://api.sportmonks.com/v3/odds"
        self.rate_limit_delay = 1.2  # Conservative rate limiting
        
        # Define target betting markets with correct SportMonks market IDs (from API discovery)
        self.target_markets = {
            "fulltime_result": {"id": 1, "name": "Fulltime Result"},
            "double_chance": {"id": 2, "name": "Double Chance"},
            "match_goals": {"id": 4, "name": "Match Goals"},
            "alternative_match_goals": {"id": 5, "name": "Alternative Match Goals"},
            "asian_handicap": {"id": 6, "name": "Asian Handicap"},
            "goal_line": {"id": 7, "name": "Goal Line"},
            "final_score": {"id": 8, "name": "Final Score"},
            "three_way_handicap": {"id": 9, "name": "3-Way Handicap"}
        }
        
        # Priority bookmakers (from API discovery - adjusted to available ones)
        self.priority_bookmakers = [
            "bet365",      # ID: 2 - Most comprehensive
            "betfair",     # ID: 9 - Exchange odds
            "coral",       # ID: 13 - Traditional UK
            "betvictor",   # ID: 12 - Good coverage
            "888sport",    # ID: 5 - European coverage
            "10bet",       # ID: 1 - Alternative
            "betfred",     # ID: 6 - UK traditional
            "dafabet"      # ID: 14 - Asian coverage
        ]
        
        # Bookmaker ID mapping (from discovery)
        self.bookmaker_id_map = {
            1: "10Bet", 2: "bet365", 3: "188Bet", 4: "5 Dimes", 5: "888Sport",
            6: "BetFred", 7: "Bet-At-Home", 8: "BetCRIS", 9: "Betfair", 10: "BetOnline",
            11: "BetRedKings", 12: "BetVictor", 13: "Coral", 14: "Dafabet", 15: "Intertops"
        }
        
        self.collected_odds = []
        self.failed_fixtures = []
        
        logger.info("🎯 SportMonks Enhanced Odds Collector initialized")
        logger.info(f"📊 Target markets: {list(self.target_markets.keys())}")
        logger.info(f"🏪 Priority bookmakers: {self.priority_bookmakers}")

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

    def get_fixture_odds_comprehensive(self, fixture_id: int, fixture_info: Dict) -> List[Dict]:
        """Get comprehensive odds for a specific fixture using multiple approaches"""
        logger.debug(f"🎲 Getting odds for fixture {fixture_id}: {fixture_info.get('home_team')} vs {fixture_info.get('away_team')}")
        
        fixture_odds = []
        
        # Approach 1: Get fixture with odds included
        logger.debug("   🔄 Trying: fixtures/{fixture_id}?include=odds")
        endpoint = f"fixtures/{fixture_id}"
        params = {"include": "odds"}
        
        fixture_data = self._make_api_request(endpoint, params)
        
        if fixture_data and isinstance(fixture_data, dict) and "odds" in fixture_data:
            odds_list = fixture_data["odds"]
            logger.debug(f"      ✅ Found {len(odds_list)} odds from include=odds")
            
            for odds_entry in odds_list:
                odds_record = self._extract_odds_record(odds_entry, fixture_id, fixture_info)
                if odds_record:
                    fixture_odds.append(odds_record)
        
        # Approach 2: Try direct odds endpoints for each market
        if not fixture_odds:
            logger.debug("   🔄 Trying direct odds endpoints by market")
            
            for market_key, market_info in self.target_markets.items():
                market_id = market_info["id"]
                
                # Try odds endpoint with market filter
                odds_endpoint = f"fixtures/{fixture_id}/odds"
                odds_params = {"markets": market_id}
                
                odds_data = self._make_api_request(odds_endpoint, odds_params, base_url=self.odds_base_url)
                
                if odds_data:
                    if isinstance(odds_data, list):
                        for odds_entry in odds_data:
                            odds_record = self._extract_odds_record(odds_entry, fixture_id, fixture_info)
                            if odds_record:
                                fixture_odds.append(odds_record)
                    elif isinstance(odds_data, dict):
                        odds_record = self._extract_odds_record(odds_data, fixture_id, fixture_info)
                        if odds_record:
                            fixture_odds.append(odds_record)
        
        # Approach 3: Try getting all odds for the fixture without market filter
        if not fixture_odds:
            logger.debug("   🔄 Trying: odds/fixtures/{fixture_id}/odds (no filter)")
            
            odds_endpoint = f"fixtures/{fixture_id}/odds"
            odds_data = self._make_api_request(odds_endpoint, base_url=self.odds_base_url)
            
            if odds_data:
                if isinstance(odds_data, list):
                    for odds_entry in odds_data:
                        odds_record = self._extract_odds_record(odds_entry, fixture_id, fixture_info)
                        if odds_record:
                            fixture_odds.append(odds_record)
                elif isinstance(odds_data, dict):
                    odds_record = self._extract_odds_record(odds_data, fixture_id, fixture_info)
                    if odds_record:
                        fixture_odds.append(odds_record)
        
        # Approach 4: Try different odds endpoints structure
        if not fixture_odds:
            logger.debug("   🔄 Trying: football/fixtures/{fixture_id}/odds")
            
            odds_endpoint = f"fixtures/{fixture_id}/odds"
            odds_data = self._make_api_request(odds_endpoint, base_url=self.base_url)
            
            if odds_data:
                if isinstance(odds_data, list):
                    for odds_entry in odds_data:
                        odds_record = self._extract_odds_record(odds_entry, fixture_id, fixture_info)
                        if odds_record:
                            fixture_odds.append(odds_record)
                elif isinstance(odds_data, dict):
                    odds_record = self._extract_odds_record(odds_data, fixture_id, fixture_info)
                    if odds_record:
                        fixture_odds.append(odds_record)
        
        logger.debug(f"📊 Found {len(fixture_odds)} odds entries for fixture {fixture_id}")
        return fixture_odds

    def _extract_odds_record(self, odds_entry: Dict, fixture_id: int, fixture_info: Dict) -> Optional[Dict]:
        """Extract odds record from API response"""
        try:
            # Extract basic odds information
            odds_record = {
                "fixture_id": fixture_id,
                "market_id": odds_entry.get("market_id"),
                "market_name": odds_entry.get("market_name") or odds_entry.get("market_description", ""),
                "bookmaker_id": odds_entry.get("bookmaker_id"),
                "bookmaker_name": odds_entry.get("bookmaker_name", "Unknown"),
                "label": odds_entry.get("label", ""),
                "value": self._parse_odds_value(odds_entry.get("value")),
                "probability": odds_entry.get("probability"),
                "fractional": odds_entry.get("fractional"),
                "american": odds_entry.get("american"),
                "handicap": odds_entry.get("handicap"),
                "total": odds_entry.get("total"),
                "home_team": fixture_info.get("home_team"),
                "away_team": fixture_info.get("away_team"),
                "fixture_date": fixture_info.get("date")
            }
            
            # Only return if we have minimum required data
            if odds_record["market_id"] and odds_record["value"] is not None:
                return odds_record
            
        except (ValueError, TypeError) as e:
            logger.debug(f"⚠️ Failed to parse odds entry: {e}")
        
        return None

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
        logger.info("🚀 Starting enhanced odds collection for training dataset")
        
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
            
            if processed_count % 10 == 0:
                logger.info(f"🔄 [{processed_count}/{total_fixtures}] Processing fixture {fixture_id}")
            
            # Get odds for this fixture
            fixture_odds = self.get_fixture_odds_comprehensive(fixture_id, fixture_info)
            
            if fixture_odds:
                self.collected_odds.extend(fixture_odds)
                odds_found_count += 1
                logger.debug(f"   ✅ Found {len(fixture_odds)} odds for fixture {fixture_id}")
            else:
                self.failed_fixtures.append({
                    "fixture_id": fixture_id,
                    "home_team": fixture_info["home_team"],
                    "away_team": fixture_info["away_team"],
                    "date": str(fixture_info["date"])
                })
                logger.debug(f"   ⚠️ No odds found for fixture {fixture_id}")
            
            # Progress update every 25 fixtures
            if processed_count % 25 == 0:
                logger.info(f"📈 Progress: {processed_count}/{total_fixtures} processed, {odds_found_count} with odds")
        
        logger.info(f"✅ Enhanced odds collection completed!")
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
        logger.info(f"📈 Enhanced odds collection summary:")
        logger.info(f"   - Total odds entries: {len(odds_df)}")
        logger.info(f"   - Unique fixtures: {odds_df['fixture_id'].nunique()}")
        
        if 'market_name' in odds_df.columns:
            logger.info(f"   - Unique markets: {odds_df['market_name'].nunique()}")
            
            # Market breakdown
            market_counts = odds_df['market_name'].value_counts()
            logger.info("📊 Market breakdown:")
            for market, count in market_counts.head(10).items():
                logger.info(f"   - {market}: {count} entries")
        
        if 'bookmaker_name' in odds_df.columns:
            logger.info(f"   - Unique bookmakers: {odds_df['bookmaker_name'].nunique()}")
            
            # Bookmaker breakdown  
            bookie_counts = odds_df['bookmaker_name'].value_counts()
            logger.info("🏪 Bookmaker breakdown:")
            for bookie, count in bookie_counts.head(10).items():
                logger.info(f"   - {bookie}: {count} entries")
        
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
            if market_key == "fulltime_result":
                features.update(self._extract_1x2_features(best_odds, market_key))
            elif market_key in ["match_goals", "alternative_match_goals", "goal_line"]:
                features.update(self._extract_totals_features(best_odds, market_key))
            elif market_key == "asian_handicap":
                features.update(self._extract_handicap_features(best_odds, market_key))
            elif market_key == "double_chance":
                features.update(self._extract_double_chance_features(best_odds, market_key))
            elif market_key == "final_score":
                features.update(self._extract_correct_score_features(best_odds, market_key))
            elif market_key == "three_way_handicap":
                features.update(self._extract_1x2_features(best_odds, f"{market_key}_3way"))
        
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
            raw_odds_file = f"sportmonks_enhanced_raw_odds_{timestamp}.csv"
            odds_df.to_csv(raw_odds_file, index=False)
            logger.info(f"💾 Raw odds data saved to: {raw_odds_file}")
        
        # Save enhanced training dataset
        enhanced_file = f"enhanced_training_with_sportmonks_odds_{timestamp}.csv"
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
            "target_markets": list(self.target_markets.keys()),
            "available_bookmakers": list(set([odds.get('bookmaker_name') for odds in self.collected_odds])) if self.collected_odds else []
        }
        
        summary_file = f"sportmonks_enhanced_collection_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        logger.info(f"📊 Collection summary saved to: {summary_file}")
        
        # Save failed fixtures if any
        if self.failed_fixtures:
            failed_file = f"failed_fixtures_enhanced_{timestamp}.json"
            with open(failed_file, 'w') as f:
                json.dump(self.failed_fixtures, f, indent=2, default=str)
            logger.info(f"📝 Failed fixtures log saved to: {failed_file}")

def main():
    """Main execution function"""
    print("🚀 SportMonks Enhanced Historical Odds Collector")
    print("=" * 60)
    
    # Initialize collector
    collector = SportMonksEnhancedOddsCollector()
    
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
    
    print("\n✅ SportMonks enhanced odds collection completed successfully!")
    
    if not odds_df.empty:
        print(f"📊 Total odds collected: {len(odds_df)}")
        print(f"🎯 Fixtures with odds: {enhanced_df['has_odds'].sum()}/{len(enhanced_df)}")
        print(f"📈 Coverage: {enhanced_df['has_odds'].sum()/len(enhanced_df)*100:.1f}%")
        print(f"🆕 New columns added: {len(enhanced_df.columns) - len(training_df.columns)}")
    else:
        print("❌ No odds data collected. Check your API connection and data availability.")

if __name__ == "__main__":
    main()