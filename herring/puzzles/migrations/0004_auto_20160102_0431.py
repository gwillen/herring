# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('puzzles', '0003_auto_20150628_2355'),
    ]

    operations = [
        migrations.AddField(
            model_name='puzzle',
            name='url',
            field=models.CharField(blank=True, max_length=1000, null=True, default=''),
        ),
        migrations.AlterField(
            model_name='puzzle',
            name='answer',
            field=models.CharField(blank=True, max_length=200, null=True, default=''),
        ),
        migrations.AlterField(
            model_name='puzzle',
            name='note',
            field=models.CharField(blank=True, max_length=200, null=True, default=''),
        ),
        migrations.AlterField(
            model_name='puzzle',
            name='tags',
            field=models.CharField(blank=True, max_length=200, null=True, default=''),
        ),
    ]
