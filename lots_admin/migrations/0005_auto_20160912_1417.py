# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-12 19:17
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lots_admin', '0004_auto_20160912_1411'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='status',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='lots_admin.ApplicationStatus'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='applicationstatus',
            name='review_status',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='lots_admin.ReviewStatus'),
        ),
    ]
