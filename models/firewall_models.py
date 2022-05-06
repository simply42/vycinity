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

import uuid
from django.core.exceptions import ValidationError
from django.db import models
from vycinity.models import AbstractOwnedObject, customer_models, network_models, OwnedObject, SemiOwnedObject
from typing import Any, List

ACTION_ACCEPT = 'accept'
ACTION_REJECT = 'reject'
ACTION_DROP = 'drop'
ACTIONS = [
    (ACTION_ACCEPT, 'accept'),
    (ACTION_DROP, 'drop'),
    (ACTION_REJECT, 'reject')
]

IP_VERSION_4 = 4
IP_VERSION_6 = 6
IP_VERSIONS = [
    (IP_VERSION_4, 'IPv4'),
    (IP_VERSION_6, 'IPv6')
]

DIRECTION_INTO = 'into'
DIRECTION_FROM = 'from'
DIRECTIONS = [
    (DIRECTION_INTO, 'into'),
    (DIRECTION_FROM, 'from')
]

def validate_priority_rule(value):
    if value < 0 or value > 65535:
        raise ValidationError('Priority must be in range 0-65535')
validate_priority_ruleset = validate_priority_rule

def validate_port_simpleserviceobject(value):
    if value < 1 or value > 65535:
        raise ValidationError('Port must be in range 1-65535')
validate_port_rangeserviceobject = validate_port_simpleserviceobject

class Firewall(OwnedObject):
    stateful = models.BooleanField()
    name = models.CharField(max_length=64)
    related_network = models.ForeignKey(network_models.Network, null=True, on_delete=models.SET_NULL)
    default_action_into = models.CharField(max_length=16, choices=ACTIONS)
    default_action_from = models.CharField(max_length=16, choices=ACTIONS)

    def get_related_owned_objects(self) -> List[AbstractOwnedObject]:
        rtn = []
        for ruleset in RuleSet.objects.filter(firewalls=self):
            rtn.append(ruleset)
        if self.related_network is not None:
            rtn.append(self.related_network)
        return rtn

    def get_dependent_owned_objects(self) -> List['AbstractOwnedObject']:
        return []

class RuleSet(OwnedObject):
    firewalls = models.ManyToManyField(Firewall)
    priority = models.IntegerField(validators=[validate_priority_ruleset])
    comment = models.TextField(null=True)

    def get_related_owned_objects(self) -> List[AbstractOwnedObject]:
        rtn = []
        rtn += self.firewalls.all()
        rtn += self.rules.all()
        return rtn
    
    def get_dependent_owned_objects(self) -> List['AbstractOwnedObject']:
        return []

class Rule(SemiOwnedObject):
    related_ruleset = models.ForeignKey(RuleSet, on_delete=models.CASCADE, related_name='rules')
    priority = models.IntegerField(validators=[validate_priority_rule])
    comment = models.TextField(null=True)
    disable = models.BooleanField()

    @property
    def owner(self):
        return self.related_ruleset.owner

    @property
    def public(self):
        return self.related_ruleset.public

    @staticmethod
    def filter_query_by_customers_or_public(query: Any, customers: List[customer_models.Customer]):
        return query.filter(models.Q(ruleset__owner__in = customers) | models.Q(ruleset__public = True))

    def get_related_owned_objects(self) -> List[AbstractOwnedObject]:
        if hasattr(self, 'basicrule'):
            return self.basicrule.get_related_owned_objects()
        elif hasattr(self, 'customrule'):
            return self.customrule.get_related_owned_objects()
        raise ValueError('Inconsistent Rule({})'.format(self.pk))

    def get_dependent_owned_objects(self) -> List['AbstractOwnedObject']:
        return self.get_related_owned_objects()

class AddressObject(OwnedObject):
    name = models.CharField(max_length=64)

    def get_related_owned_objects(self) -> List[AbstractOwnedObject]:
        if hasattr(self, 'networkaddressobject'):
            return self.networkaddressobject.get_related_owned_objects()
        elif hasattr(self, 'cidraddressobject'):
            return self.cidraddressobject.get_related_owned_objects()
        elif hasattr(self, 'hostaddressobject'):
            return self.hostaddressobject.get_related_owned_objects()
        elif hasattr(self, 'listaddressobject'):
            return self.listaddressobject.get_related_owned_objects()
        raise ValueError('Inconsistent AddressObject({})'.format(self.pk))

    def get_dependent_owned_objects(self) -> List['AbstractOwnedObject']:
        return self.get_related_owned_objects()

