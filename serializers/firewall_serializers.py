# This file is part of VyCinity.
# 
# VyCinity is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
# 
# VyCinity is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with VyCinity. If not, see <https://www.gnu.org/licenses/>.

from rest_framework import serializers
from vycinity.models import customer_models, firewall_models, network_models

class FirewallSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.Firewall
        fields = ['id', 'owner', 'stateful', 'name', 'network', 'default_action_into', 'default_action_from', 'public']
        read_only_fields = ['id']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)

class RuleSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.RuleSet
        fields = ['id', 'owner', 'priority', 'firewalls', 'comment', 'public']
        read_only_fields = ['id']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)
    firewalls = serializers.PrimaryKeyRelatedField(many=True, queryset=firewall_models.Firewall.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=False)

class RuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.Rule
        fields = ['id', 'ruleset', 'priority', 'comment', 'disable']
        read_only_fields = ['id']
    ruleset = serializers.PrimaryKeyRelatedField(queryset=firewall_models.RuleSet.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)

class AddressObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.AddressObject
        fields = ['id', 'name', 'owner', 'public']
        read_only_fields = ['id']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)

class ServiceObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.ServiceObject
        fields = ['id', 'name', 'owner', 'public']
        read_only_fields = ['id']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)

class BasicRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.BasicRule
        fields = ['id', 'ruleset', 'priority', 'comment', 'disable', 'source_address', 'destination_address', 'destination_service', 'action', 'log']
        read_only_fields = ['id']
    ruleset = serializers.PrimaryKeyRelatedField(queryset=firewall_models.RuleSet.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)
    source_address = serializers.PrimaryKeyRelatedField(queryset=firewall_models.AddressObject.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)
    destination_address = serializers.PrimaryKeyRelatedField(queryset=firewall_models.AddressObject.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)
    destination_service = serializers.PrimaryKeyRelatedField(queryset=firewall_models.ServiceObject.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)

class CustomRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.CustomRule
        fields = ['id', 'ruleset', 'priority', 'comment', 'disable', 'ip_version', 'rule']
        read_only_fields = ['id']
    ruleset = serializers.PrimaryKeyRelatedField(queryset=firewall_models.RuleSet.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)

class NetworkAddressObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.NetworkAddressObject
        fields = ['id', 'name', 'owner', 'public', 'network']
        read_only_fields = ['id']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)
    network = serializers.PrimaryKeyRelatedField(queryset=network_models.Network.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)

class CIDRAddressObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.CIDRAddressObject
        fields = ['id', 'name', 'owner', 'public', 'ipv6_network_address', 'ipv6_network_bits', 'ipv4_network_address', 'ipv4_network_bits']
        read_only_fields = ['id']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)

class HostAddressObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.HostAddressObject
        fields = ['id', 'name', 'owner', 'public', 'ipv6_address', 'ipv4_address']
        read_only_fields = ['id']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)

class ListAddressObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.ListAddressObject
        fields = ['id', 'name', 'owner', 'public', 'elements']
        read_only_fields = ['id']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)
    elements = serializers.PrimaryKeyRelatedField(many=True, queryset=firewall_models.AddressObject.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=False)

class SimpleServiceObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.SimpleServiceObject
        fields = ['id', 'name', 'owner', 'public', 'protocol', 'port']
        read_only_fields = ['id']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)

class ListServiceObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.ListServiceObject
        fields = ['id', 'name', 'owner', 'public', 'elements']
        read_only_fields = ['id']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)
    elements = serializers.PrimaryKeyRelatedField(many=True, queryset=firewall_models.ServiceObject.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=False)

class RangeServiceObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.RangeServiceObject
        fields = ['id', 'name', 'owner', 'public', 'protocol', 'start_port', 'end_port']
        read_only_fields = ['id']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)