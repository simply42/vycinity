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

from vycinity.models import firewall_models as models
from vycinity.serializers import firewall_serializers as serializers
from vycinity.views import GenericOwnedObjectList, GenericOwnedObjectDetail, GenericOwnedObjectSchema

REFERENCED_OBJECT_NOT_FOUND = 'Referenced object not found'
REFERENCED_OBJECT_ACCESS_DENIED = 'Access to referenced object is denied'
REFERENCED_OBJECT_INVALID_STATE = 'Referenced object is not in a referencable state'

class FirewallList(GenericOwnedObjectList):
    '''
    General operations on firewalls. Firewalls consist of Rulesets.

    get:
        List available firewalls.

    post:
        Create a new firewall.
    '''

    schema = GenericOwnedObjectSchema(serializer=serializers.FirewallSerializer, operation_id_base='Firewall', component_name='Firewall', tags=['firewall'])

    def get_model(self):
        return models.Firewall

    def get_serializer_class(self):
        return serializers.FirewallSerializer


class FirewallDetailView(GenericOwnedObjectDetail):
    '''
    Operations on specific firewalls.

    get:
        Retrieve a specific firewall.

    put:
        Change a firewall.

    delete:
        Delete a firewall.
    '''

    schema = GenericOwnedObjectSchema(serializer=serializers.FirewallSerializer, operation_id_base='Firewall', component_name='Firewall', tags=['firewall'])

    def get_model(self):
        return models.Firewall

    def get_serializer_class(self):
        return serializers.FirewallSerializer


class RuleSetList(GenericOwnedObjectList):
    '''
    get:
        Rulesets contain rules and can be tied to multiple firewalls.
        List all available rulesets.

    post:
        Rulesets contain rules and can be tied to multiple firewalls.
        Create an empty ruleset.
    '''

    schema = GenericOwnedObjectSchema(serializer=serializers.RuleSetSerializer, operation_id_base='RuleSet', component_name='RuleSet', tags=['ruleset'])

    def get_model(self):
        return models.RuleSet

    def get_serializer_class(self):
        return serializers.RuleSetSerializer


class RuleSetDetailView(GenericOwnedObjectDetail):
    '''
    get:
        Rulesets contain rules and can be tied to multiple firewalls.
        Retrieve a ruleset
    
    put:
        Rulesets contain rules and can be tied to multiple firewalls.
        Update a ruleset

    delete:
        Delete a ruleset.
    '''
    schema = GenericOwnedObjectSchema(serializer=serializers.RuleSetSerializer, operation_id_base='RuleSet', component_name='RuleSet', tags=['ruleset'])

    def get_model(self):
        return models.RuleSet

    def get_serializer_class(self):
        return serializers.RuleSetSerializer


class BasicRuleList(GenericOwnedObjectList):
    '''
    Basic rules are firewall rules, which are pretty simple and should be usable for most cases.

    get:
        Basic rules define simple firewall rules just containing source, destination and service.
        Retrieve all available basic rules.

    post:
        Basic rules define simple firewall rules just containing source, destination and service.
        Create a new basic rule.
    '''
    schema = GenericOwnedObjectSchema(serializer=serializers.BasicRuleSerializer, operation_id_base='BasicRule', component_name='BasicRule', tags=['rule', 'basic rule'])

    def get_model(self):
        return models.BasicRule

    def get_serializer_class(self):
        return serializers.BasicRuleSerializer


class BasicRuleDetail(GenericOwnedObjectDetail):
    '''
    get:
        Basic rules define simple firewall rules just containing source, destination and service.
        Retrieve a specifgic basic rule.

    put:
        Basic rules define simple firewall rules just containing source, destination and service.
        Update an existing basic rule.

    delete:
        Basic rules define simple firewall rules just containing source, destination and service.
        Delete an existing basic rule.
    '''
    schema = GenericOwnedObjectSchema(serializer=serializers.BasicRuleSerializer, operation_id_base='BasicRule', component_name='BasicRule', tags=['rule', 'basic rule'])

    def get_model(self):
        return models.BasicRule

    def get_serializer_class(self):
        return serializers.BasicRuleSerializer


class CustomRuleList(GenericOwnedObjectList):
    '''
    get:
        Custom rules are specific and require knowledge about the router implementing it.
        Retrieve all custom rules.

    post:
        Custom rules are specific and require knowledge about the router implementing it.
        Create a new custom rule.
    '''
    schema = GenericOwnedObjectSchema(serializer=serializers.CustomRuleSerializer, operation_id_base='CustomRule', component_name='CustomRule', tags=['rule', 'custom rule'])

    def get_model(self):
        return models.CustomRule

    def get_serializer_class(self):
        return serializers.CustomRuleSerializer


