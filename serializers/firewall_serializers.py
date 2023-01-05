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
from vycinity.models import OWNED_OBJECT_STATE_LIVE, OwnedObject, customer_models, firewall_models, network_models, change_models
from vycinity.serializers.generics import AbstractOwnedObjectSerializer, BaseOwnedObjectSerializer

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

class FirewallSerializer(BaseOwnedObjectSerializer):
    class Meta:
        model = firewall_models.Firewall
        fields = BaseOwnedObjectSerializer.Meta.fields + ['stateful', 'name', 'related_network', 'default_action_into', 'default_action_from']
        read_only_fields = BaseOwnedObjectSerializer.Meta.read_only_fields
    related_network = OwnedObjectRelatedField(model=network_models.Network, required=False)

    def validate(self, data):
        if 'related_network' in data:
            if (not data['related_network'].public) and data['related_network'].owner not in data['owner'].get_visible_customers():
                raise serializers.ValidationError({'network': ['Referenced object not found.']})
        return super().validate(data)

class RuleSetSerializer(BaseOwnedObjectSerializer):
    class Meta:
        model = firewall_models.RuleSet
        fields = BaseOwnedObjectSerializer.Meta.fields + ['priority', 'firewalls', 'comment']
        read_only_fields = BaseOwnedObjectSerializer.Meta.read_only_fields
    firewalls = OwnedObjectRelatedField(many=True, model=firewall_models.Firewall, required=False)

    def validate(self, data):
        if 'firewalls' in data:
            for firewall in data['firewalls']:
                if (not firewall.public) and firewall.owner not in data['owner'].get_visible_customers():
                    raise serializers.ValidationError({'firewalls': ['Referenced object not found.']})
        return super().validate(data)

class RuleSerializer(AbstractOwnedObjectSerializer):
    class Meta:
        model = firewall_models.Rule
        fields = AbstractOwnedObjectSerializer.Meta.fields + ['related_ruleset', 'priority', 'comment', 'disable']
        read_only_fields = AbstractOwnedObjectSerializer.Meta.fields
    related_ruleset = OwnedObjectRelatedField(model=firewall_models.RuleSet, required=True)

class AddressObjectSerializer(BaseOwnedObjectSerializer):
    class Meta:
        model = firewall_models.AddressObject
        fields = BaseOwnedObjectSerializer.Meta.fields + ['name']
        read_only_fields = BaseOwnedObjectSerializer.Meta.read_only_fields

class ServiceObjectSerializer(BaseOwnedObjectSerializer):
    class Meta:
        model = firewall_models.ServiceObject
        fields = BaseOwnedObjectSerializer.Meta.fields + ['name']
        read_only_fields = BaseOwnedObjectSerializer.Meta.read_only_fields

class BasicRuleSerializer(RuleSerializer):
    class Meta:
        model = firewall_models.BasicRule
        fields = RuleSerializer.Meta.fields + ['source_address', 'destination_address', 'destination_service', 'action', 'log']
        read_only_fields = RuleSerializer.Meta.read_only_fields
    source_address = OwnedObjectRelatedField(model=firewall_models.AddressObject, required=False)
    destination_address = OwnedObjectRelatedField(model=firewall_models.AddressObject, required=True)
    destination_service = OwnedObjectRelatedField(model=firewall_models.ServiceObject, required=False)

    def validate(self, data):
        if 'related_ruleset' not in data:
            raise serializers.ValidationError({'related_ruleset': ['This item is required.']})
        for attr in ['source_address', 'destination_address', 'destination_service']:
            if attr in data:
                if (not data[attr].public) and data[attr].owner not in data['related_ruleset'].owner.get_visible_customers():
                    raise serializers.ValidationError({attr: ['Referenced object not found.']})
        return super().validate(data)

class CustomRuleSerializer(RuleSerializer):
    class Meta:
        model = firewall_models.CustomRule
        fields = RuleSerializer.Meta.fields + ['ip_version', 'rule']
        read_only_fields = RuleSerializer.Meta.read_only_fields

class NetworkAddressObjectSerializer(AddressObjectSerializer):
    class Meta:
        model = firewall_models.NetworkAddressObject
        fields = AddressObjectSerializer.Meta.fields + ['related_network']
        read_only_fields = AddressObjectSerializer.Meta.read_only_fields
    related_network = OwnedObjectRelatedField(model=network_models.Network, required=True)

    def validate(self, data):
        if 'related_network' in data:
            if (not data['related_network'].public) and data['related_network'].owner not in data['owner'].get_visible_customers():
                raise serializers.ValidationError({'network': ['Referenced object not found.']})
        return super().validate(data)

class CIDRAddressObjectSerializer(AddressObjectSerializer):
    class Meta:
        model = firewall_models.CIDRAddressObject
        fields = AddressObjectSerializer.Meta.fields + ['ipv6_network_address', 'ipv6_network_bits', 'ipv4_network_address', 'ipv4_network_bits']
        read_only_fields = AddressObjectSerializer.Meta.read_only_fields

class HostAddressObjectSerializer(AddressObjectSerializer):
    class Meta:
        model = firewall_models.HostAddressObject
        fields = AddressObjectSerializer.Meta.fields + ['ipv6_address', 'ipv4_address']
        read_only_fields = AddressObjectSerializer.Meta.read_only_fields

class ListAddressObjectSerializer(AddressObjectSerializer):
    class Meta:
        model = firewall_models.ListAddressObject
        fields = AddressObjectSerializer.Meta.fields + ['elements']
        read_only_fields = AddressObjectSerializer.Meta.read_only_fields
    elements = OwnedObjectRelatedField(many=True, model=firewall_models.AddressObject, required=False)

    def validate(self, data):
        if 'elements' in data:
            for element in data['elements']:
                if (not element.public) and element.owner not in data['owner'].get_visible_customers():
                    raise serializers.ValidationError({'elements': ['Referenced object not found.']})
        return super().validate(data)

class SimpleServiceObjectSerializer(ServiceObjectSerializer):
    class Meta:
        model = firewall_models.SimpleServiceObject
        fields = ServiceObjectSerializer.Meta.fields + ['protocol', 'port']
        read_only_fields = ServiceObjectSerializer.Meta.read_only_fields

class ListServiceObjectSerializer(ServiceObjectSerializer):
    class Meta:
        model = firewall_models.ListServiceObject
        fields = ServiceObjectSerializer.Meta.fields + ['elements']
        read_only_fields = ServiceObjectSerializer.Meta.read_only_fields
    elements = OwnedObjectRelatedField(many=True, model=firewall_models.ServiceObject, required=False)

    def validate(self, data):
        if 'elements' in data:
            for element in data['elements']:
                if (not element.public) and element.owner not in data['owner'].get_visible_customers():
                    raise serializers.ValidationError({'elements': ['Referenced object not found.']})
        return super().validate(data)

class RangeServiceObjectSerializer(ServiceObjectSerializer):
    class Meta:
        model = firewall_models.RangeServiceObject
        fields = ServiceObjectSerializer.Meta.fields + ['protocol', 'start_port', 'end_port']
        read_only_fields = ServiceObjectSerializer.Meta.read_only_fields
