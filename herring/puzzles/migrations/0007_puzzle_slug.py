# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import puzzles.slugtools
import autoslug.fields


class Migration(migrations.Migration):

    dependencies = [
        ('puzzles', '0006_auto_20160110_2158'),
    ]

    operations = [
        migrations.AddField(
            model_name='puzzle',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=puzzles.slugtools.puzzle_to_slug, unique=True, editable=True),
        ),
    ]
