from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='match',
            name='avg_cards_away',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='avg_cards_home',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='avg_goals_away',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='avg_goals_home',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='injured_starters_away',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='injured_starters_home',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='team_form_away',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='team_form_home',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='oddssnapshot',
            name='closing_odds_away',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='oddssnapshot',
            name='closing_odds_draw',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='oddssnapshot',
            name='closing_odds_home',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='oddssnapshot',
            name='opening_odds_away',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='oddssnapshot',
            name='opening_odds_draw',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='oddssnapshot',
            name='opening_odds_home',
            field=models.FloatField(blank=True, null=True),
        ),
    ] 