class CustomRuleDetail(GenericOwnedObjectDetail):
    '''
    get:
        Custom rules are specific and require knowledge about the router implementing it.
        Retrieve a specific custom rule.

    put:
        Custom rules are specific and require knowledge about the router implementing it.
        Update a custom rule.

    delete:
        Custom rules are specific and require knowledge about the router implementing it.
        Delete a custom rule.
    '''
    schema = GenericOwnedObjectSchema(serializer=serializers.CustomRuleSerializer, operation_id_base='CustomRule', component_name='CustomRule', tags=['rule', 'custom rule'])

    def get_model(self):
        return models.CustomRule

    def get_serializer_class(self):
        return serializers.CustomRuleSerializer


class NetworkAddressObjectList(GenericOwnedObjectList):
    '''
    get:
        Network address objects link existing networks and make them usable for the firewall.
        Retrieve all network address objects.

    post:
        Network address objects link existing networks and make them usable for the firewall.
        Create a network address object.
    '''
    schema = GenericOwnedObjectSchema(serializer=serializers.NetworkAddressObjectSerializer, operation_id_base='NetworkAddressObject', component_name='NetworkAddressObject', tags=['address object', 'network'])

    def get_model(self):
        return models.NetworkAddressObject

    def get_serializer_class(self):
        return serializers.NetworkAddressObjectSerializer


class NetworkAddressObjectDetail(GenericOwnedObjectDetail):
    '''
    get:
        Network address objects link existing networks and make them usable for the firewall.
        Retrieve a specific network address object.

    put:
        Network address objects link existing networks and make them usable for the firewall.
        Update a network address object.

    delete:
        Delete a network address object.
    '''
    schema = GenericOwnedObjectSchema(serializer=serializers.NetworkAddressObjectSerializer, operation_id_base='NetworkAddressObject', component_name='NetworkAddressObject', tags=['address object', 'network'])

    def get_model(self):
        return models.NetworkAddressObject

    def get_serializer_class(self):
        return serializers.NetworkAddressObjectSerializer


class CIDRAddressObjectList(GenericOwnedObjectList):
    '''
    get:
        CIDR address objects define networks by a prefix and a prefix length in bits.
        Retrieve all cidr address objects.

    post:
        CIDR address objects define networks by a prefix and a prefix length in bits.
        Create a cidr address object.
    '''
    schema = GenericOwnedObjectSchema(serializer=serializers.CIDRAddressObjectSerializer, operation_id_base='CIDRAddressObject', component_name='CIDRAddressObject', tags=['address object', 'cidr'])

    def get_model(self):
        return models.CIDRAddressObject

    def get_serializer_class(self):
        return serializers.CIDRAddressObjectSerializer


class CIDRAddressObjectDetail(GenericOwnedObjectDetail):
    '''
    get:
        CIDR address objects define networks by a prefix and a prefix length in bits.
        Retrieve a specific cidr address object.

    put:
        CIDR address objects define networks by a prefix and a prefix length in bits.
        Create a cidr address object.

    delete:
        Delete a cidr address object.
    '''
    schema = GenericOwnedObjectSchema(serializer=serializers.CIDRAddressObjectSerializer, operation_id_base='CIDRAddressObject', component_name='CIDRAddressObject', tags=['address object', 'cidr'])

    def get_model(self):
        return models.CIDRAddressObject

    def get_serializer_class(self):
        return serializers.CIDRAddressObjectSerializer

class HostAddressObjectList(GenericOwnedObjectList):
    '''
    get:
        Host address objects define single network addresses for hosts.
        Retrieve all host address objects.

    post:
        Host address objects define single network addresses for hosts.
        Create a host address object.
    '''
    schema = GenericOwnedObjectSchema(serializer=serializers.HostAddressObjectSerializer, operation_id_base='HostAddressObject', component_name='HostAddressObject', tags=['address object', 'host address'])

    def get_model(self):
        return models.HostAddressObject

    def get_serializer_class(self):
        return serializers.HostAddressObjectSerializer


class HostAddressObjectDetail(GenericOwnedObjectDetail):
    '''
    get:
        Host address objects define single network addresses for hosts.
        Retrieve a specific host address object.

    put:
        Host address objects define single network addresses for hosts.
        Update a host address object.

    delete:
        Delete a host address object.
    '''
    schema = GenericOwnedObjectSchema(serializer=serializers.HostAddressObjectSerializer, operation_id_base='HostAddressObject', component_name='HostAddressObject', tags=['address object', 'host address'])

    def get_model(self):
        return models.HostAddressObject

    def get_serializer_class(self):
        return serializers.HostAddressObjectSerializer

