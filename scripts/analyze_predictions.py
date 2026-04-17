#!/usr/bin/env python3
"""
Prediction Performance Analysis & Backtesting Script
=====================================================

Analyzes current prediction performance and simulates what the improved
PredictionEnhancerV2 strategy would have produced.

Compares V1 vs V2:
- Accuracy (overall, by league, by market, by confidence band)
- ROI simulation
- Recommendation volume (how many picks pass each filter)
- Quality score distributions

Usage:
    # From project root with Django settings:
    python scripts/analyze_predictions.py

    # Or via Django management:
    DJANGO_SETTINGS_MODULE=smartbet.settings python scripts/analyze_predictions.py

    # Standalone (simulated data when DB unavailable):
    python scripts/analyze_predictions.py --simulated
"""

import os
import sys
import json
import csv
import math
import argparse
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# ---------------------------------------------------------------------------
# Try Django setup, fall back to standalone mode
# ---------------------------------------------------------------------------
DJANGO_AVAILABLE = False
try:
    # Add project root to path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartbet.settings')
    import django
    django.setup()
    DJANGO_AVAILABLE = True
except Exception:
    pass


def load_predictions_from_db() -> List[Dict]:
    """Load completed predictions from PredictionLog."""
    from core.models import PredictionLog

    predictions = PredictionLog.objects.filter(
        actual_outcome__isnull=False,
        was_correct__isnull=False,
    ).order_by('kickoff')

    results = []
    for p in predictions:
        # Normalize confidence to 0-1
        conf = p.confidence
        if conf is not None and conf > 1:
            conf = conf / 100

        ev = p.expected_value
        if ev is not None and abs(ev) > 1:
            ev = ev / 100

        prob_home = p.probability_home or 0
        prob_draw = p.probability_draw or 0
        prob_away = p.probability_away or 0
        if prob_home > 1:
            prob_home, prob_draw, prob_away = prob_home / 100, prob_draw / 100, prob_away / 100

        # Get predicted odds
        predicted_outcome = (p.predicted_outcome or '').lower()
        predicted_odds = None
        if predicted_outcome == 'home' and p.odds_home:
            predicted_odds = p.odds_home
        elif predicted_outcome == 'draw' and p.odds_draw:
            predicted_odds = p.odds_draw
        elif predicted_outcome == 'away' and p.odds_away:
            predicted_odds = p.odds_away

        results.append({
            'fixture_id': p.fixture_id,
            'home_team': p.home_team,
            'away_team': p.away_team,
            'league': p.league,
            'league_id': p.league_id,
            'kickoff': p.kickoff,
            'predicted_outcome': p.predicted_outcome or '',
            'confidence': conf or 0,
            'expected_value': ev or 0,
            'probabilities': {
                'home': prob_home,
                'draw': prob_draw,
                'away': prob_away,
            },
            'odds_data': {
                'home': p.odds_home,
                'draw': p.odds_draw,
                'away': p.odds_away,
                predicted_outcome: predicted_odds,
            },
            'odds': predicted_odds or 0,
            'variance': p.variance,
            'consensus': p.consensus,
            'model_count': p.model_count or 0,
            'market_type': getattr(p, 'market_type', '1x2') or '1x2',
            'is_recommended': p.is_recommended,
            'actual_outcome': p.actual_outcome,
            'was_correct': p.was_correct,
            'profit_loss_10': p.profit_loss_10,
            'home_team_form': p.home_team_form,
            'away_team_form': p.away_team_form,
        })

    return results


