#!/usr/bin/env python3
"""
SERIE A 1X2 MODEL VALIDATION SUITE
==================================

Comprehensive validation of Serie A dataset and model before production deployment.
Checks data quality, model performance, and generates diagnostic reports.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import lightgbm as lgb
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score
from datetime import datetime
import warnings
import os
warnings.filterwarnings('ignore')

class SerieAModelValidator:
    """Comprehensive validation suite for Serie A 1X2 model."""
    
    def __init__(self):
        self.dataset_file = 'serie_a_complete_training_dataset_20250630_125108.csv'
        self.validation_file = 'validation_serie_a_20250630_125109.csv'
        self.feature_importance_file = 'feature_importance_serie_a_20250630_125109.csv'
        self.model_file = 'league_model_1x2_serie_a_20250630_125109.txt'
        
        self.validation_results = {}
        self.warnings = []
        self.recommendations = []
        
        print("🔍 Serie A 1X2 Model Validator initialized")
        print("=" * 50)
    
    def validate_dataset(self):
        """Part 1: Comprehensive dataset validation."""
        print("📊 PART 1: DATASET VALIDATION")
        print("-" * 30)
        
        # Load dataset
        try:
            df = pd.read_csv(self.dataset_file)
            print(f"✅ Dataset loaded: {len(df)} rows, {len(df.columns)} columns")
        except FileNotFoundError:
            print(f"❌ Dataset file not found: {self.dataset_file}")
            return None
        
        # 1. Column checks - detect post-match features
        print("\n1️⃣ COLUMN VALIDATION")
        print("-" * 20)
        
        post_match_indicators = [
            'goal_difference', 'total_goals', 'final_result', 'winner', 
            'full_time_result', 'match_result', 'outcome'
        ]
        
        problematic_columns = []
        for col in df.columns:
            if any(indicator in col.lower() for indicator in post_match_indicators):
                problematic_columns.append(col)
        
        if problematic_columns:
            print(f"⚠️ WARNING: Potential post-match features detected: {problematic_columns}")
            self.warnings.append(f"Post-match features found: {problematic_columns}")
        else:
            print("✅ No post-match leak features detected")
        
        # Expected columns validation
        required_cols = ['home_team', 'away_team', 'home_score', 'away_score', 'target']
        missing_required = [col for col in required_cols if col not in df.columns]
        
        if missing_required:
            print(f"❌ Missing required columns: {missing_required}")
        else:
            print("✅ All required columns present")
        
        # 2. Missing values analysis
        print("\n2️⃣ MISSING VALUES ANALYSIS")
        print("-" * 25)
        
        missing_analysis = df.isnull().sum()
        missing_pct = (missing_analysis / len(df) * 100).round(2)
        
        print("Missing values by column:")
        for col, count in missing_analysis.items():
            if count > 0:
                print(f"   {col}: {count} ({missing_pct[col]}%)")
        
        if missing_analysis.sum() == 0:
            print("✅ No missing values detected")
        else:
            high_missing = missing_pct[missing_pct > 5].index.tolist()
            if high_missing:
                print(f"⚠️ WARNING: High missing values in: {high_missing}")
                self.warnings.append(f"High missing values: {high_missing}")
        
        # 3. Duplicate fixtures check
        print("\n3️⃣ DUPLICATE FIXTURES CHECK")
        print("-" * 26)
        
        duplicate_cols = ['home_team', 'away_team', 'date']
        available_dup_cols = [col for col in duplicate_cols if col in df.columns]
        
        if len(available_dup_cols) >= 2:
            duplicates = df.duplicated(subset=available_dup_cols).sum()
            print(f"Duplicate fixtures: {duplicates}")
            
            if duplicates > 0:
                print(f"⚠️ WARNING: {duplicates} duplicate fixtures found")
                self.warnings.append(f"Duplicate fixtures: {duplicates}")
            else:
                print("✅ No duplicate fixtures")
        else:
            print("⚠️ Cannot check duplicates - missing required columns")
        
        # 4. Class balance analysis
        print("\n4️⃣ CLASS BALANCE ANALYSIS")
        print("-" * 23)
        
        if 'target' in df.columns:
            class_counts = df['target'].value_counts().sort_index()
            class_pct = (class_counts / len(df) * 100).round(1)
            
            target_names = {0: 'Home Win', 1: 'Away Win', 2: 'Draw'}
            
            print("Class distribution:")
            for target, count in class_counts.items():
                name = target_names.get(target, f'Class {target}')
                print(f"   {name}: {count} ({class_pct[target]}%)")
            
            # Check for severe class imbalance
            min_pct = class_pct.min()
            max_pct = class_pct.max()
            
            if min_pct < 20 or max_pct > 60:
                print(f"⚠️ WARNING: Class imbalance detected (min: {min_pct}%, max: {max_pct}%)")
                self.warnings.append(f"Class imbalance: {min_pct}%-{max_pct}%")
            else:
                print("✅ Reasonable class balance")
            
            self.validation_results['class_balance'] = class_pct.to_dict()
        else:
            print("❌ Target column not found")
        
        # 5. Outlier odds analysis
        print("\n5️⃣ OUTLIER ODDS ANALYSIS")
        print("-" * 22)
        
        odds_cols = ['avg_home_odds', 'avg_away_odds', 'avg_draw_odds']
        available_odds_cols = [col for col in odds_cols if col in df.columns]
        
        if available_odds_cols:
            outlier_summary = {}
            
            for col in available_odds_cols:
                low_odds = (df[col] < 1.1).sum()
                high_odds = (df[col] > 20).sum()
                outlier_summary[col] = {'low': low_odds, 'high': high_odds}
                
                print(f"{col}:")
                print(f"   Range: {df[col].min():.2f} - {df[col].max():.2f}")
                print(f"   Outliers: {low_odds} below 1.1, {high_odds} above 20")
                
                if low_odds > 0 or high_odds > 0:
                    self.warnings.append(f"Outlier odds in {col}: {low_odds} low, {high_odds} high")
            
            self.validation_results['odds_outliers'] = outlier_summary
        else:
            print("❌ No odds columns found")
        
        # 6. Margin distribution analysis
        print("\n6️⃣ MARGIN DISTRIBUTION")
        print("-" * 20)
        
        if 'bookmaker_margin' in df.columns:
            margin_stats = df['bookmaker_margin'].describe()
            print(f"Bookmaker margin statistics:")
            print(f"   Mean: {margin_stats['mean']:.4f}")
            print(f"   Std: {margin_stats['std']:.4f}")
            print(f"   Range: {margin_stats['min']:.4f} - {margin_stats['max']:.4f}")
            
            # Check for unrealistic margins
            negative_margins = (df['bookmaker_margin'] < -0.1).sum()
            high_margins = (df['bookmaker_margin'] > 0.15).sum()
            
            if negative_margins > 0:
                print(f"⚠️ WARNING: {negative_margins} fixtures with highly negative margins")
                self.warnings.append(f"Negative margins: {negative_margins} fixtures")
            
            if high_margins > 0:
                print(f"⚠️ WARNING: {high_margins} fixtures with very high margins (>15%)")
                self.warnings.append(f"High margins: {high_margins} fixtures")
            
            self.validation_results['margin_stats'] = margin_stats.to_dict()
        else:
            print("❌ Bookmaker margin column not found")
        
        print("\n" + "="*50)
        return df
    
    def validate_model_performance(self):
        """Part 2: Model performance validation."""
        print("🤖 PART 2: MODEL PERFORMANCE VALIDATION")
        print("-" * 40)
        
        # Load validation results
        try:
            val_df = pd.read_csv(self.validation_file)
            print(f"✅ Validation results loaded: {len(val_df)} predictions")
        except FileNotFoundError:
            print(f"❌ Validation file not found: {self.validation_file}")
            return None
        
        # 1. Confusion matrix and classification metrics
        print("\n1️⃣ CONFUSION MATRIX & METRICS")
        print("-" * 30)
        
        y_true = val_df['true_label']
        y_pred = val_df['predicted_label']
        
        # Generate confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        target_names = ['Home Win', 'Away Win', 'Draw']
        
        print("Confusion Matrix:")
        print("                Predicted")
        print("                H    A    D")
        for i, true_label in enumerate(target_names):
            print(f"Actual {true_label[0]}   {cm[i][0]:4d} {cm[i][1]:4d} {cm[i][2]:4d}")
        
        # Classification report
        class_report = classification_report(y_true, y_pred, target_names=target_names, output_dict=True)
        
        print("\nPer-class Performance:")
        for i, class_name in enumerate(target_names):
            precision = class_report[class_name]['precision']
            recall = class_report[class_name]['recall']
            f1 = class_report[class_name]['f1-score']
            
            print(f"   {class_name}: Precision={precision:.3f}, Recall={recall:.3f}, F1={f1:.3f}")
            
            # Flag poor performance
            if precision < 0.30:
                self.warnings.append(f"Low precision for {class_name}: {precision:.3f}")
            if recall < 0.30:
                self.warnings.append(f"Low recall for {class_name}: {recall:.3f}")
        
        overall_accuracy = class_report['accuracy']
        print(f"\nOverall Accuracy: {overall_accuracy:.3f}")
        
        self.validation_results['confusion_matrix'] = cm.tolist()
        self.validation_results['classification_report'] = class_report
        
        # 2. Feature importance analysis
        print("\n2️⃣ FEATURE IMPORTANCE ANALYSIS")
        print("-" * 31)
        
        try:
            feat_imp = pd.read_csv(self.feature_importance_file)
            print(f"✅ Feature importance loaded: {len(feat_imp)} features")
            
            print("\nTop 10 Features:")
            for i, row in feat_imp.head(10).iterrows():
                print(f"   {i+1:2d}. {row['feature']:25s}: {row['importance']:8.1f}")
            
            # Check for over-reliance on specific features
            total_importance = feat_imp['importance'].sum()
            feat_imp['importance_pct'] = feat_imp['importance'] / total_importance * 100
            
            dominant_features = feat_imp[feat_imp['importance_pct'] > 30]
            if not dominant_features.empty:
                print(f"\n⚠️ WARNING: Over-reliance on features:")
                for _, row in dominant_features.iterrows():
                    print(f"   {row['feature']}: {row['importance_pct']:.1f}%")
                self.warnings.append("Over-reliance on specific features detected")
            
            # Check for team-specific features
            team_features = feat_imp[feat_imp['feature'].str.contains('team|home|away', case=False, na=False)]
            if not team_features.empty:
                print(f"\nTeam-specific features detected: {len(team_features)}")
                for _, row in team_features.iterrows():
                    print(f"   {row['feature']}: {row['importance']:8.1f}")
            
            self.validation_results['feature_importance'] = feat_imp.head(15).to_dict('records')
            
        except FileNotFoundError:
            print(f"❌ Feature importance file not found: {self.feature_importance_file}")
        
        # 3. Probability distribution analysis
        print("\n3️⃣ PROBABILITY DISTRIBUTION")
        print("-" * 29)
        
        prob_cols = ['prob_home', 'prob_away', 'prob_draw']
        available_prob_cols = [col for col in prob_cols if col in val_df.columns]
        
        if available_prob_cols:
            for col in available_prob_cols:
                prob_stats = val_df[col].describe()
                print(f"{col}:")
                print(f"   Mean: {prob_stats['mean']:.3f}, Std: {prob_stats['std']:.3f}")
                print(f"   Range: {prob_stats['min']:.3f} - {prob_stats['max']:.3f}")
                
                # Check for extreme probabilities
                extreme_low = (val_df[col] < 0.05).sum()
                extreme_high = (val_df[col] > 0.95).sum()
                
                if extreme_low > 0 or extreme_high > 0:
                    print(f"   Extreme values: {extreme_low} below 0.05, {extreme_high} above 0.95")
        
        print("\n" + "="*50)
        return val_df, feat_imp if 'feat_imp' in locals() else None
    
    def create_visualizations(self, dataset_df, validation_df, feature_importance_df):
        """Create diagnostic visualizations."""
        print("📊 CREATING DIAGNOSTIC VISUALIZATIONS")
        print("-" * 37)
        
        plt.style.use('default')
        fig = plt.figure(figsize=(16, 12))
        
        # 1. Class Balance Chart
        ax1 = plt.subplot(2, 3, 1)
        if 'target' in dataset_df.columns:
            class_counts = dataset_df['target'].value_counts().sort_index()
            target_names = ['Home Win', 'Away Win', 'Draw']
            colors = ['#2E8B57', '#DC143C', '#4169E1']
            
            bars = ax1.bar(target_names, class_counts.values, color=colors, alpha=0.7)
            ax1.set_title('Serie A: Class Distribution', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Number of Fixtures')
            
            # Add percentage labels
            total = len(dataset_df)
            for bar, count in zip(bars, class_counts.values):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height + 5,
                        f'{count}\n({count/total*100:.1f}%)',
                        ha='center', va='bottom', fontweight='bold')
        
        # 2. Confusion Matrix
        ax2 = plt.subplot(2, 3, 2)
        if validation_df is not None:
            cm = confusion_matrix(validation_df['true_label'], validation_df['predicted_label'])
            sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                       xticklabels=['Home Win', 'Away Win', 'Draw'],
                       yticklabels=['Home Win', 'Away Win', 'Draw'],
                       ax=ax2)
            ax2.set_title('Confusion Matrix', fontsize=14, fontweight='bold')
            ax2.set_ylabel('True Label')
            ax2.set_xlabel('Predicted Label')
        
        # 3. Feature Importance (Top 10)
        ax3 = plt.subplot(2, 3, 3)
        if feature_importance_df is not None:
            top_features = feature_importance_df.head(10)
            bars = ax3.barh(range(len(top_features)), top_features['importance'].values, 
                           color='skyblue', alpha=0.7)
            ax3.set_yticks(range(len(top_features)))
            ax3.set_yticklabels(top_features['feature'].values)
            ax3.set_title('Top 10 Feature Importance', fontsize=14, fontweight='bold')
            ax3.set_xlabel('Importance Score')
            ax3.invert_yaxis()
        
        # 4. Odds Distribution
        ax4 = plt.subplot(2, 3, 4)
        odds_cols = ['avg_home_odds', 'avg_away_odds', 'avg_draw_odds']
        available_odds = [col for col in odds_cols if col in dataset_df.columns]
        
        if available_odds:
            for i, col in enumerate(available_odds):
                ax4.hist(dataset_df[col], bins=30, alpha=0.5, 
                        label=col.replace('avg_', '').replace('_odds', '').title(),
                        color=['green', 'red', 'blue'][i])
            ax4.set_title('Odds Distribution', fontsize=14, fontweight='bold')
            ax4.set_xlabel('Odds Value')
            ax4.set_ylabel('Frequency')
            ax4.legend()
        
        # 5. Margin Distribution
        ax5 = plt.subplot(2, 3, 5)
        if 'bookmaker_margin' in dataset_df.columns:
            ax5.hist(dataset_df['bookmaker_margin'], bins=30, color='orange', alpha=0.7)
            ax5.axvline(dataset_df['bookmaker_margin'].mean(), color='red', linestyle='--', 
                       label=f'Mean: {dataset_df["bookmaker_margin"].mean():.3f}')
            ax5.set_title('Bookmaker Margin Distribution', fontsize=14, fontweight='bold')
            ax5.set_xlabel('Margin')
            ax5.set_ylabel('Frequency')
            ax5.legend()
        
        # 6. Probability Calibration
        ax6 = plt.subplot(2, 3, 6)
        if validation_df is not None:
            prob_cols = ['prob_home', 'prob_away', 'prob_draw']
            available_probs = [col for col in prob_cols if col in validation_df.columns]
            
            if available_probs:
                for i, col in enumerate(available_probs):
                    ax6.hist(validation_df[col], bins=20, alpha=0.5,
                            label=col.replace('prob_', '').title(),
                            color=['green', 'red', 'blue'][i])
                ax6.set_title('Predicted Probability Distribution', fontsize=14, fontweight='bold')
                ax6.set_xlabel('Probability')
                ax6.set_ylabel('Frequency')
                ax6.legend()
        
        plt.tight_layout()
        
        # Save visualization
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        chart_filename = f'serie_a_validation_charts_{timestamp}.png'
        plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"✅ Diagnostic charts saved: {chart_filename}")
        return chart_filename
    
    def generate_report(self, chart_filename):
        """Generate comprehensive validation report."""
        print("📝 GENERATING VALIDATION REPORT")
        print("-" * 31)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f'serie_a_validation_report_{timestamp}.md'
        
        report_content = f"""# SERIE A 1X2 MODEL VALIDATION REPORT

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Validator**: Serie A Model Validation Suite  
**Status**: {'⚠️ WARNINGS DETECTED' if self.warnings else '✅ VALIDATION PASSED'}

