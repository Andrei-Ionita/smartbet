
import os
import sys
import django
from django.db.models import Count, Avg, Sum, Case, When, IntegerField, F
from django.db.models.functions import Round

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartbet.settings")
django.setup()

from core.models import PredictionLog

def analyze_strategy():
    print("\n🔍 ANALYZING PREDICTION STRATEGY PERFORMANCE\n")
    
    total_logs = PredictionLog.objects.count()
    settled_logs = PredictionLog.objects.filter(match_status='FT').count()
    
    print(f"Total Logs: {total_logs}")
    print(f"Settled Logs: {settled_logs}")
    
    if settled_logs == 0:
        print("No settled matches to analyze.")
        return

    # 1. Performance by Confidence Interval
    print("\n📊 Performance by Confidence Interval:")
    print("-" * 65)
    print(f"{'Range':<15} | {'Count':<8} | {'Accuracy':<10} | {'ROI':<10} | {'Profit':<10}")
    print("-" * 65)
    
    individuals = [(0.50, 0.60), (0.60, 0.70), (0.70, 0.80), (0.80, 1.00)]
    
    for low, high in individuals:
        matches = PredictionLog.objects.filter(
            match_status='FT',
            confidence__gte=low,
            confidence__lt=high
        )
        count = matches.count()
        if count > 0:
            correct = matches.filter(was_correct=True).count()
            accuracy = (correct / count) * 100
            roi = matches.aggregate(Avg('roi_percent'))['roi_percent__avg'] or 0
            profit = matches.aggregate(Sum('profit_loss_10'))['profit_loss_10__sum'] or 0
            
            print(f"{low*100:.0f}-{high*100:.0f}%{'':<9} | {count:<8} | {accuracy:.1f}%{'':<5} | {roi:.1f}%{'':<5} | ${profit:.2f}")
    
    # 2. Performance by Market Type
    print("\n📈 Performance by Market Type:")
    print("-" * 65)
    print(f"{'Market':<20} | {'Count':<8} | {'Accuracy':<10} | {'ROI':<10}")
    print("-" * 65)
    
    # Group by market_type (handling nulls as '1x2' historically)
    markets = PredictionLog.objects.filter(match_status='FT').values('market_type').annotate(
        total=Count('id'),
        correct_count=Sum(Case(When(was_correct=True, then=1), default=0, output_field=IntegerField())),
        avg_roi=Avg('roi_percent')
    ).order_by('-total')
    
    for m in markets:
        m_type = m['market_type'] or '1x2 (Legacy)'
        acc = (m['correct_count'] / m['total']) * 100
        roi = m['avg_roi'] or 0
        print(f"{m_type:<20} | {m['total']:<8} | {acc:.1f}%{'':<5} | {roi:.1f}%")

    # 3. Performance by League (Top 5 worst performing)
    print("\n⚠️ Worst Performing Leagues (by Accuracy):")
    print("-" * 65)
    leagues = PredictionLog.objects.filter(match_status='FT').values('league').annotate(
        total=Count('id'),
        correct_count=Sum(Case(When(was_correct=True, then=1), default=0, output_field=IntegerField())),
        avg_roi=Avg('roi_percent')
    ).filter(total__gte=3).order_by('avg_roi')[:5]  # Minimum 3 matches to be significant
    
    for l in leagues:
        acc = (l['correct_count'] / l['total']) * 100
        roi = l['avg_roi'] or 0
        print(f"{l['league']:<25} | {l['total']} bets | Acc: {acc:.1f}% | ROI: {roi:.1f}%")

if __name__ == '__main__':
    analyze_strategy()
