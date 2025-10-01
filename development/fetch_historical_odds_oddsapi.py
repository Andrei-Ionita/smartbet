"""
Historical Odds Fetcher for OddsAPI Integration
Fetches comprehensive historical odds for Premier League fixtures to enhance training dataset.
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
        logging.FileHandler(f'historical_odds_fetch_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HistoricalOddsFetcher:
    """Fetches historical odds from OddsAPI for Premier League fixtures"""
    
    def __init__(self):
        self.api_key = os.getenv('ODDSAPI_KEY')
        if not self.api_key:
            raise ValueError("ODDSAPI_KEY environment variable not found. Please set it in your .env file.")
        
        self.base_url = "https://api.the-odds-api.com/v4"
        self.sport = "soccer_epl"  # Premier League
        self.regions = "uk,eu,us"  # Multiple regions for better coverage
        self.rate_limit_delay = 1.1  # Slightly more than 1 second to be safe
        
        # Target markets for comprehensive odds
        self.target_markets = [
            "h2h",              # Match Winner (1X2)
            "spreads",          # Asian Handicap
            "totals",           # Over/Under Goals
            "btts",             # Both Teams to Score
            "h2h_lay",          # Lay betting (if available)
            "draw_no_bet",      # Draw No Bet
            "double_chance"     # Double Chance
        ]
        
        # Premium bookmakers for best odds
        self.target_bookmakers = [
            "pinnacle",
            "bet365", 
            "betfair",
            "marathonbet",
            "williamhill",
            "unibet",
            "betway",
            "ladbrokes",
            "coral"
        ]
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SmartBet-HistoricalOdds/1.0'
        })
        
    def load_training_dataset(self, filepath: str) -> pd.DataFrame:
        """Load the existing training dataset"""
        logger.info(f"Loading training dataset from {filepath}")
        df = pd.read_csv(filepath)
        logger.info(f"Loaded {len(df)} records from training dataset")
        
        # Parse dates and extract fixture info
        df['date'] = pd.to_datetime(df['date'])
        df['season_year'] = df['season_name'].str.extract(r'(\d{4})/\d{4}').astype(int)
        
        return df
    
    def get_historical_odds(self, fixture_id: str, commence_time: str) -> Optional[Dict]:
        """
        Fetch historical odds for a specific fixture.
        
        Args:
            fixture_id: The fixture ID (if available from OddsAPI)
            commence_time: Match start time in ISO format
            
        Returns:
            Dictionary containing odds data or None if failed
        """
        try:
            # Try to get historical odds using the historical endpoint
            url = f"{self.base_url}/sports/{self.sport}/odds-history"
            
            params = {
                'apiKey': self.api_key,
                'regions': self.regions,
                'markets': ','.join(self.target_markets),
                'bookmakers': ','.join(self.target_bookmakers),
                'date': commence_time[:10],  # YYYY-MM-DD format
                'oddsFormat': 'decimal'
            }
            
            logger.debug(f"Fetching historical odds for {commence_time}")
            
            response = self.session.get(url, params=params)
            
            if response.status_code == 429:
                logger.warning("Rate limit hit, waiting 30 seconds...")
                time.sleep(30)
                return self.get_historical_odds(fixture_id, commence_time)
            
            response.raise_for_status()
            
            data = response.json()
            
            # Log remaining requests
            remaining = response.headers.get('x-requests-remaining', 'Unknown')
            logger.info(f"Requests remaining: {remaining}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {commence_time}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching odds for {commence_time}: {e}")
            return None
    
    def get_live_odds_for_date(self, target_date: str) -> Optional[List[Dict]]:
        """
        Fetch odds for all matches on a specific date using the current odds endpoint.
        This is useful for recent matches where historical data might not be available.
        
        Args:
            target_date: Date in YYYY-MM-DD format
            
        Returns:
            List of match odds or None if failed
        """
        try:
            url = f"{self.base_url}/sports/{self.sport}/odds"
            
            params = {
                'apiKey': self.api_key,
                'regions': self.regions,
                'markets': ','.join(self.target_markets),
                'bookmakers': ','.join(self.target_bookmakers),
                'oddsFormat': 'decimal',
                'dateFormat': 'iso'
            }
            
            logger.debug(f"Fetching live odds for date {target_date}")
            
            response = self.session.get(url, params=params)
            
            if response.status_code == 429:
                logger.warning("Rate limit hit, waiting 30 seconds...")
                time.sleep(30)
                return self.get_live_odds_for_date(target_date)
            
            response.raise_for_status()
            
            data = response.json()
            
            # Filter matches for the target date
            target_matches = []
            for match in data:
                match_date = match.get('commence_time', '')[:10]
                if match_date == target_date:
                    target_matches.append(match)
            
            logger.info(f"Found {len(target_matches)} matches for {target_date}")
            
            return target_matches
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for date {target_date}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching odds for date {target_date}: {e}")
            return None
    
    def find_matching_odds(self, row: pd.Series, available_odds: List[Dict]) -> Optional[Dict]:
        """
        Find odds data that matches a training dataset row.
        
        Args:
            row: Row from training dataset
            available_odds: List of odds data from API
            
        Returns:
            Matching odds dictionary or None
        """
        home_team = row['home_team'].lower().strip()
        away_team = row['away_team'].lower().strip()
        
        # Team name mappings for better matching
        team_mappings = {
            'manchester united': ['man united', 'manchester utd', 'man utd'],
            'manchester city': ['man city', 'manchester city fc'],
            'tottenham hotspur': ['tottenham', 'spurs'],
            'wolverhampton wanderers': ['wolves', 'wolverhampton'],
            'brighton & hove albion': ['brighton', 'brighton and hove albion'],
            'afc bournemouth': ['bournemouth'],
            'west ham united': ['west ham'],
            'newcastle united': ['newcastle'],
            'nottingham forest': ['nott\'m forest', 'nottingham'],
            'sheffield united': ['sheffield utd'],
            'leicester city': ['leicester']
        }
        
        def normalize_team_name(team_name: str) -> List[str]:
            """Get all possible variations of a team name"""
            team_lower = team_name.lower().strip()
            variations = [team_lower]
            
            for key, alternatives in team_mappings.items():
                if team_lower == key:
                    variations.extend(alternatives)
                elif team_lower in alternatives:
                    variations.append(key)
                    variations.extend([alt for alt in alternatives if alt != team_lower])
            
            return list(set(variations))
        
        home_variations = normalize_team_name(home_team)
        away_variations = normalize_team_name(away_team)
        
        for odds_data in available_odds:
            api_home = odds_data.get('home_team', '').lower().strip()
            api_away = odds_data.get('away_team', '').lower().strip()
            
            if api_home in home_variations and api_away in away_variations:
                return odds_data
        
        return None
    
    def extract_odds_features(self, odds_data: Dict, row: pd.Series) -> Dict:
        """
        Extract comprehensive odds features from API response.
        
        Args:
            odds_data: Odds data from API
            row: Training dataset row
            
        Returns:
            Dictionary of extracted odds features
        """
        features = {
            'fixture_id': row['fixture_id'],
            'match_date': row['date'],
            'home_team': row['home_team'],
            'away_team': row['away_team'],
            'actual_outcome': row['outcome']
        }
        
        bookmakers = odds_data.get('bookmakers', [])
        
        # Extract odds for each market and bookmaker
        for bookmaker in bookmakers:
            bookie_name = bookmaker.get('key', '')
            if bookie_name not in self.target_bookmakers:
                continue
                
            markets = bookmaker.get('markets', [])
            
            for market in markets:
                market_key = market.get('key', '')
                outcomes = market.get('outcomes', [])
                
                if market_key == 'h2h':  # Match Winner (1X2)
                    for outcome in outcomes:
                        name = outcome.get('name', '').lower()
                        price = outcome.get('price', 0)
                        
                        if name == row['home_team'].lower():
                            features[f'{bookie_name}_h2h_home'] = price
                        elif name == row['away_team'].lower():
                            features[f'{bookie_name}_h2h_away'] = price
                        elif 'draw' in name:
                            features[f'{bookie_name}_h2h_draw'] = price
                
                elif market_key == 'totals':  # Over/Under Goals
                    for outcome in outcomes:
                        name = outcome.get('name', '').lower()
                        price = outcome.get('price', 0)
                        point = outcome.get('point', 0)
                        
                        if 'over' in name and point == 2.5:
                            features[f'{bookie_name}_over_2_5'] = price
                        elif 'under' in name and point == 2.5:
                            features[f'{bookie_name}_under_2_5'] = price
                        elif 'over' in name and point == 1.5:
                            features[f'{bookie_name}_over_1_5'] = price
                        elif 'under' in name and point == 1.5:
                            features[f'{bookie_name}_under_1_5'] = price
                
                elif market_key == 'btts':  # Both Teams to Score
                    for outcome in outcomes:
                        name = outcome.get('name', '').lower()
                        price = outcome.get('price', 0)
                        
                        if 'yes' in name:
                            features[f'{bookie_name}_btts_yes'] = price
                        elif 'no' in name:
                            features[f'{bookie_name}_btts_no'] = price
                
                elif market_key == 'spreads':  # Asian Handicap
                    for outcome in outcomes:
                        name = outcome.get('name', '').lower()
                        price = outcome.get('price', 0)
                        point = outcome.get('point', 0)
                        
                        if name == row['home_team'].lower():
                            features[f'{bookie_name}_ah_home_{point}'] = price
                        elif name == row['away_team'].lower():
                            features[f'{bookie_name}_ah_away_{point}'] = price
        
        # Calculate market averages and best odds
        self._calculate_market_statistics(features)
        
        return features
    
    def _calculate_market_statistics(self, features: Dict):
        """Calculate average odds and best odds across bookmakers"""
        
        # Group odds by market
        markets = {}
        
        for key, value in features.items():
            if isinstance(value, (int, float)) and value > 0:
                parts = key.split('_')
                if len(parts) >= 3:
                    bookie = parts[0]
                    market = '_'.join(parts[1:])
                    
                    if market not in markets:
                        markets[market] = []
                    markets[market].append(value)
        
        # Calculate statistics for each market
        for market, odds_list in markets.items():
            if len(odds_list) > 1:
                features[f'avg_{market}'] = sum(odds_list) / len(odds_list)
                features[f'best_{market}'] = max(odds_list)
                features[f'worst_{market}'] = min(odds_list)
                features[f'market_efficiency_{market}'] = min(odds_list) / max(odds_list)
    
    def fetch_odds_for_dataset(self, dataset_path: str, output_path: str, max_requests: int = 500):
        """
        Main method to fetch odds for the entire training dataset.
        
        Args:
            dataset_path: Path to training dataset CSV
            output_path: Path to save odds-enhanced dataset
            max_requests: Maximum API requests to make (rate limiting)
        """
        logger.info("Starting historical odds collection for training dataset")
        
        # Load training dataset
        df = self.load_training_dataset(dataset_path)
        
        # Sort by date to process older matches first
        df = df.sort_values('date')
        
        # Group by date to minimize API calls
        date_groups = df.groupby(df['date'].dt.date)
        
        enhanced_records = []
        requests_made = 0
        
        for match_date, group in date_groups:
            if requests_made >= max_requests:
                logger.warning(f"Reached maximum requests limit ({max_requests})")
                break
            
            date_str = match_date.strftime('%Y-%m-%d')
            logger.info(f"Processing {len(group)} matches for {date_str}")
            
            # Fetch odds for this date
            available_odds = self.get_live_odds_for_date(date_str)
            requests_made += 1
            
            if available_odds is None:
                logger.warning(f"No odds data available for {date_str}")
                # Add rows without odds data
                for _, row in group.iterrows():
                    enhanced_records.append({
                        'fixture_id': row['fixture_id'],
                        'match_date': row['date'],
                        'home_team': row['home_team'],
                        'away_team': row['away_team'],
                        'actual_outcome': row['outcome'],
                        'odds_available': False
                    })
                continue
            
            # Match each fixture with odds data
            for _, row in group.iterrows():
                matching_odds = self.find_matching_odds(row, available_odds)
                
                if matching_odds:
                    odds_features = self.extract_odds_features(matching_odds, row)
                    odds_features['odds_available'] = True
                    enhanced_records.append(odds_features)
                    logger.info(f"✅ Found odds for {row['home_team']} vs {row['away_team']}")
                else:
                    enhanced_records.append({
                        'fixture_id': row['fixture_id'],
                        'match_date': row['date'],
                        'home_team': row['home_team'],
                        'away_team': row['away_team'],
                        'actual_outcome': row['outcome'],
                        'odds_available': False
                    })
                    logger.warning(f"❌ No odds found for {row['home_team']} vs {row['away_team']}")
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
        
        # Save enhanced dataset
        enhanced_df = pd.DataFrame(enhanced_records)
        enhanced_df.to_csv(output_path, index=False)
        
        odds_found = enhanced_df['odds_available'].sum()
        total_matches = len(enhanced_df)
        
        logger.info(f"✅ Historical odds collection complete!")
        logger.info(f"📊 Results: {odds_found}/{total_matches} matches with odds ({odds_found/total_matches*100:.1f}%)")
        logger.info(f"💾 Enhanced dataset saved to: {output_path}")
        logger.info(f"🔥 API requests used: {requests_made}")
        
        return enhanced_df

def main():
    """Main execution function"""
    # Configuration
    TRAINING_DATASET = "premier_league_complete_4_seasons_20250624_175954.csv"
    OUTPUT_FILE = f"premier_league_with_historical_odds_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    MAX_REQUESTS = 100  # Adjust based on your API plan
    
    try:
        # Initialize fetcher
        fetcher = HistoricalOddsFetcher()
        
        print(f"\n🎯 Historical odds collection will start!")
        print(f"📈 Will process training dataset: {TRAINING_DATASET}")
        
    except Exception as e:
        logger.error(f"Fatal error in main execution: {e}")
        raise

if __name__ == "__main__":
    main() 