---

## 📊 EXECUTIVE SUMMARY

### Dataset Validation
- **Total Fixtures**: {self.validation_results.get('total_fixtures', 'N/A')}
- **Missing Values**: {'None detected' if not any('missing' in w.lower() for w in self.warnings) else 'Issues detected'}
- **Class Balance**: {'Acceptable' if not any('imbalance' in w.lower() for w in self.warnings) else 'Imbalanced'}
- **Odds Quality**: {'Good' if not any('odds' in w.lower() for w in self.warnings) else 'Issues detected'}

### Model Performance
- **Overall Accuracy**: {self.validation_results.get('classification_report', {}).get('accuracy', 'N/A'):.3f}
- **Performance Balance**: {'Good' if not any('precision' in w.lower() or 'recall' in w.lower() for w in self.warnings) else 'Issues detected'}

---

## ⚠️ WARNINGS & ISSUES

"""
        
        if self.warnings:
            for i, warning in enumerate(self.warnings, 1):
                report_content += f"{i}. **{warning}**\n"
        else:
            report_content += "✅ No critical issues detected.\n"
        
        report_content += f"""

---

## 📈 DETAILED VALIDATION RESULTS

### Class Distribution
"""
        
        if 'class_balance' in self.validation_results:
            cb = self.validation_results['class_balance']
            target_names = {0: 'Home Win', 1: 'Away Win', 2: 'Draw'}
            for target, pct in cb.items():
                name = target_names.get(target, f'Class {target}')
                report_content += f"- **{name}**: {pct:.1f}%\n"
        
        report_content += f"""

