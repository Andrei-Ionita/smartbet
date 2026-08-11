from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0038_signalobservation_provider_context'),
    ]

    operations = [
        migrations.CreateModel(
            name='FixtureContextObservation',
            fields=[
                ('observation_id', models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ('ingestion_run_id', models.CharField(db_index=True, max_length=64)),
                ('source_payload_hash', models.CharField(max_length=64, unique=True)),
                ('fixture_id', models.IntegerField(db_index=True)),
                ('home_team', models.CharField(max_length=100)),
                ('away_team', models.CharField(max_length=100)),
                ('league', models.CharField(blank=True, default='', max_length=100)),
                ('league_id', models.IntegerField(blank=True, null=True)),
                ('kickoff', models.DateTimeField(db_index=True)),
                ('observed_at', models.DateTimeField(db_index=True)),
                ('hours_to_kickoff', models.FloatField()),
                ('fixture_predictable', models.BooleanField(blank=True, null=True)),
                ('lineup_status', models.CharField(choices=[('confirmed', 'Confirmed'), ('available_unconfirmed', 'Available, not confirmed'), ('unavailable', 'Unavailable')], default='unavailable', max_length=24)),
                ('home_formation', models.CharField(blank=True, default='', max_length=32)),
                ('away_formation', models.CharField(blank=True, default='', max_length=32)),
                ('home_form', models.CharField(blank=True, default='', max_length=20)),
                ('away_form', models.CharField(blank=True, default='', max_length=20)),
                ('home_sidelined_count', models.PositiveSmallIntegerField(default=0)),
                ('away_sidelined_count', models.PositiveSmallIntegerField(default=0)),
                ('sidelined', models.JSONField(blank=True, default=list)),
                ('lineups', models.JSONField(blank=True, default=list)),
                ('referees', models.JSONField(blank=True, default=list)),
                ('venue', models.JSONField(blank=True, null=True)),
                ('neutral_venue', models.BooleanField(blank=True, null=True)),
                ('data_availability', models.JSONField(blank=True, default=dict)),
                ('provider', models.CharField(default='sportmonks', max_length=32)),
                ('calculation_version', models.CharField(blank=True, default='', max_length=80)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Fixture Context Observation',
                'ordering': ['-observed_at'],
                'indexes': [
                    models.Index(fields=['fixture_id', 'observed_at'], name='core_fixtur_fixture_7571d1_idx'),
                    models.Index(fields=['kickoff'], name='core_fixtur_kickoff_d4019a_idx'),
                    models.Index(fields=['ingestion_run_id'], name='core_fixtur_ingesti_e65ded_idx'),
                ],
            },
        ),
    ]
