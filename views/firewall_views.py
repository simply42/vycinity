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

import copy
from django.http import Http404
from vycinity.models import OwnedObject, customer_models, firewall_models, network_models, change_models, OWNED_OBJECT_STATE_LIVE, OWNED_OBJECT_STATE_PREPARED
from vycinity.models import firewall_models as models
from vycinity.serializers import firewall_serializers as serializers
from vycinity.meta.change_management import ChangedObjectCollection
from vycinity.views import GenericOwnedObjectList, GenericOwnedObjectDetail, VALIDATION_OK, ValidationResult
from typing import Any, List

REFERENCED_OBJECT_ACCESS_DENIED = 'Access to referenced object is denied'
REFERENCED_OBJECT_INVALID_STATE = 'Referenced object is not in a referencable state'

class FirewallList(GenericOwnedObjectList):
    def get_model(self):
        return models.Firewall

    def get_serializer(self):
        return serializers.FirewallSerializer

    def filter_attributes(self, object_list: List[Any], customer: customer_models.Customer):
        rtn = []
        for firewall_raw in object_list:
            if not 'network' in firewall_raw or firewall_raw['network'] is None:
                rtn.append(copy.deepcopy(firewall_raw))
            else:
                firewall_raw_mod = copy.deepcopy(firewall_raw)
                network = network_models.Network.objects.get(uuid=firewall_raw['network'])
                if not (network.public or network.owned_by(customer)):
                    del firewall_raw_mod['network']
                rtn.append(firewall_raw_mod)
        return rtn

    def post_validate(self, object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        return FirewallList.set_validate(object, customer, changeset)

    @staticmethod
    def set_validate(object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        if 'network' in object:
            if not (object['network'].state == OWNED_OBJECT_STATE_LIVE or (object['network'].state == OWNED_OBJECT_STATE_PREPARED and object['network'].change.changeset == changeset)):
                return ValidationResult(True, {'network': REFERENCED_OBJECT_INVALID_STATE})
            if not object['network'].owned_by(customer):
                return ValidationResult(False, {'network': REFERENCED_OBJECT_ACCESS_DENIED})
        return VALIDATION_OK


class FirewallDetailView(GenericOwnedObjectDetail):
    def get_model(self):
        return models.Firewall

    def get_serializer(self):
        return serializers.FirewallSerializer

    def filter_attributes(self, object: Any, customer: customer_models.Customer):
        if not 'network' in object or object['network'] is None:
            return copy.deepcopy(object)
        else:
            firewall_raw_mod = copy.deepcopy(object)
            network = network_models.Network.objects.get(id=object['network'])
            if not (network.public or network.owned_by(customer)):
                del firewall_raw_mod['network']
            return firewall_raw_mod

    def put_validate(self, object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet):
        return FirewallList.set_validate(object, customer, changeset)

class RuleSetList(GenericOwnedObjectList):
    def get_model(self):
        return models.RuleSet

    def get_serializer(self):
        return serializers.RuleSetSerializer

    def filter_attributes(self, object_list: List[Any], customer: customer_models.Customer):
        rtn = []
        for object in object_list:
            mod_object = copy.deepcopy(object)
            mod_object['firewalls'] = []
            for firewall_uuid in object['firewalls']:
                firewall = models.Firewall.objects.get(uuid=firewall_uuid)
                if firewall.public or firewall.owned_by(customer):
                    mod_object['firewalls'].append(firewall_uuid)
            rtn.append(mod_object)
        return rtn

    def post_validate(self, object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        return RuleSetList.set_allowed(object, changeset)

    @staticmethod
    def set_allowed(object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        rtn = ValidationResult()
        if ('firewalls' in object and isinstance(object['firewalls'], list)):
            target_visible_customers = customer.get_visible_customers()
            for firewall in object['firewalls']:
                if not firewall.public and not firewall.owner in target_visible_customers and (firewall.state == OWNED_OBJECT_STATE_LIVE or (firewall.state == OWNED_OBJECT_STATE_PREPARED and firewall.change.changeset == changeset)):
                    rtn.errors = {'firewall': [REFERENCED_OBJECT_ACCESS_DENIED]}
                    rtn.access_ok = False
                    break
        return rtn

class RuleSetDetailView(GenericOwnedObjectDetail):
    def get_model(self):
        return models.RuleSet

    def get_serializer(self):
        return serializers.RuleSetSerializer

    def filter_attributes(self, object: Any, customer: customer_models.Customer):
        filtered_firewalls = []
        for firewall_uuid in object['firewalls']:
            firewall = models.Firewall.objects.get(uuid=firewall_uuid)
            if firewall.public or firewall.owned_by(customer):
                filtered_firewalls.append(firewall_uuid)
        rtn = copy.deepcopy(object)
        rtn['firewalls'] = filtered_firewalls
        return rtn

    def put_validate(self, object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        return RuleSetList.set_allowed(object, customer, changeset)

def set_allowed_by_ruleset(object: dict, customer: customer_models.Customer) -> bool:
    '''
    Prüfe Schreib-Recht für angehängte RuleSets in basis-validierten dicts.
    '''
    if not object['ruleset'].owned_by(customer):
        return False
    return True

class BasicRuleList(GenericOwnedObjectList):
    def get_model(self):
        return models.BasicRule

    def get_serializer(self):
        return serializers.BasicRuleSerializer

    def post_validate(self, object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        return BasicRuleList.set_allowed(object, customer, changeset)

    def filter_attributes(self, object_list: List[Any], customer: customer_models.Customer):
        return copy.deepcopy(object_list)

    def validate_owner(self):
        return False

    @staticmethod
    def set_allowed(object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        rtn = ValidationResult()
        if not set_allowed_by_ruleset(object, customer):
            rtn.access_ok = False
            rtn.errors = {'ruleset':[REFERENCED_OBJECT_ACCESS_DENIED]}
            return rtn
        rtn.access_ok = True
        rtn.errors = {}
        for attr in ['source_address', 'destination_address', 'destination_service']:
            if attr in object and not object[attr] is None:
                if not (object[attr].public or object[attr].owned_by(customer)):
                    rtn.access_ok = False
                    rtn.errors[attr] = [REFERENCED_OBJECT_ACCESS_DENIED]
                    continue
                if not (object[attr].state == OWNED_OBJECT_STATE_LIVE or (object[attr].state == OWNED_OBJECT_STATE_PREPARED and object[attr].change.changeset == changeset)):
                    if attr not in rtn.errors:
                        rtn.errors[attr] = []
                    rtn.errors[attr].append(REFERENCED_OBJECT_INVALID_STATE)
        return rtn


class BasicRuleDetail(GenericOwnedObjectDetail):
    def get_model(self):
        return models.BasicRule

    def get_serializer(self):
        return serializers.BasicRuleSerializer

    def put_validate(self, object: Any, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        return BasicRuleList.set_allowed(object, customer, changeset)

    def filter_attributes(self, object: Any, customer: customer_models.Customer):
        return copy.deepcopy(object)

    def validate_owner(self):
        return False

class CustomRuleList(GenericOwnedObjectList):
    def get_model(self):
        return models.CustomRule

    def get_serializer(self):
        return serializers.CustomRuleSerializer

    def post_validate(self, object: Any, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> bool:
        if set_allowed_by_ruleset(object, customer):
            return VALIDATION_OK
        else:
            return ValidationResult(access_ok=False, errors={'ruleset':[REFERENCED_OBJECT_ACCESS_DENIED]})

    def filter_attributes(self, object_list: List[Any], customer: customer_models.Customer):
        return copy.deepcopy(object_list)

    def validate_owner(self):
        return False

class CustomRuleDetail(GenericOwnedObjectDetail):
    def get_model(self):
        return models.CustomRule

    def get_serializer(self):
        return serializers.CustomRuleSerializer

    def put_validate(self, object: Any, customer: customer_models.Customer, changeset: change_models.ChangeSet):
        if set_allowed_by_ruleset(object, customer):
            return VALIDATION_OK
        else:
            return ValidationResult(access_ok=False, errors={'ruleset':[REFERENCED_OBJECT_ACCESS_DENIED]})

    def filter_attributes(self, object: Any, customer: customer_models.Customer):
        return copy.deepcopy(object)
    
    def validate_owner(self):
        return False

class NetworkAddressObjectList(GenericOwnedObjectList):
    def get_model(self):
        return models.NetworkAddressObject

    def get_serializer(self):
        return serializers.NetworkAddressObjectSerializer

    def post_validate(self, object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        return NetworkAddressObjectList.set_allowed_by_network(object, customer, changeset)

    def filter_attributes(self, object_list: List[Any], customer: customer_models.Customer):
        return copy.deepcopy(object_list)

    @staticmethod
    def set_allowed_by_network(object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        if not object['network'].owned_by(customer):
            return ValidationResult(access_ok=False, errors={'network':[REFERENCED_OBJECT_ACCESS_DENIED]})
        if not (object['network'].state == OWNED_OBJECT_STATE_LIVE or (object['network'].state == OWNED_OBJECT_STATE_PREPARED and object['network'].change.changeset == changeset)):
            return ValidationResult(access_ok=False, errors={'network':[REFERENCED_OBJECT_INVALID_STATE]})
        return VALIDATION_OK


class NetworkAddressObjectDetail(GenericOwnedObjectDetail):
    def get_model(self):
        return models.NetworkAddressObject

    def get_serializer(self):
        return serializers.NetworkAddressObjectSerializer

    def put_validate(self, object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        return NetworkAddressObjectList.set_allowed_by_network(object, customer, changeset)

    def filter_attributes(self, object: Any, customer: customer_models.Customer):
        return copy.deepcopy(object)

class CIDRAddressObjectList(GenericOwnedObjectList):
    def get_model(self):
        return models.CIDRAddressObject

    def get_serializer(self):
        return serializers.CIDRAddressObjectSerializer

    def post_validate(self, object: Any, customer: customer_models.Customer, changeset: change_models.ChangeSet):
        return VALIDATION_OK

    def filter_attributes(self, object_list: List[Any], customer: customer_models.Customer):
        return copy.deepcopy(object_list)

class CIDRAddressObjectDetail(GenericOwnedObjectDetail):
    def get_model(self):
        return models.CIDRAddressObject

    def get_serializer(self):
        return serializers.CIDRAddressObjectSerializer

    def put_validate(self, object: Any, customer: customer_models.Customer, changeset: change_models.ChangeSet):
        return VALIDATION_OK

    def filter_attributes(self, object: Any, customer: customer_models.Customer):
        return copy.deepcopy(object)

class HostAddressObjectList(GenericOwnedObjectList):
    def get_model(self):
        return models.HostAddressObject

    def get_serializer(self):
        return serializers.HostAddressObjectSerializer

    def post_validate(self, object: Any, customer: customer_models.Customer, changeset: change_models.ChangeSet):
        return VALIDATION_OK

    def filter_attributes(self, object_list: List[Any], customer: customer_models.Customer):
        return copy.deepcopy(object_list)

class HostAddressObjectDetail(GenericOwnedObjectDetail):
    def get_model(self):
        return models.HostAddressObject

    def get_serializer(self):
        return serializers.HostAddressObjectSerializer

    def put_validate(self, object: Any, customer: customer_models.Customer, changeset: change_models.ChangeSet):
        return VALIDATION_OK

    def filter_attributes(self, object: Any, customer: customer_models.Customer):
        return copy.deepcopy(object)

def set_allowed_by_elements(object: Any, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
    '''
    Prüft die Schreibberechtigung für ein Listen-Objekt, das in seinem 'elements'-Attribut auf ein
    anderes Model verweist.
    '''
    for element in object['elements']:
        if not element.owned_by(customer) or element.public:
            return ValidationResult(access_ok=False, errors={'elements':[REFERENCED_OBJECT_ACCESS_DENIED]})
        if not (element.state == OWNED_OBJECT_STATE_LIVE or (element.state == OWNED_OBJECT_STATE_PREPARED and element.change.changeset == changeset)):
            return ValidationResult(access_ok=False, errors={'elements':[REFERENCED_OBJECT_INVALID_STATE]})
    return VALIDATION_OK

def filter_attributes_by_elements(object: Any, customer: customer_models.Customer, dest_model):
    '''
    Filtert Elemente aus dem 'elements'-Attribut heraus, die nicht vom Customer oder öffentlich
    sind.
    '''
    cleaned_object = copy.deepcopy(object)
    cleaned_object['elements'] = []
    for element_id in object['elements']:
        element_object = dest_model.objects.get(id = element_id)
        if element_object.public or element_object.owned_by(customer):
            cleaned_object['elements'].append(element_id)
    return cleaned_object

class ListAddressObjectList(GenericOwnedObjectList):
    def get_model(self):
        return models.ListAddressObject

    def get_serializer(self):
        return serializers.ListAddressObjectSerializer

    def post_validate(self, object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        return set_allowed_by_elements(object, object['owner'], changeset)

    def filter_attributes(self, object_list: List[Any], customer: customer_models.Customer):
        rtn = []
        for object in object_list:
            rtn.append(filter_attributes_by_elements(object, customer, self.get_model()))
        return rtn

class ListAddressObjectDetail(GenericOwnedObjectDetail):
    def get_model(self):
        return models.ListAddressObject

    def get_serializer(self):
        return serializers.ListAddressObjectSerializer

    def put_validate(self, object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        return set_allowed_by_elements(object, object['owner'], changeset)

    def filter_attributes(self, object: List[Any], customer: customer_models.Customer):
        return filter_attributes_by_elements(object, customer, self.get_model())

class SimpleServiceObjectList(GenericOwnedObjectList):
    def get_model(self):
        return models.SimpleServiceObject
    
    def get_serializer(self):
        return serializers.SimpleServiceObjectSerializer

    def post_validate(self, object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        return VALIDATION_OK

    def filter_attributes(self, object_list: Any, customer: customer_models.Customer):
        return copy.deepcopy(object_list)

class SimpleServiceObjectDetail(GenericOwnedObjectDetail):
    def get_model(self):
        return models.SimpleServiceObject
    
    def get_serializer(self):
        return serializers.SimpleServiceObjectSerializer

    def put_validate(self, object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        return VALIDATION_OK

    def filter_attributes(self, object: Any, customer: customer_models.Customer):
        return copy.deepcopy(object)

class RangeServiceObjectList(GenericOwnedObjectList):
    def get_model(self):
        return models.RangeServiceObject
    
    def get_serializer(self):
        return serializers.RangeServiceObjectSerializer

    def post_validate(self, object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        return VALIDATION_OK

    def filter_attributes(self, object_list: Any, customer: customer_models.Customer):
        return copy.deepcopy(object_list)

class RangeServiceObjectDetail(GenericOwnedObjectDetail):
    def get_model(self):
        return models.RangeServiceObject
    
    def get_serializer(self):
        return serializers.RangeServiceObjectSerializer

    def put_validate(self, object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        return VALIDATION_OK

    def filter_attributes(self, object: Any, customer: customer_models.Customer):
        return copy.deepcopy(object)

class ListServiceObjectList(GenericOwnedObjectList):
    def get_model(self):
        return models.ListServiceObject
    
    def get_serializer(self):
        return serializers.ListServiceObjectSerializer

    def post_validate(self, object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        return set_allowed_by_elements(object, object['owner'], changeset)

    def filter_attributes(self, object_list: List[Any], customer: customer_models.Customer):
        rtn = []
        for object in object_list:
            rtn.append(filter_attributes_by_elements(object, customer, self.get_model()))
        return rtn

class ListServiceObjectDetail(GenericOwnedObjectDetail):
    def get_model(self):
        return models.ListServiceObject
    
    def get_serializer(self):
        return serializers.ListServiceObjectSerializer

    def put_validate(self, object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        return set_allowed_by_elements(object, object['owner'], changeset)

    def filter_attributes(self, object: List[Any], customer: customer_models.Customer):
        return filter_attributes_by_elements(object, customer, self.get_model())