# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-27 14:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lots_admin', '0020_address_ward'),
    ]

    operations = [
        migrations.AlterField(
            model_name='address',
            name='ward',
            field=models.CharField(max_length=10),
        ),
    ]