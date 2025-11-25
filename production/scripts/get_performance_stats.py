"""
Get performance statistics from the prediction tracking database.
Can be used standalone or imported by Next.js API.

Usage:
  python get_performance_stats.py
  python get_performance_stats.py --json
  python get_performance_stats.py --league "Premier League"
"""

import os
import sys
import json
import django

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartbet.settings')
django.setup()

from django.db.models import Count, Avg, Sum, Q
from core.models import PredictionLog


def get_overall_stats():
    """Get overall performance statistics (filtered for confidence >= 60%)."""
    # Filter for confidence >= 0.60 (Medium and High confidence)
    base_query = PredictionLog.objects.filter(
        actual_outcome__isnull=False,
        confidence__gte=0.60
    )
    
    total = base_query.count()
    
    if total == 0:
        return {
            'total_predictions': 0,
            'correct_predictions': 0,
            'accuracy_percent': 0.0,
            'total_profit_loss': 0.0,
            'roi_percent': 0.0,
            'average_confidence': 0.0
        }
    
    correct = base_query.filter(was_correct=True).count()
    accuracy = (correct / total) * 100 if total > 0 else 0
    
    # Financial metrics
    total_pl = base_query.filter(
        profit_loss_10__isnull=False
    ).aggregate(Sum('profit_loss_10'))['profit_loss_10__sum'] or 0
    
    roi = (total_pl / (total * 10)) * 100 if total > 0 else 0
    
    # Average confidence
    avg_confidence = base_query.aggregate(Avg('confidence'))['confidence__avg'] or 0
    
    return {
        'total_predictions': total,
        'correct_predictions': correct,
        'accuracy_percent': round(accuracy, 2),
        'total_profit_loss': round(total_pl, 2),
        'roi_percent': round(roi, 2),
        'average_confidence': round(avg_confidence, 2)
    }


def get_by_outcome_stats():
    """Get stats broken down by predicted outcome."""
    stats = {}
    
    for outcome in ['Home', 'Draw', 'Away']:
        predictions = PredictionLog.objects.filter(
            predicted_outcome=outcome,
            actual_outcome__isnull=False
        )
        
        total = predictions.count()
        if total == 0:
            stats[outcome.lower()] = {
                'total': 0,
                'correct': 0,
                'accuracy_percent': 0.0
            }
            continue
        
        correct = predictions.filter(was_correct=True).count()
        accuracy = (correct / total) * 100
        
        stats[outcome.lower()] = {
            'total': total,
            'correct': correct,
            'accuracy_percent': round(accuracy, 2)
        }
    
    return stats


def get_by_confidence_level_stats():
    """Get stats by confidence level."""
    stats = {}
    
    levels = [
        ('high', 70, 100),
        ('medium', 60, 70),
        ('low', 0, 60)
    ]
    
    for level_name, min_conf, max_conf in levels:
        predictions = PredictionLog.objects.filter(
            confidence__gte=min_conf / 100.0,
            confidence__lt=max_conf / 100.0,
            actual_outcome__isnull=False
        )
        
        total = predictions.count()
        if total == 0:
            stats[level_name] = {
                'total': 0,
                'correct': 0,
                'accuracy_percent': 0.0,
                'roi_percent': 0.0
            }
            continue
        
        correct = predictions.filter(was_correct=True).count()
        accuracy = (correct / total) * 100
        
        total_pl = predictions.filter(
            profit_loss_10__isnull=False
        ).aggregate(Sum('profit_loss_10'))['profit_loss_10__sum'] or 0
        
        roi = (total_pl / (total * 10)) * 100 if total > 0 else 0
        
        stats[level_name] = {
            'total': total,
            'correct': correct,
            'accuracy_percent': round(accuracy, 2),
            'roi_percent': round(roi, 2)
        }
    
    return stats


def get_by_league_stats(limit=10):
    """Get stats by league (top performing leagues)."""
    leagues = PredictionLog.objects.filter(
        actual_outcome__isnull=False
    ).values('league').annotate(
        total=Count('id'),
        correct=Count('id', filter=Q(was_correct=True))
    ).order_by('-total')[:limit]
    
    stats = []
    for league in leagues:
        accuracy = (league['correct'] / league['total']) * 100 if league['total'] > 0 else 0
        stats.append({
            'league': league['league'],
            'total': league['total'],
            'correct': league['correct'],
            'accuracy_percent': round(accuracy, 2)
        })
    
    return stats


def get_recent_predictions(limit=10):
    """Get recent completed predictions."""
    predictions = PredictionLog.objects.filter(
        actual_outcome__isnull=False
    ).order_by('-kickoff')[:limit]
    
    recent = []
    for pred in predictions:
        recent.append({
            'fixture_id': pred.fixture_id,
            'home_team': pred.home_team,
            'away_team': pred.away_team,
            'league': pred.league,
            'kickoff': pred.kickoff.isoformat(),
            'predicted_outcome': pred.predicted_outcome,
            'actual_outcome': pred.actual_outcome,
            'confidence': pred.confidence,
            'was_correct': pred.was_correct,
            'profit_loss': pred.profit_loss_10,
            'score': f"{pred.actual_score_home}-{pred.actual_score_away}" if pred.actual_score_home is not None else None
        })
    
    return recent


def get_all_stats():
    """Get all performance statistics."""
    return {
        'overall': get_overall_stats(),
        'by_outcome': get_by_outcome_stats(),
        'by_confidence_level': get_by_confidence_level_stats(),
        'by_league': get_by_league_stats(),
        'recent_predictions': get_recent_predictions()
    }


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Get performance statistics')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--league', type=str, help='Filter by specific league')
    
    args = parser.parse_args()
    
    stats = get_all_stats()
    
    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        # Pretty print
        print("\n" + "="*60)
        print("SMARTBET PERFORMANCE STATISTICS")
        print("="*60 + "\n")
        
        overall = stats['overall']
        print(f"Overall Performance:")
        print(f"  Total Predictions: {overall['total_predictions']}")
        print(f"  Correct: {overall['correct_predictions']}")
        print(f"  Accuracy: {overall['accuracy_percent']}%")
        print(f"  Total P/L: ${overall['total_profit_loss']}")
        print(f"  ROI: {overall['roi_percent']}%")
        print(f"  Avg Confidence: {overall['average_confidence']}%\n")
        
        print(f"By Outcome:")
        for outcome, data in stats['by_outcome'].items():
            print(f"  {outcome.capitalize():6s}: {data['total']:3d} total | {data['correct']:3d} correct | {data['accuracy_percent']:5.1f}% accuracy")
        print()
        
        print(f"By Confidence Level:")
        for level, data in stats['by_confidence_level'].items():
            print(f"  {level.capitalize():6s}: {data['total']:3d} total | {data['correct']:3d} correct | {data['accuracy_percent']:5.1f}% accuracy | {data['roi_percent']:6.1f}% ROI")
        print()
        
        print(f"Top Leagues:")
        for league_data in stats['by_league']:
            print(f"  {league_data['league']:30s}: {league_data['accuracy_percent']:5.1f}% ({league_data['correct']}/{league_data['total']})")
        print()


if __name__ == '__main__':
    main()

