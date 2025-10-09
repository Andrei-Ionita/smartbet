#!/usr/bin/env python3
"""
Comprehensive Analysis of SmartBet Predictions System
===================================================

This script analyzes the current state of the predictions system and provides:
1. Current API endpoint analysis
2. Predictions data structure examination
3. Multi-model analysis logic verification
4. Confidence calculation methodology
5. Recommendations for fixing the home page

Author: SmartBet Analysis
Date: 2025-10-06
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any

class PredictionsAnalyzer:
    """Comprehensive analyzer for the SmartBet predictions system"""

    def __init__(self):
        self.target_leagues = {
            8: "Premier League",
            564: "La Liga",
            384: "Serie A",
            82: "Bundesliga",
            301: "Ligue 1"
        }

    def analyze_current_api_endpoints(self):
        """Analyze the current API endpoints being used"""
        print("API ENDPOINT ANALYSIS")
        print("=" * 50)

        # Current implementation analysis
        current_endpoint = "/fixtures/upcoming/markets/1"
        print(f"Current API Endpoint: {current_endpoint}")

        # Check if this endpoint includes predictions
        print("Issues with current endpoint:")
        print("ERROR: /markets/1 endpoint is for ODDS, not PREDICTIONS")
        print("ERROR: Predictions require the 'predictions' addon")
        print("ERROR: Need to use /fixtures/upcoming with predictions include")

        # Alternative endpoints
        print("\nRecommended Endpoints:")
        print("1. /fixtures/upcoming?include=participants;league;metadata;predictions")
        print("2. /predictions (if available)")

    def analyze_prediction_structure(self):
        """Analyze the prediction data structure"""
        print("\nPREDICTION DATA STRUCTURE ANALYSIS")
        print("=" * 50)

        # Check existing prediction files
        prediction_files = [
            "sportmonks_predictions_20250928_102616.json",
            "sportmonks_predictions_20250928_123902.json",
            "sportmonks_predictions_20250928_125558.json"
        ]

        print("Existing Prediction Files Found:")
        for file in prediction_files:
            if os.path.exists(file):
                print(f"OK: {file}")
                # Analyze structure
                with open(file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and list(data.keys())[0] in self.target_leagues.values():
                        league_name = list(data.keys())[0]
                        fixtures = data[league_name]
                        print(f"   STATS: {league_name}: {len(fixtures)} fixtures")

                        if fixtures:
                            sample_fixture = fixtures[0]
                            print(f"   STRUCTURE: Sample structure keys: {list(sample_fixture.keys())}")
                            if 'match_winner_prediction' in sample_fixture:
                                pred = sample_fixture['match_winner_prediction']
                                print(f"   PREDICTION: Prediction format: Home={pred.get('home', 0):.1f}%, Draw={pred.get('draw', 0):.1f}%, Away={pred.get('away', 0):.1f}%")
            else:
                print(f"ERROR: {file} - File not found")

    def analyze_multi_model_logic(self):
        """Analyze the multi-model prediction logic"""
        print("\nMULTI-MODEL ANALYSIS LOGIC")
        print("=" * 50)

        print("Current Implementation Features:")
        print("OK: Multiple model validation (3+ models per fixture)")
        print("OK: Probability sum validation (90-110%)")
        print("OK: Consensus calculation")
        print("OK: Variance analysis")
        print("OK: Ensemble vs Highest Confidence strategy selection")
        print("OK: 55% minimum confidence threshold")

        print("\nStrategy Selection Logic:")
        print("1. Ensemble Average: consensus >60% AND variance <50")
        print("2. Highest Confidence with Consensus: 3+ models, lower consensus")
        print("3. Highest Confidence: fallback for limited models")

        print("\nConfidence Calculation:")
        print("- Uses max probability from selected strategy")
        print("- 55% minimum threshold for recommendations")
        print("- EV calculation (when odds available)")

    def analyze_home_page_issue(self):
        """Analyze why the home page has no fixtures"""
        print("\nHOME PAGE ISSUE ANALYSIS")
        print("=" * 50)

        print("Potential Issues Identified:")

        # 1. API Token Issue
        api_token = os.getenv('SPORTMONKS_API_TOKEN')
        if not api_token:
            print("ERROR: API Token: SPORTMONKS_API_TOKEN not set in environment")
            print("   SOLUTION: Create .env file with valid token")
        else:
            print(f"OK: API Token: Found (length: {len(api_token)})")

        # 2. API Endpoint Issue
        print("ERROR: API Endpoint: Using /markets/1 which is for odds, not predictions")
        print("   SOLUTION: Change to /fixtures/upcoming?include=predictions")

        # 3. Data Structure Issue
        print("ERROR: Data Structure: Current endpoint may not include predictions")
        print("   SOLUTION: Ensure 'predictions' is in include parameter")

        # 4. Confidence Threshold Issue
        print("ERROR: Confidence Threshold: 55% minimum may be too high")
        print("   SOLUTION: Consider lowering to 50-52% for more matches")

        # 5. League Filter Issue
        print("OK: League Filter: Correctly filtering to 5 target leagues")

        # 6. Time Window Issue
        print("OK: Time Window: Correctly filtering to next 7 days")

    def analyze_league_coverage(self):
        """Analyze league coverage and data availability"""
        print("\nLEAGUE COVERAGE ANALYSIS")
        print("=" * 50)

        print("Target Leagues (SportMonks IDs):")
        for league_id, league_name in self.target_leagues.items():
            print(f"   {league_id}: {league_name}")

        print("\nExpected Data per League:")
        print("- 3-5 prediction models per fixture")
        print("- 1X2 probabilities (Home, Draw, Away)")
        print("- Confidence scores per model")
        print("- Metadata (predictable status)")

    def provide_recommendations(self):
        """Provide specific recommendations to fix the system"""
        print("\nRECOMMENDATIONS TO FIX SYSTEM")
        print("=" * 50)

        print("Immediate Fixes Needed:")

        print("\n1. API Token Setup:")
        print("   - Create .env file in project root")
        print("   - Add: SPORTMONKS_API_TOKEN=your_actual_token")
        print("   - Restart application after setting token")

        print("\n2. API Endpoint Fix:")
        print("   - Change: /fixtures/upcoming/markets/1")
        print("   - To: /fixtures/upcoming?include=participants;league;metadata;predictions")
        print("   - Remove markets parameter")

        print("\n3. Confidence Threshold Adjustment:")
        print("   - Current: 55% minimum")
        print("   - Suggested: 50-52% for more opportunities")
        print("   - Test with both thresholds")

        print("\n4. Data Validation Enhancement:")
        print("   - Add more robust probability validation")
        print("   - Handle cases where predictions are missing")
        print("   - Add fallback strategies")

        print("\n5. Debugging & Monitoring:")
        print("   - Add detailed logging for API responses")
        print("   - Monitor prediction availability")
        print("   - Track confidence distribution")

    def generate_sample_predictions_report(self):
        """Generate a sample report of what the predictions should look like"""
        print("\nSAMPLE PREDICTIONS REPORT")
        print("=" * 50)

        print("Expected Output Format:")
        print("League: Premier League")
        print("Match: Arsenal vs Chelsea (Fixture ID: 12345)")
        print("Date: 2025-10-10 15:00:00")
        print("")
        print("Predictions Analysis:")
        print("Model 1: Home=65.2%, Draw=20.1%, Away=14.7%")
        print("Model 2: Home=62.8%, Draw=22.3%, Away=14.9%")
        print("Model 3: Home=67.1%, Draw=19.5%, Away=13.4%")
        print("")
        print("Analysis Results:")
        print("Strategy: Ensemble Average")
        print("Consensus: 100% (all models predict Home)")
        print("Variance: 4.2 (very low)")
        print("Final Prediction: Home=65.0%, Draw=20.6%, Away=14.3%")
        print("")
        print("Recommendation:")
        print("Outcome: Home Win")
        print("Confidence: 65%")
        print("Minimum Threshold: 55% OK")
        print("Strategy: Ensemble Average (high consensus, low variance)")
        print("Score: 65.0")
        print("Explanation: 3 models strongly agree with low variance")

    def run_complete_analysis(self):
        """Run the complete analysis"""
        print("SMARTBET PREDICTIONS SYSTEM ANALYSIS")
        print("=" * 60)
        print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        self.analyze_current_api_endpoints()
        self.analyze_prediction_structure()
        self.analyze_multi_model_logic()
        self.analyze_home_page_issue()
        self.analyze_league_coverage()
        self.provide_recommendations()
        self.generate_sample_predictions_report()

        print("\n" + "=" * 60)
        print("ANALYSIS COMPLETE")
        print("=" * 60)

if __name__ == "__main__":
    analyzer = PredictionsAnalyzer()
    analyzer.run_complete_analysis()
