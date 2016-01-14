# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autoslug.fields
import puzzles.slugtools


class Migration(migrations.Migration):

    dependencies = [
        ('puzzles', '0007_puzzle_slug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='puzzle',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=puzzles.slugtools.puzzle_to_slug, editable=False, unique=True),
        ),
    ]