class ListAddressObjectList(GenericOwnedObjectList):
    '''
    get:
        List address objects collect multiple other address objects for use as a single object.
        Retrieve all list address objects.

    post:
        List address objects collect multiple other address objects for use as a single object.
        Create a list address object.
    '''
    schema = GenericOwnedObjectSchema(serializer=serializers.ListAddressObjectSerializer, operation_id_base='ListAddressObject', component_name='ListAddressObject', tags=['address object', 'address list'])

    def get_model(self):
        return models.ListAddressObject

    def get_serializer_class(self):
        return serializers.ListAddressObjectSerializer


class ListAddressObjectDetail(GenericOwnedObjectDetail):
    '''
    get:
        List address objects collect multiple other address objects for use as a single object.
        Retrieve a single address object.

    put:
        List address objects collect multiple other address objects for use as a single object.
        Update a list address object.

    delete:
        Delete a list address object.
    '''
    schema = GenericOwnedObjectSchema(serializer=serializers.ListAddressObjectSerializer, operation_id_base='ListAddressObject', component_name='ListAddressObject', tags=['address object', 'address list'])

    def get_model(self):
        return models.ListAddressObject

    def get_serializer_class(self):
        return serializers.ListAddressObjectSerializer


class SimpleServiceObjectList(GenericOwnedObjectList):
    '''
    get:
        Simple service objects define a single service by protocol and port.
        Retrieve all simple service objects.

    post:
        Simple service objects define a single service by protocol and port.
        Create a simple service object.
    '''
    schema = GenericOwnedObjectSchema(serializer=serializers.SimpleServiceObjectSerializer, operation_id_base='SimpleServiceObject', component_name='SimpleServiceObject', tags=['service object', 'simple service'])

    def get_model(self):
        return models.SimpleServiceObject
    
    def get_serializer_class(self):
        return serializers.SimpleServiceObjectSerializer


class SimpleServiceObjectDetail(GenericOwnedObjectDetail):
    '''
    get:
        Simple service objects define a single service by protocol and port.
        Retrieve a specific simple service object.

    put:
        Simple service objects define a single service by protocol and port.
        Update a simple service object.

    delete:
        Delete a simple service object.
    '''
    schema = GenericOwnedObjectSchema(serializer=serializers.SimpleServiceObjectSerializer, operation_id_base='SimpleServiceObject', component_name='SimpleServiceObject', tags=['service object', 'simple service'])

    def get_model(self):
        return models.SimpleServiceObject
    
    def get_serializer_class(self):
        return serializers.SimpleServiceObjectSerializer


class RangeServiceObjectList(GenericOwnedObjectList):
    '''
    get:
        Range service objects define a service by protocol and portrange.
        Retrieve all range service objects.

    post:
        Range service objects define a service by protocol and portrange.
        Create a range service object.
    '''
    schema = GenericOwnedObjectSchema(serializer=serializers.RangeServiceObjectSerializer, operation_id_base='RangeServiceObject', component_name='RangeServiceObject', tags=['service object', 'service range'])

    def get_model(self):
        return models.RangeServiceObject
    
    def get_serializer_class(self):
        return serializers.RangeServiceObjectSerializer


class RangeServiceObjectDetail(GenericOwnedObjectDetail):
    '''
    get:
        Range service objects define a service by protocol and portrange.
        Retrieve a specific range service object.

    put:
        Range service objects define a service by protocol and portrange.
        Update a range service object.

    delete:
        Delete a range service object.
    '''
    schema = GenericOwnedObjectSchema(serializer=serializers.RangeServiceObjectSerializer, operation_id_base='RangeServiceObject', component_name='RangeServiceObject', tags=['service object', 'service range'])

    def get_model(self):
        return models.RangeServiceObject
    
    def get_serializer_class(self):
        return serializers.RangeServiceObjectSerializer


class ListServiceObjectList(GenericOwnedObjectList):
    '''
    get:
        List service objects collect multiple other service objects for use as a single object.
        Retrieve all list service objects.

    post:
        List service objects collect multiple other service objects for use as a single object.
        Create a list service object.
    '''
    schema = GenericOwnedObjectSchema(serializer=serializers.ListServiceObjectSerializer, operation_id_base='ListServiceObject', component_name='ListServiceObject', tags=['service object', 'service list'])

    def get_model(self):
        return models.ListServiceObject
    
    def get_serializer(self):
        return serializers.ListServiceObjectSerializer


class ListServiceObjectDetail(GenericOwnedObjectDetail):
    '''
    get:
        List service objects collect multiple other service objects for use as a single object.
        Retrieve a single list service object.

    put:
        List service objects collect multiple other service objects for use as a single object.
        Update a list service object.

    delete:
        Delete a list service object.
    '''
    schema = GenericOwnedObjectSchema(serializer=serializers.ListServiceObjectSerializer, operation_id_base='ListServiceObject', component_name='ListServiceObject', tags=['service object', 'service list'])

    def get_model(self):
        return models.ListServiceObject
    
    def get_serializer_class(self):
        return serializers.ListServiceObjectSerializer

