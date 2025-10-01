from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_matchscoremodel_expected_value'),
    ]

    operations = [
        migrations.RenameField(
            model_name='match',
            old_name='home_goals',
            new_name='home_score',
        ),
        migrations.RenameField(
            model_name='match',
            old_name='away_goals',
            new_name='away_score',
        ),
    ] 