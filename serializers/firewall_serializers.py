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

from rest_framework import serializers, relations
from rest_framework.request import Request
from uuid import UUID
from vycinity.models import OWNED_OBJECT_STATE_LIVE, AbstractOwnedObject, OwnedObject, customer_models, firewall_models, network_models, change_models
from vycinity.serializers.generics import BaseOwnedObjectSerializer

class ManyWithoutNoneRelatedField(serializers.ManyRelatedField):
    def to_representation(self, iterable):
        return filter(lambda i: i is not None, [
            self.child_relation.to_representation(value) # type: ignore
            for value in iterable
        ])


class OwnedObjectRelatedField(serializers.RelatedField):
    '''
    A custom related field relating uuid of owned objects. Normally a SlugRelatedField would do
    what we want, but it does not serialize UUIDs correctly.
    '''

    def __init__(self, **kwargs):
        self.model: OwnedObject = kwargs.pop('model')
        if self.model is None:
            raise AssertionError('OwnedObjectRelatedField requires an AbstractOwnedObject as model, but got None')
        super().__init__(**kwargs)

    @classmethod
    def many_init(cls, *args, **kwargs):
        list_kwargs = {'child_relation': cls(*args, **kwargs)}
        for key in kwargs:
            if key in relations.MANY_RELATION_KWARGS:
                list_kwargs[key] = kwargs[key]
        return ManyWithoutNoneRelatedField(**list_kwargs)

    def get_queryset(self):
        return self.model.objects.all()

    def to_representation(self, value):
        if self.parent is None or not hasattr(self.parent, 'context') or self.parent.context is None:
            raise AssertionError('Parent Field or serializer is not set properly but required for it\'s context.')
        request = self.parent.context.get('request', None)
        if not isinstance(request, Request):
            raise AssertionError('Request is not set in context.')
        if not isinstance(request.user, customer_models.User):
            raise AssertionError('Related field requires an internal user for verifiying the visibility.')

        if value.public or value.owner in request.user.customer.get_visible_customers():
            return str(value.uuid)
        else:
            return None

    def to_internal_value(self, data):
        if self.parent is None or not hasattr(self.parent, 'context') or self.parent.context is None:
            raise AssertionError('Parent Field or serializer is not set properly but required for it\'s context.')
        request = self.parent.context.get('request', None)
        if not isinstance(request, Request):
            raise AssertionError('Request is not set in context.')
        if not isinstance(request.user, customer_models.User):
            raise AssertionError('Related field requires an internal user for verifiying the visibility.')
        try:

            uuid = UUID(data)

            result = None
            visible_customers = request.user.customer.get_visible_customers()
            if 'changeset' in request.query_params:
                changeset_uuid = UUID(request.query_params['changeset'])
                try:
                    changeset = change_models.ChangeSet.objects.get(pk=changeset_uuid)
                    result = self.model.filter_by_changeset_and_visibility(self.get_queryset().filter(uuid=uuid), changeset=changeset, visible_customers=visible_customers).order_by('-pk').first()
                except change_models.ChangeSet.DoesNotExist:
                    pass
            else:
                result = self.model.filter_query_by_customers_or_public(self.get_queryset().filter(uuid=uuid, state=OWNED_OBJECT_STATE_LIVE), visible_customers).order_by('-pk').first()
            if result is None:
                raise serializers.ValidationError(['Referenced object not found.'])
            return result
        except ValueError as e:
            raise serializers.ValidationError(['Reference UUID is not valid.'])

#def check_access_linked_object(linked_o)

class FirewallSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.Firewall
        fields = ['uuid', 'owner', 'stateful', 'name', 'related_network', 'default_action_into', 'default_action_from', 'public']
        read_only_fields = ['uuid']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)
    related_network = OwnedObjectRelatedField(model=network_models.Network, required=False)

class RuleSetSerializer(BaseOwnedObjectSerializer):
    class Meta:
        model = firewall_models.RuleSet
        fields = BaseOwnedObjectSerializer.Meta.fields + ['owner', 'priority', 'firewalls', 'comment', 'public']
        read_only_fields = BaseOwnedObjectSerializer.Meta.read_only_fields
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)
    firewalls = OwnedObjectRelatedField(many=True, model=firewall_models.Firewall, required=False)

    def validate(self, data):
        if 'firewalls' in data:
            for firewall in data['firewalls']:
                if (not firewall.public) and firewall.owner not in data['owner'].get_visible_customers():
                    raise serializers.ValidationError({'firewalls': ['Referenced object not found.']})
        return data

class RuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.Rule
        fields = ['uuid', 'related_ruleset', 'priority', 'comment', 'disable']
        read_only_fields = ['uuid']
    related_ruleset = OwnedObjectRelatedField(model=firewall_models.RuleSet, required=True)

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
        fields = ['uuid', 'related_ruleset', 'priority', 'comment', 'disable', 'source_address', 'destination_address', 'destination_service', 'action', 'log']
        read_only_fields = ['uuid']
    related_ruleset = OwnedObjectRelatedField(model=firewall_models.RuleSet, required=True)
    source_address = OwnedObjectRelatedField(model=firewall_models.AddressObject, required=False)
    destination_address = OwnedObjectRelatedField(model=firewall_models.AddressObject, required=True)
    destination_service = OwnedObjectRelatedField(model=firewall_models.ServiceObject, required=False)

class CustomRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.CustomRule
        fields = ['id', 'related_ruleset', 'priority', 'comment', 'disable', 'ip_version', 'rule']
        read_only_fields = ['id']
    related_ruleset = OwnedObjectRelatedField(model=firewall_models.RuleSet, required=True)

class NetworkAddressObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.NetworkAddressObject
        fields = ['uuid', 'name', 'owner', 'public', 'related_network']
        read_only_fields = ['uuid']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)
    related_network = OwnedObjectRelatedField(model=network_models.Network, required=True)

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
    elements = OwnedObjectRelatedField(many=True, model=firewall_models.AddressObject, required=False)

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
    elements = OwnedObjectRelatedField(many=True, model=firewall_models.ServiceObject, required=False)

class RangeServiceObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = firewall_models.RangeServiceObject
        fields = ['uuid', 'name', 'owner', 'public', 'protocol', 'start_port', 'end_port']
        read_only_fields = ['uuid']
    owner = serializers.PrimaryKeyRelatedField(queryset=customer_models.Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)