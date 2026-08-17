from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0038_signalobservation_provider_context'),
    ]

    operations = [
        migrations.CreateModel(
            name='GemFeedCache',
            fields=[
                (
                    'key',
                    models.CharField(
                        default='current',
                        editable=False,
                        max_length=16,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ('payload', models.JSONField(default=dict)),
                ('generated_at', models.DateTimeField(db_index=True)),
                ('refreshed_at', models.DateTimeField(auto_now=True)),
                (
                    'ranking_version',
                    models.CharField(blank=True, max_length=128, null=True),
                ),
                ('recommendation_count', models.PositiveIntegerField(default=0)),
            ],
            options={'verbose_name': 'Gem feed cache'},
        ),
    ]
