# Generated by Django 3.0.2 on 2020-12-17 23:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('puzzles', '0014_auto_20201126_0504'),
    ]

    operations = [
        migrations.AddField(
            model_name='channelparticipation',
            name='display_name',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
