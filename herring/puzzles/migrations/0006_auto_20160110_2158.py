# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('puzzles', '0005_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='puzzle',
            name='hunt_url',
            field=models.CharField(null=True, blank=True, default='', max_length=1000),
        ),
        migrations.AddField(
            model_name='round',
            name='hunt_url',
            field=models.CharField(null=True, blank=True, default='', max_length=1000),
        ),
    ]
