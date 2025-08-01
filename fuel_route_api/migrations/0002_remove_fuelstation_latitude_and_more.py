# Generated by Django 5.2.4 on 2025-07-26 23:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fuel_route_api', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='fuelstation',
            name='latitude',
        ),
        migrations.RemoveField(
            model_name='fuelstation',
            name='location',
        ),
        migrations.RemoveField(
            model_name='fuelstation',
            name='longitude',
        ),
        migrations.AlterField(
            model_name='fuelstation',
            name='retail_price',
            field=models.DecimalField(decimal_places=3, max_digits=5),
        ),
    ]
