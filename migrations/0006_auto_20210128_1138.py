# Generated by Django 3.1.5 on 2021-01-28 11:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vycinity', '0005_deployment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='deployment',
            name='state',
            field=models.CharField(choices=[('preparation', 'preparation'), ('running', 'running'), ('failed', 'failed'), ('succeed', 'succeed')], max_length=32),
        ),
    ]
