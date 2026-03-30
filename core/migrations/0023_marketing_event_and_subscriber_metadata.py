from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_emailsubscriber'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailsubscriber',
            name='email_platform_status',
            field=models.CharField(blank=True, default='pending', max_length=30),
        ),
        migrations.AddField(
            model_name='emailsubscriber',
            name='landing_page',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='emailsubscriber',
            name='language',
            field=models.CharField(blank=True, default='en', max_length=10),
        ),
        migrations.AddField(
            model_name='emailsubscriber',
            name='last_synced_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='emailsubscriber',
            name='league_interest',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='emailsubscriber',
            name='utm_campaign',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
        migrations.AddField(
            model_name='emailsubscriber',
            name='utm_medium',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='emailsubscriber',
            name='utm_source',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.CreateModel(
            name='MarketingEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_name', models.CharField(choices=[('email_subscribed', 'Email Subscribed'), ('welcome_sequence_started', 'Welcome Sequence Started'), ('weekly_picks_sent', 'Weekly Picks Sent'), ('email_clicked', 'Email Clicked'), ('pricing_viewed', 'Pricing Viewed'), ('paid_converted', 'Paid Converted')], db_index=True, max_length=50)),
                ('source', models.CharField(blank=True, default='', max_length=50)),
                ('page', models.CharField(blank=True, default='', max_length=255)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('subscriber', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='marketing_events', to='core.emailsubscriber')),
            ],
            options={
                'verbose_name': 'Marketing Event',
                'verbose_name_plural': 'Marketing Events',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['event_name', '-created_at'], name='core_market_event_n_42504e_idx'), models.Index(fields=['source', '-created_at'], name='core_market_source_5f85e8_idx')],
            },
        ),
    ]
