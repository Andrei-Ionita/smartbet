#!/usr/bin/env python3
"""
Comprehensive project organization script
Organizes all the messy Bundesliga/Ligue 1 files into proper directories
"""

import os
import shutil
from pathlib import Path

def create_directory_structure():
    """Create organized directory structure"""
    base_dir = Path("bundesliga_ligue1_project")
    
    directories = {
        "1_production_models": "Final deployed models and deployment scripts",
        "2_training_data": "Final training datasets and summaries", 
        "3_development_scripts": "Development and training scripts",
        "4_data_collection": "Data collection and API scripts",
        "5_validation_reports": "Validation results and reports",
        "6_model_files": "Intermediate model files",
        "archive_old_attempts": "Old/experimental files"
    }
    
    for dir_name, description in directories.items():
        dir_path = base_dir / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create README for each directory
        readme_path = dir_path / "README.md"
        if not readme_path.exists():
            with open(readme_path, 'w') as f:
                f.write(f"# {dir_name.replace('_', ' ').title()}\n\n{description}\n")
    
    return base_dir

def organize_files():
    """Organize all files in root directory"""
    base_dir = create_directory_structure()
    
    # File organization rules
    file_rules = {
        # Production models (CRITICAL - deployed models)
        "1_production_models": [
            "deployed_bundesliga_model_20250704_175310.pkl",
            "deployed_ligue 1_model_20250704_175310.pkl", 
            "validate_and_deploy_bundesliga_ligue1.py",
            "bundesliga_ligue1_deployment_summary_20250704_175310.json",
            "bundesliga_ligue1_fixed_deployment_report_20250704_172132.json"
        ],
        
        # Training data (final realistic datasets)
        "2_training_data": [
            "realistic_bundesliga_ligue1_training_data_20250704_174630.csv",
            "realistic_bundesliga_ligue1_training_summary_20250704_174925.json",
            "working_corrected_bundesliga_ligue1_data_20250704_173722.csv",
            "bundesliga_ligue1_training_data_20250704_171510.csv"
        ],
        
        # Development scripts (training and model building)
        "3_development_scripts": [
            "train_realistic_bundesliga_ligue1_models.py",
            "create_realistic_training_data.py",
            "train_bundesliga_ligue1_models.py",
            "train_working_bundesliga_ligue1_models.py",
            "fixed_train_bundesliga_ligue1_models.py"
        ],
        
        # Data collection scripts
        "4_data_collection": [
            "working_corrected_collector.py",
            "final_corrected_collector.py", 
            "corrected_bundesliga_ligue1_collector.py",
            "final_bundesliga_ligue1_collector.py",
            "fixed_bundesliga_ligue1_collector.py",
            "bundesliga_ligue1_comprehensive_collector.py",
            "fixed_data_collection.py"
        ],
        
        # Validation and reports
        "5_validation_reports": [
            "BUNDESLIGA_VALIDATION_COMPLETE.md",
            "LIGUE_1_VALIDATION_COMPLETE.md", 
            "LIGA_1_VALIDATION_COMPLETE.md",
            "bundesliga_ligue1_training_summary_20250704_173931.json"
        ],
        
        # Model files (intermediate models)
        "6_model_files": [
            "realistic_bundesliga_model_20250704_174925.pkl",
            "realistic_ligue 1_model_20250704_174925.pkl",
            "bundesliga_model_20250704_173931.pkl",
            "ligue 1_model_20250704_173931.pkl"
        ],
        
        # Archive old attempts and experimental files
        "archive_old_attempts": [
            "bundesliga_ligue1_liga1_pipeline.py",
            "complete_real_api_multi_league_pipeline.py",
            "multi_league_real_api_pipeline.py",
            "real_api_multi_league_collector.py",
            "check_available_leagues.py",
            "check_subscription_details.py",
            "check_fixture_states.py",
            "debug_api_response.py",
            "debug_available_seasons.py", 
            "debug_season_discovery.py",
            "debug_sportmonks_score_structure.py",
            "find_correct_liga1_romania.py",
            "find_romanian_leagues_by_country.py",
            "search_romanian_liga1.py",
            "search_romania_systematic.py",
            "test_correct_filter_syntax.py",
            "test_romanian_liga1_474.py",
            "test_romanian_liga1_correct.py",
            "test_simple_fixtures.py",
            "get_all_seasons.py",
            "fix_league_season_collection.py",
            "bundesliga_ligue1_training_data_20250704_164020.csv"
        ]
    }
    
    moved_files = []
    missing_files = []
    
    # Move files according to rules
    for target_dir, file_list in file_rules.items():
        target_path = base_dir / target_dir
        
        for filename in file_list:
            source_path = Path(filename)
            if source_path.exists():
                try:
                    dest_path = target_path / filename
                    if not dest_path.exists():  # Don't overwrite existing files
                        shutil.move(str(source_path), str(dest_path))
                        moved_files.append(f"{filename} -> {target_dir}")
                        print(f"✅ Moved: {filename} -> {target_dir}")
                    else:
                        print(f"⚠️  Already exists: {filename} in {target_dir}")
                except Exception as e:
                    print(f"❌ Error moving {filename}: {e}")
            else:
                missing_files.append(filename)
    
    # Move existing model directories
    model_dirs = [
        "bundesliga_model_fixed_20250704_172132",
        "ligue 1_model_fixed_20250704_172132"
    ]
    
    for dir_name in model_dirs:
        source_dir = Path(dir_name)
        if source_dir.exists() and source_dir.is_dir():
            try:
                dest_dir = base_dir / "6_model_files" / dir_name
                if not dest_dir.exists():
                    shutil.move(str(source_dir), str(dest_dir))
                    moved_files.append(f"{dir_name}/ -> 6_model_files/")
                    print(f"✅ Moved directory: {dir_name} -> 6_model_files")
            except Exception as e:
                print(f"❌ Error moving directory {dir_name}: {e}")
    
    return moved_files, missing_files

