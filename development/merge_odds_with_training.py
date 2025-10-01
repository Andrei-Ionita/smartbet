#!/usr/bin/env python3
"""
Safe Odds and Training Dataset Merger

This script safely merges extracted odds data with the training dataset,
creating a new enhanced dataset while keeping all original files intact.
"""

import os
import pandas as pd
from datetime import datetime
import json

def find_latest_files():
    """Find the latest odds file and training dataset"""
    
    # Find latest odds file
    odds_files = [f for f in os.listdir('.') if f.startswith('sportmonks_extracted_odds_') and f.endswith('.csv')]
    training_files = [f for f in os.listdir('.') if f.startswith('premier_league_') and f.endswith('.csv')]
    
    if not odds_files:
        raise FileNotFoundError("❌ No extracted odds files found. Run sportmonks_odds_extractor.py first.")
    
    if not training_files:
        raise FileNotFoundError("❌ No training dataset files found.")
    
    latest_odds = sorted(odds_files)[-1]
    latest_training = sorted(training_files)[-1]
    
    return latest_odds, latest_training

def load_data(odds_file: str, training_file: str):
    """Load odds and training data"""
    print(f"📂 Loading odds data from: {odds_file}")
    odds_df = pd.read_csv(odds_file)
    print(f"✅ Loaded {len(odds_df)} odds entries")
    
    print(f"📂 Loading training data from: {training_file}")
    training_df = pd.read_csv(training_file)
    print(f"✅ Loaded {len(training_df)} training fixtures")
    
    return odds_df, training_df

def create_odds_features(odds_df: pd.DataFrame) -> pd.DataFrame:
    """Create structured odds features for each fixture"""
    print("🔧 Creating odds features...")
    
    features_list = []
    
    # Group odds by fixture
    for fixture_id in odds_df['fixture_id'].unique():
        fixture_odds = odds_df[odds_df['fixture_id'] == fixture_id]
        
        # Create base record
        feature_record = {
            'fixture_id': fixture_id,
            'has_odds': 1,
            'total_odds_entries': len(fixture_odds)
        }
        
        # Process each market
        for market_name in fixture_odds['market_name'].unique():
            market_odds = fixture_odds[fixture_odds['market_name'] == market_name]
            
            # Clean market name for column naming
            clean_market = market_name.lower().replace(" ", "_").replace("-", "_")
            
            # Select best bookmaker (prefer bet365, betfair, etc.)
            priority_bookies = ["bet365", "betfair", "coral", "betvictor", "888sport"]
            best_odds = None
            
            for bookie in priority_bookies:
                bookie_odds = market_odds[market_odds['bookmaker_name'].str.contains(bookie, case=False, na=False)]
                if not bookie_odds.empty:
                    best_odds = bookie_odds
                    break
            
            if best_odds is None:
                best_odds = market_odds.head(1)  # Take first available
            
            # Extract odds by label
            for _, odds_row in best_odds.iterrows():
                label = str(odds_row['label']).lower().strip()
                odds_value = odds_row['odds_value']
                
                if pd.isna(odds_value) or odds_value <= 0:
                    continue
                
                # Create feature name based on market and label
                if label in ['home', '1']:
                    feature_record[f'{clean_market}_home_odds'] = odds_value
                elif label in ['draw', 'x']:
                    feature_record[f'{clean_market}_draw_odds'] = odds_value
                elif label in ['away', '2']:
                    feature_record[f'{clean_market}_away_odds'] = odds_value
                elif label in ['over']:
                    feature_record[f'{clean_market}_over_odds'] = odds_value
                elif label in ['under']:
                    feature_record[f'{clean_market}_under_odds'] = odds_value
                elif label in ['yes']:
                    feature_record[f'{clean_market}_yes_odds'] = odds_value
                elif label in ['no']:
                    feature_record[f'{clean_market}_no_odds'] = odds_value
                elif '1x' in label:
                    feature_record[f'{clean_market}_1x_odds'] = odds_value
                elif 'x2' in label:
                    feature_record[f'{clean_market}_x2_odds'] = odds_value
                elif '12' in label:
                    feature_record[f'{clean_market}_12_odds'] = odds_value
                else:
                    # Generic label handling
                    safe_label = label.replace(' ', '_').replace('-', '_')
                    feature_record[f'{clean_market}_{safe_label}_odds'] = odds_value
                
                # Add bookmaker info
                feature_record[f'{clean_market}_bookmaker'] = odds_row['bookmaker_name']
                
                # Add handicap/total info if available
                if pd.notna(odds_row.get('handicap')):
                    feature_record[f'{clean_market}_handicap'] = odds_row['handicap']
                if pd.notna(odds_row.get('total')):
                    feature_record[f'{clean_market}_total'] = odds_row['total']
        
        features_list.append(feature_record)
    
    features_df = pd.DataFrame(features_list)
    
    print(f"✅ Created odds features for {len(features_df)} fixtures")
    print(f"📊 Generated {len(features_df.columns)-1} odds feature columns")
    
    return features_df