def load_predictions_from_csv(filepath: str) -> List[Dict]:
    """Load predictions from CSV export."""
    results = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            def safe_float(val, default=0):
                try:
                    return float(val) if val else default
                except (ValueError, TypeError):
                    return default

            conf = safe_float(row.get('confidence'), 0)
            if conf > 1:
                conf = conf / 100

            ev = safe_float(row.get('expected_value'), 0)
            if abs(ev) > 1:
                ev = ev / 100

            prob_home = safe_float(row.get('probability_home'), 0)
            prob_draw = safe_float(row.get('probability_draw'), 0)
            prob_away = safe_float(row.get('probability_away'), 0)
            if prob_home > 1:
                prob_home, prob_draw, prob_away = prob_home / 100, prob_draw / 100, prob_away / 100

            predicted_outcome = (row.get('predicted_outcome') or '').lower()
            odds_home = safe_float(row.get('odds_home'))
            odds_draw = safe_float(row.get('odds_draw'))
            odds_away = safe_float(row.get('odds_away'))

            predicted_odds = 0
            if predicted_outcome == 'home':
                predicted_odds = odds_home
            elif predicted_outcome == 'draw':
                predicted_odds = odds_draw
            elif predicted_outcome == 'away':
                predicted_odds = odds_away

            was_correct_raw = row.get('was_correct', '')
            was_correct = was_correct_raw.lower() in ('true', '1', 'yes') if was_correct_raw else None

            results.append({
                'fixture_id': row.get('fixture_id', ''),
                'home_team': row.get('home_team', ''),
                'away_team': row.get('away_team', ''),
                'league': row.get('league', ''),
                'kickoff': row.get('kickoff', ''),
                'predicted_outcome': row.get('predicted_outcome', ''),
                'confidence': conf,
                'expected_value': ev,
                'probabilities': {
                    'home': prob_home,
                    'draw': prob_draw,
                    'away': prob_away,
                },
                'odds_data': {
                    'home': odds_home,
                    'draw': odds_draw,
                    'away': odds_away,
                    predicted_outcome: predicted_odds,
                },
                'odds': predicted_odds,
                'variance': safe_float(row.get('variance')),
                'consensus': safe_float(row.get('consensus')),
                'model_count': int(safe_float(row.get('model_count'))),
                'market_type': row.get('market_type', '1x2') or '1x2',
                'is_recommended': row.get('is_recommended', '').lower() in ('true', '1', 'yes'),
                'actual_outcome': row.get('actual_outcome', ''),
                'was_correct': was_correct,
                'profit_loss_10': safe_float(row.get('profit_loss_10')),
                'home_team_form': row.get('home_team_form', ''),
                'away_team_form': row.get('away_team_form', ''),
            })

    return results


def generate_simulated_data(n: int = 200) -> List[Dict]:
    """
    Generate simulated prediction data for testing when DB is unavailable.
    Mimics real-world distributions based on known system characteristics.
    """
    import random
    random.seed(42)

    leagues = [
        ('Premier League', 0.62), ('La Liga', 0.60), ('Serie A', 0.58),
        ('Bundesliga', 0.61), ('Ligue 1', 0.55), ('Eredivisie', 0.50),
        ('Admiral Bundesliga', 0.35), ('Liga Portugal', 0.38),
        ('Super Lig', 0.33), ('Championship', 0.48),
        ('FA Cup', 0.45), ('Super League', 0.40),
    ]
    markets = ['1x2', 'btts', 'over_under_2.5', 'double_chance']
    outcomes_1x2 = ['Home', 'Draw', 'Away']

    predictions = []
    for i in range(n):
        league, base_acc = random.choice(leagues)
        market = random.choice(markets)
        predicted_outcome = random.choice(outcomes_1x2) if market == '1x2' else random.choice(['Over 2.5', 'Under 2.5'])

        confidence = random.gauss(0.58, 0.12)
        confidence = max(0.30, min(0.85, confidence))

        ev = random.gauss(0.08, 0.10)

        # Accuracy correlated with confidence and league
        actual_acc = base_acc * (confidence / 0.55) * random.gauss(1.0, 0.1)
        was_correct = random.random() < min(actual_acc, 0.90)

        odds = random.uniform(1.3, 4.5)
        prob_home = random.uniform(0.25, 0.60)
        prob_away = random.uniform(0.15, 0.45)
        prob_draw = max(0.05, 1.0 - prob_home - prob_away)

        pl = (odds - 1) * 10 if was_correct else -10

        predictions.append({
            'fixture_id': 10000 + i,
            'home_team': f'Team {i*2}',
            'away_team': f'Team {i*2+1}',
            'league': league,
            'kickoff': (datetime(2026, 1, 1) + timedelta(days=i % 90)).isoformat(),
            'predicted_outcome': predicted_outcome,
            'confidence': confidence,
            'expected_value': ev,
            'probabilities': {
                'home': prob_home,
                'draw': prob_draw,
                'away': prob_away,
            },
            'odds_data': {
                'home': odds if predicted_outcome.lower() == 'home' else odds * 1.5,
                'draw': odds * 1.2,
                'away': odds if predicted_outcome.lower() == 'away' else odds * 1.3,
                predicted_outcome.lower(): odds,
            },
            'odds': odds,
            'variance': random.uniform(0, 25),
            'consensus': random.uniform(0.50, 0.95),
            'model_count': 3,
            'market_type': market,
            'is_recommended': confidence >= 0.55 and ev > 0.05,
            'actual_outcome': predicted_outcome if was_correct else random.choice(outcomes_1x2),
            'was_correct': was_correct,
            'profit_loss_10': pl,
            'home_team_form': random.choice(['W,W,D,L,W', 'L,D,W,W,L', 'W,W,W,D,W', None]),
            'away_team_form': random.choice(['L,L,D,W,L', 'W,D,L,L,W', 'D,D,W,L,D', None]),
        })

    return predictions


