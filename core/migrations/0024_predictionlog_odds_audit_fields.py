# Generated for PredictionLog data-integrity fix (Stage A of audit remediation).
# Adds:
#   - odds: bet-time odds for the predicted outcome (works for any market type)
#   - raw_expected_value: pre-clamp EV, preserved for audit
#   - is_audit_excluded: marks rows hidden from public stats due to data-quality issues

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_marketing_event_and_subscriber_metadata'),
    ]

    operations = [
        migrations.AddField(
            model_name='predictionlog',
            name='odds',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='predictionlog',
            name='raw_expected_value',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='predictionlog',
            name='is_audit_excluded',
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
