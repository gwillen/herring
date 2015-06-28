# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('puzzles', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='puzzle',
            options={'ordering': ['parent', '-is_meta', 'number']},
        ),
        migrations.AlterField(
            model_name='puzzle',
            name='number',
            field=models.IntegerField(null=True, blank=True),
        ),
    ]