# =============================================================================
# V1 Simulation (mirrors current PredictionEnhancer logic)
# =============================================================================

def simulate_v1_filter(prediction: Dict) -> Tuple[bool, str]:
    """Simulate current V1 filtering logic (strict mode)."""
    confidence = prediction.get('confidence', 0)
    ev = prediction.get('expected_value', 0) or 0
    predicted_outcome = (prediction.get('predicted_outcome', '')).lower()
    predicted_odds = prediction.get('odds', 0)

    LEAGUE_BLACKLIST = ['Admiral Bundesliga', 'Liga Portugal', 'Super Lig']
    league = prediction.get('league', '')

    # Hard floors
    if confidence < 0.35:
        return False, 'Confidence < 35%'
    if predicted_odds > 2.50:
        return False, 'Odds > 2.50'

    # Track 1: Safe (>60% confidence)
    if confidence >= 0.60:
        if predicted_odds < 1.30:
            return False, 'Odds too low (<1.30)'
        return True, 'Safe Bet'

    # Track 2: Value (>10% EV, confidence > 35%)
    if ev >= 0.10:
        if predicted_odds > 4.50:
            return False, 'Odds too extreme'
        return True, 'Value Bet'

    return False, 'Below thresholds'


def simulate_v1_quality_score(prediction: Dict) -> float:
    """Simulate V1 quality score calculation."""
    score = 0.0
    confidence = prediction.get('confidence', 0)
    ev = prediction.get('expected_value', 0) or 0
    predicted_outcome = (prediction.get('predicted_outcome', '')).lower()
    predicted_odds = prediction.get('odds', 0)
    league = prediction.get('league', '')

    LEAGUE_BLACKLIST = ['Admiral Bundesliga', 'Liga Portugal', 'Super Lig']
    LEAGUE_WATCHLIST = ['Eredivisie', 'Pro League']

    # Confidence (0-40)
    if confidence >= 0.70:
        score += 40
    elif confidence >= 0.65:
        score += 30
    elif confidence >= 0.60:
        score += 20
    elif confidence >= 0.55:
        score += 10

    # EV (0-25)
    if ev >= 0.25:
        score += 25
    elif ev >= 0.20:
        score += 20
    elif ev >= 0.15:
        score += 15
    elif ev >= 0.10:
        score += 10
    elif ev >= 0.05:
        score += 5

    # Odds range (0-15)
    if 1.6 <= predicted_odds <= 2.5:
        score += 15
    elif 1.4 <= predicted_odds <= 3.0:
        score += 10
    elif predicted_odds > 3.5:
        score -= 10

    # Probability gap (0-15)
    probs = prediction.get('probabilities', {})
    vals = [probs.get('home', 0), probs.get('draw', 0), probs.get('away', 0)]
    vals = [v / 100 if v > 1 else v for v in vals]
    sorted_probs = sorted(vals, reverse=True)
    if len(sorted_probs) >= 2:
        gap = sorted_probs[0] - sorted_probs[1]
        if gap >= 0.40:
            score += 15
        elif gap >= 0.25:
            score += 12
        elif gap >= 0.20:
            score += 5

    # Variance
    variance = prediction.get('variance', 0) or 0
    if variance and variance < 0.1:
        score += 10
    elif variance and variance < 0.2:
        score += 5

    # Outcome penalty
    if 'under' in predicted_outcome:
        score -= 10
    elif 'over' in predicted_outcome:
        score += 5

    # League penalty
    if league in LEAGUE_BLACKLIST:
        score -= 15
    elif league in LEAGUE_WATCHLIST:
        score -= 5

    return min(score, 100.0)


