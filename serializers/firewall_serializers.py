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
from uuid import UUID
from vycinity.models import customer_models, firewall_models, network_models

class OwnedObjectRelatedField(serializers.RelatedField):
    '''
    A custom related field relating uuid of owned objects. Normally a SlugRelatedField would do
    what we want, but it does not serialize UUIDs correctly.
    '''

    def to_representation(self, value):
        return str(value.uuid)

    def to_internal_value(self, data):
        try:
            uuid = UUID(data)
            result = self.get_queryset().filter(uuid=uuid).order_by('-pk').first()
            if result is None:
                serializers.ValidationError(['Referenced object not found.'])
            return result
        except ValueError as e:
            raise serializers.ValidationError(['Reference UUID is not valid.'])

class FirewallSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.Firewall
        fields = ['uuid', 'owner', 'stateful', 'name', 'network', 'default_action_into', 'default_action_from', 'public']
        read_only_fields = ['uuid']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)
    network = OwnedObjectRelatedField(queryset=firewall_models.Firewall.objects.all(), required=False)

class RuleSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.RuleSet
        fields = ['uuid', 'owner', 'priority', 'firewalls', 'comment', 'public']
        read_only_fields = ['uuid']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)
    firewalls = OwnedObjectRelatedField(many=True, queryset=firewall_models.Firewall.objects.all(), required=False)

class RuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.Rule
        fields = ['uuid', 'ruleset', 'priority', 'comment', 'disable']
        read_only_fields = ['uuid']
    ruleset = OwnedObjectRelatedField(queryset=firewall_models.RuleSet.objects.all(), required=True)

class AddressObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.AddressObject
        fields = ['uuid', 'name', 'owner', 'public']
        read_only_fields = ['uuid']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)

class ServiceObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.ServiceObject
        fields = ['uuid', 'name', 'owner', 'public']
        read_only_fields = ['uuid']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)

class BasicRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.BasicRule
        fields = ['uuid', 'ruleset', 'priority', 'comment', 'disable', 'source_address', 'destination_address', 'destination_service', 'action', 'log']
        read_only_fields = ['uuid']
    ruleset = OwnedObjectRelatedField(source='related_ruleset', queryset=firewall_models.RuleSet.objects.all(), required=True)
    source_address = OwnedObjectRelatedField(queryset=firewall_models.AddressObject.objects.all(), required=False)
    destination_address = OwnedObjectRelatedField(queryset=firewall_models.AddressObject.objects.all(), required=True)
    destination_service = OwnedObjectRelatedField(queryset=firewall_models.ServiceObject.objects.all(), required=False)

class CustomRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.CustomRule
        fields = ['id', 'ruleset', 'priority', 'comment', 'disable', 'ip_version', 'rule']
        read_only_fields = ['id']
    ruleset = OwnedObjectRelatedField(queryset=firewall_models.RuleSet.objects.all(), required=True)

class NetworkAddressObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.NetworkAddressObject
        fields = ['uuid', 'name', 'owner', 'public', 'network']
        read_only_fields = ['uuid']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)
    network = OwnedObjectRelatedField(queryset=network_models.Network.objects.all(), required=True)

class CIDRAddressObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.CIDRAddressObject
        fields = ['uuid', 'name', 'owner', 'public', 'ipv6_network_address', 'ipv6_network_bits', 'ipv4_network_address', 'ipv4_network_bits']
        read_only_fields = ['uuid']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)

class HostAddressObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.HostAddressObject
        fields = ['uuid', 'name', 'owner', 'public', 'ipv6_address', 'ipv4_address']
        read_only_fields = ['uuid']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)

class ListAddressObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.ListAddressObject
        fields = ['uuid', 'name', 'owner', 'public', 'elements']
        read_only_fields = ['uuid']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)
    elements = OwnedObjectRelatedField(many=True, queryset=firewall_models.AddressObject.objects.all(), required=False)

class SimpleServiceObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.SimpleServiceObject
        fields = ['uuid', 'name', 'owner', 'public', 'protocol', 'port']
        read_only_fields = ['uuid']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)

class ListServiceObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.ListServiceObject
        fields = ['uuid', 'name', 'owner', 'public', 'elements']
        read_only_fields = ['uuid']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)
    elements = OwnedObjectRelatedField(many=True, queryset=firewall_models.ServiceObject.objects.all(), required=False)

class RangeServiceObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.RangeServiceObject
        fields = ['uuid', 'name', 'owner', 'public', 'protocol', 'start_port', 'end_port']
        read_only_fields = ['uuid']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)