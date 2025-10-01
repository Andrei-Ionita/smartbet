#!/usr/bin/env python3
"""
Comprehensive Data Collection Pipeline for Bundesliga and Ligue 1
Follows the same successful approach used for Premier League, Serie A, and La Liga
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

class BundesligaLigue1Collector:
    def __init__(self):
        self.api_token = os.getenv('SPORTMONKS_API_TOKEN')
        if not self.api_token:
            raise ValueError("SPORTMONKS_API_TOKEN not found in environment variables")
        
        # League configurations with verified IDs
        self.leagues = {
            'bundesliga': {
                'league_id': 82,
                'name': 'Bundesliga',
                'country': 'Germany',
                'seasons': [23744, 21795, 19744]  # 2024/2025, 2023/2024, 2022/2023
            },
            'ligue1': {
                'league_id': 301,
                'name': 'Ligue 1',
                'country': 'France', 
                'seasons': [23643, 21779, 19745]  # 2024/2025, 2023/2024, 2022/2023
            }
        }
        
        self.base_url = "https://api.sportmonks.com/v3/football"
        self.session = requests.Session()
        
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
                print(f"API Error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"Exception in API request: {e}")
            return None
    
    def collect_season_fixtures(self, league_key, season_id):
        """Collect all fixtures for a specific season with pagination."""
        print(f"📅 Collecting {self.leagues[league_key]['name']} season {season_id} fixtures...")
        
        all_fixtures = []
        page = 1
        
        while True:
            params = {
                'filters': f'seasonId:{season_id}',
                'include': 'participants;scores;state;statistics.details',
                'per_page': 50,
                'page': page
            }
            
            data = self.make_api_request('fixtures', params)
            
            if not data or 'data' not in data:
                break
                
            fixtures = data['data']
            if not fixtures:
                break
                
            all_fixtures.extend(fixtures)
            print(f"   Page {page}: {len(fixtures)} fixtures collected")
            
            # Check if there are more pages
            pagination = data.get('pagination', {})
            if not pagination.get('has_more', False):
                break
                
            page += 1
            time.sleep(0.1)  # Rate limiting
        
        print(f"   ✅ Total fixtures collected: {len(all_fixtures)}")
        return all_fixtures
    
    def process_fixture_data(self, fixtures, league_key):
        """Process fixture data into structured format."""
        processed_data = []
        
        for fixture in fixtures:
            try:
                # Skip if not completed
                if not fixture.get('state') or fixture['state'].get('state') != 'FINISHED':
                    continue
                
                # Get participants
                participants = fixture.get('participants', [])
                if len(participants) < 2:
                    continue
                
                home_team = participants[0]
                away_team = participants[1]
                
                # Get scores
                scores = fixture.get('scores', [])
                if not scores:
                    continue
                
                # Find full-time score
                ft_score = next((s for s in scores if s.get('description') == 'CURRENT'), None)
                if not ft_score:
                    continue
                
                home_goals = ft_score.get('score', {}).get('participant', 0)
                away_goals = ft_score.get('score', {}).get('goals', 0)
                
                # Determine outcome (1X2)
                if home_goals > away_goals:
                    outcome = 1  # Home win
                elif home_goals < away_goals:
                    outcome = 2  # Away win
                else:
                    outcome = 0  # Draw (X)
                
                # Extract match statistics
                statistics = fixture.get('statistics', [])
                home_stats = {}
                away_stats = {}
                
                for stat in statistics:
                    if stat.get('location') == 'home':
                        for detail in stat.get('details', []):
                            home_stats[detail.get('type', {}).get('name', '')] = detail.get('value', 0)
                    elif stat.get('location') == 'away':
                        for detail in stat.get('details', []):
                            away_stats[detail.get('type', {}).get('name', '')] = detail.get('value', 0)
                
                match_data = {
                    'fixture_id': fixture['id'],
                    'league': self.leagues[league_key]['name'],
                    'league_id': self.leagues[league_key]['league_id'],
                    'season_id': fixture.get('season_id'),
                    'round': fixture.get('round', {}).get('name', ''),
                    'date': fixture.get('starting_at', ''),
                    'home_team': home_team.get('name', ''),
                    'away_team': away_team.get('name', ''),
                    'home_team_id': home_team.get('id'),
                    'away_team_id': away_team.get('id'),
                    'home_goals': home_goals,
                    'away_goals': away_goals,
                    'outcome': outcome,  # Target variable for ML
                    
                    # Match statistics (12 key features like existing leagues)
                    'home_possession': home_stats.get('Ball Possession', 0),
                    'away_possession': away_stats.get('Ball Possession', 0),
                    'home_shots': home_stats.get('Total Shots', 0),
                    'away_shots': away_stats.get('Total Shots', 0),
                    'home_shots_on_target': home_stats.get('Shots On Target', 0),
                    'away_shots_on_target': away_stats.get('Shots On Target', 0),
                    'home_corners': home_stats.get('Corner Kicks', 0),
                    'away_corners': away_stats.get('Corner Kicks', 0),
                    'home_fouls': home_stats.get('Fouls', 0),
                    'away_fouls': away_stats.get('Fouls', 0),
                    'home_yellow_cards': home_stats.get('Yellow Cards', 0),
                    'away_yellow_cards': away_stats.get('Yellow Cards', 0),
                    'home_red_cards': home_stats.get('Red Cards', 0),
                    'away_red_cards': away_stats.get('Red Cards', 0),
                    'home_offsides': home_stats.get('Offsides', 0),
                    'away_offsides': away_stats.get('Offsides', 0),
                    'home_attacks': home_stats.get('Attacks', 0),
                    'away_attacks': away_stats.get('Attacks', 0),
                    'home_dangerous_attacks': home_stats.get('Dangerous Attacks', 0),
                    'away_dangerous_attacks': away_stats.get('Dangerous Attacks', 0)
                }
                
                processed_data.append(match_data)
                
            except Exception as e:
                print(f"Error processing fixture {fixture.get('id', 'unknown')}: {e}")
                continue
        
        return processed_data
    
    def collect_league_data(self, league_key):
        """Collect all data for a specific league."""
        print(f"\n🏆 COLLECTING {self.leagues[league_key]['name'].upper()} DATA")
        print("=" * 60)
        
        all_data = []
        
        for season_id in self.leagues[league_key]['seasons']:
            fixtures = self.collect_season_fixtures(league_key, season_id)
            if fixtures:
                processed = self.process_fixture_data(fixtures, league_key)
                all_data.extend(processed)
                print(f"   ✅ Processed {len(processed)} completed matches")
            
            time.sleep(0.5)  # Rate limiting between seasons
        
        return all_data
    
    def engineer_features(self, data):
        """Engineer ML features from raw data."""
        print("🔧 Engineering ML features...")
        
        df = pd.DataFrame(data)
        
        if df.empty:
            return df
        
        # Calculate derived features (same as existing leagues)
        df['total_goals'] = df['home_goals'] + df['away_goals']
        df['goal_difference'] = df['home_goals'] - df['away_goals']
        
        # Possession difference
        df['possession_difference'] = df['home_possession'] - df['away_possession']
        
        # Shot accuracy
        df['home_shot_accuracy'] = df.apply(
            lambda row: (row['home_shots_on_target'] / row['home_shots'] * 100) 
            if row['home_shots'] > 0 else 0, axis=1
        )
        df['away_shot_accuracy'] = df.apply(
            lambda row: (row['away_shots_on_target'] / row['away_shots'] * 100) 
            if row['away_shots'] > 0 else 0, axis=1
        )
        
        # Attack efficiency
        df['home_attack_efficiency'] = df.apply(
            lambda row: (row['home_dangerous_attacks'] / row['home_attacks'] * 100) 
            if row['home_attacks'] > 0 else 0, axis=1
        )
        df['away_attack_efficiency'] = df.apply(
            lambda row: (row['away_dangerous_attacks'] / row['away_attacks'] * 100) 
            if row['away_attacks'] > 0 else 0, axis=1
        )
        
        # Disciplinary
        df['home_total_cards'] = df['home_yellow_cards'] + (df['home_red_cards'] * 2)
        df['away_total_cards'] = df['away_yellow_cards'] + (df['away_red_cards'] * 2)
        df['cards_difference'] = df['home_total_cards'] - df['away_total_cards']
        
        # Select final 12 features for ML (same structure as existing leagues)
        feature_columns = [
            'fixture_id', 'league', 'league_id', 'season_id', 'date', 
            'home_team', 'away_team', 'home_team_id', 'away_team_id',
            'home_goals', 'away_goals', 'outcome',  # Target
            
            # 12 key ML features
            'possession_difference',
            'home_shots', 'away_shots',
            'home_shot_accuracy', 'away_shot_accuracy', 
            'home_corners', 'away_corners',
            'home_attack_efficiency', 'away_attack_efficiency',
            'home_fouls', 'away_fouls',
            'cards_difference'
        ]
        
        return df[feature_columns]
    
    def collect_all_data(self):
        """Collect data for both Bundesliga and Ligue 1."""
        print("🚀 STARTING BUNDESLIGA AND LIGUE 1 DATA COLLECTION")
        print("=" * 70)
        
        all_league_data = []
        
        # Collect Bundesliga data
        bundesliga_data = self.collect_league_data('bundesliga')
        if bundesliga_data:
            all_league_data.extend(bundesliga_data)
        
        # Collect Ligue 1 data  
        ligue1_data = self.collect_league_data('ligue1')
        if ligue1_data:
            all_league_data.extend(ligue1_data)
        
        # Engineer features
        final_df = self.engineer_features(all_league_data)
        
        # Save data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bundesliga_ligue1_training_data_{timestamp}.csv"
        
        final_df.to_csv(filename, index=False)
        
        print(f"\n📊 COLLECTION SUMMARY:")
        print(f"Total matches collected: {len(final_df)}")
        print(f"Bundesliga matches: {len(final_df[final_df['league'] == 'Bundesliga'])}")
        print(f"Ligue 1 matches: {len(final_df[final_df['league'] == 'Ligue 1'])}")
        print(f"Data saved to: {filename}")
        
        # Show sample data
        if not final_df.empty:
            print(f"\n📋 SAMPLE DATA:")
            print(final_df.head())
            
            print(f"\n📈 OUTCOME DISTRIBUTION:")
            print(final_df['outcome'].value_counts().sort_index())
        
        return final_df, filename

def main():
    """Main execution function."""
    try:
        collector = BundesligaLigue1Collector()
        data, filename = collector.collect_all_data()
        
        print(f"\n✅ SUCCESS: Bundesliga and Ligue 1 data collection completed!")
        print(f"📁 File saved: {filename}")
        print(f"🔢 Total records: {len(data)}")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 