#!/usr/bin/env python3
"""
MULTI-LEAGUE MODEL INTEGRITY CHECKER
====================================

Comprehensive integrity verification for production models:
- La Liga (PRIMARY): 74.4% hit rate, 138.92% ROI 🥇
- Serie A (BACKUP): 61.5% hit rate, -9.10% ROI

Monitors both models and maintains performance hierarchy.
"""

import os
import hashlib
import json
from datetime import datetime
import pandas as pd

class MultiLeagueIntegrityChecker:
    def __init__(self):
        # La Liga model (PRIMARY - SUPERIOR PERFORMANCE)
        self.la_liga_files = {
            "model": "LOCKED_PRODUCTION_league_model_1x2_la_liga_20250630_152907.txt",
            "training_data": "LOCKED_PRODUCTION_la_liga_complete_training_dataset_20250630_152907.csv",
            "feature_importance": "LOCKED_PRODUCTION_feature_importance_la_liga_20250630_152907.csv",
            "production_interface": "LOCKED_PRODUCTION_la_liga_production_ready.py"
        }
        
        # Serie A model (BACKUP - SECONDARY)
        self.serie_a_files = {
            "model": "LOCKED_PRODUCTION_league_model_1x2_serie_a_20250630_125109.txt",
            "training_data": "LOCKED_PRODUCTION_serie_a_complete_training_dataset_20250630_125108.csv",
            "validation": "LOCKED_PRODUCTION_validation_serie_a_20250630_125109.csv",
            "feature_importance": "LOCKED_PRODUCTION_feature_importance_serie_a_20250630_125109.csv",
            "production_interface": "LOCKED_PRODUCTION_serie_a_production_ready.py"
        }
        
        # Performance benchmarks
        self.performance_benchmarks = {
            "la_liga": {
                "hit_rate": 0.744,
                "roi": 138.92,
                "status": "PRIMARY",
                "priority": 1,
                "allocation": 0.70
            },
            "serie_a": {
                "hit_rate": 0.615,
                "roi": -9.10,
                "status": "BACKUP",
                "priority": 2,
                "allocation": 0.30
            }
        }
        
        self.integrity_file = "multi_league_integrity_baseline.json"
        self.create_baseline_if_needed()
    
    def calculate_file_hash(self, filepath):
        """Calculate SHA-256 hash of a file."""
        if not os.path.exists(filepath):
            return None
        
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def create_baseline_if_needed(self):
        """Create integrity baseline for all locked production models."""
        if os.path.exists(self.integrity_file):
            return
        
        print("🔐 Creating multi-league integrity baseline...")
        
        baseline = {
            "created_date": datetime.now().isoformat(),
            "leagues": {
                "la_liga": {
                    "status": "PRIMARY",
                    "performance": self.performance_benchmarks["la_liga"],
                    "files": {}
                },
                "serie_a": {
                    "status": "BACKUP", 
                    "performance": self.performance_benchmarks["serie_a"],
                    "files": {}
                }
            }
        }
        
        # Process La Liga files (PRIMARY)
        print("\n🥇 LA LIGA MODEL (PRIMARY):")
        for file_type, filepath in self.la_liga_files.items():
            if os.path.exists(filepath):
                file_hash = self.calculate_file_hash(filepath)
                file_size = os.path.getsize(filepath)
                
                baseline["leagues"]["la_liga"]["files"][file_type] = {
                    "filepath": filepath,
                    "hash": file_hash,
                    "size": file_size,
                    "locked_date": datetime.now().isoformat()
                }
                print(f"   ✅ {file_type}: {os.path.basename(filepath)} ({file_size:,} bytes)")
            else:
                print(f"   ⚠️ {file_type}: {filepath} - FILE NOT FOUND")
        
        # Process Serie A files (BACKUP)
        print("\n🥈 SERIE A MODEL (BACKUP):")
        for file_type, filepath in self.serie_a_files.items():
            if os.path.exists(filepath):
                file_hash = self.calculate_file_hash(filepath)
                file_size = os.path.getsize(filepath)
                
                baseline["leagues"]["serie_a"]["files"][file_type] = {
                    "filepath": filepath,
                    "hash": file_hash,
                    "size": file_size,
                    "locked_date": datetime.now().isoformat()
                }
                print(f"   ✅ {file_type}: {os.path.basename(filepath)} ({file_size:,} bytes)")
            else:
                print(f"   ⚠️ {file_type}: {filepath} - FILE NOT FOUND")
        
        # Save baseline
        with open(self.integrity_file, 'w') as f:
            json.dump(baseline, f, indent=2)
        
        print(f"\n✅ Multi-league integrity baseline saved: {self.integrity_file}")
    
    def verify_integrity(self, verbose=True):
        """Verify integrity of all production models."""
        if verbose:
            print("🔍 MULTI-LEAGUE MODEL INTEGRITY CHECK")
            print("=" * 45)
        
        if not os.path.exists(self.integrity_file):
            print("❌ CRITICAL: No integrity baseline found!")
            return False
        
        # Load baseline
        with open(self.integrity_file, 'r') as f:
            baseline = json.load(f)
        
        all_verified = True
        issues = []
        
        # Check each league model
        for league_name, league_data in baseline["leagues"].items():
            league_display = "🥇 LA LIGA (PRIMARY)" if league_name == "la_liga" else "🥈 SERIE A (BACKUP)"
            
            if verbose:
                print(f"\n{league_display}")
                print("-" * 30)
            
            league_verified = True
            
            for file_type, expected_data in league_data["files"].items():
                filepath = expected_data["filepath"]
                expected_hash = expected_data["hash"]
                expected_size = expected_data["size"]
                
                if verbose:
                    print(f"📁 {file_type}: {os.path.basename(filepath)}")
                
                # Check file existence
                if not os.path.exists(filepath):
                    issue = f"❌ CRITICAL: {league_name} {file_type} missing - {filepath}"
                    issues.append(issue)
                    all_verified = False
                    league_verified = False
                    if verbose:
                        print(f"   {issue}")
                    continue
                
                # Check file size
                actual_size = os.path.getsize(filepath)
                size_diff = abs(actual_size - expected_size)
                size_threshold = max(1000, expected_size * 0.01)
                
                if size_diff > size_threshold:
                    issue = f"⚠️ WARNING: {league_name} {file_type} size changed"
                    issues.append(issue)
                    if verbose:
                        print(f"   {issue}")
                else:
                    if verbose:
                        print(f"   ✅ Size OK: {actual_size:,} bytes")
                
                # Check file hash
                actual_hash = self.calculate_file_hash(filepath)
                if actual_hash != expected_hash:
                    issue = f"❌ CRITICAL: {league_name} {file_type} modified - Hash mismatch!"
                    issues.append(issue)
                    all_verified = False
                    league_verified = False
                    if verbose:
                        print(f"   {issue}")
                else:
                    if verbose:
                        print(f"   ✅ Hash OK: {actual_hash[:16]}...")
            
            # Show league performance
            if verbose and league_verified:
                perf = league_data["performance"]
                print(f"   📊 Performance: {perf['hit_rate']:.1%} hit rate, {perf['roi']:.2f}% ROI")
                print(f"   🎯 Status: {perf['status']} ({perf['allocation']:.0%} allocation)")
        
        # Summary
        if verbose:
            print(f"\n🏁 INTEGRITY CHECK COMPLETE")
            print("=" * 35)
        
        if all_verified:
            if verbose:
                print("✅ ALL MODELS VERIFIED - INTEGRITY INTACT")
                self.show_model_hierarchy(baseline)
            return True
        else:
            if verbose:
                print("❌ INTEGRITY ISSUES DETECTED:")
                for issue in issues:
                    print(f"   {issue}")
                print("\n🚨 DO NOT USE MODELS UNTIL ISSUES RESOLVED!")
            return False
    
    def show_model_hierarchy(self, baseline):
        """Display current model hierarchy and performance."""
        print(f"\n🏆 PRODUCTION MODEL HIERARCHY")
        print("-" * 35)
        
        la_liga_perf = baseline["leagues"]["la_liga"]["performance"]
        serie_a_perf = baseline["leagues"]["serie_a"]["performance"]
        
        print(f"🥇 PRIMARY: LA LIGA")
        print(f"   Hit Rate: {la_liga_perf['hit_rate']:.1%}")
        print(f"   ROI: {la_liga_perf['roi']:.2f}%")
        print(f"   Allocation: {la_liga_perf['allocation']:.0%}")
        print(f"   Status: PRODUCTION READY ✅")
        
        print(f"\n🥈 BACKUP: SERIE A")
        print(f"   Hit Rate: {serie_a_perf['hit_rate']:.1%}")
        print(f"   ROI: {serie_a_perf['roi']:.2f}%")
        print(f"   Allocation: {serie_a_perf['allocation']:.0%}")
        print(f"   Status: DIVERSIFICATION")
        
        # Performance comparison
        hit_rate_diff = (la_liga_perf['hit_rate'] - serie_a_perf['hit_rate']) * 100
        roi_diff = la_liga_perf['roi'] - serie_a_perf['roi']
        
        print(f"\n📈 LA LIGA ADVANTAGE:")
        print(f"   Hit Rate: +{hit_rate_diff:.1f}%")
        print(f"   ROI: +{roi_diff:.1f}%")
        print(f"   Winner: LA LIGA 🏆")
    
    def get_deployment_status(self):
        """Get current deployment status and recommendations."""
        if not os.path.exists(self.integrity_file):
            return {"status": "ERROR", "message": "No baseline found"}
        
        with open(self.integrity_file, 'r') as f:
            baseline = json.load(f)
        
        la_liga_perf = baseline["leagues"]["la_liga"]["performance"] 
        serie_a_perf = baseline["leagues"]["serie_a"]["performance"]
        
        deployment_status = {
            "primary_model": {
                "league": "La Liga",
                "hit_rate": la_liga_perf['hit_rate'],
                "roi": la_liga_perf['roi'],
                "allocation": la_liga_perf['allocation'],
                "status": "PRODUCTION_READY",
                "priority": 1
            },
            "backup_model": {
                "league": "Serie A", 
                "hit_rate": serie_a_perf['hit_rate'],
                "roi": serie_a_perf['roi'],
                "allocation": serie_a_perf['allocation'],
                "status": "BACKUP_READY",
                "priority": 2
            },
            "recommendation": {
                "deploy_primary": True,
                "deploy_backup": True,
                "portfolio_approach": True,
                "la_liga_superior": True
            },
            "performance_comparison": {
                "hit_rate_advantage": (la_liga_perf['hit_rate'] - serie_a_perf['hit_rate']) * 100,
                "roi_advantage": la_liga_perf['roi'] - serie_a_perf['roi'],
                "winner": "La Liga"
            }
        }
        
        return deployment_status
    
    def emergency_restore_procedures(self):
        """Provide comprehensive restore procedures for both models."""
        print("\n🚨 EMERGENCY RESTORATION PROCEDURES")
        print("=" * 45)
        
        print("If integrity check fails, follow these steps:")
        
        print("\n🥇 LA LIGA MODEL (PRIMARY) - CRITICAL:")
        print("   1. 🛑 STOP ALL LA LIGA PREDICTIONS IMMEDIATELY")
        print("   2. 🔍 Check La Liga files:")
        for file_type, filepath in self.la_liga_files.items():
            print(f"      - {filepath}")
        print("   3. 📥 RESTORE from backups (HIGHEST PRIORITY)")
        print("   4. ✅ Verify 74.4% hit rate capability")
        
        print("\n🥈 SERIE A MODEL (BACKUP) - SECONDARY:")
        print("   1. 🔍 Check Serie A files:")
        for file_type, filepath in self.serie_a_files.items():
            print(f"      - {filepath}")
        print("   2. 📥 RESTORE from backups (if needed)")
        print("   3. ✅ Verify 61.5% hit rate capability")
        
        print("\n🆘 COMPLETE SYSTEM FAILURE:")
        print("   1. 🛑 HALT ALL BETTING OPERATIONS")
        print("   2. 📞 EMERGENCY PROTOCOL: Use original model files")
        print("   3. 🔄 RECREATE integrity baseline")
        print("   4. 📊 RE-RUN performance validation")
        print("   5. ✅ RESUME only after full verification")
        
        print("\n📋 VERIFICATION CHECKLIST:")
        print("   □ La Liga model loads successfully")
        print("   □ Serie A model loads successfully") 
        print("   □ Feature columns match exactly")
        print("   □ Prediction outputs are reasonable")
        print("   □ Performance benchmarks maintained")
        print("   □ Integrity check passes completely")

