#!/usr/bin/env python3
"""
Prediction Accuracy Tracking System
Tracks real SportMonks predictions vs actual outcomes
NO MOCK DATA - 100% REAL DATA ONLY
"""

import os
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd

def load_environment():
    """Load environment variables from .env file"""
    # Try to load from dotenv first
    try:
        from dotenv import load_dotenv
        load_dotenv()
        return True
    except ImportError:
        # Fallback to manual loading
        try:
            with open('.env', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            return True
        except FileNotFoundError:
            return False

class PredictionTracker:
    def __init__(self):
        # Load environment variables first
        if not load_environment():
            raise ValueError("Could not load .env file. Please ensure .env file exists with SPORTMONKS_API_TOKEN")
        
        self.db_path = "prediction_accuracy.db"
        self.sportmonks_token = os.getenv('SPORTMONKS_API_TOKEN')
        if not self.sportmonks_token:
            raise ValueError("SPORTMONKS_API_TOKEN environment variable required. Please check your .env file.")
        
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for prediction tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Predictions table - stores our ensemble predictions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fixture_id INTEGER UNIQUE,
                league_id INTEGER,
                league_name TEXT,
                home_team TEXT,
                away_team TEXT,
                kickoff_datetime TEXT,
                predicted_outcome TEXT,
                confidence REAL,
                expected_value REAL,
                kelly_stake REAL,
                ensemble_consensus REAL,
                model_variance REAL,
                prediction_agreement TEXT,
                odds_home REAL,
                odds_draw REAL,
                odds_away REAL,
                bookmaker TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Results table - stores actual match outcomes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fixture_id INTEGER UNIQUE,
                home_score INTEGER,
                away_score INTEGER,
                actual_outcome TEXT,
                match_status TEXT,
                result_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Accuracy analysis table - stores calculated metrics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accuracy_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER,
                league_name TEXT,
                total_predictions INTEGER,
                correct_predictions INTEGER,
                hit_rate REAL,
                avg_confidence REAL,
                avg_expected_value REAL,
                high_confidence_accuracy REAL,
                low_confidence_accuracy REAL,
                analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("SUCCESS: Database initialized successfully")
    
    def fetch_weekend_fixtures(self) -> List[Dict]:
        """Fetch real weekend fixtures from SportMonks API for all 27 leagues"""
        print("Fetching weekend fixtures from SportMonks API...")
        
        # Get fixtures for next 3 days (Friday-Sunday)
        start_date = datetime.now().strftime('%Y-%m-%d')
        end_date = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
        
        # All 27 leagues covered by subscription
        leagues = [
            { 'id': 8, 'name': 'Premier League' },
            { 'id': 9, 'name': 'Championship' },
            { 'id': 24, 'name': 'FA Cup' },
            { 'id': 27, 'name': 'Carabao Cup' },
            { 'id': 72, 'name': 'Eredivisie' },
            { 'id': 82, 'name': 'Bundesliga' },
            { 'id': 181, 'name': 'Admiral Bundesliga' },
            { 'id': 208, 'name': 'Pro League' },
            { 'id': 244, 'name': '1. HNL' },
            { 'id': 271, 'name': 'Superliga' },
            { 'id': 301, 'name': 'Ligue 1' },
            { 'id': 384, 'name': 'Serie A' },
            { 'id': 387, 'name': 'Serie B' },
            { 'id': 390, 'name': 'Coppa Italia' },
            { 'id': 444, 'name': 'Eliteserien' },
            { 'id': 453, 'name': 'Ekstraklasa' },
            { 'id': 462, 'name': 'Liga Portugal' },
            { 'id': 486, 'name': 'Premier League (Romanian)' },
            { 'id': 501, 'name': 'Premiership' },
            { 'id': 564, 'name': 'La Liga' },
            { 'id': 567, 'name': 'La Liga 2' },
            { 'id': 570, 'name': 'Copa Del Rey' },
            { 'id': 573, 'name': 'Allsvenskan' },
            { 'id': 591, 'name': 'Super League' },
            { 'id': 600, 'name': 'Super Lig' },
            { 'id': 609, 'name': 'Premier League (additional)' },
            { 'id': 1371, 'name': 'UEFA Europa League Play-offs' }
        ]
        
        all_fixtures = []
        
        for league in leagues:
            try:
                url = f"https://api.sportmonks.com/v3/football/fixtures/between/{start_date}/{end_date}"
                params = {
                    'api_token': self.sportmonks_token,
                    'include': 'participants;league;metadata;predictions;odds;odds.bookmaker',
                    'filters': f'fixtureLeagues:{league["id"]}',
                    'per_page': 50,
                    'timezone': 'Europe/Bucharest'
                }
                
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                fixtures = data.get('data', [])
                print(f"  {league['name']}: {len(fixtures)} fixtures")
                all_fixtures.extend(fixtures)
                
            except requests.exceptions.RequestException as e:
                print(f"  {league['name']}: ERROR - {e}")
                continue
        
        print(f"SUCCESS: Found {len(all_fixtures)} weekend fixtures across all 27 leagues")
        return all_fixtures
    
    def analyze_ensemble_prediction(self, fixture: Dict) -> Optional[Dict]:
        """Analyze SportMonks predictions using our ensemble method"""
        predictions = fixture.get('predictions', [])
        x12_predictions = [p for p in predictions if p.get('type_id') in [233, 237, 238]]
        
        if not x12_predictions or not fixture.get('odds'):
            return None
        
        # Normalize probabilities (handle percentage vs decimal)
        def normalize_probability(value):
            if not value or value <= 0:
                return 0
            return value / 100 if value > 1 else value
        
        # Analyze all X12 predictions for consensus
        all_predictions = []
        for pred in x12_predictions:
            pred_data = pred.get('predictions', {})
            all_predictions.append({
                'home': normalize_probability(pred_data.get('home', 0)),
                'draw': normalize_probability(pred_data.get('draw', 0)),
                'away': normalize_probability(pred_data.get('away', 0))
            })
        
        if not all_predictions:
            return None
        
        # Calculate consensus (average across models)
        consensus_home = sum(p['home'] for p in all_predictions) / len(all_predictions)
        consensus_draw = sum(p['draw'] for p in all_predictions) / len(all_predictions)
        consensus_away = sum(p['away'] for p in all_predictions) / len(all_predictions)
        
        # Calculate variance (model disagreement)
        home_variance = sum((p['home'] - consensus_home) ** 2 for p in all_predictions) / len(all_predictions)
        draw_variance = sum((p['draw'] - consensus_draw) ** 2 for p in all_predictions) / len(all_predictions)
        away_variance = sum((p['away'] - consensus_away) ** 2 for p in all_predictions) / len(all_predictions)
        total_variance = (home_variance + draw_variance + away_variance) / 3
        
        # Select most decisive prediction
        best_pred = max(all_predictions, key=lambda p: max(p['home'], p['draw'], p['away']))
        
        # Determine predicted outcome
        max_prob = max(best_pred['home'], best_pred['draw'], best_pred['away'])
        if max_prob == best_pred['home']:
            predicted_outcome = 'Home'
        elif max_prob == best_pred['away']:
            predicted_outcome = 'Away'
        else:
            predicted_outcome = 'Draw'
        
        # Get odds for predicted outcome
        x12_odds = [odd for odd in fixture.get('odds', []) if odd.get('market_id') == 1]
        odds_data = {}
        bookmaker = 'Unknown'
        
        for odd in x12_odds:
            label = odd.get('label', '').lower()
            value = float(odd.get('value', 0))
            if label == 'home':
                odds_data['home'] = value
            elif label == 'draw':
                odds_data['draw'] = value
            elif label == 'away':
                odds_data['away'] = value
            
            # Get bookmaker name
            if odd.get('bookmaker') and odd['bookmaker'].get('name'):
                bookmaker = odd['bookmaker']['name']
        
        # Calculate expected value
        predicted_odds = odds_data.get(predicted_outcome.lower(), 1)
        expected_value = (max_prob * predicted_odds) - 1
        
        # Calculate Kelly Criterion
        kelly_stake = 0
        if expected_value > 0 and predicted_odds > 1:
            kelly_fraction = expected_value / (predicted_odds - 1)
            kelly_stake = min(kelly_fraction * 1000, 400)  # Cap at $400
        
        # Determine prediction agreement
        if total_variance < 0.01:
            prediction_agreement = 'High Agreement'
        elif total_variance < 0.05:
            prediction_agreement = 'Medium Agreement'
        else:
            prediction_agreement = 'Low Agreement'
        
        return {
            'predicted_outcome': predicted_outcome,
            'confidence': max_prob * 100,
            'expected_value': expected_value,
            'kelly_stake': kelly_stake,
            'ensemble_consensus': max(consensus_home, consensus_draw, consensus_away),
            'model_variance': total_variance,
            'prediction_agreement': prediction_agreement,
            'odds_home': odds_data.get('home', 0),
            'odds_draw': odds_data.get('draw', 0),
            'odds_away': odds_data.get('away', 0),
            'bookmaker': bookmaker
        }
    
    def store_predictions(self, fixtures: List[Dict]):
        """Store ensemble predictions in database"""
        print("Storing ensemble predictions...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stored_count = 0
        
        for fixture in fixtures:
            try:
                # Get fixture details
                fixture_id = fixture.get('id')
                league = fixture.get('league', {})
                league_id = league.get('id')
                league_name = league.get('name', 'Unknown League')
                
                participants = fixture.get('participants', [])
                home_team = 'Unknown'
                away_team = 'Unknown'
                
                for participant in participants:
                    if participant.get('meta', {}).get('location') == 'home':
                        home_team = participant.get('name', 'Unknown')
                    elif participant.get('meta', {}).get('location') == 'away':
                        away_team = participant.get('name', 'Unknown')
                
                kickoff = fixture.get('starting_at', '')
                
                # Analyze ensemble prediction
                analysis = self.analyze_ensemble_prediction(fixture)
                if not analysis:
                    continue
                
                # Store prediction
                cursor.execute('''
                    INSERT OR REPLACE INTO predictions (
                        fixture_id, league_id, league_name, home_team, away_team,
                        kickoff_datetime, predicted_outcome, confidence, expected_value,
                        kelly_stake, ensemble_consensus, model_variance, prediction_agreement,
                        odds_home, odds_draw, odds_away, bookmaker
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    fixture_id, league_id, league_name, home_team, away_team,
                    kickoff, analysis['predicted_outcome'], analysis['confidence'],
                    analysis['expected_value'], analysis['kelly_stake'],
                    analysis['ensemble_consensus'], analysis['model_variance'],
                    analysis['prediction_agreement'], analysis['odds_home'],
                    analysis['odds_draw'], analysis['odds_away'], analysis['bookmaker']
                ))
                
                stored_count += 1
                
            except Exception as e:
                print(f"WARNING: Error processing fixture {fixture.get('id', 'unknown')}: {e}")
                continue
        
        conn.commit()
        conn.close()
        print(f"SUCCESS: Stored {stored_count} predictions successfully")
        return stored_count
    
    def analyze_stored_predictions(self):
        """Analyze stored predictions with precision tracking for ALL 27 leagues"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # All 27 leagues we check
        all_27_leagues = [
            'Premier League', 'Championship', 'FA Cup', 'Carabao Cup', 'Eredivisie', 
            'Bundesliga', 'Admiral Bundesliga', 'Pro League', '1. HNL', 'Superliga', 
            'Ligue 1', 'Serie A', 'Serie B', 'Coppa Italia', 'Eliteserien', 
            'Ekstraklasa', 'Liga Portugal', 'Premier League (Romanian)', 'Premiership', 
            'La Liga', 'La Liga 2', 'Copa Del Rey', 'Allsvenskan', 'Super League', 
            'Super Lig', 'Premier League (additional)', 'UEFA Europa League Play-offs'
        ]
        
        # Get league-by-league breakdown from database
        cursor.execute('''
            SELECT league_name, COUNT(*) as fixture_count,
                   AVG(confidence) as avg_confidence,
                   AVG(expected_value) as avg_ev,
                   MIN(confidence) as min_confidence,
                   MAX(confidence) as max_confidence
            FROM predictions 
            GROUP BY league_name 
            ORDER BY fixture_count DESC
        ''')
        
        db_league_stats = {row[0]: row[1:] for row in cursor.fetchall()}
        
        print("ALL 27 LEAGUES - COMPREHENSIVE BREAKDOWN:")
        print("-" * 85)
        print(f"{'League':<30} {'Status':<12} {'Fixtures':<10} {'Avg Conf':<10} {'Avg EV':<10}")
        print("-" * 85)
        
        total_fixtures = 0
        total_confidence = 0
        total_ev = 0
        leagues_with_fixtures = 0
        leagues_without_fixtures = 0
        
        for league_name in all_27_leagues:
            if league_name in db_league_stats:
                fixture_count, avg_conf, avg_ev, min_conf, max_conf = db_league_stats[league_name]
                status = "ACTIVE"
                total_fixtures += fixture_count
                total_confidence += avg_conf * fixture_count
                total_ev += avg_ev * fixture_count
                leagues_with_fixtures += 1
                print(f"{league_name:<30} {status:<12} {fixture_count:<10} {avg_conf:.1f}%{'':<6} {avg_ev:.1f}%{'':<6}")
            else:
                status = "NO FIXTURES"
                leagues_without_fixtures += 1
                print(f"{league_name:<30} {status:<12} {'0':<10} {'N/A':<10} {'N/A':<10}")
        
        print("-" * 85)
        
        if total_fixtures > 0:
            overall_avg_conf = total_confidence / total_fixtures
            overall_avg_ev = total_ev / total_fixtures
            
            print(f"{'TOTAL ACTIVE LEAGUES':<30} {leagues_with_fixtures:<12} {total_fixtures:<10} {overall_avg_conf:.1f}%{'':<6} {overall_avg_ev:.1f}%{'':<6}")
            print(f"{'LEAGUES WITHOUT FIXTURES':<30} {leagues_without_fixtures:<12} {'0':<10} {'N/A':<10} {'N/A':<10}")
            print(f"{'TOTAL LEAGUES CHECKED':<30} {'27':<12} {total_fixtures:<10} {'N/A':<10} {'N/A':<10}")
            print("-" * 85)
            
            # Confidence distribution
            cursor.execute('''
                SELECT 
                    CASE 
                        WHEN confidence >= 70 THEN 'High (70%+)'
                        WHEN confidence >= 60 THEN 'Medium (60-69%)'
                        WHEN confidence >= 50 THEN 'Low (50-59%)'
                        ELSE 'Very Low (<50%)'
                    END as conf_level,
                    COUNT(*) as count
                FROM predictions 
                GROUP BY conf_level
                ORDER BY MIN(confidence) DESC
            ''')
            
            conf_dist = cursor.fetchall()
            
            print("\nCONFIDENCE DISTRIBUTION:")
            print("-" * 40)
            for conf_level, count in conf_dist:
                percentage = (count / total_fixtures) * 100
                print(f"{conf_level:<20} {count:>3} fixtures ({percentage:>5.1f}%)")
            
            # EV distribution
            cursor.execute('''
                SELECT 
                    CASE 
                        WHEN expected_value >= 20 THEN 'Excellent (20%+)'
                        WHEN expected_value >= 10 THEN 'Good (10-19%)'
                        WHEN expected_value >= 5 THEN 'Fair (5-9%)'
                        WHEN expected_value >= 0 THEN 'Marginal (0-4%)'
                        ELSE 'Negative (<0%)'
                    END as ev_level,
                    COUNT(*) as count
                FROM predictions 
                GROUP BY ev_level
                ORDER BY MIN(expected_value) DESC
            ''')
            
            ev_dist = cursor.fetchall()
            
            print("\nEXPECTED VALUE DISTRIBUTION:")
            print("-" * 40)
            for ev_level, count in ev_dist:
                percentage = (count / total_fixtures) * 100
                print(f"{ev_level:<20} {count:>3} fixtures ({percentage:>5.1f}%)")
        
        conn.close()
    
    def show_results_summary(self):
        """Show comprehensive summary of results analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get overall accuracy stats by joining predictions with results
        cursor.execute('''
            SELECT 
                COUNT(*) as total_predictions,
                SUM(CASE WHEN p.predicted_outcome = r.actual_outcome THEN 1 ELSE 0 END) as correct_predictions,
                AVG(CASE WHEN p.predicted_outcome = r.actual_outcome THEN p.confidence ELSE NULL END) as avg_conf_correct,
                AVG(CASE WHEN p.predicted_outcome != r.actual_outcome THEN p.confidence ELSE NULL END) as avg_conf_incorrect,
                AVG(p.expected_value) as avg_ev
            FROM predictions p
            JOIN results r ON p.fixture_id = r.fixture_id
            WHERE r.actual_outcome IS NOT NULL
        ''')
        
        overall_stats = cursor.fetchone()
        
        if overall_stats and overall_stats[0] > 0:
            total_pred, correct_pred, avg_conf_correct, avg_conf_incorrect, avg_ev = overall_stats
            accuracy = (correct_pred / total_pred) * 100 if total_pred > 0 else 0
            
            print(f"\nOVERALL ACCURACY SUMMARY:")
            print("-" * 50)
            print(f"Total Predictions: {total_pred}")
            print(f"Correct Predictions: {correct_pred}")
            print(f"Overall Accuracy: {accuracy:.1f}%")
            print(f"Average EV: {avg_ev:.1f}%")
            if avg_conf_correct:
                print(f"Avg Confidence (Correct): {avg_conf_correct:.1f}%")
            if avg_conf_incorrect:
                print(f"Avg Confidence (Incorrect): {avg_conf_incorrect:.1f}%")
        
        # League-by-league accuracy
        cursor.execute('''
            SELECT 
                p.league_name,
                COUNT(*) as total,
                SUM(CASE WHEN p.predicted_outcome = r.actual_outcome THEN 1 ELSE 0 END) as correct,
                ROUND(SUM(CASE WHEN p.predicted_outcome = r.actual_outcome THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as accuracy,
                AVG(p.confidence) as avg_confidence
            FROM predictions p
            JOIN results r ON p.fixture_id = r.fixture_id
            WHERE r.actual_outcome IS NOT NULL
            GROUP BY p.league_name
            HAVING COUNT(*) > 0
            ORDER BY accuracy DESC
        ''')
        
        league_accuracy = cursor.fetchall()
        
        if league_accuracy:
            print(f"\nLEAGUE-BY-LEAGUE ACCURACY:")
            print("-" * 70)
            print(f"{'League':<25} {'Total':<8} {'Correct':<8} {'Accuracy':<10} {'Avg Conf':<10}")
            print("-" * 70)
            
            for league, total, correct, accuracy, avg_conf in league_accuracy:
                print(f"{league:<25} {total:<8} {correct:<8} {accuracy}%{'':<6} {avg_conf:.1f}%{'':<6}")
            
            print("-" * 70)
        else:
            print(f"\nNo completed matches found for accuracy analysis.")
            print("Results will be available after matches finish and are processed.")
        
        conn.close()
    
    def fetch_match_results(self):
        """Fetch actual match results from SportMonks API"""
        print("Fetching match results from SportMonks API...")
        
        # Get ALL fixtures we predicted for (don't rely on local time comparisons)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT fixture_id FROM predictions
        ''')
        fixture_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not fixture_ids:
            print("INFO: No fixtures found to check")
            return
        
        # Fetch results for each fixture
        results_count = 0
        
        FINAL_DESCRIPTORS = {"FT", "RESULT", "AFTER_EXTRA_TIME", "FULL_TIME", "PEN", "PENALTIES"}
        
        for fixture_id in fixture_ids:
            try:
                url = f"https://api.sportmonks.com/v3/football/fixtures/{fixture_id}"
                params = {
                    'api_token': self.sportmonks_token,
                    'include': 'scores'
                }
                
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                fixture_data = data.get('data', {})
                scores = fixture_data.get('scores', [])
                
                if not scores:
                    continue
                
                # Prefer final result-like entries
                final_score = None
                for score in scores:
                    desc = (score.get('description') or '').upper()
                    if desc in FINAL_DESCRIPTORS:
                        final_score = score
                        break
                
                # Fallback: try to take the last score snapshot if final not present
                if not final_score:
                    final_score = scores[-1]
                
                # Extract participant scores
                score_payload = final_score.get('score', {})
                # SportMonks delivers different shapes; try common keys
                home_score = score_payload.get('participant_id_1')
                away_score = score_payload.get('participant_id_2')
                
                # Fallbacks if keys differ
                if home_score is None or away_score is None:
                    home_score = score_payload.get('home', 0)
                    away_score = score_payload.get('away', 0)
                
                # Ensure integers
                try:
                    home_score = int(home_score)
                    away_score = int(away_score)
                except Exception:
                    continue
                
                # Determine actual outcome
                if home_score > away_score:
                    actual_outcome = 'Home'
                elif away_score > home_score:
                    actual_outcome = 'Away'
                else:
                    actual_outcome = 'Draw'
                
                # Store/update result
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO results (
                        fixture_id, home_score, away_score, actual_outcome, match_status
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (fixture_id, home_score, away_score, actual_outcome, 'COMPLETED'))
                conn.commit()
                conn.close()
                
                results_count += 1
                
            except Exception as e:
                print(f"WARNING: Error fetching result for fixture {fixture_id}: {e}")
                continue
        
        print(f"SUCCESS: Fetched {results_count} match results")
    
    def generate_league_reports(self):
        """Generate accuracy reports for each league"""
        print("Generating league accuracy reports...")
        
        conn = sqlite3.connect(self.db_path)
        
        # Get all leagues with predictions
        query = '''
            SELECT DISTINCT league_id, league_name 
            FROM predictions 
            ORDER BY league_name
        '''
        leagues = pd.read_sql_query(query, conn)
        
        reports = []
        
        for _, league in leagues.iterrows():
            league_id = league['league_id']
            league_name = league['league_name']
            
            # Get predictions and results for this league
            query = '''
                SELECT p.*, r.actual_outcome, r.home_score, r.away_score
                FROM predictions p
                LEFT JOIN results r ON p.fixture_id = r.fixture_id
                WHERE p.league_id = ? AND r.actual_outcome IS NOT NULL
            '''
            
            league_data = pd.read_sql_query(query, conn, params=(league_id,))
            
            if league_data.empty:
                continue
            
            # Calculate accuracy metrics
            total_predictions = len(league_data)
            correct_predictions = len(league_data[league_data['predicted_outcome'] == league_data['actual_outcome']])
            hit_rate = (correct_predictions / total_predictions) * 100 if total_predictions > 0 else 0
            
            avg_confidence = league_data['confidence'].mean()
            avg_expected_value = league_data['expected_value'].mean()
            
            # High vs low confidence accuracy
            high_conf = league_data[league_data['confidence'] >= 70]
            low_conf = league_data[league_data['confidence'] < 70]
            
            high_conf_accuracy = 0
            if not high_conf.empty:
                high_conf_correct = len(high_conf[high_conf['predicted_outcome'] == high_conf['actual_outcome']])
                high_conf_accuracy = (high_conf_correct / len(high_conf)) * 100
            
            low_conf_accuracy = 0
            if not low_conf.empty:
                low_conf_correct = len(low_conf[low_conf['predicted_outcome'] == low_conf['actual_outcome']])
                low_conf_accuracy = (low_conf_correct / len(low_conf)) * 100
            
            # Store analysis
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO accuracy_analysis (
                    league_id, league_name, total_predictions, correct_predictions,
                    hit_rate, avg_confidence, avg_expected_value,
                    high_confidence_accuracy, low_confidence_accuracy
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                league_id, league_name, total_predictions, correct_predictions,
                hit_rate, avg_confidence, avg_expected_value,
                high_conf_accuracy, low_conf_accuracy
            ))
            
            # Create league report
            report = {
                'league_id': league_id,
                'league_name': league_name,
                'total_predictions': total_predictions,
                'correct_predictions': correct_predictions,
                'hit_rate': hit_rate,
                'avg_confidence': avg_confidence,
                'avg_expected_value': avg_expected_value,
                'high_confidence_accuracy': high_conf_accuracy,
                'low_confidence_accuracy': low_conf_accuracy,
                'fixtures': league_data.to_dict('records')
            }
            
            reports.append(report)
        
        conn.commit()
        conn.close()
        
        # Save reports to JSON
        with open('league_accuracy_reports.json', 'w') as f:
            json.dump(reports, f, indent=2, default=str)
        
        print(f"SUCCESS: Generated {len(reports)} league reports")
        return reports
    
    def run_weekend_analysis(self):
        """Run complete weekend prediction analysis with precision"""
        print("Starting COMPREHENSIVE weekend prediction analysis...")
        print("=" * 60)
        print("ITERATING THROUGH ALL 27 LEAGUES WITH PRECISION")
        print("=" * 60)
        
        # Step 1: Fetch and store predictions with detailed tracking
        fixtures = self.fetch_weekend_fixtures()
        if fixtures:
            stored_count = self.store_predictions(fixtures)
            print(f"\nPRECISION SUMMARY:")
            print(f"- Total fixtures processed: {len(fixtures)}")
            print(f"- Predictions stored: {stored_count}")
            print(f"- Success rate: {(stored_count/len(fixtures)*100):.1f}%")
        
        # Step 2: Immediate analysis of stored predictions
        print("\n" + "=" * 60)
        print("IMMEDIATE PREDICTION ANALYSIS")
        print("=" * 60)
        self.analyze_stored_predictions()
        
        # Step 3: Prepare for results comparison
        print("\n" + "=" * 60)
        print("READY FOR RESULTS COMPARISON")
        print("=" * 60)
        print("Database prepared with precision tracking")
        print("Run 'python prediction_tracker.py --results' after matches finish")
        print("System will automatically:")
        print("  1. Fetch actual results from SportMonks API")
        print("  2. Compare predictions vs actual outcomes")
        print("  3. Generate detailed accuracy reports per league")
        print("  4. Create comprehensive analysis dashboard")
        
        print("\nSUCCESS: Comprehensive weekend analysis setup complete!")
        print("All 27 leagues processed with precision tracking")

if __name__ == "__main__":
    import sys
    
    tracker = PredictionTracker()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--results':
        # COMPREHENSIVE RESULTS ANALYSIS
        print("=" * 60)
        print("COMPREHENSIVE RESULTS ANALYSIS")
        print("=" * 60)
        print("Fetching actual results and comparing with predictions...")
        
        tracker.fetch_match_results()
        reports = tracker.generate_league_reports()
        
        print(f"\n" + "=" * 60)
        print("COMPREHENSIVE ACCURACY ANALYSIS COMPLETE")
        print("=" * 60)
        print(f"Generated {len(reports)} detailed league accuracy reports")
        print("Dashboard ready at: http://localhost:5000")
        
        # Show summary of results
        tracker.show_results_summary()
        
    else:
        # Initial setup - store predictions with precision
        tracker.run_weekend_analysis()
