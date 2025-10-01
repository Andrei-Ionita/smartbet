#!/usr/bin/env python3
"""
Dataset Merger for Training Enhancement
Merges original training dataset with collected odds data to create comprehensive dataset
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os

class DatasetMerger:
    def __init__(self):
        """Initialize the dataset merger"""
        self.original_features = []
        self.odds_features = []
        self.merged_features = []
        
    def load_original_dataset(self, filepath):
        """Load the original training dataset"""
        print(f"📂 Loading original training dataset: {filepath}")
        
        try:
            df = pd.read_csv(filepath)
            df['date'] = pd.to_datetime(df['date'])
            
            print(f"✅ Loaded original dataset: {len(df)} records")
            print(f"📊 Features: {len(df.columns)} columns")
            print(f"📅 Date range: {df['date'].min()} to {df['date'].max()}")
            
            self.original_features = df.columns.tolist()
            return df
            
        except Exception as e:
            print(f"❌ Failed to load original dataset: {e}")
            raise
    
    def load_odds_dataset(self, filepath):
        """Load the odds-enhanced dataset"""
        print(f"📂 Loading odds dataset: {filepath}")
        
        try:
            df = pd.read_csv(filepath)
            df['date'] = pd.to_datetime(df['date'])
            
            print(f"✅ Loaded odds dataset: {len(df)} records")
            print(f"📊 Features: {len(df.columns)} columns")
            
            # Identify odds-specific features
            odds_cols = [col for col in df.columns if any(keyword in col.lower() 
                        for keyword in ['odds', 'pinnacle', 'bet365', 'betfair', 'has_odds'])]
            
            print(f"🎲 Odds features identified: {len(odds_cols)}")
            self.odds_features = odds_cols
            
            return df
            
        except Exception as e:
            print(f"❌ Failed to load odds dataset: {e}")
            raise
    
    def merge_datasets(self, original_df, odds_df):
        """Merge original dataset with odds data"""
        print("🔄 Merging datasets...")
        
        # Merge on fixture_id to maintain all original records
        merged_df = original_df.merge(
            odds_df[['fixture_id'] + self.odds_features], 
            on='fixture_id', 
            how='left'
        )
        
        print(f"✅ Merge completed: {len(merged_df)} records")
        
        # Fill missing odds data with appropriate defaults
        odds_columns = [col for col in merged_df.columns if 'odds' in col.lower()]
        
        for col in odds_columns:
            if merged_df[col].dtype in ['float64', 'int64']:
                merged_df[col] = merged_df[col].fillna(0)  # Fill numeric odds with 0
        
        # Fill has_odds column
        if 'has_odds' in merged_df.columns:
            merged_df['has_odds'] = merged_df['has_odds'].fillna(False)
        
        return merged_df
    
    def calculate_enhanced_features(self, df):
        """Calculate additional features from odds data"""
        print("🧮 Calculating enhanced features...")
        
        enhanced_df = df.copy()
        
        # Calculate implied probabilities from best available odds
        home_odds_cols = [col for col in df.columns if 'home' in col and 'odds' in col]
        draw_odds_cols = [col for col in df.columns if 'draw' in col and 'odds' in col]
        away_odds_cols = [col for col in df.columns if 'away' in col and 'odds' in col]
        
        if home_odds_cols:
            # Best home odds (highest value)
            enhanced_df['best_home_odds'] = df[home_odds_cols].max(axis=1)
            enhanced_df['avg_home_odds'] = df[home_odds_cols].replace(0, np.nan).mean(axis=1)
            enhanced_df['implied_prob_home'] = 1 / enhanced_df['avg_home_odds'].replace(0, np.inf)
        
        if draw_odds_cols:
            enhanced_df['best_draw_odds'] = df[draw_odds_cols].max(axis=1)
            enhanced_df['avg_draw_odds'] = df[draw_odds_cols].replace(0, np.nan).mean(axis=1)
            enhanced_df['implied_prob_draw'] = 1 / enhanced_df['avg_draw_odds'].replace(0, np.inf)
        
        if away_odds_cols:
            enhanced_df['best_away_odds'] = df[away_odds_cols].max(axis=1)
            enhanced_df['avg_away_odds'] = df[away_odds_cols].replace(0, np.nan).mean(axis=1)
            enhanced_df['implied_prob_away'] = 1 / enhanced_df['avg_away_odds'].replace(0, np.inf)
        
        # Calculate market efficiency metrics
        if all(col in enhanced_df.columns for col in ['implied_prob_home', 'implied_prob_draw', 'implied_prob_away']):
            enhanced_df['total_implied_prob'] = (
                enhanced_df['implied_prob_home'].fillna(0) + 
                enhanced_df['implied_prob_draw'].fillna(0) + 
                enhanced_df['implied_prob_away'].fillna(0)
            )
            enhanced_df['market_margin'] = enhanced_df['total_implied_prob'] - 1.0
            enhanced_df['market_efficiency'] = 1 / enhanced_df['total_implied_prob'].replace(0, np.inf)
        
        # Over/Under features
        over25_cols = [col for col in df.columns if 'over25' in col or 'over_2_5' in col]
        under25_cols = [col for col in df.columns if 'under25' in col or 'under_2_5' in col]
        
        if over25_cols:
            enhanced_df['avg_over25_odds'] = df[over25_cols].replace(0, np.nan).mean(axis=1)
            enhanced_df['implied_prob_over25'] = 1 / enhanced_df['avg_over25_odds'].replace(0, np.inf)
        
        if under25_cols:
            enhanced_df['avg_under25_odds'] = df[under25_cols].replace(0, np.nan).mean(axis=1)
            enhanced_df['implied_prob_under25'] = 1 / enhanced_df['avg_under25_odds'].replace(0, np.inf)
        
        # BTTS features
        btts_yes_cols = [col for col in df.columns if 'btts' in col and 'yes' in col]
        btts_no_cols = [col for col in df.columns if 'btts' in col and 'no' in col]
        
        if btts_yes_cols:
            enhanced_df['avg_btts_yes_odds'] = df[btts_yes_cols].replace(0, np.nan).mean(axis=1)
            enhanced_df['implied_prob_btts_yes'] = 1 / enhanced_df['avg_btts_yes_odds'].replace(0, np.inf)
        
        # Clean up infinite and NaN values
        enhanced_df = enhanced_df.replace([np.inf, -np.inf], np.nan)
        enhanced_df = enhanced_df.fillna(0)
        
        print(f"✅ Enhanced features calculated")
        
        return enhanced_df
    
    def analyze_dataset_quality(self, df):
        """Analyze the quality of the merged dataset"""
        print("\n📊 Dataset Quality Analysis")
        print("=" * 40)
        
        total_records = len(df)
        print(f"📋 Total records: {total_records}")
        
        # Odds availability
        if 'has_odds' in df.columns:
            odds_available = df['has_odds'].sum()
            odds_percentage = (odds_available / total_records) * 100
            print(f"🎲 Records with odds: {odds_available} ({odds_percentage:.1f}%)")
        
        # Feature completeness
        odds_columns = [col for col in df.columns if 'odds' in col.lower()]
        print(f"📈 Odds features: {len(odds_columns)}")
        
        # Check for missing values in key features
        key_features = ['home_team', 'away_team', 'outcome', 'date']
        missing_data = {}
        
        for feature in key_features:
            if feature in df.columns:
                missing_count = df[feature].isnull().sum()
                missing_data[feature] = missing_count
        
        if any(missing_data.values()):
            print("⚠️ Missing data found:")
            for feature, count in missing_data.items():
                if count > 0:
                    print(f"   {feature}: {count} missing")
        else:
            print("✅ No missing data in key features")
        
        # Outcome distribution
        if 'outcome' in df.columns:
            outcome_counts = df['outcome'].value_counts()
            print(f"\n🎯 Outcome distribution:")
            for outcome, count in outcome_counts.items():
                percentage = (count / total_records) * 100
                print(f"   {outcome}: {count} ({percentage:.1f}%)")
        
        return {
            'total_records': total_records,
            'odds_availability': odds_available if 'has_odds' in df.columns else 0,
            'odds_features': len(odds_columns),
            'missing_data': missing_data
        }
    
    def save_final_dataset(self, df, output_path):
        """Save the final enhanced dataset"""
        df.to_csv(output_path, index=False)
        print(f"💾 Final dataset saved to: {output_path}")
        print(f"📊 Final dataset shape: {df.shape}")
        
        # Show sample of final dataset
        print(f"\n📋 Sample of final enhanced dataset:")
        display_columns = ['home_team', 'away_team', 'outcome']
        
        # Add some odds columns if available
        odds_cols = [col for col in df.columns if 'odds' in col.lower()][:3]
        display_columns.extend(odds_cols)
        
        # Add enhanced features if available
        enhanced_cols = [col for col in df.columns if 'implied_prob' in col][:2]
        display_columns.extend(enhanced_cols)
        
        available_cols = [col for col in display_columns if col in df.columns]
        print(df[available_cols].head())

def main():
    """Main execution function"""
    print("🎯 Dataset Merger for Training Enhancement")
    print("=" * 50)
    
    # Configuration
    ORIGINAL_DATASET = "premier_league_complete_4_seasons_20250624_175954.csv"
    ODDS_DATASET = None  # Will need to be specified after odds collection
    OUTPUT_DATASET = f"final_enhanced_training_dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    try:
        merger = DatasetMerger()
        
        # Check if we have an odds dataset to merge
        odds_files = [f for f in os.listdir('.') if f.startswith('enhanced_training_data_') and f.endswith('.csv')]
        
        if not odds_files:
            print("❌ No odds dataset found.")
            print("💡 Please run the odds_integrator.py script first to collect odds data.")
            return False
        
        # Use the most recent odds dataset
        odds_files.sort(reverse=True)
        ODDS_DATASET = odds_files[0]
        print(f"📁 Using odds dataset: {ODDS_DATASET}")
        
        # Load datasets
        original_df = merger.load_original_dataset(ORIGINAL_DATASET)
        odds_df = merger.load_odds_dataset(ODDS_DATASET)
        
        # Merge datasets
        merged_df = merger.merge_datasets(original_df, odds_df)
        
        # Calculate enhanced features
        enhanced_df = merger.calculate_enhanced_features(merged_df)
        
        # Analyze quality
        quality_stats = merger.analyze_dataset_quality(enhanced_df)
        
        # Save final dataset
        merger.save_final_dataset(enhanced_df, OUTPUT_DATASET)
        
        print(f"\n🎉 Dataset merging completed successfully!")
        print(f"📊 Final enhanced dataset: {enhanced_df.shape[0]} records, {enhanced_df.shape[1]} features")
        print(f"💾 Saved to: {OUTPUT_DATASET}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in dataset merging: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1) 