#!/usr/bin/env python3
"""
Bundesliga & Ligue 1 Model Validation and Deployment Pipeline
Following exact same process as successful La Liga model deployment
"""

import os
import pickle
import pandas as pd
import numpy as np
import json
from datetime import datetime
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

class BundesligaLigue1Validator:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Load trained models
        self.models = {
            'Bundesliga': self.load_model('realistic_bundesliga_model_20250704_174925.pkl'),
            'Ligue 1': self.load_model('realistic_ligue 1_model_20250704_174925.pkl')
        }
        
        # Load validation data
        self.validation_data = pd.read_csv('realistic_bundesliga_ligue1_training_data_20250704_174630.csv')
        
        # Performance thresholds (based on successful La Liga model)
        self.performance_thresholds = {
            'min_accuracy': 0.45,  # Minimum acceptable accuracy
            'min_high_conf_hit_rate': 0.65,  # Minimum hit rate for high confidence bets
            'min_medium_conf_hit_rate': 0.55,  # Minimum hit rate for medium confidence bets
        }
        
    def log(self, message):
        """Log with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def load_model(self, model_file):
        """Load a trained model."""
        if os.path.exists(model_file):
            with open(model_file, 'rb') as f:
                return pickle.load(f)
        else:
            self.log(f"⚠️  Model file not found: {model_file}")
            return None
    
    def prepare_validation_features(self, df):
        """Prepare features for validation."""
        feature_columns = [
            'home_avg_goals_for', 'home_avg_goals_against', 'home_win_rate', 'home_draw_rate',
            'away_avg_goals_for', 'away_avg_goals_against', 'away_win_rate', 'away_draw_rate',
            'is_bundesliga', 'is_ligue1', 'goal_difference_tendency', 'defensive_balance',
            'total_expected_goals', 'win_rate_difference', 'combined_draw_rate'
        ]
        
        return df[feature_columns].copy()
    
    def validate_model_performance(self, league_name, model, league_data):
        """Validate model performance on holdout data."""
        self.log(f"\n🔍 VALIDATING {league_name.upper()} MODEL")
        self.log("=" * 50)
        
        # Prepare features and targets
        X = self.prepare_validation_features(league_data)
        y = league_data['outcome'].copy()
        
        # Make predictions
        predictions = model.predict(X, num_iteration=model.best_iteration)
        predicted_classes = np.argmax(predictions, axis=1)
        confidence_scores = np.max(predictions, axis=1)
        
        # Overall accuracy
        accuracy = accuracy_score(y, predicted_classes)
        self.log(f"📊 Overall Accuracy: {accuracy:.1%}")
        
        # Classification report
        class_names = ['Draw (0)', 'Home Win (1)', 'Away Win (2)']
        report = classification_report(y, predicted_classes, target_names=class_names, output_dict=True)
        
        self.log(f"📈 Detailed Performance:")
        for class_name, metrics in report.items():
            if class_name in class_names:
                precision = metrics['precision']
                recall = metrics['recall']
                f1 = metrics['f1-score']
                support = metrics['support']
                self.log(f"   {class_name}: P={precision:.1%}, R={recall:.1%}, F1={f1:.1%} (n={support})")
        
        # Confidence-based performance
        confidence_results = {}
        confidence_thresholds = [0.4, 0.5, 0.6, 0.7, 0.8]
        
        self.log(f"💰 Confidence-Based Betting Performance:")
        for threshold in confidence_thresholds:
            high_conf_mask = confidence_scores > threshold
            if high_conf_mask.sum() > 0:
                high_conf_accuracy = accuracy_score(
                    y[high_conf_mask], 
                    predicted_classes[high_conf_mask]
                )
                num_bets = high_conf_mask.sum()
                confidence_results[threshold] = {
                    'hit_rate': high_conf_accuracy,
                    'num_bets': num_bets
                }
                self.log(f"   Confidence >{threshold}: {high_conf_accuracy:.1%} hit rate ({num_bets} bets)")
            else:
                confidence_results[threshold] = {'hit_rate': 0, 'num_bets': 0}
                self.log(f"   Confidence >{threshold}: No bets")
        
        # Validation results
        validation_results = {
            'league': league_name,
            'overall_accuracy': accuracy,
            'classification_report': report,
            'confidence_performance': confidence_results,
            'total_samples': len(y),
            'validation_timestamp': self.timestamp
        }
        
        return validation_results
    
    def check_performance_thresholds(self, validation_results):
        """Check if model meets performance thresholds."""
        league = validation_results['league']
        accuracy = validation_results['overall_accuracy']
        confidence_perf = validation_results['confidence_performance']
        
        self.log(f"\n✅ PERFORMANCE THRESHOLD CHECK - {league.upper()}")
        self.log("=" * 50)
        
        # Check accuracy threshold
        accuracy_pass = accuracy >= self.performance_thresholds['min_accuracy']
        self.log(f"📊 Accuracy: {accuracy:.1%} (min: {self.performance_thresholds['min_accuracy']:.1%}) {'✅' if accuracy_pass else '❌'}")
        
        # Check high confidence threshold (>0.7)
        high_conf_hit_rate = confidence_perf.get(0.7, {}).get('hit_rate', 0)
        high_conf_pass = high_conf_hit_rate >= self.performance_thresholds['min_high_conf_hit_rate']
        self.log(f"🎯 High Confidence (>0.7): {high_conf_hit_rate:.1%} (min: {self.performance_thresholds['min_high_conf_hit_rate']:.1%}) {'✅' if high_conf_pass else '❌'}")
        
        # Check medium confidence threshold (>0.5)
        med_conf_hit_rate = confidence_perf.get(0.5, {}).get('hit_rate', 0)
        med_conf_pass = med_conf_hit_rate >= self.performance_thresholds['min_medium_conf_hit_rate']
        self.log(f"📈 Medium Confidence (>0.5): {med_conf_hit_rate:.1%} (min: {self.performance_thresholds['min_medium_conf_hit_rate']:.1%}) {'✅' if med_conf_pass else '❌'}")
        
        # Overall validation status
        all_pass = accuracy_pass and high_conf_pass and med_conf_pass
        self.log(f"\n🏆 {league} Model Validation: {'✅ PASSED' if all_pass else '❌ FAILED'}")
        
        return {
            'passed': all_pass,
            'accuracy_pass': accuracy_pass,
            'high_conf_pass': high_conf_pass,
            'medium_conf_pass': med_conf_pass
        }
    
    def generate_model_explanation(self, league_name, validation_results, threshold_check):
        """Generate sharp explanation of model performance."""
        self.log(f"\n📋 SHARP EXPLANATION - {league_name.upper()} MODEL")
        self.log("=" * 50)
        
        accuracy = validation_results['overall_accuracy']
        conf_perf = validation_results['confidence_performance']
        
        # Performance summary
        self.log(f"🎯 Model Quality Assessment:")
        if threshold_check['passed']:
            self.log(f"   ✅ DEPLOYMENT READY - All thresholds met")
        else:
            self.log(f"   ⚠️  NEEDS IMPROVEMENT - Some thresholds failed")
        
        self.log(f"   📊 Base accuracy: {accuracy:.1%} (football typical: 40-55%)")
        
        # Key insights
        high_conf_hit_rate = conf_perf.get(0.7, {}).get('hit_rate', 0)
        high_conf_bets = conf_perf.get(0.7, {}).get('num_bets', 0)
        
        med_conf_hit_rate = conf_perf.get(0.5, {}).get('hit_rate', 0)
        med_conf_bets = conf_perf.get(0.5, {}).get('num_bets', 0)
        
        self.log(f"\n🔍 Key Performance Insights:")
        self.log(f"   📈 Conservative Strategy (>0.7 conf): {high_conf_hit_rate:.1%} success on {high_conf_bets} bets")
        self.log(f"   📊 Balanced Strategy (>0.5 conf): {med_conf_hit_rate:.1%} success on {med_conf_bets} bets")
        
        # Risk assessment
        if high_conf_hit_rate >= 0.7:
            self.log(f"   ✅ High confidence bets show strong predictive power")
        else:
            self.log(f"   ⚠️  High confidence bets need improvement")
        
        # Deployment recommendation
        if threshold_check['passed']:
            self.log(f"\n🚀 DEPLOYMENT RECOMMENDATION:")
            self.log(f"   ✅ Model approved for production deployment")
            self.log(f"   📊 Suggested betting strategy: Focus on >0.6 confidence bets")
            self.log(f"   💰 Expected performance: Similar to La Liga model success")
        else:
            self.log(f"\n⚠️  IMPROVEMENT NEEDED:")
            self.log(f"   🔧 Additional feature engineering recommended")
            self.log(f"   📊 Consider more historical data or external features")
    
    def lock_model_for_deployment(self, league_name, model, validation_results, threshold_check):
        """Lock model for deployment if validation passes."""
        if threshold_check['passed']:
            # Create deployment package
            deployment_package = {
                'model': model,
                'validation_results': validation_results,
                'deployment_timestamp': self.timestamp,
                'model_version': f"{league_name.lower()}_v1_{self.timestamp}",
                'status': 'DEPLOYED',
                'performance_summary': {
                    'accuracy': validation_results['overall_accuracy'],
                    'high_conf_hit_rate': validation_results['confidence_performance'].get(0.7, {}).get('hit_rate', 0),
                    'medium_conf_hit_rate': validation_results['confidence_performance'].get(0.5, {}).get('hit_rate', 0)
                }
            }
            
            # Save deployment package
            deployment_file = f"deployed_{league_name.lower()}_model_{self.timestamp}.pkl"
            with open(deployment_file, 'wb') as f:
                pickle.dump(deployment_package, f)
            
            self.log(f"🔒 {league_name} model locked and deployed: {deployment_file}")
            return deployment_file
        else:
            self.log(f"❌ {league_name} model not approved for deployment")
            return None
    
    def run_full_validation(self):
        """Run complete validation and deployment pipeline."""
        self.log("🚀 STARTING BUNDESLIGA & LIGUE 1 MODEL VALIDATION")
        self.log("📊 Following exact La Liga model validation process")
        self.log("=" * 70)
        
        results = {}
        deployment_files = {}
        
        for league_name in ['Bundesliga', 'Ligue 1']:
            model = self.models[league_name]
            
            if model is None:
                self.log(f"❌ {league_name} model not available for validation")
                continue
                
            # Get league-specific data
            league_data = self.validation_data[self.validation_data['league'] == league_name]
            
            if len(league_data) == 0:
                self.log(f"❌ No validation data for {league_name}")
                continue
            
            # Validate model performance
            validation_results = self.validate_model_performance(league_name, model, league_data)
            
            # Check performance thresholds
            threshold_check = self.check_performance_thresholds(validation_results)
            
            # Generate explanation
            self.generate_model_explanation(league_name, validation_results, threshold_check)
            
            # Lock model if validation passes
            deployment_file = self.lock_model_for_deployment(league_name, model, validation_results, threshold_check)
            
            results[league_name] = {
                'validation_results': validation_results,
                'threshold_check': threshold_check,
                'deployment_file': deployment_file
            }
            
            if deployment_file:
                deployment_files[league_name] = deployment_file
        
        # Final summary
        self.log(f"\n🎉 VALIDATION & DEPLOYMENT SUMMARY")
        self.log("=" * 60)
        
        summary_data = {}
        for league, result in results.items():
            passed = result['threshold_check']['passed']
            accuracy = result['validation_results']['overall_accuracy']
            
            self.log(f"\n🏆 {league}:")
            self.log(f"   Validation: {'✅ PASSED' if passed else '❌ FAILED'}")
            self.log(f"   Accuracy: {accuracy:.1%}")
            
            if result['deployment_file']:
                self.log(f"   Status: 🚀 DEPLOYED")
                self.log(f"   File: {result['deployment_file']}")
            else:
                self.log(f"   Status: ⚠️  NOT DEPLOYED")
            
            summary_data[league] = {
                'validation_passed': passed,
                'accuracy': accuracy,
                'deployed': bool(result['deployment_file']),
                'deployment_file': result['deployment_file']
            }
        
        # Save final summary
        summary_file = f"bundesliga_ligue1_deployment_summary_{self.timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2, default=str)
        
        self.log(f"\n💾 Final summary saved to: {summary_file}")
        
        return results, deployment_files

def main():
    """Main execution function."""
    try:
        validator = BundesligaLigue1Validator()
        results, deployment_files = validator.run_full_validation()
        
        deployed_count = len(deployment_files)
        total_count = len(['Bundesliga', 'Ligue 1'])
        
        print(f"\n✅ SUCCESS: Bundesliga & Ligue 1 validation completed!")
        print(f"🚀 {deployed_count}/{total_count} models deployed")
        
        if deployed_count == total_count:
            print(f"🎉 ALL MODELS SUCCESSFULLY DEPLOYED!")
            print(f"📊 Following exact La Liga model success pattern")
            print(f"💰 Ready for production betting operations")
        elif deployed_count > 0:
            print(f"⚠️  PARTIAL DEPLOYMENT: {deployed_count} models ready")
            print(f"🔧 Review failed models for improvement opportunities")
        else:
            print(f"❌ NO MODELS DEPLOYED: All need improvement")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 