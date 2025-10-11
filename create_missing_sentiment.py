#!/usr/bin/env python
"""
Script to create missing sentiment data for all frontend fixture IDs
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.join(os.path.dirname(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartbet.settings')
django.setup()

from core.models import MatchSentiment
from core.management.commands.analyze_sentiment import Command

# All frontend fixture IDs
frontend_fixtures = [
    {'fixture_id': 19431855, 'home_team': 'Birmingham City', 'away_team': 'Hull City', 'league': 'Championship'},
    {'fixture_id': 19427539, 'home_team': 'Brentford', 'away_team': 'Liverpool', 'league': 'Premier League'},
    {'fixture_id': 19429269, 'home_team': 'Excelsior', 'away_team': 'Fortuna Sittard', 'league': 'Eredivisie'},
    {'fixture_id': 19427542, 'home_team': 'Leeds United', 'away_team': 'West Ham United', 'league': 'Premier League'},
    {'fixture_id': 19347900, 'home_team': 'Norrköping', 'away_team': 'Malmö FF', 'league': 'Allsvenskan'},
    {'fixture_id': 19434301, 'home_team': 'Blau-Weiß Linz', 'away_team': 'Sturm Graz', 'league': 'Austrian Bundesliga'},
]

command = Command()

for fixture in frontend_fixtures:
    if not MatchSentiment.objects.filter(fixture_id=fixture['fixture_id']).exists():
        print(f"Creating sentiment data for {fixture['home_team']} vs {fixture['away_team']}")
        
        # Create realistic prediction probabilities
        prediction_probs = {'home': 0.45, 'draw': 0.30, 'away': 0.25}
        
        # Generate fallback sentiment data
        sentiment_data, trap_analysis = command._create_fallback_sentiment_data(
            fixture['home_team'], 
            fixture['away_team'], 
            fixture['league'], 
            prediction_probs
        )
        
        # Create the database record
        MatchSentiment.objects.create(
            fixture_id=fixture['fixture_id'],
            home_team=fixture['home_team'],
            away_team=fixture['away_team'],
            league=fixture['league'],
            match_date=django.utils.timezone.now() + django.utils.timezone.timedelta(hours=24),
            home_mentions_count=sentiment_data.home_mentions_count,
            away_mentions_count=sentiment_data.away_mentions_count,
            home_sentiment_score=sentiment_data.home_sentiment_score,
            away_sentiment_score=sentiment_data.away_sentiment_score,
            public_attention_ratio=sentiment_data.public_attention_ratio,
            trap_score=trap_analysis.trap_score,
            trap_level=trap_analysis.trap_level,
            alert_message=trap_analysis.alert_message,
            recommendation=trap_analysis.recommendation,
            confidence_divergence=trap_analysis.confidence_divergence,
            data_sources=sentiment_data.data_sources,
            top_keywords=sentiment_data.top_keywords,
            total_mentions=sentiment_data.total_mentions
        )
        
        print(f"SUCCESS: Created {fixture['home_team']} vs {fixture['away_team']} - Trap: {trap_analysis.trap_level} ({trap_analysis.trap_score}/10)")
    else:
        print(f"SKIP: {fixture['home_team']} vs {fixture['away_team']} - already exists")

print(f"\nTotal sentiment records in database: {MatchSentiment.objects.count()}")
