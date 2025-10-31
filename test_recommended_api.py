#!/usr/bin/env python
"""Quick test script to verify recommended predictions API"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartbet.settings')
django.setup()

from django.test import Client
import json

client = Client()
response = client.get('/api/recommended-predictions/?include_pending=true')

print(f"Status: {response.status_code}")
data = json.loads(response.content)
print(f"Success: {data.get('success')}")
print(f"Count: {data.get('count')}")
print(f"Summary: {data.get('summary', {})}")

if data.get('data'):
    print(f"\nFirst 3 predictions:")
    for i, pred in enumerate(data['data'][:3], 1):
        print(f"  {i}. {pred['home_team']} vs {pred['away_team']}")
        print(f"     Predicted: {pred['predicted_outcome']}, Confidence: {pred['confidence']}%")
        print(f"     Actual: {pred.get('actual_outcome', 'Pending')}")
        print(f"     Correct: {pred.get('was_correct', 'N/A')}")