def main():
    """Run comprehensive multi-league integrity check."""
    print("🔐 MULTI-LEAGUE MODEL INTEGRITY SYSTEM")
    print("=" * 50)
    print("🥇 La Liga: 74.4% hit rate, 138.92% ROI (PRIMARY)")
    print("🥈 Serie A: 61.5% hit rate, -9.10% ROI (BACKUP)")
    print("🎯 Comprehensive integrity verification\n")
    
    checker = MultiLeagueIntegrityChecker()
    
    # Verify integrity
    is_intact = checker.verify_integrity()
    
    if is_intact:
        print("\n🎯 READY FOR PRODUCTION")
        print("All models verified - safe to proceed with predictions")
        
        # Show deployment status
        status = checker.get_deployment_status()
        print(f"\n📊 DEPLOYMENT STATUS:")
        print(f"   Primary: {status['primary_model']['league']} ({status['primary_model']['hit_rate']:.1%} hit rate)")
        print(f"   Backup: {status['backup_model']['league']} ({status['backup_model']['hit_rate']:.1%} hit rate)")
        print(f"   Winner: {status['performance_comparison']['winner']} 🏆")
        
        if status['recommendation']['deploy_primary']:
            print("\n✅ DEPLOYMENT AUTHORIZED")
            print("   🥇 La Liga: PRIMARY MODEL (70% allocation)")
            print("   🥈 Serie A: BACKUP MODEL (30% allocation)")
        
    else:
        print("\n🚨 PRODUCTION HALTED")
        print("Model integrity issues detected - predictions blocked")
        checker.emergency_restore_procedures()
    
    return is_intact

if __name__ == "__main__":
    main() 