from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0037_alter_userbankroll_staking_strategy'),
    ]

    operations = [
        migrations.AddField(
            model_name='signalobservation',
            name='provider_context',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    'Pre-match provider quality context observed with the signal: '
                    'fixture predictability, league/market report card and native '
                    'value-bet payload. Stored raw so future strategies can be '
                    'evaluated without reconstructing data after kickoff.'
                ),
            ),
        ),
    ]