# =============================================================================
# V2 Simulation (uses PredictionEnhancerV2)
# =============================================================================

def get_v2_enhancer():
    """Get V2 enhancer instance."""
    try:
        from core.services.prediction_enhancer_v2 import PredictionEnhancerV2
        return PredictionEnhancerV2()
    except ImportError:
        # Inline V2 logic for standalone use
        return None


def simulate_v2_filter(prediction: Dict, enhancer=None) -> Tuple[bool, str, str]:
    """Simulate V2 filtering logic."""
    if enhancer:
        return enhancer.should_recommend(prediction)

    # Fallback: inline V2 logic
    confidence = prediction.get('confidence', 0)
    ev = prediction.get('expected_value', 0) or 0
    predicted_odds = prediction.get('odds', 0)
    league = prediction.get('league', '')

    BLACKLIST = ['Admiral Bundesliga', 'Liga Portugal', 'Super Lig']

    if confidence < 0.35:
        return False, 'Confidence < 35%', 'none'
    if predicted_odds > 4.50:
        return False, 'Odds > 4.50', 'none'
    if predicted_odds < 1.25 and predicted_odds > 0:
        return False, 'Odds < 1.25', 'none'
    if league in BLACKLIST:
        return False, f'Blacklisted: {league}', 'none'

    # Premium
    if confidence >= 0.68 and ev >= 0.10:
        return True, 'Premium pick', 'premium'
    # Safe
    if confidence >= 0.58:
        if predicted_odds >= 1.35:
            return True, 'Safe pick', 'safe'
    # Value
    if ev >= 0.05 and confidence >= 0.42:
        return True, 'Value bet', 'value'

    return False, 'Below thresholds', 'none'


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def analyze_accuracy(predictions: List[Dict], label: str) -> Dict:
    """Calculate comprehensive accuracy metrics for a set of predictions."""
    if not predictions:
        return {'label': label, 'total': 0}

    total = len(predictions)
    correct = sum(1 for p in predictions if p.get('was_correct'))
    incorrect = total - correct
    accuracy = correct / total * 100 if total > 0 else 0

    # ROI
    total_pl = sum(p.get('profit_loss_10', 0) or 0 for p in predictions)
    roi = (total_pl / (total * 10)) * 100 if total > 0 else 0

    # By league
    by_league = defaultdict(lambda: {'total': 0, 'correct': 0, 'pl': 0})
    for p in predictions:
        league = p.get('league', 'Unknown')
        by_league[league]['total'] += 1
        if p.get('was_correct'):
            by_league[league]['correct'] += 1
        by_league[league]['pl'] += p.get('profit_loss_10', 0) or 0

    # By confidence band
    by_confidence = defaultdict(lambda: {'total': 0, 'correct': 0})
    for p in predictions:
        conf = p.get('confidence', 0)
        if conf >= 0.70:
            band = '70%+'
        elif conf >= 0.65:
            band = '65-70%'
        elif conf >= 0.60:
            band = '60-65%'
        elif conf >= 0.55:
            band = '55-60%'
        elif conf >= 0.50:
            band = '50-55%'
        else:
            band = '<50%'
        by_confidence[band]['total'] += 1
        if p.get('was_correct'):
            by_confidence[band]['correct'] += 1

    # By market type
    by_market = defaultdict(lambda: {'total': 0, 'correct': 0, 'pl': 0})
    for p in predictions:
        market = p.get('market_type', '1x2')
        by_market[market]['total'] += 1
        if p.get('was_correct'):
            by_market[market]['correct'] += 1
        by_market[market]['pl'] += p.get('profit_loss_10', 0) or 0

    # By outcome type
    by_outcome = defaultdict(lambda: {'total': 0, 'correct': 0})
    for p in predictions:
        outcome = (p.get('predicted_outcome', '') or '').lower()
        by_outcome[outcome]['total'] += 1
        if p.get('was_correct'):
            by_outcome[outcome]['correct'] += 1

    return {
        'label': label,
        'total': total,
        'correct': correct,
        'incorrect': incorrect,
        'accuracy': round(accuracy, 2),
        'total_pl': round(total_pl, 2),
        'roi': round(roi, 2),
        'avg_confidence': round(
            sum(p.get('confidence', 0) for p in predictions) / total * 100, 1
        ),
        'avg_ev': round(
            sum((p.get('expected_value', 0) or 0) for p in predictions) / total * 100, 1
        ),
        'avg_odds': round(
            sum(p.get('odds', 0) or 0 for p in predictions) / total, 2
        ),
        'by_league': {
            k: {
                'total': v['total'],
                'correct': v['correct'],
                'accuracy': round(v['correct'] / v['total'] * 100, 1) if v['total'] > 0 else 0,
                'pl': round(v['pl'], 2),
            }
            for k, v in sorted(by_league.items(), key=lambda x: x[1]['total'], reverse=True)
        },
        'by_confidence': {
            k: {
                'total': v['total'],
                'correct': v['correct'],
                'accuracy': round(v['correct'] / v['total'] * 100, 1) if v['total'] > 0 else 0,
            }
            for k, v in sorted(by_confidence.items())
        },
        'by_market': {
            k: {
                'total': v['total'],
                'correct': v['correct'],
                'accuracy': round(v['correct'] / v['total'] * 100, 1) if v['total'] > 0 else 0,
                'pl': round(v['pl'], 2),
            }
            for k, v in sorted(by_market.items(), key=lambda x: x[1]['total'], reverse=True)
        },
        'by_outcome': {
            k: {
                'total': v['total'],
                'correct': v['correct'],
                'accuracy': round(v['correct'] / v['total'] * 100, 1) if v['total'] > 0 else 0,
            }
            for k, v in sorted(by_outcome.items(), key=lambda x: x[1]['total'], reverse=True)
        },
    }


