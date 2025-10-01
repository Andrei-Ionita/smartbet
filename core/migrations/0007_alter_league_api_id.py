from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_alter_prediction_unique_together_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='league',
            name='api_id',
            field=models.IntegerField(blank=True, null=True),
        ),
    ] 