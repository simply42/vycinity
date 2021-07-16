# Generated by Django 3.1.5 on 2021-01-21 10:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Router',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64)),
                ('loopback', models.CharField(max_length=39)),
                ('type', models.CharField(max_length=64)),
            ],
        ),
        migrations.CreateModel(
            name='StaticConfigSection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('context', models.CharField(max_length=256)),
                ('content', models.TextField()),
                ('type', models.CharField(max_length=64)),
                ('absolute', models.BooleanField()),
            ],
        ),
        migrations.CreateModel(
            name='Vyos13Router',
            fields=[
                ('router_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='vycinity.router')),
                ('token', models.CharField(max_length=256)),
            ],
            bases=('vycinity.router',),
        ),
    ]
