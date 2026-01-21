"""
Debug script to check PredictionLog database state
Run with: python manage.py shell < scripts/debug_prediction_logs.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartbet.settings')
django.setup()

from django.utils import timezone
from datetime import datetime, timezone as dt_timezone
from core.models import PredictionLog

print("\n" + "="*60)
print("PREDICTION LOG DATABASE AUDIT")
print("="*60 + "\n")

# Total predictions
total = PredictionLog.objects.count()
print(f"📊 Total Predictions in Database: {total}")

# Recommended predictions
recommended = PredictionLog.objects.filter(is_recommended=True).count()
not_recommended = total - recommended
print(f"   ✅ Recommended (is_recommended=True): {recommended}")
print(f"   ❌ Not Recommended: {not_recommended}")

print("\n" + "-"*40 + "\n")

# Completed vs Pending
completed_recommended = PredictionLog.objects.filter(
    is_recommended=True,
    actual_outcome__isnull=False
).count()
pending_recommended = PredictionLog.objects.filter(
    is_recommended=True,
    actual_outcome__isnull=True
).count()

print(f"🎯 Recommended Predictions Status:")
print(f"   ✅ Completed (has result): {completed_recommended}")
print(f"   ⏳ Pending (no result): {pending_recommended}")

print("\n" + "-"*40 + "\n")

# V2 Filter Impact
V2_LAUNCH_DATE = datetime(2025, 12, 24, 0, 0, 0, tzinfo=dt_timezone.utc)
v2_recommended = PredictionLog.objects.filter(
    is_recommended=True,
    prediction_logged_at__gte=V2_LAUNCH_DATE
).count()
v1_recommended = PredictionLog.objects.filter(
    is_recommended=True,
    prediction_logged_at__lt=V2_LAUNCH_DATE
).count()

print(f"📅 Model Version Breakdown (based on V2 launch: {V2_LAUNCH_DATE.date()}):")
print(f"   V2 (after launch): {v2_recommended}")
print(f"   V1 (before launch): {v1_recommended}")

# V2 completed
v2_completed = PredictionLog.objects.filter(
    is_recommended=True,
    prediction_logged_at__gte=V2_LAUNCH_DATE,
    actual_outcome__isnull=False
).count()
print(f"   V2 Completed: {v2_completed}")

print("\n" + "-"*40 + "\n")

# Recent predictions (last 10)
print("📋 Last 10 Recommended Predictions:")
recent = PredictionLog.objects.filter(is_recommended=True).order_by('-prediction_logged_at')[:10]
for pred in recent:
    status = "✅" if pred.actual_outcome else "⏳"
    result = f"({pred.actual_outcome})" if pred.actual_outcome else "(pending)"
    print(f"   {status} {pred.fixture_id} | {pred.home_team} vs {pred.away_team} | Logged: {pred.prediction_logged_at.date()} | {result}")

print("\n" + "="*60)
print("END OF AUDIT")
print("="*60 + "\n")
