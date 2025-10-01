#!/usr/bin/env python3
"""
Quick cleanup of remaining files - avoid terminal timeouts
"""

import os
import shutil
from pathlib import Path

def analyze_remaining_files():
    """Quickly analyze what's left in root directory"""
    
    # CRITICAL FILES TO NEVER TOUCH (absolute protection)
    CRITICAL_PRESERVE = {
        'LOCKED_PRODUCTION/',  # Existing production models directory
        '.env',                # API keys
        'db.sqlite3',         # Database
        'manage.py'           # Django management
    }
    
    # Files that should be moved to appropriate locations
    CLEANUP_RULES = {
        # SHAP analysis files (our recent work)
        'analysis_results': [
            'la_liga_shap_predictions.csv',
            'premier_league_shap_predictions.csv', 
            'serie_a_shap_predictions.csv',
            'premier_league_shap_predictor.py',
            'SHAP_PREDICTIONS_SUMMARY.md'
        ],
        
        # Additional LOCKED production files (move to organized structure)
        'bundesliga_ligue1_production': [
            'LOCKED_PRODUCTION_league_model_1x2_bundesliga_20250704_142204.txt',
            'LOCKED_PRODUCTION_league_model_1x2_bundesliga_20250704_142323.txt', 
            'LOCKED_PRODUCTION_league_model_1x2_bundesliga_20250704_142533.txt',
            'LOCKED_PRODUCTION_league_model_1x2_liga_1_20250704_142533.txt',
            'LOCKED_PRODUCTION_league_model_1x2_ligue_1_20250704_142533.txt'
        ],
        
        # Project documentation
        'documentation_files': [
            'API_SECURITY_CLEANUP_SUMMARY.md'
        ],
        
        # Scripts to keep in root (organizational)
        'utility_scripts': [
            'organize_project.py',
            'cleanup_remaining_files.py'
        ]
    }
    
    print("🔍 ANALYZING REMAINING FILES...")
    print("=" * 50)
    
    # Get all files in root
    all_files = []
    all_dirs = []
    
    for item in Path('.').iterdir():
        if item.name.startswith('.'):
            continue
        if item.is_file():
            all_files.append(item.name)
        elif item.is_dir():
            all_dirs.append(item.name + '/')
    
    # Categorize files
    protected_files = []
    files_to_move = []
    unknown_files = []
    
    for file in all_files:
        if any(file.startswith(p.rstrip('/')) for p in CRITICAL_PRESERVE):
            protected_files.append(file)
        else:
            # Check if file matches any cleanup rule
            moved = False
            for category, file_list in CLEANUP_RULES.items():
                if file in file_list:
                    files_to_move.append((file, category))
                    moved = True
                    break
            if not moved:
                unknown_files.append(file)
    
    # Check directories
    protected_dirs = []
    for dir in all_dirs:
        if any(dir.startswith(p) for p in CRITICAL_PRESERVE):
            protected_dirs.append(dir)
    
    # Print analysis
    print(f"📁 DIRECTORIES ({len(all_dirs)}):")
    for d in sorted(all_dirs):
        status = "🔒 PROTECTED" if d in protected_dirs else "✅ OK"
        print(f"  {status}: {d}")
    
    print(f"\n📄 FILES ANALYSIS:")
    print(f"  🔒 PROTECTED: {len(protected_files)} files")
    print(f"  📦 TO ORGANIZE: {len(files_to_move)} files")
    print(f"  ❓ UNKNOWN: {len(unknown_files)} files")
    
    if protected_files:
        print(f"\n🔒 PROTECTED FILES (NEVER TOUCH):")
        for f in protected_files:
            print(f"  - {f}")
    
    if files_to_move:
        print(f"\n📦 FILES TO ORGANIZE:")
        for f, cat in files_to_move:
            print(f"  - {f} -> {cat}")
    
    if unknown_files:
        print(f"\n❓ UNKNOWN FILES (need manual review):")
        for f in unknown_files:
            print(f"  - {f}")
    
    return files_to_move, unknown_files, protected_files

def perform_cleanup(files_to_move):
    """Safely move files to organized locations"""
    
    # Create target directories
    targets = {
        'analysis_results': Path('bundesliga_ligue1_project/analysis_results'),
        'bundesliga_ligue1_production': Path('bundesliga_ligue1_project/1_production_models'),
        'documentation_files': Path('documentation'),
        'utility_scripts': Path('scripts')  # Keep utility scripts organized
    }
    
    moved_count = 0
    
    for target_path in targets.values():
        target_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n🚀 PERFORMING CLEANUP...")
    print("-" * 30)
    
    for file, category in files_to_move:
        source = Path(file)
        target_dir = targets[category]
        target = target_dir / file
        
        try:
            if source.exists() and not target.exists():
                shutil.move(str(source), str(target))
                print(f"✅ Moved: {file} -> {category}/")
                moved_count += 1
            elif target.exists():
                print(f"⚠️  Exists: {file} already in {category}/")
            else:
                print(f"❌ Missing: {file} not found")
        except Exception as e:
            print(f"❌ Error moving {file}: {e}")
    
    return moved_count

def main():
    """Main cleanup function"""
    print("🧹 SMARTBET PROJECT CLEANUP")
    print("=" * 50)
    
    # Analyze first
    files_to_move, unknown_files, protected_files = analyze_remaining_files()
    
    # Perform cleanup if there are files to move
    if files_to_move:
        moved_count = perform_cleanup(files_to_move)
        print(f"\n✅ CLEANUP COMPLETE!")
        print(f"📦 Moved {moved_count} files")
    else:
        print(f"\n✅ NO CLEANUP NEEDED!")
    
    # Final summary
    print(f"\n📋 FINAL STATUS:")
    print(f"  🔒 {len(protected_files)} critical files preserved") 
    print(f"  ❓ {len(unknown_files)} files need manual review")
    
    if unknown_files:
        print(f"\n⚠️  MANUAL REVIEW NEEDED for:")
        for f in unknown_files:
            print(f"  - {f}")
        print(f"\nThese files were not moved automatically for safety.")
    
    return True

if __name__ == "__main__":
    main() 