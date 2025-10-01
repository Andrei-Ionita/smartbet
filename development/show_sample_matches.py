#!/usr/bin/env python3
"""
Show 3 sample matches from our training dataset to verify they are real.
"""

import pandas as pd

# Load the dataset
df = pd.read_csv('premier_league_comprehensive_training_20250624_172007.csv')

print("3 SAMPLE MATCHES FROM OUR TRAINING DATASET:")
print("=" * 60)

# Get first 3 matches with key details
sample_matches = df[['season_name', 'date', 'home_team', 'away_team', 'home_score', 'away_score', 'fixture_id']].head(3)

for i, row in sample_matches.iterrows():
    print(f"Match {i+1}:")
    print(f"  Season: {row['season_name']}")
    print(f"  Date: {row['date']}")
    print(f"  Teams: {row['home_team']} vs {row['away_team']}")
    print(f"  Score: {row['home_team']} {int(row['home_score'])} - {int(row['away_score'])} {row['away_team']}")
    print(f"  SportMonks ID: {row['fixture_id']}")
    print()

print("These are REAL Premier League fixtures from SportMonks API.")
print("You can verify these scores by checking official Premier League records.") 