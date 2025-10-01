from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_matchscoremodel_expected_value'),  # Updated to the latest migration
    ]

    operations = [
        # Create MatchMetadata model
        migrations.CreateModel(
            name='MatchMetadata',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('match', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='metadata', to='core.match')),
            ],
            options={
                'verbose_name': 'Match Metadata',
                'verbose_name_plural': 'Match Metadata',
            },
        ),
    ] 