# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('puzzles', '0002_auto_20150628_2350'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='round',
            options={'ordering': ['number']},
        ),
    ]