def merge_datasets(training_df: pd.DataFrame, features_df: pd.DataFrame) -> pd.DataFrame:
    """Merge training dataset with odds features"""
    print("🔄 Merging training dataset with odds features...")
    
    # Start with training dataset
    enhanced_df = training_df.copy()
    
    # Add has_odds flag for all fixtures
    enhanced_df['has_odds'] = 0
    
    # Merge odds features
    enhanced_df = enhanced_df.merge(features_df, on='fixture_id', how='left', suffixes=('', '_odds'))
    
    # Update has_odds flag
    enhanced_df['has_odds'] = enhanced_df['has_odds_odds'].fillna(0)
    enhanced_df.drop('has_odds_odds', axis=1, inplace=True, errors='ignore')
    
    # Fill NaN values in odds columns with appropriate defaults
    odds_columns = [col for col in enhanced_df.columns if '_odds' in col or col in ['total_odds_entries']]
    for col in odds_columns:
        if 'odds' in col:
            enhanced_df[col] = enhanced_df[col].fillna(0)  # 0 for missing odds
        else:
            enhanced_df[col] = enhanced_df[col].fillna(0)  # 0 for counts
    
    print(f"✅ Merged datasets successfully")
    print(f"📊 Enhanced dataset shape: {enhanced_df.shape}")
    print(f"🎯 Fixtures with odds: {enhanced_df['has_odds'].sum()}/{len(enhanced_df)}")
    print(f"📈 Coverage: {enhanced_df['has_odds'].sum()/len(enhanced_df)*100:.1f}%")
    
    return enhanced_df

def save_enhanced_dataset(enhanced_df: pd.DataFrame, original_training_file: str, odds_file: str):
    """Save the enhanced dataset"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create descriptive filename
    enhanced_filename = f"enhanced_training_with_odds_{timestamp}.csv"
    
    # Save enhanced dataset
    enhanced_df.to_csv(enhanced_filename, index=False)
    print(f"💾 Enhanced dataset saved to: {enhanced_filename}")
    
    # Create merge summary
    summary = {
        "merge_date": timestamp,
        "original_training_file": original_training_file,
        "odds_file": odds_file,
        "enhanced_file": enhanced_filename,
        "original_fixtures": len(enhanced_df),
        "fixtures_with_odds": int(enhanced_df['has_odds'].sum()),
        "coverage_percentage": float(enhanced_df['has_odds'].sum() / len(enhanced_df) * 100),
        "original_columns": "Unknown",  # Would need to track this
        "enhanced_columns": len(enhanced_df.columns),
        "new_odds_columns": len([col for col in enhanced_df.columns if '_odds' in col or col in ['has_odds', 'total_odds_entries']])
    }
    
    summary_file = f"merge_summary_{timestamp}.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"📊 Merge summary saved to: {summary_file}")
    
    return enhanced_filename

def display_sample_features(enhanced_df: pd.DataFrame):
    """Display sample of new odds features"""
    print("\n📋 Sample of new odds features:")
    
    # Find fixtures with odds
    fixtures_with_odds = enhanced_df[enhanced_df['has_odds'] == 1]
    
    if len(fixtures_with_odds) > 0:
        sample_fixture = fixtures_with_odds.iloc[0]
        
        print(f"\nSample fixture: {sample_fixture['home_team']} vs {sample_fixture['away_team']}")
        
        # Show odds columns
        odds_cols = [col for col in enhanced_df.columns if '_odds' in col]
        for col in sorted(odds_cols):
            value = sample_fixture[col]
            if pd.notna(value) and value != 0:
                print(f"  {col}: {value}")
    else:
        print("❌ No fixtures with odds found in the enhanced dataset")

def main():
    """Main merger function"""
    print("🔄 Safe Odds and Training Dataset Merger")
    print("=" * 50)
    print("This script merges extracted odds with your training dataset")
    print("All original files remain unchanged")
    print("=" * 50)
    
    try:
        # Find latest files
        odds_file, training_file = find_latest_files()
        print(f"📂 Found odds file: {odds_file}")
        print(f"📂 Found training file: {training_file}")
        
        # Confirm with user
        proceed = input(f"\n🔄 Proceed with merging these files? (y/n): ").lower().strip()
        if proceed != 'y':
            print("❌ Merge cancelled")
            return
        
        # Load data
        odds_df, training_df = load_data(odds_file, training_file)
        
        # Create odds features
        features_df = create_odds_features(odds_df)
        
        # Merge datasets
        enhanced_df = merge_datasets(training_df, features_df)
        
        # Save enhanced dataset
        enhanced_filename = save_enhanced_dataset(enhanced_df, training_file, odds_file)
        
        # Display sample
        display_sample_features(enhanced_df)
        
        print(f"\n✅ Merge completed successfully!")
        print(f"💾 Enhanced dataset: {enhanced_filename}")
        print(f"📊 Total fixtures: {len(enhanced_df)}")
        print(f"🎯 Fixtures with odds: {enhanced_df['has_odds'].sum()}")
        print(f"📈 Odds coverage: {enhanced_df['has_odds'].sum()/len(enhanced_df)*100:.1f}%")
        print(f"🆕 Total columns: {len(enhanced_df.columns)}")
        
    except Exception as e:
        print(f"❌ Error during merge: {e}")
        print("💡 Make sure you have run sportmonks_odds_extractor.py first")

if __name__ == "__main__":
    main()