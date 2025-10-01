"""
Historical Odds Collector for OddsAPI Integration
Fetches comprehensive historical odds for Premier League fixtures from the paid OddsAPI
and stores them in a structured format for integration with the training dataset.
"""

import os
import time
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'historical_odds_collection_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OddsAPIHistoricalCollector:
    """Collects historical odds from OddsAPI for Premier League fixtures"""
    
    def __init__(self):
        """Initialize the odds collector"""
        self.api_key = os.getenv('ODDSAPI_KEY')
        if not self.api_key:
            print("❌ ODDSAPI_KEY not found in environment variables")
            print("💡 Please create a .env file in the project root with:")
            print("   ODDSAPI_KEY=your_actual_api_key_here")
            raise ValueError("ODDSAPI_KEY environment variable required")
        
        self.base_url = "https://api.the-odds-api.com/v4"
        self.sport = "soccer_epl"  # Premier League
        self.regions = "uk,eu,us"
        self.rate_limit_delay = 1.2  # Be conservative with rate limiting
        
        # Target markets for comprehensive betting analysis
        self.markets = {
            "h2h": "Match Winner (1X2)",
            "totals": "Over/Under Goals", 
            "btts": "Both Teams to Score",
            "spreads": "Asian Handicap",
            "double_chance": "Double Chance"
        }
        
        # Premium bookmakers for quality odds
        self.bookmakers = [
            "pinnacle", "bet365", "betfair", "marathonbet", 
            "williamhill", "unibet", "betway", "ladbrokes"
        ]
        
        self.session = requests.Session()
        self.odds_storage = []
        
        logger.info("🔑 OddsAPI Historical Collector initialized")
        logger.info(f"🎯 Target sport: {self.sport}")
        logger.info(f"📊 Target markets: {list(self.markets.keys())}")
    
    def test_api_connection(self) -> bool:
        """Test API connection and check remaining quota"""
        try:
            url = f"{self.base_url}/sports"
            params = {'apiKey': self.api_key}
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 401:
                logger.error("❌ API key authentication failed")
                return False
            elif response.status_code == 429:
                logger.error("❌ Rate limit exceeded")
                return False
            
            response.raise_for_status()
            
            remaining = response.headers.get('x-requests-remaining', 'Unknown')
            used = response.headers.get('x-requests-used', 'Unknown')
            
            logger.info(f"✅ API connection successful")
            logger.info(f"📊 Quota: {used} used, {remaining} remaining")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ API connection test failed: {e}")
            return False
    
    def load_training_fixtures(self, filepath: str) -> pd.DataFrame:
        """Load Premier League fixtures from training dataset"""
        logger.info(f"📂 Loading training dataset: {filepath}")
        
        try:
            df = pd.read_csv(filepath)
            df['date'] = pd.to_datetime(df['date'])
            
            # Extract unique fixtures for odds collection
            fixtures = df[['fixture_id', 'date', 'home_team', 'away_team', 'season_name']].copy()
            fixtures = fixtures.drop_duplicates(subset=['fixture_id'])
            fixtures = fixtures.sort_values('date')
            
            logger.info(f"✅ Loaded {len(fixtures)} unique fixtures")
            logger.info(f"📅 Date range: {fixtures['date'].min()} to {fixtures['date'].max()}")
            
            return fixtures
            
        except Exception as e:
            logger.error(f"❌ Failed to load training dataset: {e}")
            raise
    
    def get_historical_odds_by_date(self, target_date: str) -> Optional[List[Dict]]:
        """
        Fetch historical odds for all Premier League matches on a specific date
        
        Args:
            target_date: Date in YYYY-MM-DD format
            
        Returns:
            List of match odds or None if failed
        """
        try:
            # Use the historical odds endpoint
            url = f"{self.base_url}/sports/{self.sport}/odds-history"
            
            params = {
                'apiKey': self.api_key,
                'regions': self.regions,
                'markets': ','.join(self.markets.keys()),
                'bookmakers': ','.join(self.bookmakers),
                'date': target_date,
                'oddsFormat': 'decimal'
            }
            
            logger.debug(f"🔍 Fetching odds for {target_date}")
            
            response = self.session.get(url, params=params, timeout=30)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('retry-after', 60))
                logger.warning(f"⏱️ Rate limited, waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self.get_historical_odds_by_date(target_date)
            
            response.raise_for_status()
            data = response.json()
            
            # Log API usage
            remaining = response.headers.get('x-requests-remaining', 'Unknown')
            logger.info(f"📊 Requests remaining: {remaining}")
            
            if isinstance(data, list):
                logger.info(f"✅ Found {len(data)} matches with odds for {target_date}")
                return data
            else:
                logger.warning(f"⚠️ Unexpected response format for {target_date}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ API request failed for {target_date}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error for {target_date}: {e}")
            return None
    
    def match_fixture_to_odds(self, fixture_row: pd.Series, odds_data: List[Dict]) -> Optional[Dict]:
        """
        Match a training dataset fixture to odds data from API
        
        Args:
            fixture_row: Row from training dataset
            odds_data: List of odds from API
            
        Returns:
            Matching odds dictionary or None
        """
        home_team = fixture_row['home_team'].lower().strip()
        away_team = fixture_row['away_team'].lower().strip()
        
        # Team name mapping for better matching
        team_aliases = {
            'manchester united': ['man united', 'manchester utd', 'man utd'],
            'manchester city': ['man city'],
            'tottenham hotspur': ['tottenham', 'spurs'],
            'wolverhampton wanderers': ['wolves', 'wolverhampton'],
            'brighton & hove albion': ['brighton'],
            'afc bournemouth': ['bournemouth'],
            'west ham united': ['west ham'],
            'newcastle united': ['newcastle'],
            'nottingham forest': ['nott\'m forest', 'nottingham'],
            'leicester city': ['leicester'],
            'sheffield united': ['sheffield utd']
        }
        
        def get_team_variations(team_name: str) -> List[str]:
            """Get all possible variations of a team name"""
            team_lower = team_name.lower().strip()
            variations = [team_lower]
            
            # Add known aliases
            if team_lower in team_aliases:
                variations.extend(team_aliases[team_lower])
            
            # Check if team is an alias
            for main_name, aliases in team_aliases.items():
                if team_lower in aliases:
                    variations.append(main_name)
                    variations.extend([alias for alias in aliases if alias != team_lower])
            
            return list(set(variations))
        
        home_variations = get_team_variations(home_team)
        away_variations = get_team_variations(away_team)
        
        # Search for matching odds
        for match_odds in odds_data:
            api_home = match_odds.get('home_team', '').lower().strip()
            api_away = match_odds.get('away_team', '').lower().strip()
            
            if api_home in home_variations and api_away in away_variations:
                logger.debug(f"✅ Matched: {fixture_row['home_team']} vs {fixture_row['away_team']}")
                return match_odds
        
        return None
    
    def extract_odds_data(self, match_odds: Dict, fixture_row: pd.Series) -> Dict:
        """
        Extract structured odds data from API response
        
        Args:
            match_odds: Odds data from API
            fixture_row: Training dataset row
            
        Returns:
            Dictionary with extracted odds features
        """
        extracted = {
            'fixture_id': fixture_row['fixture_id'],
            'api_match_id': match_odds.get('id', ''),
            'commence_time': match_odds.get('commence_time', ''),
            'home_team': fixture_row['home_team'],
            'away_team': fixture_row['away_team'],
            'season': fixture_row['season_name'],
            'collection_timestamp': datetime.now().isoformat()
        }
        
        bookmakers = match_odds.get('bookmakers', [])
        
        for bookmaker in bookmakers:
            bookie_key = bookmaker.get('key', '')
            if bookie_key not in self.bookmakers:
                continue
            
            markets = bookmaker.get('markets', [])
            
            for market in markets:
                market_key = market.get('key', '')
                outcomes = market.get('outcomes', [])
                
                if market_key == 'h2h':  # Match Winner
                    for outcome in outcomes:
                        name = outcome.get('name', '').lower()
                        price = outcome.get('price', 0)
                        
                        if fixture_row['home_team'].lower() in name:
                            extracted[f'{bookie_key}_1x2_home'] = price
                        elif fixture_row['away_team'].lower() in name:
                            extracted[f'{bookie_key}_1x2_away'] = price
                        elif 'draw' in name:
                            extracted[f'{bookie_key}_1x2_draw'] = price
                
                elif market_key == 'totals':  # Over/Under
                    for outcome in outcomes:
                        name = outcome.get('name', '').lower()
                        price = outcome.get('price', 0)
                        point = outcome.get('point', 0)
                        
                        if point == 2.5:
                            if 'over' in name:
                                extracted[f'{bookie_key}_ou25_over'] = price
                            elif 'under' in name:
                                extracted[f'{bookie_key}_ou25_under'] = price
                
                elif market_key == 'btts':  # Both Teams to Score
                    for outcome in outcomes:
                        name = outcome.get('name', '').lower()
                        price = outcome.get('price', 0)
                        
                        if 'yes' in name:
                            extracted[f'{bookie_key}_btts_yes'] = price
                        elif 'no' in name:
                            extracted[f'{bookie_key}_btts_no'] = price
        
        return extracted
    
    def collect_historical_odds(self, training_dataset: str, max_requests: int = 200) -> pd.DataFrame:
        """
        Main method to collect historical odds for the training dataset
        
        Args:
            training_dataset: Path to training dataset CSV
            max_requests: Maximum API requests to make
            
        Returns:
            DataFrame with collected odds data
        """
        logger.info("🚀 Starting historical odds collection")
        
        # Test API connection first
        if not self.test_api_connection():
            raise Exception("API connection test failed")
        
        # Load training fixtures
        fixtures = self.load_training_fixtures(training_dataset)
        
        # Group fixtures by date to minimize API calls
        date_groups = fixtures.groupby(fixtures['date'].dt.date)
        
        collected_odds = []
        requests_made = 0
        successful_matches = 0
        
        logger.info(f"📅 Processing {len(date_groups)} unique dates")
        
        for match_date, group in date_groups:
            if requests_made >= max_requests:
                logger.warning(f"⚠️ Reached maximum requests limit ({max_requests})")
                break
            
            date_str = match_date.strftime('%Y-%m-%d')
            logger.info(f"📅 Processing {len(group)} fixtures for {date_str}")
            
            # Fetch odds for this date
            odds_data = self.get_historical_odds_by_date(date_str)
            requests_made += 1
            
            if odds_data is None:
                logger.warning(f"⚠️ No odds data for {date_str}")
                continue
            
            # Match each fixture with odds
            for _, fixture in group.iterrows():
                matching_odds = self.match_fixture_to_odds(fixture, odds_data)
                
                if matching_odds:
                    extracted_odds = self.extract_odds_data(matching_odds, fixture)
                    collected_odds.append(extracted_odds)
                    successful_matches += 1
                    logger.info(f"✅ {fixture['home_team']} vs {fixture['away_team']}")
                else:
                    logger.warning(f"❌ No odds: {fixture['home_team']} vs {fixture['away_team']}")
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
        
        # Create DataFrame from collected odds
        odds_df = pd.DataFrame(collected_odds)
        
        logger.info(f"✅ Historical odds collection completed!")
        logger.info(f"📊 Results: {successful_matches}/{len(fixtures)} fixtures with odds")
        logger.info(f"🔥 API requests used: {requests_made}")
        
        return odds_df
    
    def save_odds_data(self, odds_df: pd.DataFrame, output_file: str):
        """Save collected odds data to CSV"""
        odds_df.to_csv(output_file, index=False)
        logger.info(f"💾 Odds data saved to: {output_file}")

def main():
    """Main execution function"""
    
    # Configuration
    TRAINING_DATASET = "premier_league_complete_4_seasons_20250624_175954.csv"
    OUTPUT_FILE = f"premier_league_historical_odds_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    MAX_REQUESTS = 50  # Start conservative for testing
    
    print("🎯 Premier League Historical Odds Collection")
    print("=" * 50)
    
    try:
        # Initialize collector
        collector = OddsAPIHistoricalCollector()
        
        # Collect historical odds
        odds_df = collector.collect_historical_odds(
            training_dataset=TRAINING_DATASET,
            max_requests=MAX_REQUESTS
        )
        
        # Save results
        collector.save_odds_data(odds_df, OUTPUT_FILE)
        
        print(f"\n🎉 Collection completed successfully!")
        print(f"📊 Collected odds for {len(odds_df)} fixtures")
        print(f"💾 Results saved to: {OUTPUT_FILE}")
        
        # Display sample of collected data
        if len(odds_df) > 0:
            print(f"\n📋 Sample of collected odds:")
            print(odds_df[['home_team', 'away_team', 'commence_time']].head())
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        print(f"\n❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1) 