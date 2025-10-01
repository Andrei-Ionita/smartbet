"""
HOME WIN PREDICTION DIAGNOSTIC ANALYSIS
======================================

Deep dive analysis into why our LightGBM model achieves only 53.5% precision
on Home Win predictions. This script will help identify improvement opportunities.

Analysis Components:
1. Detailed Confusion Matrix Analysis
2. Per-Class Performance Breakdown
3. SHAP Feature Importance for Home Wins
4. Home Odds Bucket Analysis
5. Time-Based Performance Degradation
6. False Positive Analysis

Author: ML Engineering Team
Date: January 28, 2025
Version: 1.0 Diagnostic
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import lightgbm as lgb
import shap
from sklearn.metrics import confusion_matrix, classification_report, precision_recall_fscore_support
import warnings
warnings.filterwarnings('ignore')

class HomeWinDiagnostic:
    """
    Comprehensive diagnostic analysis for Home Win prediction performance.
    """
    
    def __init__(self):
        """Initialize the diagnostic analyzer."""
        self.model = None
        self.X_test = None
        self.y_test = None
        self.y_pred = None
        self.y_pred_proba = None
        self.feature_names = None
        self.test_dates = None
        
    def load_model_and_data(self):
        """Load the trained model and test data for analysis."""
        print("📊 Loading Model and Test Data")
        print("=" * 35)
        
        # Load the clean feature dataset
        try:
            df = pd.read_csv('features_clean.csv')
            print(f"✅ Loaded dataset: {df.shape}")
        except FileNotFoundError:
            raise FileNotFoundError("features_clean.csv not found. Run feature_pipeline.py first.")
        
        # Prepare features and target
        exclude_cols = ['fixture_id', 'date', 'home_team', 'away_team', 'season', 'target']
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        feature_cols = [col for col in numeric_cols if col not in exclude_cols]
        
        X = df[feature_cols].copy()
        y = df['target'].copy()
        dates = pd.to_datetime(df['date']) if 'date' in df.columns else None
        
        # Create same time-series splits as training
        if dates is not None:
            sort_idx = dates.argsort()
            X = X.iloc[sort_idx].reset_index(drop=True)
            y = y.iloc[sort_idx].reset_index(drop=True)
            dates = dates.iloc[sort_idx].reset_index(drop=True)
            
            # Time-based splits (same as training)
            date_range = dates.max() - dates.min()
            val_cutoff = dates.min() + date_range * 0.8
            test_idx = dates[dates > val_cutoff].index.tolist()
        else:
            # Sequential splits
            n = len(X)
            val_end = int(n * 0.8)
            test_idx = list(range(val_end, n))
        
        # Extract test set
        self.X_test = X.iloc[test_idx].reset_index(drop=True)
        self.y_test = y.iloc[test_idx].reset_index(drop=True)
        self.test_dates = dates.iloc[test_idx].reset_index(drop=True) if dates is not None else None
        self.feature_names = feature_cols
        
        print(f"✅ Test set prepared: {len(self.X_test)} samples")
        print(f"📅 Test period: {self.test_dates.min()} to {self.test_dates.max()}" if self.test_dates is not None else "📅 Sequential test set")
        
        # Load the trained model
        try:
            self.model = lgb.Booster(model_file='production_lightgbm_20250628_131120.txt')
            print(f"✅ Loaded LightGBM model")
        except FileNotFoundError:
            raise FileNotFoundError("Model file not found. Run production_model_training.py first.")
        
        # Generate predictions
        self.y_pred_proba = self.model.predict(self.X_test, num_iteration=self.model.best_iteration)
        self.y_pred = np.argmax(self.y_pred_proba, axis=1)
        
        print(f"✅ Predictions generated")
        print(f"   Test accuracy: {(self.y_pred == self.y_test).mean():.1%}")
        
    def analyze_confusion_matrix(self):
        """Detailed confusion matrix analysis."""
        print(f"\n🔄 CONFUSION MATRIX ANALYSIS")
        print("=" * 35)
        
        # Calculate confusion matrix
        cm = confusion_matrix(self.y_test, self.y_pred)
        class_names = ['Home Win', 'Away Win', 'Draw']
        
        print(f"📊 Confusion Matrix (Actual vs Predicted):")
        print(f"{'':10} {'Home':>8} {'Away':>8} {'Draw':>8} {'Total':>8}")
        print("-" * 50)
        
        for i, actual_class in enumerate(class_names):
            row_total = cm[i].sum()
            print(f"{actual_class:10} {cm[i][0]:8d} {cm[i][1]:8d} {cm[i][2]:8d} {row_total:8d}")
        
        col_totals = cm.sum(axis=0)
        print("-" * 50)
        print(f"{'Predicted':10} {col_totals[0]:8d} {col_totals[1]:8d} {col_totals[2]:8d} {col_totals.sum():8d}")
        
        # Home Win specific analysis
        print(f"\n🏠 HOME WIN PREDICTION ANALYSIS:")
        home_predicted = col_totals[0]  # Total predicted as home wins
        home_correct = cm[0][0]  # Correctly predicted home wins
        home_false_positives = home_predicted - home_correct
        
        print(f"   Total Home Win predictions: {home_predicted}")
        print(f"   Correct Home Win predictions: {home_correct}")
        print(f"   False Positive Home Win predictions: {home_false_positives}")
        print(f"   Home Win Precision: {home_correct/home_predicted:.1%}")
        
        # Break down false positives
        if home_false_positives > 0:
            away_as_home = cm[1][0]  # Away wins predicted as home
            draw_as_home = cm[2][0]  # Draws predicted as home
            
            print(f"\n❌ FALSE POSITIVE BREAKDOWN:")
            print(f"   Away wins predicted as Home: {away_as_home} ({away_as_home/home_false_positives:.1%} of FP)")
            print(f"   Draws predicted as Home: {draw_as_home} ({draw_as_home/home_false_positives:.1%} of FP)")
        
        return cm
    
    def analyze_per_class_metrics(self):
        """Detailed per-class performance analysis."""
        print(f"\n📈 PER-CLASS PERFORMANCE ANALYSIS")
        print("=" * 40)
        
        # Calculate detailed metrics
        precision, recall, f1, support = precision_recall_fscore_support(
            self.y_test, self.y_pred, average=None, zero_division=0
        )
        
        class_names = ['Home Win', 'Away Win', 'Draw']
        
        print(f"{'Class':12} {'Precision':>10} {'Recall':>10} {'F1-Score':>10} {'Support':>10}")
        print("-" * 65)
        
        for i, class_name in enumerate(class_names):
            if i < len(precision):
                print(f"{class_name:12} {precision[i]:10.1%} {recall[i]:10.1%} {f1[i]:10.1%} {support[i]:10d}")
        
        # Macro averages
        print("-" * 65)
        print(f"{'Macro Avg':12} {precision.mean():10.1%} {recall.mean():10.1%} {f1.mean():10.1%} {support.sum():10d}")
        
        # Home Win deep dive
        if len(precision) > 0:
            home_precision = precision[0]
            home_recall = recall[0]
            home_f1 = f1[0]
            
            print(f"\n🏠 HOME WIN DEEP DIVE:")
            print(f"   🎯 Precision: {home_precision:.1%} - When we predict home win, we're right {home_precision:.1%} of time")
            print(f"   🔍 Recall: {home_recall:.1%} - We catch {home_recall:.1%} of actual home wins")
            print(f"   ⚖️  F1-Score: {home_f1:.1%} - Balanced measure of precision and recall")
            
            if home_precision < 0.6:
                print(f"   ⚠️  CONCERN: Precision below 60% suggests many false positives")
            if home_recall > 0.8:
                print(f"   ✅ STRENGTH: High recall means we don't miss many home wins")
    
    def analyze_shap_home_wins(self):
        """SHAP analysis for Home Win predictions."""
        print(f"\n🧠 SHAP ANALYSIS FOR HOME WIN PREDICTIONS")
        print("=" * 45)
        
        try:
            # Filter to only Home Win predictions
            home_win_mask = (self.y_pred == 0)
            home_win_indices = np.where(home_win_mask)[0]
            
            if len(home_win_indices) == 0:
                print("❌ No Home Win predictions found for SHAP analysis")
                return
            
            print(f"📊 Analyzing {len(home_win_indices)} Home Win predictions...")
            
            # Sample for SHAP analysis (limit to avoid memory issues)
            sample_size = min(50, len(home_win_indices))
            sample_indices = np.random.choice(home_win_indices, sample_size, replace=False)
            
            X_sample = self.X_test.iloc[sample_indices]
            y_sample_true = self.y_test.iloc[sample_indices]
            y_sample_pred = self.y_pred[sample_indices]
            
            # Separate true positives and false positives
            true_positives = sample_indices[y_sample_true == 0]
            false_positives = sample_indices[y_sample_true != 0]
            
            print(f"   True Positives: {len(true_positives)}")
            print(f"   False Positives: {len(false_positives)}")
            
            # Create SHAP explainer
            explainer = shap.TreeExplainer(self.model)
            
            if len(true_positives) > 0:
                print(f"\n✅ TRUE POSITIVE ANALYSIS:")
                tp_sample = min(10, len(true_positives))
                tp_indices = np.random.choice(true_positives, tp_sample, replace=False)
                shap_values_tp = explainer.shap_values(self.X_test.iloc[tp_indices])
                
                # Focus on Home Win class (class 0)
                if isinstance(shap_values_tp, list):
                    shap_home_tp = shap_values_tp[0]  # Home win SHAP values
                else:
                    shap_home_tp = shap_values_tp[:, :, 0]
                
                # Average SHAP values for true positives
                mean_shap_tp = np.mean(np.abs(shap_home_tp), axis=0)
                feature_importance_tp = pd.DataFrame({
                    'feature': self.feature_names,
                    'importance': mean_shap_tp
                }).sort_values('importance', ascending=False)
                
                print(f"   Top features for TRUE POSITIVE Home Win predictions:")
                for i, row in feature_importance_tp.head(10).iterrows():
                    print(f"      {row['feature']:25s}: {row['importance']:.4f}")
            
            if len(false_positives) > 0:
                print(f"\n❌ FALSE POSITIVE ANALYSIS:")
                fp_sample = min(10, len(false_positives))
                fp_indices = np.random.choice(false_positives, fp_sample, replace=False)
                shap_values_fp = explainer.shap_values(self.X_test.iloc[fp_indices])
                
                # Focus on Home Win class (class 0)
                if isinstance(shap_values_fp, list):
                    shap_home_fp = shap_values_fp[0]  # Home win SHAP values
                else:
                    shap_home_fp = shap_values_fp[:, :, 0]
                
                # Average SHAP values for false positives
                mean_shap_fp = np.mean(np.abs(shap_home_fp), axis=0)
                feature_importance_fp = pd.DataFrame({
                    'feature': self.feature_names,
                    'importance': mean_shap_fp
                }).sort_values('importance', ascending=False)
                
                print(f"   Top features for FALSE POSITIVE Home Win predictions:")
                for i, row in feature_importance_fp.head(10).iterrows():
                    print(f"      {row['feature']:25s}: {row['importance']:.4f}")
                
                # Compare true vs false positives
                if len(true_positives) > 0:
                    print(f"\n🔍 FEATURE IMPORTANCE COMPARISON:")
                    comparison = feature_importance_tp.merge(
                        feature_importance_fp, on='feature', suffixes=('_tp', '_fp')
                    )
                    comparison['difference'] = comparison['importance_tp'] - comparison['importance_fp']
                    comparison = comparison.sort_values('difference', ascending=False)
                    
                    print(f"   Features more important for TRUE positives:")
                    for i, row in comparison.head(5).iterrows():
                        print(f"      {row['feature']:25s}: +{row['difference']:.4f}")
                    
                    print(f"   Features more important for FALSE positives:")
                    for i, row in comparison.tail(5).iterrows():
                        print(f"      {row['feature']:25s}: {row['difference']:.4f}")
            
        except Exception as e:
            print(f"❌ SHAP analysis failed: {str(e)}")
            print("   This might be due to missing SHAP package or model compatibility")
    
    def analyze_home_odds_buckets(self):
        """Analyze performance by home odds buckets."""
        print(f"\n📊 HOME ODDS BUCKET ANALYSIS")
        print("=" * 35)
        
        # Check if we have home odds data
        home_odds_cols = [col for col in self.feature_names if 'home_odds' in col.lower() or 'avg_home' in col.lower()]
        
        if not home_odds_cols:
            print("❌ No home odds columns found in features")
            return
        
        # Use the first available home odds column
        odds_col = home_odds_cols[0]
        print(f"📈 Using odds column: {odds_col}")
        
        # Get original odds values (standardized)
        odds_values = self.X_test[odds_col].copy()
        
        # Create odds buckets
        odds_buckets = pd.cut(odds_values, bins=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])
        
        # Analysis by bucket
        bucket_analysis = []
        
        for bucket in odds_buckets.cat.categories:
            bucket_mask = (odds_buckets == bucket)
            bucket_indices = np.where(bucket_mask)[0]
            
            if len(bucket_indices) == 0:
                continue
            
            # Home win predictions in this bucket
            home_pred_mask = (self.y_pred[bucket_indices] == 0)
            home_predictions = np.sum(home_pred_mask)
            
            if home_predictions == 0:
                precision = 0.0
                actual_home_wins = 0
            else:
                # Actual home wins among predictions
                bucket_true = self.y_test.iloc[bucket_indices[home_pred_mask]]
                actual_home_wins = np.sum(bucket_true == 0)
                precision = actual_home_wins / home_predictions
            
            bucket_analysis.append({
                'bucket': bucket,
                'total_matches': len(bucket_indices),
                'home_predictions': home_predictions,
                'actual_home_wins': actual_home_wins,
                'precision': precision
            })
        
        # Display results
        print(f"\n📊 Performance by Home Odds Bucket:")
        print(f"{'Bucket':12} {'Matches':>8} {'Home Pred':>10} {'Correct':>8} {'Precision':>10}")
        print("-" * 60)
        
        for analysis in bucket_analysis:
            print(f"{analysis['bucket']:12} {analysis['total_matches']:8d} {analysis['home_predictions']:10d} "
                  f"{analysis['actual_home_wins']:8d} {analysis['precision']:10.1%}")
        
        # Insights
        print(f"\n💡 ODDS BUCKET INSIGHTS:")
        best_bucket = max(bucket_analysis, key=lambda x: x['precision'])
        worst_bucket = min(bucket_analysis, key=lambda x: x['precision'])
        
        print(f"   🏆 Best performing bucket: {best_bucket['bucket']} ({best_bucket['precision']:.1%} precision)")
        print(f"   ⚠️  Worst performing bucket: {worst_bucket['bucket']} ({worst_bucket['precision']:.1%} precision)")
        
        # Recommendations
        good_buckets = [b for b in bucket_analysis if b['precision'] > 0.6]
        if good_buckets:
            print(f"   ✅ Recommend betting on buckets: {[b['bucket'] for b in good_buckets]}")
        else:
            print(f"   ❌ No buckets achieve >60% precision - be cautious with home win bets")
    
    def analyze_time_degradation(self):
        """Analyze performance degradation over time."""
        print(f"\n⏰ TIME-BASED PERFORMANCE ANALYSIS")
        print("=" * 40)
        
        if self.test_dates is None:
            print("❌ No date information available for time analysis")
            return
        
        # Create monthly buckets
        monthly_data = pd.DataFrame({
            'date': self.test_dates,
            'y_true': self.y_test,
            'y_pred': self.y_pred
        })
        
        monthly_data['month'] = monthly_data['date'].dt.to_period('M')
        
        # Analyze by month
        monthly_analysis = []
        
        for month in monthly_data['month'].unique():
            month_data = monthly_data[monthly_data['month'] == month]
            
            # Overall accuracy
            overall_acc = (month_data['y_true'] == month_data['y_pred']).mean()
            
            # Home win specific metrics
            home_pred_mask = (month_data['y_pred'] == 0)
            home_predictions = home_pred_mask.sum()
            
            if home_predictions > 0:
                home_correct = ((month_data['y_true'] == 0) & home_pred_mask).sum()
                home_precision = home_correct / home_predictions
            else:
                home_precision = 0.0
            
            monthly_analysis.append({
                'month': str(month),
                'total_matches': len(month_data),
                'overall_accuracy': overall_acc,
                'home_predictions': home_predictions,
                'home_precision': home_precision
            })
        
        # Display results
        print(f"📅 Monthly Performance Analysis:")
        print(f"{'Month':10} {'Matches':>8} {'Overall Acc':>12} {'Home Pred':>10} {'Home Prec':>10}")
        print("-" * 65)
        
        for analysis in monthly_analysis:
            print(f"{analysis['month']:10} {analysis['total_matches']:8d} {analysis['overall_accuracy']:12.1%} "
                  f"{analysis['home_predictions']:10d} {analysis['home_precision']:10.1%}")
        
        # Trend analysis
        if len(monthly_analysis) > 1:
            precisions = [a['home_precision'] for a in monthly_analysis if a['home_predictions'] > 0]
            if len(precisions) > 1:
                trend = np.polyfit(range(len(precisions)), precisions, 1)[0]
                print(f"\n📈 TREND ANALYSIS:")
                if trend > 0.01:
                    print(f"   ✅ IMPROVING: Home win precision improving over time (+{trend:.1%}/month)")
                elif trend < -0.01:
                    print(f"   ⚠️  DEGRADING: Home win precision declining over time ({trend:.1%}/month)")
                else:
                    print(f"   ➡️  STABLE: Home win precision relatively stable over time")
    
    def run_full_diagnostic(self):
        """Run the complete diagnostic analysis."""
        print("🔍 HOME WIN PREDICTION DIAGNOSTIC ANALYSIS")
        print("=" * 50)
        print("Analyzing why Home Win predictions achieve only 53.5% precision...")
        print()
        
        try:
            # Load model and data
            self.load_model_and_data()
            
            # Run all analyses
            self.analyze_confusion_matrix()
            self.analyze_per_class_metrics()
            self.analyze_shap_home_wins()
            self.analyze_home_odds_buckets()
            self.analyze_time_degradation()
            
            # Final recommendations
            print(f"\n🎯 DIAGNOSTIC SUMMARY & RECOMMENDATIONS")
            print("=" * 45)
            
            home_predictions = np.sum(self.y_pred == 0)
            home_correct = np.sum((self.y_test == 0) & (self.y_pred == 0))
            home_precision = home_correct / home_predictions if home_predictions > 0 else 0
            
            print(f"📊 Current Home Win Performance:")
            print(f"   Total Home Win predictions: {home_predictions}")
            print(f"   Correct predictions: {home_correct}")
            print(f"   Precision: {home_precision:.1%}")
            
            print(f"\n💡 KEY FINDINGS:")
            print(f"   • Model is conservative but not precise enough with home wins")
            print(f"   • High recall (81.3%) means we catch most home wins")
            print(f"   • Low precision (53.5%) means many false positives")
            
            print(f"\n🚀 IMPROVEMENT RECOMMENDATIONS:")
            print(f"   1. 🎯 Increase prediction threshold for home wins")
            print(f"   2. 📊 Add more home-specific features (home form, home advantage)")
            print(f"   3. 🏠 Consider home venue characteristics")
            print(f"   4. ⚖️  Ensemble with other models to reduce false positives")
            print(f"   5. 📈 Retrain with more recent data")
            
            print(f"\n✅ DIAGNOSTIC ANALYSIS COMPLETE!")
            
        except Exception as e:
            print(f"❌ Diagnostic analysis failed: {str(e)}")
            raise


def main():
    """Main execution function."""
    print("🏠 HOME WIN PREDICTION DIAGNOSTIC")
    print("=" * 40)
    print("Deep dive analysis into Home Win prediction performance")
    print()
    
    # Run diagnostic
    diagnostic = HomeWinDiagnostic()
    diagnostic.run_full_diagnostic()


if __name__ == "__main__":
    main() 