### Model Performance Metrics
"""
        
        if 'classification_report' in self.validation_results:
            cr = self.validation_results['classification_report']
            target_names = ['Home Win', 'Away Win', 'Draw']
            
            for class_name in target_names:
                if class_name.replace(' ', '_').lower() in cr:
                    class_data = cr[class_name.replace(' ', '_').lower()]
                elif class_name in cr:
                    class_data = cr[class_name]
                else:
                    continue
                    
                precision = class_data.get('precision', 0)
                recall = class_data.get('recall', 0)
                f1 = class_data.get('f1-score', 0)
                
                report_content += f"""
**{class_name}**:
- Precision: {precision:.3f}
- Recall: {recall:.3f}
- F1-Score: {f1:.3f}
"""
        
        report_content += f"""

### Top Features (by Importance)
"""
        
        if 'feature_importance' in self.validation_results:
            for i, feat in enumerate(self.validation_results['feature_importance'][:10], 1):
                report_content += f"{i}. **{feat['feature']}**: {feat['importance']:.1f}\n"
        
        report_content += f"""

---

## 🎯 RECOMMENDATIONS

### Immediate Actions
"""
        
        if self.warnings:
            if any('imbalance' in w.lower() for w in self.warnings):
                report_content += "- **Address class imbalance** through stratified sampling or class weights\n"
            if any('precision' in w.lower() or 'recall' in w.lower() for w in self.warnings):
                report_content += "- **Improve model performance** on poorly performing classes\n"
            if any('odds' in w.lower() for w in self.warnings):
                report_content += "- **Review odds data quality** and filtering logic\n"
            if any('missing' in w.lower() for w in self.warnings):
                report_content += "- **Handle missing values** through imputation or removal\n"
        else:
            report_content += "- ✅ **Model ready for production deployment**\n"
            report_content += "- Monitor real-world performance and collect feedback\n"
        
        report_content += f"""