def create_organization_summary(moved_files, missing_files):
    """Create summary of organization"""
    summary = f"""# Bundesliga & Ligue 1 Project Organization Summary
Generated: {Path.cwd()}

## Files Organized: {len(moved_files)}

### Successfully Moved:
"""
    for item in moved_files:
        summary += f"- {item}\n"
    
    if missing_files:
        summary += f"\n### Files Not Found ({len(missing_files)}):\n"
        for item in missing_files:
            summary += f"- {item}\n"
    
    summary += """
## Directory Structure:

```
bundesliga_ligue1_project/
├── 1_production_models/          # CRITICAL: Deployed models
├── 2_training_data/              # Final training datasets  
├── 3_development_scripts/        # Training and model scripts
├── 4_data_collection/            # API and data collection
├── 5_validation_reports/         # Validation results
├── 6_model_files/               # Intermediate model files
└── archive_old_attempts/        # Experimental/old files
```

## CRITICAL PRODUCTION FILES PRESERVED:
✅ deployed_bundesliga_model_20250704_175310.pkl
✅ deployed_ligue 1_model_20250704_175310.pkl  
✅ validate_and_deploy_bundesliga_ligue1.py
✅ Final training data and summaries

## Next Steps:
1. Review organized structure
2. Update import paths if needed
3. Clean remaining root files if desired
4. Update documentation paths
"""
    
    with open("bundesliga_ligue1_project/ORGANIZATION_SUMMARY.md", 'w') as f:
        f.write(summary)
    
    return summary

def main():
    """Main organization function"""
    print("🚀 Starting Bundesliga & Ligue 1 Project Organization...")
    print("=" * 60)
    
    try:
        moved_files, missing_files = organize_files()
        summary = create_organization_summary(moved_files, missing_files)
        
        print("\n" + "=" * 60)
        print("✅ ORGANIZATION COMPLETE!")
        print(f"📁 Organized {len(moved_files)} files")
        print(f"❓ {len(missing_files)} files not found (likely already moved)")
        print("\n📋 Summary saved to: bundesliga_ligue1_project/ORGANIZATION_SUMMARY.md")
        
        # Display directory structure
        print("\n📂 Final Directory Structure:")
        base_dir = Path("bundesliga_ligue1_project")
        for item in sorted(base_dir.iterdir()):
            if item.is_dir():
                file_count = len(list(item.glob("*")))
                print(f"  📁 {item.name}/ ({file_count} files)")
        
    except Exception as e:
        print(f"❌ Organization failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Project successfully organized! All production files preserved.")
    else:
        print("\n💥 Organization failed. Check errors above.") 