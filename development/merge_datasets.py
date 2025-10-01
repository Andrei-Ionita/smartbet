#!/usr/bin/env python3
"""
Dataset Merger - Combines original training data with odds data
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime

def find_latest_odds_file():
    """Find the most recent odds dataset file"""
    odds_files = [f for f in os.listdir('.') if f.startswith('enhanced_training_data_') and f.endswith('.csv')]
    
    if not odds_files:
        return None
    
    odds_files.sort(reverse=True)
    return odds_files[0]

def merge_datasets():
    """Main merging function"""
    print("🎯 Dataset Merger for Enhanced Training Data")
    print("=" * 50)
    
    # File paths
    original_file = "premier_league_complete_4_seasons_20250624_175954.csv"
    odds_file = find_latest_odds_file()
    
    if not odds_file:
        print("❌ No odds dataset found.")
        print("💡 Run odds_integrator.py first to collect odds data.")
        return False
    
    print(f"📂 Original dataset: {original_file}")
    print(f"📂 Odds dataset: {odds_file}")
    
    try:
        # Load datasets
        print("\n📊 Loading datasets...")
        original_df = pd.read_csv(original_file)
        odds_df = pd.read_csv(odds_file)
        
        print(f"✅ Original: {len(original_df)} records, {len(original_df.columns)} features")
        print(f"✅ Odds: {len(odds_df)} records, {len(odds_df.columns)} features")
        
        # Identify odds features
        odds_features = [col for col in odds_df.columns 
                        if col not in ['fixture_id', 'date', 'home_team', 'away_team', 'outcome']]
        
        print(f"🎲 Odds features to merge: {len(odds_features)}")
        
        # Merge on fixture_id
        print("\n🔄 Merging datasets...")
        merged_df = original_df.merge(
            odds_df[['fixture_id'] + odds_features],
            on='fixture_id',
            how='left'
        )
        
        print(f"✅ Merged dataset: {len(merged_df)} records, {len(merged_df.columns)} features")
        
        # Calculate summary statistics
        has_odds_count = merged_df.get('has_odds', pd.Series([False]*len(merged_df))).sum()
        print(f"📊 Records with odds: {has_odds_count}/{len(merged_df)} ({has_odds_count/len(merged_df)*100:.1f}%)")
        
        # Save merged dataset
        output_file = f"complete_training_dataset_with_odds_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        merged_df.to_csv(output_file, index=False)
        
        print(f"\n💾 Final dataset saved: {output_file}")
        print(f"📈 Shape: {merged_df.shape}")
        
        # Show sample
        print(f"\n📋 Sample of merged dataset:")
        sample_cols = ['home_team', 'away_team', 'outcome']
        
        # Add odds columns if available
        odds_cols = [col for col in merged_df.columns if 'odds' in col.lower()][:3]
        sample_cols.extend(odds_cols)
        
        available_cols = [col for col in sample_cols if col in merged_df.columns]
        print(merged_df[available_cols].head())
        
        print(f"\n🎉 Dataset merging completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during merging: {e}")
        return False

if __name__ == "__main__":
    success = merge_datasets()
    if not success:
        exit(1) 