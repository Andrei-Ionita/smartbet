import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0044_publicselection_publicselectionresult'),
    ]

    operations = [
        migrations.CreateModel(
            name='PublicSelectionClosingPrice',
            fields=[
                ('closing_price_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('odds', models.FloatField()),
                ('bookmaker', models.CharField(blank=True, default='', max_length=64)),
                ('bookmaker_count', models.PositiveIntegerField(default=1)),
                ('odds_captured_at', models.DateTimeField()),
                ('recorded_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('source_ref', models.CharField(max_length=160)),
                ('closing_line_value', models.FloatField(help_text='Published decimal odds / closing decimal odds - 1.')),
                ('evidence_hash', models.CharField(max_length=64, unique=True)),
                ('selection', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='closing_price', to='core.publicselection')),
            ],
            options={'ordering': ['-recorded_at']},
        ),
    ]
