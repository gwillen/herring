# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Puzzle',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('number', models.IntegerField(default=1)),
                ('answer', models.CharField(default=b'', max_length=200, null=True, blank=True)),
                ('note', models.CharField(default=b'', max_length=200, null=True, blank=True)),
                ('tags', models.CharField(default=b'', max_length=200, null=True, blank=True)),
                ('is_meta', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Round',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.IntegerField(default=1)),
                ('name', models.CharField(max_length=200)),
            ],
        ),
        migrations.AddField(
            model_name='puzzle',
            name='parent',
            field=models.ForeignKey(to='puzzles.Round'),
        ),
    ]