### Future Enhancements
- Collect real historical data to replace simulated data
- Implement ensemble methods for improved accuracy
- Add player-specific and injury features
- Develop live model updating capabilities

---

## 📊 VISUALIZATIONS

Diagnostic charts available in: `{chart_filename}`

---

## 🔍 TECHNICAL DETAILS

### Files Validated
- **Dataset**: `{self.dataset_file}`
- **Validation Results**: `{self.validation_file}`
- **Feature Importance**: `{self.feature_importance_file}`
- **Model File**: `{self.model_file}`

### Validation Timestamp
- **Generated**: {timestamp}
- **Validation Suite Version**: 1.0

---

## ✅ DEPLOYMENT DECISION

"""
        
        # Deployment recommendation
        critical_warnings = [w for w in self.warnings if any(keyword in w.lower() 
                            for keyword in ['precision', 'recall', 'accuracy', 'missing'])]
        
        if critical_warnings:
            report_content += "**RECOMMENDATION**: ⚠️ **CONDITIONAL DEPLOYMENT**\n\n"
            report_content += "Address critical warnings before full production deployment.\n"
            report_content += "Consider limited testing or shadow deployment first.\n"
        else:
            report_content += "**RECOMMENDATION**: ✅ **APPROVED FOR DEPLOYMENT**\n\n"
            report_content += "Model validation passed. Ready for production deployment.\n"
            report_content += "Continue with systematic expansion to remaining leagues.\n"
        
        report_content += f"""