def run_comparison(predictions: List[Dict]) -> Dict:
    """Run V1 vs V2 comparison."""
    v2_enhancer = get_v2_enhancer()

    v1_accepted = []
    v2_accepted = []
    v1_only = []
    v2_only = []
    both = []
    neither = []

    for p in predictions:
        if p.get('was_correct') is None:
            continue

        v1_pass, v1_reason = simulate_v1_filter(p)
        v2_pass, v2_reason, v2_type = simulate_v2_filter(p, v2_enhancer)

        p_copy = dict(p)
        p_copy['v1_pass'] = v1_pass
        p_copy['v1_reason'] = v1_reason
        p_copy['v2_pass'] = v2_pass
        p_copy['v2_reason'] = v2_reason
        p_copy['v2_type'] = v2_type

        if v1_pass:
            v1_accepted.append(p_copy)
        if v2_pass:
            v2_accepted.append(p_copy)

        if v1_pass and v2_pass:
            both.append(p_copy)
        elif v1_pass and not v2_pass:
            v1_only.append(p_copy)
        elif v2_pass and not v1_pass:
            v2_only.append(p_copy)
        else:
            neither.append(p_copy)

    return {
        'total_predictions': len([p for p in predictions if p.get('was_correct') is not None]),
        'v1_analysis': analyze_accuracy(v1_accepted, 'V1 (Current)'),
        'v2_analysis': analyze_accuracy(v2_accepted, 'V2 (Proposed)'),
        'overlap_analysis': {
            'both_accept': len(both),
            'v1_only': len(v1_only),
            'v2_only': len(v2_only),
            'neither': len(neither),
        },
        'v1_only_accuracy': analyze_accuracy(v1_only, 'V1 Only'),
        'v2_only_accuracy': analyze_accuracy(v2_only, 'V2 Only'),
        'both_accuracy': analyze_accuracy(both, 'Both V1+V2'),
    }


