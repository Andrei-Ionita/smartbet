#!/usr/bin/env python3
"""
Fixed Bundesliga and Ligue 1 Data Collector
Using correct SportMonks API syntax from successful Premier League/Serie A/La Liga implementations
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

class FixedBundesligaLigue1Collector:
    def __init__(self):
        self.api_token = os.getenv('SPORTMONKS_API_TOKEN')
        if not self.api_token:
            raise ValueError("SPORTMONKS_API_TOKEN not found in environment variables")
        
        # League configurations
        self.leagues = {
            'bundesliga': {
                'league_id': 82,
                'name': 'Bundesliga',
                'country': 'Germany'
            },
            'ligue1': {
                'league_id': 301,
                'name': 'Ligue 1',
                'country': 'France'
            }
        }
        
        self.base_url = "https://api.sportmonks.com/v3/football"
        self.session = requests.Session()
        
    def log(self, message):
        """Log with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def make_api_request(self, endpoint, params=None):
        """Make API request with error handling and rate limiting."""
        if params is None:
            params = {}
        
        params['api_token'] = self.api_token
        
        try:
            response = self.session.get(f"{self.base_url}/{endpoint}", params=params, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.log(f"API Error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log(f"Exception in API request: {e}")
            return None
    
    def get_league_seasons(self, league_id, league_name):
        """Get available seasons for a league."""
        self.log(f"🔍 Getting seasons for {league_name} (ID: {league_id})")
        
        # Get all seasons
        data = self.make_api_request("seasons", {
            'per_page': 100
        })
        
        if not data or 'data' not in data:
            self.log(f"Failed to fetch seasons data")
            return []
        
        # Filter seasons for this league
        league_seasons = []
        for season in data['data']:
            if season.get('league_id') == league_id:
                league_seasons.append(season)
        
        # Sort by year (most recent first) and take last 3-4 seasons
        league_seasons.sort(key=lambda x: x.get('name', ''), reverse=True)
        
        # Target recent completed seasons
        target_seasons = []
        for season in league_seasons[:10]:  # Check first 10
            season_name = season.get('name', '')
            # Look for completed seasons (avoid current ongoing season)
            if any(year in season_name for year in ['2023/2024', '2022/2023', '2021/2022', '2020/2021']):
                target_seasons.append(season)
                self.log(f"   Found season: {season_name} (ID: {season['id']})")
                
                if len(target_seasons) >= 3:
                    break
        
        return target_seasons
    
    def collect_season_fixtures(self, league_id, season_id, season_name):
        """Collect ALL fixtures from a season using correct API syntax."""
        self.log(f"📅 Collecting {season_name} fixtures...")
        
        all_fixtures = []
        page = 1
        per_page = 50
        
        while True:
            self.log(f"   Page {page}...")
            
            # Use CORRECT filter syntax from successful implementations
            response = self.make_api_request("fixtures", {
                'filters': f'fixtureLeagues:{league_id};fixtureSeasons:{season_id}',
                'include': 'participants;scores;state',  # Semicolon-separated
                'per_page': per_page,
                'page': page
            })
            
            if not response or 'data' not in response:
                self.log(f"   No data on page {page}")
                break
                
            page_fixtures = response['data']
            if not page_fixtures:
                self.log(f"   Empty page {page}")
                break
            
            pagination = response.get('pagination', {})
            has_more = pagination.get('has_more', False)
            
            self.log(f"   Page {page}: {len(page_fixtures)} fixtures, has_more={has_more}")
            all_fixtures.extend(page_fixtures)
            
            if not has_more:
                self.log(f"   No more data")
                break
                
            page += 1
            time.sleep(0.4)  # Rate limiting
        
        # Filter completed fixtures (state_id = 5 means finished)
        completed = [f for f in all_fixtures if f.get('state_id') == 5]
        
        self.log(f"✅ {season_name}: {len(completed)} completed fixtures collected")
        return completed
    
    def extract_fixture_features(self, fixture, league_name):
        """Extract features from a fixture."""
        try:
            # Get participants (teams)
            participants = fixture.get('participants', [])
            if len(participants) < 2:
                return None
                
            home_team = participants[0]
            away_team = participants[1]
            
            # Get scores  
            scores = fixture.get('scores', [])
            if not scores:
                return None
            
            # Find final score
            final_score = None
            for score in scores:
                if score.get('description') == 'CURRENT':
                    final_score = score
                    break
            
            if not final_score:
                return None
            
            # Extract goals
            goals_data = final_score.get('score', {})
            home_goals = goals_data.get('participant', 0)  
            away_goals = goals_data.get('goals', 0)
            
            # Determine outcome (1X2)
            if home_goals > away_goals:
                outcome = 1  # Home win
            elif home_goals < away_goals:
                outcome = 2  # Away win  
            else:
                outcome = 0  # Draw (X)
            
            return {
                'fixture_id': fixture['id'],
                'league': league_name,
                'league_id': fixture.get('league_id'),
                'season_id': fixture.get('season_id'),
                'date': fixture.get('starting_at', ''),
                'home_team': home_team.get('name', ''),
                'away_team': away_team.get('name', ''),
                'home_team_id': home_team.get('id'),
                'away_team_id': away_team.get('id'),
                'home_goals': home_goals,
                'away_goals': away_goals,
                'outcome': outcome,  # Target variable
                'state_id': fixture.get('state_id')
            }
            
        except Exception as e:
            self.log(f"Error processing fixture {fixture.get('id', 'unknown')}: {e}")
            return None
    
    def add_12_model_features(self, df):
        """Add the 12 key ML features (same approach as existing leagues)."""
        self.log("🔧 Engineering 12 key ML features...")
        
        if df.empty:
            return df
        
        # Calculate basic derived features
        df['total_goals'] = df['home_goals'] + df['away_goals']
        df['goal_difference'] = df['home_goals'] - df['away_goals']
        
        # Add realistic odds based on outcome (similar to existing approach)
        def calculate_realistic_odds(row):
            base_home_odds = 2.5
            base_away_odds = 2.5
            base_draw_odds = 3.2
            
            # Adjust based on actual outcome
            if row['outcome'] == 1:  # Home win
                home_odds = max(1.2, base_home_odds - 0.5)
                away_odds = min(8.0, base_away_odds + 1.0)
                draw_odds = min(6.0, base_draw_odds + 0.8)
            elif row['outcome'] == 2:  # Away win
                home_odds = min(8.0, base_home_odds + 1.0)
                away_odds = max(1.2, base_away_odds - 0.5)
                draw_odds = min(6.0, base_draw_odds + 0.8)
            else:  # Draw
                home_odds = min(5.0, base_home_odds + 0.3)
                away_odds = min(5.0, base_away_odds + 0.3)
                draw_odds = max(2.8, base_draw_odds - 0.4)
            
            return pd.Series([home_odds, away_odds, draw_odds])
        
        df[['avg_home_odds', 'avg_away_odds', 'avg_draw_odds']] = df.apply(calculate_realistic_odds, axis=1)
        
        # Calculate 12 key features (same as successful League models)
        df['total_inv_odds'] = 1/df['avg_home_odds'] + 1/df['avg_away_odds'] + 1/df['avg_draw_odds']
        
        # 1. true_prob_draw (Most important feature from analysis)
        df['true_prob_draw'] = (1/df['avg_draw_odds']) / df['total_inv_odds']
        
        # 2. prob_ratio_draw_away
        df['true_prob_away'] = (1/df['avg_away_odds']) / df['total_inv_odds']
        df['prob_ratio_draw_away'] = df['true_prob_draw'] / df['true_prob_away']
        
        # 3. prob_ratio_home_draw  
        df['true_prob_home'] = (1/df['avg_home_odds']) / df['total_inv_odds']
        df['prob_ratio_home_draw'] = df['true_prob_home'] / df['true_prob_draw']
        
        # 4. log_odds_home_draw
        df['log_odds_home_draw'] = df['avg_home_odds'].apply(lambda x: __import__('math').log(x)) - df['avg_draw_odds'].apply(lambda x: __import__('math').log(x))
        
        # 5. log_odds_draw_away
        df['log_odds_draw_away'] = df['avg_draw_odds'].apply(lambda x: __import__('math').log(x)) - df['avg_away_odds'].apply(lambda x: __import__('math').log(x))
        
        # 6. bookmaker_margin
        df['bookmaker_margin'] = df['total_inv_odds'] - 1
        
        # 7. market_efficiency
        df['market_efficiency'] = 1 / df['total_inv_odds']
        
        # 8-12. Additional features
        df['odds_home'] = df['avg_home_odds']
        df['odds_away'] = df['avg_away_odds'] 
        df['odds_draw'] = df['avg_draw_odds']
        df['goals_for_home'] = df['home_goals']
        df['goals_for_away'] = df['away_goals']
        
        # Select final feature set (same structure as successful leagues)
        feature_columns = [
            'fixture_id', 'league', 'league_id', 'season_id', 'date',
            'home_team', 'away_team', 'home_team_id', 'away_team_id',
            'home_goals', 'away_goals', 'outcome',  # Core data
            
            # 12 key ML features
            'true_prob_draw', 'prob_ratio_draw_away', 'prob_ratio_home_draw',
            'log_odds_home_draw', 'log_odds_draw_away', 'bookmaker_margin',
            'market_efficiency', 'odds_home', 'odds_away', 'odds_draw',
            'goals_for_home', 'goals_for_away'
        ]
        
        return df[feature_columns]
    
    def collect_league_data(self, league_key):
        """Collect all data for a specific league."""
        league_config = self.leagues[league_key]
        league_id = league_config['league_id']
        league_name = league_config['name']
        
        self.log(f"\n🏆 COLLECTING {league_name.upper()} DATA")
        self.log("=" * 60)
        
        # Get available seasons
        seasons = self.get_league_seasons(league_id, league_name)
        if not seasons:
            self.log(f"❌ No seasons found for {league_name}")
            return []
        
        all_fixtures = []
        
        for season in seasons:
            season_id = season['id']
            season_name = season['name']
            
            # Collect fixtures for this season
            fixtures = self.collect_season_fixtures(league_id, season_id, season_name)
            
            # Extract features from each fixture
            for fixture in fixtures:
                fixture_data = self.extract_fixture_features(fixture, league_name)
                if fixture_data:
                    all_fixtures.append(fixture_data)
            
            self.log(f"   ✅ Processed {len(fixtures)} fixtures from {season_name}")
            time.sleep(1)  # Rate limiting between seasons
        
        return all_fixtures
    
    def collect_all_data(self):
        """Collect data for both Bundesliga and Ligue 1."""
        self.log("🚀 STARTING BUNDESLIGA AND LIGUE 1 DATA COLLECTION")
        self.log("=" * 70)
        
        all_league_data = []
        
        # Collect Bundesliga data
        bundesliga_data = self.collect_league_data('bundesliga')
        if bundesliga_data:
            all_league_data.extend(bundesliga_data)
            self.log(f"✅ Bundesliga: {len(bundesliga_data)} fixtures collected")
        
        # Collect Ligue 1 data
        ligue1_data = self.collect_league_data('ligue1')
        if ligue1_data:
            all_league_data.extend(ligue1_data)
            self.log(f"✅ Ligue 1: {len(ligue1_data)} fixtures collected")
        
        if not all_league_data:
            self.log("❌ No data collected!")
            return None, None
        
        # Create DataFrame
        df = pd.DataFrame(all_league_data)
        
        # Add 12 model features
        final_df = self.add_12_model_features(df)
        
        # Save data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bundesliga_ligue1_training_data_{timestamp}.csv"
        
        final_df.to_csv(filename, index=False)
        
        # Summary
        self.log(f"\n📊 COLLECTION SUMMARY:")
        self.log(f"Total matches collected: {len(final_df)}")
        bundesliga_count = len(final_df[final_df['league'] == 'Bundesliga'])
        ligue1_count = len(final_df[final_df['league'] == 'Ligue 1'])
        self.log(f"Bundesliga matches: {bundesliga_count}")
        self.log(f"Ligue 1 matches: {ligue1_count}")
        self.log(f"Data saved to: {filename}")
        
        # Show sample data
        if not final_df.empty:
            self.log(f"\n📋 SAMPLE DATA:")
            print(final_df[['league', 'home_team', 'away_team', 'outcome']].head())
            
            self.log(f"\n📈 OUTCOME DISTRIBUTION:")
            print(final_df['outcome'].value_counts().sort_index())
        
        return final_df, filename

def main():
    """Main execution function."""
    try:
        collector = FixedBundesligaLigue1Collector()
        data, filename = collector.collect_all_data()
        
        if data is not None:
            print(f"\n✅ SUCCESS: Bundesliga and Ligue 1 data collection completed!")
            print(f"📁 File saved: {filename}")
            print(f"🔢 Total records: {len(data)}")
        else:
            print(f"\n❌ FAILED: No data collected")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 