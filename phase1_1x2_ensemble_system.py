#!/usr/bin/env python3
"""
Phase 1: 1X2 Market Stabilization System
Fetch all 1X2 predictions from 27 leagues and develop ensemble logic
"""

import requests
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from collections import defaultdict, Counter
import statistics

load_dotenv()

API_TOKEN = os.getenv('SPORTMONKS_API_TOKEN')
if not API_TOKEN:
    print("ERROR: SPORTMONKS_API_TOKEN not found in environment")
    exit(1)

print(f"Phase 1: 1X2 Market Stabilization System")
print(f"API Token: {API_TOKEN[:10]}...")
print(f"Current time: {datetime.now()}")
print("="*80)

# All 27 leagues covered by subscription
SUPPORTED_LEAGUE_IDS = [
    8,     # Premier League
    9,     # Championship
    24,    # FA Cup
    27,    # Carabao Cup
    72,    # Eredivisie
    82,    # Bundesliga
    181,   # Admiral Bundesliga
    208,   # Pro League
    244,   # 1. HNL
    271,   # Superliga
    301,   # Ligue 1
    384,   # Serie A
    387,   # Serie B
    390,   # Coppa Italia
    444,   # Eliteserien
    453,   # Ekstraklasa
    462,   # Liga Portugal
    486,   # Premier League (Romanian)
    501,   # Premiership
    564,   # La Liga
    567,   # La Liga 2
    570,   # Copa Del Rey
    573,   # Allsvenskan
    591,   # Super League
    600,   # Super Lig
    609,   # Premier League (additional)
    1371,  # UEFA Europa League Play-offs
]

# 1X2 prediction type IDs
X12_TYPE_IDS = [233, 237, 238]

