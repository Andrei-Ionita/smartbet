from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_rename_match_score_fields'),
        ('core', 'custom_migration'),
    ]

    operations = [
        # Merge migration - no operations
    ] 