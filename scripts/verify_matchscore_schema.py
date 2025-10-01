#!/usr/bin/env python
"""
Script to verify that the MatchScore model is properly migrated and available in the database.
This script checks if the model exists and if all required fields are present.

Usage:
    python manage.py shell < scripts/verify_matchscore_schema.py
    or
    python manage.py shell -c "from scripts.verify_matchscore_schema import verify_matchscore_schema; verify_matchscore_schema()"
"""

import os
import sys
import django

# Set up Django environment if running as standalone script
if __name__ == "__main__" and "DJANGO_SETTINGS_MODULE" not in os.environ:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartbet.settings")
    django.setup()

from django.db import connection
from django.apps import apps

# Fields that should be present in the MatchScore model
REQUIRED_FIELDS = [
    "fixture_id",
    "match",  # ForeignKey
    "home_team_score",
    "away_team_score",
    "confidence_level",
    "recommended_bet",
    "predicted_outcome",
    "generated_at",
    "source"
]

def verify_matchscore_schema():
    """Verify that the MatchScore model is properly migrated and available in the database."""
    print("Verifying MatchScore model schema...")
    
    # Try to get the model
    try:
        # Check if the model exists as MatchScore
        try:
            MatchScore = apps.get_model("core", "MatchScore")
            model_name = "MatchScore"
        except LookupError:
            # Try with alternative name MatchScoreModel
            try:
                MatchScore = apps.get_model("core", "MatchScoreModel")
                model_name = "MatchScoreModel"
            except LookupError:
                print("❌ MatchScore table not found in DB.")
                return False
    
        # Get the actual table name
        table_name = MatchScore._meta.db_table
        print(f"Found model: {model_name}, table: {table_name}")
        
        # Get all fields from model
        model_fields = {f.name: f for f in MatchScore._meta.get_fields()}
        print(f"Model has {len(model_fields)} fields")
        print(f"Model fields: {', '.join(model_fields.keys())}")
        
        # Check if the table exists in the database
        with connection.cursor() as cursor:
            introspection = connection.introspection
            
            # Check if table exists
            all_tables = introspection.table_names(cursor)
            if table_name not in all_tables:
                print(f"❌ Table '{table_name}' does not exist in the database.")
                return False
                
            # Get columns from the database
            db_columns = {col.name: col for col in introspection.get_table_description(cursor, table_name)}
            print(f"Database table has {len(db_columns)} columns")
            print(f"Database columns: {', '.join(db_columns.keys())}")
            
            # For foreign keys, we need to find the actual column name
            fk_relations = introspection.get_relations(cursor, table_name)
            
            # Verify each required field exists in the database
            missing_fields = []
            for field_name in REQUIRED_FIELDS:
                field_found = False
                
                # Direct field match
                if field_name in db_columns:
                    field_found = True
                    print(f"✓ Field '{field_name}' exists in the database")
                    
                # Foreign key fields may have _id suffix
                elif field_name in model_fields and model_fields[field_name].is_relation:
                    # Check if the relation column exists (usually with _id suffix)
                    relation_name = f"{field_name}_id"
                    if relation_name in db_columns:
                        field_found = True
                        print(f"✓ Relation field '{field_name}' exists as '{relation_name}' in the database")
                
                if not field_found:
                    missing_fields.append(field_name)
                    print(f"❌ Missing field: {field_name}")
            
            if missing_fields:
                print(f"\n❌ The following fields are missing from the database: {', '.join(missing_fields)}")
                return False
            else:
                print("\n✅ MatchScore model is in sync with the DB schema.")
                return True
                
    except Exception as e:
        print(f"\n❌ Error verifying database schema: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    verify_matchscore_schema() 