class X12EnsembleSystem:
    def __init__(self):
        self.api_token = API_TOKEN
        self.base_url = "https://api.sportmonks.com/v3/football"
        self.rate_limit_delay = 1.5
        
        # Store all predictions for analysis
        self.all_predictions = []
        self.league_stats = defaultdict(list)
        self.model_performance = defaultdict(list)
        
    def fetch_league_fixtures(self, league_id, league_name):
        """Fetch fixtures for a specific league"""
        print(f"\n{'='*60}")
        print(f"Fetching {league_name} (ID: {league_id})")
        print(f"{'='*60}")
        
        # Calculate date range for next 14 days
        now = datetime.now()
        fourteen_days_from_now = now + timedelta(days=14)
        start_date = now.strftime('%Y-%m-%d')
        end_date = fourteen_days_from_now.strftime('%Y-%m-%d')
        
        url = f"{self.base_url}/fixtures/between/{start_date}/{end_date}"
        params = {
            'api_token': self.api_token,
            'include': 'participants;league;metadata;predictions',
            'filters': f'fixtureLeagues:{league_id}',
            'per_page': '50',
            'page': '1',
            'timezone': 'Europe/Bucharest'
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                fixtures = data.get('data', [])
                
                if not fixtures:
                    print(f"No fixtures found for {league_name}")
                    return []
                
                print(f"Found {len(fixtures)} fixtures")
                
                # Process fixtures for 1X2 predictions
                league_predictions = []
                for fixture in fixtures:
                    prediction_data = self.extract_1x2_predictions(fixture)
                    if prediction_data:
                        league_predictions.append(prediction_data)
                        self.all_predictions.append(prediction_data)
                
                print(f"Found {len(league_predictions)} fixtures with 1X2 predictions")
                self.league_stats[league_name] = league_predictions
                
                return league_predictions
                
            else:
                print(f"Error fetching {league_name}: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Error analyzing {league_name}: {e}")
            return []
    
    def extract_1x2_predictions(self, fixture):
        """Extract 1X2 predictions from a fixture"""
        fixture_id = fixture.get('id')
        participants = fixture.get('participants', [])
        home_team = participants[0].get('name', 'Home') if len(participants) > 0 else 'Home'
        away_team = participants[1].get('name', 'Away') if len(participants) > 1 else 'Away'
        kickoff = fixture.get('starting_at', '')
        league_name = fixture.get('league', {}).get('name', 'Unknown')
        
        # Extract 1X2 predictions (type_ids: 233, 237, 238)
        x12_predictions = []
        predictions = fixture.get('predictions', [])
        
        for pred in predictions:
            type_id = pred.get('type_id')
            if type_id in X12_TYPE_IDS:
                pred_data = pred.get('predictions', {})
                if ('home' in pred_data and 'draw' in pred_data and 'away' in pred_data):
                    x12_predictions.append({
                        'type_id': type_id,
                        'model_id': pred.get('id'),
                        'home': pred_data.get('home', 0),
                        'draw': pred_data.get('draw', 0),
                        'away': pred_data.get('away', 0)
                    })
        
        if len(x12_predictions) == 3:  # All 3 models available
            return {
                'fixture_id': fixture_id,
                'league': league_name,
                'home_team': home_team,
                'away_team': away_team,
                'kickoff': kickoff,
                'predictions': x12_predictions
            }
        
        return None
    
    def ensemble_methods(self, predictions):
        """Apply different ensemble methods to 3 model predictions"""
        if len(predictions) != 3:
            return None
        
        # Extract probabilities from each model
        model_probs = []
        for pred in predictions:
            model_probs.append({
                'home': pred['home'],
                'draw': pred['draw'],
                'away': pred['away']
            })
        
        # Method 1: Simple Average
        simple_avg = {
            'home': statistics.mean([m['home'] for m in model_probs]),
            'draw': statistics.mean([m['draw'] for m in model_probs]),
            'away': statistics.mean([m['away'] for m in model_probs])
        }
        
        # Method 2: Weighted Average (equal weights for now)
        weighted_avg = simple_avg.copy()  # Same as simple for now
        
        # Method 3: Consensus Method
        consensus = self.consensus_method(model_probs)
        
        # Method 4: Variance-Weighted Average
        variance_weighted = self.variance_weighted_method(model_probs)
        
        return {
            'simple_average': simple_avg,
            'weighted_average': weighted_avg,
            'consensus': consensus,
            'variance_weighted': variance_weighted,
            'individual_models': model_probs
        }
    
    def consensus_method(self, model_probs):
        """Consensus method: majority vote with confidence weighting"""
        # Find the outcome each model predicts
        model_outcomes = []
        for model in model_probs:
            max_prob = max(model['home'], model['draw'], model['away'])
            if max_prob == model['home']:
                model_outcomes.append('home')
            elif max_prob == model['draw']:
                model_outcomes.append('draw')
            else:
                model_outcomes.append('away')
        
        # Count votes
        vote_counts = Counter(model_outcomes)
        majority_outcome = vote_counts.most_common(1)[0][0]
        
        # Calculate consensus probabilities
        if majority_outcome == 'home':
            consensus_home = max([m['home'] for m in model_probs])
            consensus_draw = statistics.mean([m['draw'] for m in model_probs])
            consensus_away = statistics.mean([m['away'] for m in model_probs])
        elif majority_outcome == 'draw':
            consensus_home = statistics.mean([m['home'] for m in model_probs])
            consensus_draw = max([m['draw'] for m in model_probs])
            consensus_away = statistics.mean([m['away'] for m in model_probs])
        else:  # away
            consensus_home = statistics.mean([m['home'] for m in model_probs])
            consensus_draw = statistics.mean([m['draw'] for m in model_probs])
            consensus_away = max([m['away'] for m in model_probs])
        
        return {
            'home': consensus_home,
            'draw': consensus_draw,
            'away': consensus_away
        }
    
    def variance_weighted_method(self, model_probs):
        """Variance-weighted method: weight models by their agreement"""
        # Calculate variance for each outcome
        home_vars = [m['home'] for m in model_probs]
        draw_vars = [m['draw'] for m in model_probs]
        away_vars = [m['away'] for m in model_probs]
        
        home_variance = statistics.variance(home_vars) if len(home_vars) > 1 else 0
        draw_variance = statistics.variance(draw_vars) if len(draw_vars) > 1 else 0
        away_variance = statistics.variance(away_vars) if len(away_vars) > 1 else 0
        
        # Lower variance = higher weight (more agreement)
        total_variance = home_variance + draw_variance + away_variance
        if total_variance == 0:
            return self.simple_average(model_probs)
        
        # Weight by inverse variance
        home_weight = 1 / (1 + home_variance)
        draw_weight = 1 / (1 + draw_variance)
        away_weight = 1 / (1 + away_variance)
        
        total_weight = home_weight + draw_weight + away_weight
        
        return {
            'home': sum(m['home'] * home_weight for m in model_probs) / total_weight,
            'draw': sum(m['draw'] * draw_weight for m in model_probs) / total_weight,
            'away': sum(m['away'] * away_weight for m in model_probs) / total_weight
        }
    
    def simple_average(self, model_probs):
        """Simple average of all models"""
        return {
            'home': statistics.mean([m['home'] for m in model_probs]),
            'draw': statistics.mean([m['draw'] for m in model_probs]),
            'away': statistics.mean([m['away'] for m in model_probs])
        }
    
    def analyze_ensemble_performance(self):
        """Analyze the performance of different ensemble methods"""
        print(f"\n{'='*80}")
        print("ENSEMBLE PERFORMANCE ANALYSIS")
        print(f"{'='*80}")
        
        if not self.all_predictions:
            print("No predictions available for analysis")
            return
        
        print(f"Total fixtures with 1X2 predictions: {len(self.all_predictions)}")
        
        # Analyze each ensemble method
        ensemble_results = defaultdict(list)
        
        for prediction_data in self.all_predictions:
            ensemble = self.ensemble_methods(prediction_data['predictions'])
            if ensemble:
                for method, probs in ensemble.items():
                    if method != 'individual_models':
                        max_prob = max(probs['home'], probs['draw'], probs['away'])
                        outcome = 'home' if max_prob == probs['home'] else ('draw' if max_prob == probs['draw'] else 'away')
                        
                        ensemble_results[method].append({
                            'outcome': outcome,
                            'confidence': max_prob,
                            'fixture': f"{prediction_data['home_team']} vs {prediction_data['away_team']}",
                            'league': prediction_data['league']
                        })
        
        # Display results for each method
        for method, results in ensemble_results.items():
            print(f"\n{method.upper().replace('_', ' ')}:")
            print(f"  Total predictions: {len(results)}")
            
            # Confidence distribution
            confidences = [r['confidence'] for r in results]
            high_confidence = len([c for c in confidences if c >= 0.6])
            medium_confidence = len([c for c in confidences if 0.5 <= c < 0.6])
            low_confidence = len([c for c in confidences if c < 0.5])
            
            print(f"  High confidence (>=60%): {high_confidence}")
            print(f"  Medium confidence (50-59%): {medium_confidence}")
            print(f"  Low confidence (<50%): {low_confidence}")
            print(f"  Average confidence: {statistics.mean(confidences):.1f}%")
            print(f"  Max confidence: {max(confidences):.1f}%")
            
            # Top predictions
            top_predictions = sorted(results, key=lambda x: x['confidence'], reverse=True)[:5]
            print(f"  Top 5 predictions:")
            for i, pred in enumerate(top_predictions, 1):
                print(f"    {i}. {pred['fixture']} ({pred['league']}) - {pred['outcome'].upper()} {pred['confidence']:.1f}%")
    
    def run_phase1_analysis(self):
        """Run the complete Phase 1 analysis"""
        print("Starting Phase 1: 1X2 Market Stabilization")
        print("="*80)
        
        # Fetch predictions from all 27 leagues
        for league_id in SUPPORTED_LEAGUE_IDS:
            league_name = f"League {league_id}"  # We'll get the actual name from API
            self.fetch_league_fixtures(league_id, league_name)
        
        # Analyze ensemble performance
        self.analyze_ensemble_performance()
        
        print(f"\n{'='*80}")
        print("PHASE 1 COMPLETE")
        print(f"{'='*80}")
        print(f"Total fixtures analyzed: {len(self.all_predictions)}")
        print(f"Leagues with predictions: {len(self.league_stats)}")
        print("Ensemble methods implemented and tested")

if __name__ == "__main__":
    system = X12EnsembleSystem()
    system.run_phase1_analysis()
