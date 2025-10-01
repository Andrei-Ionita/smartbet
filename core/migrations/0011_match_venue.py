from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='match',
            name='venue',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ] 