# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import puzzles.slugtools
import autoslug.fields


class Migration(migrations.Migration):

    dependencies = [
        ('puzzles', '0010_auto_20200115_0730'),
    ]

    operations = [
        migrations.AddField(
            model_name='round',
            name='hunt_id',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='puzzle',
            name='hunt_id',
            field=models.IntegerField(default=0),
        ),
    ]