---

*Report generated by Serie A Model Validation Suite*  
*Timestamp: {datetime.now().isoformat()}*
"""
        
        # Save report
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"✅ Validation report saved: {report_filename}")
        return report_filename

def main():
    """Run complete Serie A model validation."""
    print("🇮🇹 SERIE A 1X2 MODEL VALIDATION SUITE")
    print("=" * 45)
    print("Comprehensive pre-deployment validation")
    print()
    
    validator = SerieAModelValidator()
    
    # Part 1: Dataset Validation
    dataset_df = validator.validate_dataset()
    
    if dataset_df is not None:
        validator.validation_results['total_fixtures'] = len(dataset_df)
    
    # Part 2: Model Performance Validation
    validation_df, feature_importance_df = validator.validate_model_performance()
    
    # Part 3: Create Visualizations
    if dataset_df is not None:
        chart_filename = validator.create_visualizations(dataset_df, validation_df, feature_importance_df)
    else:
        chart_filename = "charts_not_generated.png"
    
    # Part 4: Generate Report
    report_filename = validator.generate_report(chart_filename)
    
    # Final Summary
    print("\n" + "="*45)
    print("🏁 VALIDATION COMPLETE")
    print("=" * 45)
    print(f"📊 Warnings detected: {len(validator.warnings)}")
    print(f"📝 Report generated: {report_filename}")
    print(f"📈 Charts created: {chart_filename}")
    
    if validator.warnings:
        print("\n⚠️ CRITICAL WARNINGS:")
        for warning in validator.warnings:
            print(f"   • {warning}")
        print("\n🔧 Review warnings before deployment!")
    else:
        print("\n✅ ALL VALIDATIONS PASSED")
        print("🚀 Model ready for production deployment!")

if __name__ == "__main__":
    main() 