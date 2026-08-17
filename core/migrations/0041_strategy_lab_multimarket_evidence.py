import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0040_strategylabexperiment_strategylabobservation_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='strategylabobservation',
            name='evidence_phase',
            field=models.CharField(
                choices=[
                    ('retrospective', 'Retrospective backtest'),
                    ('forward', 'Forward validation'),
                ],
                db_index=True,
                default='forward',
                help_text=(
                    'Retrospective rows may reject a strategy but can never '
                    'make it eligible for public promotion.'
                ),
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='strategylabobservation',
            name='selection_payload',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    'Market-specific inputs needed to reproduce selection and '
                    'settlement.'
                ),
            ),
        ),
        migrations.AddField(
            model_name='strategylabobservation',
            name='source_signal',
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    'Exact immutable signal row that produced this candidate. '
                    'Null only for specialist candidates such as Asian Handicap.'
                ),
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='strategy_lab_observations',
                to='core.signalobservation',
            ),
        ),
        migrations.AlterField(
            model_name='strategylabobservation',
            name='handicap',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='strategylabobservation',
            name='side',
            field=models.CharField(max_length=32),
        ),
    ]