class ServiceObject(OwnedObject):
    name = models.CharField(max_length=64)

    def get_related_owned_objects(self) -> List[AbstractOwnedObject]:
        if hasattr(self, 'simpleserviceobject'):
            return self.simpleserviceobject.get_related_owned_objects()
        elif hasattr(self, 'listserviceobject'):
            return self.listserviceobject.get_related_owned_objects()
        elif hasattr(self, 'rangeserviceobject'):
            return self.rangeserviceobject.get_related_owned_objects()
        raise ValueError('Inconsistent ServiceObject({})'.format(self.pk))

class BasicRule(Rule):
    source_address = models.ForeignKey(AddressObject, null=True, on_delete=models.RESTRICT, related_name='+')
    destination_address = models.ForeignKey(AddressObject, on_delete=models.RESTRICT, related_name='+')
    destination_service = models.ForeignKey(ServiceObject, null=True, on_delete=models.RESTRICT, related_name='+')
    action = models.CharField(max_length=16, choices=ACTIONS)
    log = models.BooleanField()

    def get_related_owned_objects(self) -> List[AbstractOwnedObject]:
        rtn = []
        rtn.append(self.related_ruleset)
        if self.source_address is not None:
            rtn.append(self.source_address)
        if self.destination_address is not None:
            rtn.append(self.destination_address)
        if self.destination_service is not None:
            rtn.append(self.destination_service)
        return rtn

class CustomRule(Rule):
    ip_version = models.IntegerField(choices=IP_VERSIONS)
    direction = models.CharField(max_length=4, choices=DIRECTIONS)
    rule_definition = models.JSONField()

    def get_related_owned_objects(self) -> List[AbstractOwnedObject]:
        return [self.related_ruleset]

class NetworkAddressObject(AddressObject):
    related_network = models.ForeignKey(network_models.Network, on_delete=models.CASCADE)

    def get_related_owned_objects(self) -> List[AbstractOwnedObject]:
        return [self.related_network]

class CIDRAddressObject(AddressObject):
    ipv6_network_address = models.GenericIPAddressField(null=True, protocol='IPv6')
    ipv6_network_bits = models.IntegerField(null=True, validators=[network_models.validate_ipv6_network_bits])
    ipv4_network_address = models.GenericIPAddressField(null=True, protocol='IPv4')
    ipv4_network_bits = models.IntegerField(null=True, validators=[network_models.validate_ipv4_network_bits])

    def get_related_owned_objects(self) -> List[AbstractOwnedObject]:
        return []

class HostAddressObject(AddressObject):
    ipv6_address = models.GenericIPAddressField(null=True, protocol='IPv6')
    ipv4_address = models.GenericIPAddressField(null=True, protocol='IPv4')

    def get_related_owned_objects(self) -> List[AbstractOwnedObject]:
        return []

class ListAddressObject(AddressObject):
    elements = models.ManyToManyField(AddressObject, related_name='+')

    def get_related_owned_objects(self) -> List[AbstractOwnedObject]:
        rtn = []
        for element in self.elements:
            rtn += element.get_related_owned_objects()
        return rtn

class SimpleServiceObject(ServiceObject):
    protocol = models.CharField(max_length=16)
    port = models.IntegerField(validators=[validate_port_simpleserviceobject])

    def get_related_owned_objects(self) -> List[AbstractOwnedObject]:
        return []

class ListServiceObject(ServiceObject):
    elements = models.ManyToManyField(ServiceObject, related_name='+')

    def get_related_owned_objects(self) -> List[AbstractOwnedObject]:
        rtn = []
        for element in self.elements:
            rtn += element.get_related_owned_objects()
        return rtn

class RangeServiceObject(ServiceObject):
    protocol = models.CharField(max_length=16)
    start_port = models.IntegerField(validators=[validate_port_rangeserviceobject])
    end_port = models.IntegerField(validators=[validate_port_rangeserviceobject])

    def get_related_owned_objects(self) -> List[AbstractOwnedObject]:
        return []