# =============================================================================
# REPORTING
# =============================================================================

def print_section(title: str, width: int = 80):
    print(f"\n{'='*width}")
    print(f"  {title}")
    print(f"{'='*width}")


def print_analysis(analysis: Dict):
    """Pretty-print an analysis result."""
    print(f"\n  --- {analysis['label']} ---")
    if analysis['total'] == 0:
        print("  No predictions in this group.")
        return

    print(f"  Total: {analysis['total']}  |  Correct: {analysis['correct']}  |  "
          f"Accuracy: {analysis['accuracy']:.1f}%")
    print(f"  ROI: {analysis['roi']:+.1f}%  |  Total P/L: ${analysis['total_pl']:+.2f}")
    print(f"  Avg Confidence: {analysis['avg_confidence']:.1f}%  |  "
          f"Avg EV: {analysis['avg_ev']:.1f}%  |  Avg Odds: {analysis['avg_odds']:.2f}")

    if analysis.get('by_league'):
        print(f"\n  By League:")
        print(f"  {'League':<30} {'Total':>6} {'Correct':>8} {'Accuracy':>10} {'P/L':>10}")
        print(f"  {'-'*66}")
        for league, data in list(analysis['by_league'].items())[:15]:
            print(f"  {league:<30} {data['total']:>6} {data['correct']:>8} "
                  f"{data['accuracy']:>9.1f}% ${data['pl']:>+8.2f}")

    if analysis.get('by_confidence'):
        print(f"\n  By Confidence Band:")
        print(f"  {'Band':<12} {'Total':>6} {'Correct':>8} {'Accuracy':>10}")
        print(f"  {'-'*38}")
        for band, data in analysis['by_confidence'].items():
            print(f"  {band:<12} {data['total']:>6} {data['correct']:>8} "
                  f"{data['accuracy']:>9.1f}%")

    if analysis.get('by_market'):
        print(f"\n  By Market Type:")
        print(f"  {'Market':<20} {'Total':>6} {'Correct':>8} {'Accuracy':>10} {'P/L':>10}")
        print(f"  {'-'*56}")
        for market, data in analysis['by_market'].items():
            print(f"  {market:<20} {data['total']:>6} {data['correct']:>8} "
                  f"{data['accuracy']:>9.1f}% ${data['pl']:>+8.2f}")

    if analysis.get('by_outcome'):
        print(f"\n  By Predicted Outcome:")
        print(f"  {'Outcome':<15} {'Total':>6} {'Correct':>8} {'Accuracy':>10}")
        print(f"  {'-'*41}")
        for outcome, data in analysis['by_outcome'].items():
            print(f"  {outcome:<15} {data['total']:>6} {data['correct']:>8} "
                  f"{data['accuracy']:>9.1f}%")


