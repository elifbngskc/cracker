# Generated by Django 5.2 on 2025-04-28 11:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='goal',
            field=models.CharField(choices=[('maintain', 'Maintain'), ('lose', 'Lose weight'), ('gain', 'Gain weight')], default='maintain', max_length=10),
        ),
    ]
