# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-11-30 15:08
from __future__ import unicode_literals

from django.db import migrations, models
import lots_admin.models


class Migration(migrations.Migration):

    dependencies = [
        ('lots_admin', '0027_auto_20161129_1443'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='deed_image',
            field=models.FileField(max_length=1000, upload_to=lots_admin.models.upload_name),
        ),
    ]
