#!/usr/bin/env python3
"""
SMARTBET LIVE PREDICTION CLI
===========================

Command-line interface for testing live predictions across all supported leagues.
Demonstrates the full prediction pipeline with example matches.

Usage:
    python predict_live.py                    # Run demo with all leagues
    python predict_live.py --league la_liga   # Test specific league
    python predict_live.py --custom           # Enter custom match
    python predict_live.py --batch            # Test batch predictions

Supported Leagues:
    - La Liga (Primary: 74.4% hit rate, 138.92% ROI)
    - Serie A (Backup: 61.5% hit rate, -9.10% ROI)  
    - Bundesliga (61.3% accuracy, 92.2% high-confidence hit rate)
    - Ligue 1 (64.3% accuracy, 92.1% high-confidence hit rate)
    - Premier League (Research model)
    - Liga I Romania (Research model)
"""

import argparse
import json
from datetime import datetime
from typing import Dict, List, Any
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from prediction_engine import PredictionEngine

class LivePredictionCLI:
    """Command-line interface for live predictions."""
    
    def __init__(self):
        """Initialize CLI with prediction engine."""
        self.engine = PredictionEngine()
        self.example_matches = self._get_example_matches()
        
    def _get_example_matches(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get example matches for each league."""
        return {
            "la_liga": [
                {
                    "league": "La Liga",
                    "home_team": "Real Madrid", 
                    "away_team": "Barcelona",
                    "home_win_odds": 2.10,
                    "draw_odds": 3.40,
                    "away_win_odds": 3.60,
                    "home_recent_form": 1.8,
                    "away_recent_form": 1.6,
                    "home_goals_for": 2.1,
                    "home_goals_against": 0.9,
                    "away_goals_for": 1.9,
                    "away_goals_against": 1.1,
                    "home_win_rate": 0.65,
                    "away_win_rate": 0.60,
                    "recent_form_diff": 0.2
                },
                {
                    "league": "La Liga",
                    "home_team": "Atletico Madrid",
                    "away_team": "Sevilla", 
                    "home_win_odds": 1.95,
                    "draw_odds": 3.30,
                    "away_win_odds": 4.20,
                    "home_recent_form": 1.7,
                    "away_recent_form": 1.4,
                    "home_goals_for": 1.8,
                    "home_goals_against": 1.0,
                    "away_goals_for": 1.5,
                    "away_goals_against": 1.3,
                    "home_win_rate": 0.55,
                    "away_win_rate": 0.45,
                    "recent_form_diff": 0.3
                }
            ],
            
            "serie_a": [
                {
                    "league": "Serie A",
                    "home_team": "Juventus",
                    "away_team": "AC Milan",
                    "home_win_odds": 2.25,
                    "draw_odds": 3.20,
                    "away_win_odds": 3.40,
                    "away_goals_for": 1.4,
                    "home_recent_form": 1.6,
                    "away_recent_form": 1.3
                },
                {
                    "league": "Serie A", 
                    "home_team": "Inter Milan",
                    "away_team": "Napoli",
                    "home_win_odds": 2.05,
                    "draw_odds": 3.45,
                    "away_win_odds": 3.80,
                    "away_goals_for": 1.6,
                    "home_recent_form": 1.8,
                    "away_recent_form": 1.5
                }
            ],
            
            "bundesliga": [
                {
                    "league": "Bundesliga",
                    "home_team": "Bayern Munich",
                    "away_team": "Borussia Dortmund",
                    "home_win_odds": 1.85,
                    "draw_odds": 3.80,
                    "away_win_odds": 4.20,
                    "home_avg_goals_for": 2.3,
                    "home_avg_goals_against": 0.8,
                    "home_win_rate": 0.75,
                    "home_draw_rate": 0.15,
                    "away_avg_goals_for": 2.0,
                    "away_avg_goals_against": 1.2,
                    "away_win_rate": 0.65,
                    "away_draw_rate": 0.20
                },
                {
                    "league": "Bundesliga",
                    "home_team": "RB Leipzig", 
                    "away_team": "Bayer Leverkusen",
                    "home_win_odds": 2.40,
                    "draw_odds": 3.30,
                    "away_win_odds": 3.10,
                    "home_avg_goals_for": 1.8,
                    "home_avg_goals_against": 1.3,
                    "home_win_rate": 0.50,
                    "home_draw_rate": 0.25,
                    "away_avg_goals_for": 1.9,
                    "away_avg_goals_against": 1.1,
                    "away_win_rate": 0.55,
                    "away_draw_rate": 0.22
                }
            ],
            
            "ligue_1": [
                {
                    "league": "Ligue 1",
                    "home_team": "Paris Saint-Germain",
                    "away_team": "Olympique Marseille",
                    "home_win_odds": 1.65,
                    "draw_odds": 4.00,
                    "away_win_odds": 5.50,
                    "home_avg_goals_for": 2.5,
                    "home_avg_goals_against": 0.7,
                    "home_win_rate": 0.80,
                    "home_draw_rate": 0.12,
                    "away_avg_goals_for": 1.6,
                    "away_avg_goals_against": 1.4,
                    "away_win_rate": 0.45,
                    "away_draw_rate": 0.28
                },
                {
                    "league": "Ligue 1",
                    "home_team": "AS Monaco",
                    "away_team": "Olympique Lyon",
                    "home_win_odds": 2.20,
                    "draw_odds": 3.40,
                    "away_win_odds": 3.60,
                    "home_avg_goals_for": 1.9,
                    "home_avg_goals_against": 1.2,
                    "home_win_rate": 0.55,
                    "home_draw_rate": 0.25,
                    "away_avg_goals_for": 1.7,
                    "away_avg_goals_against": 1.3,
                    "away_win_rate": 0.50,
                    "away_draw_rate": 0.24
                }
            ],
            
            "premier_league": [
                {
                    "league": "Premier League",
                    "home_team": "Manchester City",
                    "away_team": "Liverpool",
                    "home_win_odds": 2.05,
                    "draw_odds": 3.50,
                    "away_win_odds": 3.75
                },
                {
                    "league": "Premier League",
                    "home_team": "Arsenal",
                    "away_team": "Chelsea",
                    "home_win_odds": 2.30,
                    "draw_odds": 3.25,
                    "away_win_odds": 3.40
                }
            ],
            
            "liga_1": [
                {
                    "league": "Liga 1",
                    "home_team": "FCSB",
                    "away_team": "CFR Cluj",
                    "home_win_odds": 1.95,
                    "draw_odds": 3.40,
                    "away_win_odds": 4.00,
                    "home_avg_goals_for": 1.8,
                    "home_avg_goals_against": 0.9,
                    "home_win_rate": 0.60,
                    "home_draw_rate": 0.22,
                    "away_avg_goals_for": 1.6,
                    "away_avg_goals_against": 1.1,
                    "away_win_rate": 0.52,
                    "away_draw_rate": 0.26
                }
            ]
        }
    
    def run_demo(self):
        """Run demonstration with matches from all leagues."""
        print("🌟 SMARTBET LIVE PREDICTION DEMO")
        print("=" * 35)
        print("🎯 Testing all supported leagues with example matches\n")
        
        all_matches = []
        for league, matches in self.example_matches.items():
            all_matches.extend(matches)
        
        results = self.engine.predict_batch(all_matches)
        
        self._display_demo_summary(results)
        return results
    
    def test_league(self, league_name: str):
        """Test predictions for a specific league."""
        try:
            normalized_league = self.engine.model_mapper.normalize_league_name(league_name)
            league_key = normalized_league
            
            if league_key not in self.example_matches:
                print(f"❌ No example matches available for {league_name}")
                return
            
            print(f"🎯 TESTING {league_name.upper()} PREDICTIONS")
            print("=" * 40)
            
            matches = self.example_matches[league_key]
            results = self.engine.predict_batch(matches)
            
            self._display_league_summary(league_name, results)
            return results
            
        except ValueError as e:
            print(f"❌ Error: {e}")
            return None
    
    def run_custom_match(self):
        """Run prediction on user-input match."""
        print("⚡ CUSTOM MATCH PREDICTION")
        print("=" * 27)
        
        try:
            # Get basic match info
            league = input("🏆 League: ").strip()
            home_team = input("🏠 Home team: ").strip()
            away_team = input("🏃 Away team: ").strip()
            
            # Get odds
            home_odds = float(input("💰 Home win odds: "))
            draw_odds = float(input("💰 Draw odds: "))
            away_odds = float(input("💰 Away win odds: "))
            
            # Create match data
            match_data = {
                "league": league,
                "home_team": home_team,
                "away_team": away_team,
                "home_win_odds": home_odds,
                "draw_odds": draw_odds,
                "away_win_odds": away_odds
            }
            
            # Get optional features
            print("\n📊 Optional features (press Enter to skip):")
            optional_features = {
                "home_recent_form": "Home recent form (1.0-2.0)",
                "away_recent_form": "Away recent form (1.0-2.0)",
                "home_avg_goals_for": "Home avg goals for",
                "away_avg_goals_for": "Away avg goals for"
            }
            
            for key, description in optional_features.items():
                value = input(f"   {description}: ").strip()
                if value:
                    try:
                        match_data[key] = float(value)
                    except ValueError:
                        print(f"   ⚠️ Invalid value for {key}, skipping")
            
            # Make prediction
            result = self.engine.predict_match(match_data)
            
            self._display_custom_result(result)
            return result
            
        except (ValueError, KeyboardInterrupt) as e:
            print(f"\n❌ Error or cancelled: {e}")
            return None
    
    def run_batch_test(self):
        """Run comprehensive batch test with performance analysis."""
        print("📊 COMPREHENSIVE BATCH TEST")
        print("=" * 28)
        
        # Collect all example matches
        all_matches = []
        league_counts = {}
        
        for league, matches in self.example_matches.items():
            all_matches.extend(matches)
            league_counts[league] = len(matches)
        
        print(f"🎯 Total matches: {len(all_matches)}")
        for league, count in league_counts.items():
            print(f"   {league.replace('_', ' ').title()}: {count} matches")
        
        # Run predictions
        results = self.engine.predict_batch(all_matches)
        
        # Analyze results
        self._analyze_batch_results(results)
        return results
    
    def _display_demo_summary(self, results: List[Dict[str, Any]]):
        """Display summary of demo results."""
        print(f"\n🏆 DEMO RESULTS SUMMARY")
        print("=" * 22)
        
        total_matches = len(results)
        successful = len([r for r in results if 'error' not in r])
        recommended_bets = len([r for r in results if r.get('recommend', False)])
        
        print(f"📊 Total matches processed: {total_matches}")
        print(f"✅ Successful predictions: {successful}")
        print(f"🎯 Betting recommendations: {recommended_bets}")
        print(f"📈 Recommendation rate: {recommended_bets/total_matches:.1%}")
        
        # Show recommended bets
        if recommended_bets > 0:
            print(f"\n💰 RECOMMENDED BETS:")
            for result in results:
                if result.get('recommend', False):
                    print(f"   ✔ {result['home_team']} vs {result['away_team']} ({result['league']})")
                    print(f"     → {result['prediction']} @ {result['predicted_odds']:.2f} ({result['confidence']:.1%} confidence)")
        else:
            print(f"\n⚠️ No bets recommended (all matches filtered out)")
        
        # Show league performance
        print(f"\n📊 LEAGUE BREAKDOWN:")
        league_stats = {}
        for result in results:
            if 'error' not in result:
                league = result['league']
                if league not in league_stats:
                    league_stats[league] = {'total': 0, 'recommended': 0}
                league_stats[league]['total'] += 1
                if result.get('recommend', False):
                    league_stats[league]['recommended'] += 1
        
        for league, stats in league_stats.items():
            rate = stats['recommended'] / stats['total'] if stats['total'] > 0 else 0
            print(f"   {league}: {stats['recommended']}/{stats['total']} ({rate:.1%})")
    
    def _display_league_summary(self, league_name: str, results: List[Dict[str, Any]]):
        """Display summary for specific league test."""
        print(f"\n🏆 {league_name.upper()} RESULTS")
        print("=" * 25)
        
        for result in results:
            if 'error' not in result:
                status = "✔ BET" if result['recommend'] else "✖ SKIP"
                print(f"{status} {result['home_team']} vs {result['away_team']}")
                print(f"    → {result['prediction']} @ {result['predicted_odds']:.2f} ({result['confidence']:.1%})")
                print(f"    💡 {result['recommendation_reason']}")
            else:
                print(f"❌ ERROR: {result.get('home_team', 'Unknown')} vs {result.get('away_team', 'Unknown')}")
                print(f"    {result['error']}")
    
    def _display_custom_result(self, result: Dict[str, Any]):
        """Display result for custom match."""
        print(f"\n🎯 PREDICTION RESULT")
        print("=" * 18)
        
        if 'error' not in result:
            print(f"🏠 Match: {result['home_team']} vs {result['away_team']}")
            print(f"🏆 League: {result['league']}")
            print(f"🔮 Prediction: {result['prediction']}")
            print(f"🎲 Confidence: {result['confidence']:.1%}")
            print(f"💰 Predicted odds: {result['predicted_odds']:.2f}")
            print(f"📊 Recommendation: {'BET' if result['recommend'] else 'SKIP'}")
            print(f"💡 Reason: {result['recommendation_reason']}")
            
            print(f"\n📈 All probabilities:")
            for outcome, prob in result['all_probabilities'].items():
                print(f"   {outcome.replace('_', ' ').title()}: {prob:.1%}")
                
            print(f"\n📊 Model info:")
            model_info = result['model_info']
            print(f"   Status: {model_info['model_status']}")
            if 'hit_rate' in model_info['model_performance']:
                print(f"   Hit rate: {model_info['model_performance']['hit_rate']:.1%}")
            if 'roi' in model_info['model_performance']:
                print(f"   ROI: {model_info['model_performance']['roi']:.2f}%")
        else:
            print(f"❌ Error: {result['error']}")
    
    def _analyze_batch_results(self, results: List[Dict[str, Any]]):
        """Analyze batch test results in detail."""
        print(f"\n📊 DETAILED BATCH ANALYSIS")
        print("=" * 27)
        
        # Basic stats
        total = len(results)
        successful = [r for r in results if 'error' not in r]
        errors = [r for r in results if 'error' in r]
        recommended = [r for r in successful if r.get('recommend', False)]
        
        print(f"📈 Processing Statistics:")
        print(f"   Total matches: {total}")
        print(f"   Successful: {len(successful)} ({len(successful)/total:.1%})")
        print(f"   Errors: {len(errors)} ({len(errors)/total:.1%})")
        print(f"   Recommended bets: {len(recommended)} ({len(recommended)/total:.1%})")
        
        # Confidence distribution
        if successful:
            confidences = [r['confidence'] for r in successful]
            print(f"\n🎯 Confidence Distribution:")
            print(f"   Average: {np.mean(confidences):.1%}")
            print(f"   Min: {min(confidences):.1%}")
            print(f"   Max: {max(confidences):.1%}")
            
            # Confidence buckets
            high_conf = len([c for c in confidences if c >= 0.7])
            med_conf = len([c for c in confidences if 0.5 <= c < 0.7])
            low_conf = len([c for c in confidences if c < 0.5])
            
            print(f"   High (≥70%): {high_conf}/{len(successful)} ({high_conf/len(successful):.1%})")
            print(f"   Medium (50-70%): {med_conf}/{len(successful)} ({med_conf/len(successful):.1%})")
            print(f"   Low (<50%): {low_conf}/{len(successful)} ({low_conf/len(successful):.1%})")
        
        # League analysis
        print(f"\n🏆 League Performance:")
        league_analysis = {}
        for result in successful:
            league = result['league']
            if league not in league_analysis:
                league_analysis[league] = {
                    'total': 0, 'recommended': 0, 'confidences': [], 'predictions': {'Home Win': 0, 'Away Win': 0, 'Draw': 0}
                }
            
            stats = league_analysis[league]
            stats['total'] += 1
            stats['confidences'].append(result['confidence'])
            stats['predictions'][result['prediction']] += 1
            if result.get('recommend', False):
                stats['recommended'] += 1
        
        for league, stats in league_analysis.items():
            rec_rate = stats['recommended'] / stats['total'] if stats['total'] > 0 else 0
            avg_conf = np.mean(stats['confidences']) if stats['confidences'] else 0
            print(f"   {league}: {stats['recommended']}/{stats['total']} ({rec_rate:.1%}) - Avg conf: {avg_conf:.1%}")
        
        # Prediction distribution
        if successful:
            pred_dist = {'Home Win': 0, 'Away Win': 0, 'Draw': 0}
            for result in successful:
                pred_dist[result['prediction']] += 1
            
            print(f"\n🔮 Prediction Distribution:")
            for pred, count in pred_dist.items():
                print(f"   {pred}: {count}/{len(successful)} ({count/len(successful):.1%})")
        
        # Show errors if any
        if errors:
            print(f"\n❌ Errors Encountered:")
            for error in errors:
                print(f"   {error.get('home_team', 'Unknown')} vs {error.get('away_team', 'Unknown')}: {error['error']}")

def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="SmartBet Live Prediction CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python predict_live.py                    # Run full demo
    python predict_live.py --league la_liga   # Test La Liga only  
    python predict_live.py --custom           # Enter custom match
    python predict_live.py --batch            # Comprehensive test
        
Supported leagues: la_liga, serie_a, bundesliga, ligue_1, premier_league, liga_1
        """
    )
    
    parser.add_argument('--league', type=str, help='Test specific league')
    parser.add_argument('--custom', action='store_true', help='Enter custom match data')
    parser.add_argument('--batch', action='store_true', help='Run comprehensive batch test')
    parser.add_argument('--output', type=str, help='Save results to JSON file')
    
    args = parser.parse_args()
    
    # Initialize CLI
    try:
        cli = LivePredictionCLI()
    except Exception as e:
        print(f"❌ Failed to initialize prediction engine: {e}")
        return 1
    
    # Execute requested action
    results = None
    
    try:
        if args.custom:
            results = cli.run_custom_match()
        elif args.league:
            results = cli.test_league(args.league)
        elif args.batch:
            results = cli.run_batch_test()
        else:
            results = cli.run_demo()
        
        # Save results if requested
        if args.output and results:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to {args.output}")
            
    except KeyboardInterrupt:
        print(f"\n⚠️ Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    import numpy as np  # For confidence analysis
    exit(main()) 