def generate_report(comparison: Dict, output_path: str = None) -> str:
    """Generate the full comparison report."""
    lines = []

    def add(text=''):
        lines.append(text)
        print(text)

    add("=" * 80)
    add("  PREDICTION PERFORMANCE: V1 vs V2 COMPARISON REPORT")
    add(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    add("=" * 80)

    add(f"\n  Total predictions analyzed: {comparison['total_predictions']}")

    # V1 Summary
    v1 = comparison['v1_analysis']
    v2 = comparison['v2_analysis']

    add(f"\n  {'Metric':<25} {'V1 (Current)':>15} {'V2 (Proposed)':>15} {'Delta':>10}")
    add(f"  {'-'*67}")

    if v1['total'] > 0 and v2['total'] > 0:
        add(f"  {'Accepted predictions':<25} {v1['total']:>15} {v2['total']:>15} {v2['total']-v1['total']:>+10}")
        add(f"  {'Accuracy':<25} {v1['accuracy']:>14.1f}% {v2['accuracy']:>14.1f}% {v2['accuracy']-v1['accuracy']:>+9.1f}%")
        add(f"  {'ROI':<25} {v1['roi']:>+14.1f}% {v2['roi']:>+14.1f}% {v2['roi']-v1['roi']:>+9.1f}%")
        add(f"  {'Total P/L ($10 stakes)':<25} ${v1['total_pl']:>+13.2f} ${v2['total_pl']:>+13.2f} ${v2['total_pl']-v1['total_pl']:>+8.2f}")
        add(f"  {'Avg Confidence':<25} {v1['avg_confidence']:>14.1f}% {v2['avg_confidence']:>14.1f}%")
        add(f"  {'Avg EV':<25} {v1['avg_ev']:>14.1f}% {v2['avg_ev']:>14.1f}%")
        add(f"  {'Avg Odds':<25} {v1['avg_odds']:>15.2f} {v2['avg_odds']:>15.2f}")
    else:
        add("  Insufficient data for comparison.")

    # Overlap analysis
    overlap = comparison['overlap_analysis']
    add(f"\n  Filter Overlap:")
    add(f"  Both V1 & V2 accept: {overlap['both_accept']}")
    add(f"  V1 only accepts:     {overlap['v1_only']}")
    add(f"  V2 only accepts:     {overlap['v2_only']}")
    add(f"  Neither accepts:     {overlap['neither']}")

    # Detailed breakdowns
    print_section("V1 DETAILED ANALYSIS")
    print_analysis(v1)

    print_section("V2 DETAILED ANALYSIS")
    print_analysis(v2)

    # V2-only picks analysis (the new picks V2 would add)
    v2_only = comparison['v2_only_accuracy']
    if v2_only['total'] > 0:
        print_section("V2-ONLY PICKS (New picks V2 adds)")
        print_analysis(v2_only)

    # V1-only picks analysis (picks V2 would drop)
    v1_only = comparison['v1_only_accuracy']
    if v1_only['total'] > 0:
        print_section("V1-ONLY PICKS (Picks V2 would drop)")
        print_analysis(v1_only)

    # Key findings
    print_section("KEY FINDINGS & RECOMMENDATIONS")
    add("")

    if v1['total'] > 0 and v2['total'] > 0:
        acc_delta = v2['accuracy'] - v1['accuracy']
        roi_delta = v2['roi'] - v1['roi']
        volume_delta = v2['total'] - v1['total']

        if acc_delta > 0:
            add(f"  1. ACCURACY: V2 improves accuracy by {acc_delta:+.1f}%")
        else:
            add(f"  1. ACCURACY: V2 changes accuracy by {acc_delta:+.1f}%")

        if roi_delta > 0:
            add(f"  2. ROI: V2 improves ROI by {roi_delta:+.1f}%")
        else:
            add(f"  2. ROI: V2 changes ROI by {roi_delta:+.1f}%")

        if volume_delta > 0:
            add(f"  3. VOLUME: V2 accepts {volume_delta} more predictions (wider net)")
        elif volume_delta < 0:
            add(f"  3. VOLUME: V2 accepts {abs(volume_delta)} fewer predictions (more selective)")
        else:
            add(f"  3. VOLUME: Same number of predictions")

        # League-specific insights
        add(f"\n  4. LEAGUE INSIGHTS:")
        for league in ['Premier League', 'La Liga', 'Serie A', 'Bundesliga']:
            v1_league = v1.get('by_league', {}).get(league, {})
            v2_league = v2.get('by_league', {}).get(league, {})
            if v1_league.get('total', 0) > 0 and v2_league.get('total', 0) > 0:
                add(f"     {league}: V1={v1_league['accuracy']:.1f}% -> V2={v2_league['accuracy']:.1f}%")

    add("")
    add("=" * 80)

    report_text = '\n'.join(lines)

    if output_path:
        with open(output_path, 'w') as f:
            f.write(report_text)
        print(f"\n  Report saved to: {output_path}")

    return report_text


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='Prediction Performance Analysis')
    parser.add_argument('--simulated', action='store_true',
                       help='Use simulated data (no database needed)')
    parser.add_argument('--csv', type=str, default=None,
                       help='Path to CSV file with prediction data')
    parser.add_argument('--output', type=str, default=None,
                       help='Output file path for the report')
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("  BETGLITCH PREDICTION ANALYSIS TOOL")
    print("=" * 80)

    # Load predictions
    predictions = []

    if args.csv:
        print(f"\n  Loading predictions from CSV: {args.csv}")
        predictions = load_predictions_from_csv(args.csv)
    elif args.simulated:
        print("\n  Generating simulated prediction data...")
        predictions = generate_simulated_data(200)
    elif DJANGO_AVAILABLE:
        print("\n  Loading predictions from database...")
        try:
            predictions = load_predictions_from_db()
        except Exception as e:
            print(f"  Database error: {e}")
            print("  Falling back to simulated data...")
            predictions = generate_simulated_data(200)
    else:
        # Try CSV export
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'analysis_export.csv'
        )
        if os.path.exists(csv_path):
            print(f"\n  Loading from CSV export: {csv_path}")
            predictions = load_predictions_from_csv(csv_path)
        else:
            print("\n  No database or CSV available. Using simulated data.")
            predictions = generate_simulated_data(200)

    print(f"  Loaded {len(predictions)} predictions")

    completed = [p for p in predictions if p.get('was_correct') is not None]
    print(f"  Completed (with results): {len(completed)}")

    if len(completed) == 0:
        print("\n  ERROR: No completed predictions with results found.")
        print("  Run 'python manage.py update_results' first, or use --simulated flag.")
        return

    # Run comparison
    print("\n  Running V1 vs V2 comparison...")
    comparison = run_comparison(predictions)

    # Generate report
    output_path = args.output or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'prediction_analysis_results.json'
    )

    report = generate_report(comparison)

    # Save JSON results
    json_output = {
        'generated_at': datetime.now().isoformat(),
        'total_predictions': comparison['total_predictions'],
        'v1_summary': {
            'total': comparison['v1_analysis']['total'],
            'accuracy': comparison['v1_analysis']['accuracy'],
            'roi': comparison['v1_analysis']['roi'],
            'total_pl': comparison['v1_analysis']['total_pl'],
        },
        'v2_summary': {
            'total': comparison['v2_analysis']['total'],
            'accuracy': comparison['v2_analysis']['accuracy'],
            'roi': comparison['v2_analysis']['roi'],
            'total_pl': comparison['v2_analysis']['total_pl'],
        },
        'overlap': comparison['overlap_analysis'],
        'v1_detailed': comparison['v1_analysis'],
        'v2_detailed': comparison['v2_analysis'],
    }

    json_path = output_path if output_path.endswith('.json') else output_path + '.json'
    with open(json_path, 'w') as f:
        json.dump(json_output, f, indent=2, default=str)
    print(f"\n  JSON results saved to: {json_path}")


if __name__ == '__main__':
    main()
