# Generated by Django 3.1.7 on 2021-03-30 14:51

from django.db import migrations, models
import django.db.models.deletion
import vycinity.models.firewall_models
import vycinity.models.network_models


class Migration(migrations.Migration):

    dependencies = [
        ('vycinity', '0012_network_vrrp_password'),
    ]

    operations = [
        migrations.CreateModel(
            name='AddressObject',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=64)),
                ('public', models.BooleanField()),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vycinity.customer')),
            ],
        ),
        migrations.CreateModel(
            name='Firewall',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('stateful', models.BooleanField()),
                ('name', models.CharField(max_length=64)),
                ('default_action', models.CharField(choices=[('accept', 'accept'), ('drop', 'drop'), ('reject', 'reject')], max_length=16)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vycinity.customer')),
            ],
        ),
        migrations.CreateModel(
            name='Rule',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('priority', models.IntegerField(validators=[vycinity.models.firewall_models.validate_priority_rule])),
                ('comment', models.TextField(null=True)),
                ('disable', models.BooleanField()),
            ],
        ),
        migrations.CreateModel(
            name='ServiceObject',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=64)),
                ('public', models.BooleanField()),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vycinity.customer')),
            ],
        ),
        migrations.CreateModel(
            name='CIDRAddressObject',
            fields=[
                ('addressobject_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='vycinity.addressobject')),
                ('ipv6_network_address', models.GenericIPAddressField(null=True, protocol='IPv6')),
                ('ipv6_network_bits', models.IntegerField(null=True, validators=[vycinity.models.network_models.validate_ipv6_network_bits])),
                ('ipv4_network_address', models.GenericIPAddressField(null=True, protocol='IPv4')),
                ('ipv4_network_bits', models.IntegerField(null=True, validators=[vycinity.models.network_models.validate_ipv4_network_bits])),
            ],
            bases=('vycinity.addressobject',),
        ),
        migrations.CreateModel(
            name='CustomRule',
            fields=[
                ('rule_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='vycinity.rule')),
                ('ip_version', models.IntegerField(choices=[(4, 'IPv4'), (6, 'IPv6')])),
                ('rule', models.JSONField()),
            ],
            bases=('vycinity.rule',),
        ),
        migrations.CreateModel(
            name='HostAddressObject',
            fields=[
                ('addressobject_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='vycinity.addressobject')),
                ('ipv6_address', models.GenericIPAddressField(null=True, protocol='IPv6')),
                ('ipv4_address', models.GenericIPAddressField(null=True, protocol='IPv4')),
            ],
            bases=('vycinity.addressobject',),
        ),
        migrations.CreateModel(
            name='RangeServiceObject',
            fields=[
                ('serviceobject_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='vycinity.serviceobject')),
                ('protocol', models.CharField(max_length=16)),
                ('start_port', models.IntegerField(validators=[vycinity.models.firewall_models.validate_port_simpleserviceobject])),
                ('end_port', models.IntegerField(validators=[vycinity.models.firewall_models.validate_port_simpleserviceobject])),
            ],
            bases=('vycinity.serviceobject',),
        ),
        migrations.CreateModel(
            name='SimpleServiceObject',
            fields=[
                ('serviceobject_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='vycinity.serviceobject')),
                ('protocol', models.CharField(max_length=16)),
                ('port', models.IntegerField(validators=[vycinity.models.firewall_models.validate_port_simpleserviceobject])),
            ],
            bases=('vycinity.serviceobject',),
        ),
        migrations.CreateModel(
            name='RuleSet',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('priority', models.IntegerField(validators=[vycinity.models.firewall_models.validate_priority_rule])),
                ('comment', models.TextField(null=True)),
                ('firewalls', models.ManyToManyField(to='vycinity.Firewall')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vycinity.customer')),
            ],
        ),
        migrations.AddField(
            model_name='rule',
            name='ruleset',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vycinity.ruleset'),
        ),
        migrations.CreateModel(
            name='StandardRule',
            fields=[
                ('rule_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='vycinity.rule')),
                ('action', models.CharField(choices=[('accept', 'accept'), ('drop', 'drop'), ('reject', 'reject')], max_length=16)),
                ('log', models.BooleanField()),
                ('destination_address', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='vycinity.addressobject')),
                ('destination_service', models.ForeignKey(null=True, on_delete=django.db.models.deletion.RESTRICT, to='vycinity.serviceobject')),
                ('source_address', models.ForeignKey(null=True, on_delete=django.db.models.deletion.RESTRICT, to='vycinity.addressobject')),
            ],
            bases=('vycinity.rule',),
        ),
        migrations.CreateModel(
            name='NetworkAddressObject',
            fields=[
                ('addressobject_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='vycinity.addressobject')),
                ('network', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vycinity.network')),
            ],
            bases=('vycinity.addressobject',),
        ),
        migrations.CreateModel(
            name='ListServiceObject',
            fields=[
                ('serviceobject_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='vycinity.serviceobject')),
                ('elements', models.ManyToManyField(to='vycinity.ServiceObject')),
            ],
            bases=('vycinity.serviceobject',),
        ),
        migrations.CreateModel(
            name='ListAddressObject',
            fields=[
                ('addressobject_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='vycinity.addressobject')),
                ('elements', models.ManyToManyField(to='vycinity.AddressObject')),
            ],
            bases=('vycinity.addressobject',),
        ),
    ]
