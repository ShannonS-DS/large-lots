# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-11-29 15:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lots_admin', '0024_auto_20160927_1639'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lot',
            name='planned_use',
            field=models.CharField(default=None, max_length=500, null=True),
        ),
    ]
