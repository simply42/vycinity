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

from typing import List, Type, Optional
from collections import namedtuple
from django.db.models import Model
from django.urls import URLPattern, path
from rest_framework.views import APIView
from rest_framework.serializers import Serializer


ChangeableObjectEntry = namedtuple('ChangeableObjectEntry', ['model', 'serializer', 'path', 'single_view', 'list_view'])

class ChangeableObjectRegistry(object):
    '''
    Registry for all changeable objects. All changeable must be registered to be supported by
    generic mechanisms like the changeset-management.

    Instead of creating a new instance, use `ChangeableObjectRegistry.instance()` for an instance,
    if possible.
    '''
    __instance = None

    def __new__(cls: Type['ChangeableObjectRegistry']) -> 'ChangeableObjectRegistry':
        if ChangeableObjectRegistry.__instance is None:
            ChangeableObjectRegistry.__instance = object.__new__(cls)
            ChangeableObjectRegistry.__instance.registry = {}

            # initialize at runtime to break import loop
            from vycinity.models import firewall_models, network_models
            from vycinity.serializers import firewall_serializers, network_serializers
            from vycinity.views import firewall_views, network_views
            ChangeableObjectRegistry.__instance.register(firewall_models.BasicRule, firewall_serializers.BasicRuleSerializer, 'rules/basic', firewall_views.BasicRuleDetail, firewall_views.BasicRuleList)
            ChangeableObjectRegistry.__instance.register(firewall_models.CIDRAddressObject, firewall_serializers.CIDRAddressObjectSerializer, 'objects/addresses/cidrs', firewall_views.CIDRAddressObjectDetail, firewall_views.CIDRAddressObjectList)
            ChangeableObjectRegistry.__instance.register(firewall_models.CustomRule, firewall_serializers.CustomRuleSerializer, 'rules/custom', firewall_views.CustomRuleDetail, firewall_views.CustomRuleList)
            ChangeableObjectRegistry.__instance.register(firewall_models.Firewall, firewall_serializers.FirewallSerializer, 'firewalls', firewall_views.FirewallDetailView, firewall_views.FirewallList)
            ChangeableObjectRegistry.__instance.register(firewall_models.HostAddressObject, firewall_serializers.HostAddressObjectSerializer, 'objects/addresses/hosts', firewall_views.HostAddressObjectDetail, firewall_views.HostAddressObjectList)
            ChangeableObjectRegistry.__instance.register(firewall_models.ListAddressObject, firewall_serializers.ListAddressObjectSerializer, 'objects/addresses/lists', firewall_views.ListAddressObjectDetail, firewall_views.ListAddressObjectList)
            ChangeableObjectRegistry.__instance.register(firewall_models.ListServiceObject, firewall_serializers.ListServiceObjectSerializer, 'objects/services/lists', firewall_views.ListServiceObjectDetail, firewall_views.ListAddressObjectList)
            ChangeableObjectRegistry.__instance.register(firewall_models.NetworkAddressObject, firewall_serializers.NetworkAddressObjectSerializer, 'objects/addresses/networks', firewall_views.NetworkAddressObjectDetail, firewall_views.NetworkAddressObjectList)
            ChangeableObjectRegistry.__instance.register(firewall_models.RangeServiceObject, firewall_serializers.RangeServiceObjectSerializer, 'objects/services/ranges', firewall_views.RangeServiceObjectDetail, firewall_views.RangeServiceObjectList)
            ChangeableObjectRegistry.__instance.register(firewall_models.RuleSet, firewall_serializers.RuleSetSerializer, 'rulesets', firewall_views.RuleSetDetailView, firewall_views.RuleSetList)
            ChangeableObjectRegistry.__instance.register(firewall_models.SimpleServiceObject, firewall_serializers.SimpleServiceObjectSerializer, 'objects/services/simple', firewall_views.SimpleServiceObjectDetail, firewall_views.SimpleServiceObjectList)
            ChangeableObjectRegistry.__instance.register(network_models.Network, network_serializers.NetworkSerializer, 'networks', network_views.NetworkDetailView, network_views.NetworkList)
            ChangeableObjectRegistry.__instance.register(network_models.ManagedInterface, network_serializers.ManagedInterfaceSerializer, 'managedinterfaces', network_views.ManagedInterfaceDetailView, network_views.ManagedInterfaceList)
            ChangeableObjectRegistry.__instance.register(network_models.ManagedVRRPInterface, network_serializers.ManagedVRRPInterfaceSerializer, 'managedinterfaces/vrrp', network_views.ManagedVRRPInterfaceDetailView, network_views.ManagedVRRPInterfaceList)
        return ChangeableObjectRegistry.__instance

    @staticmethod
    def instance() -> 'ChangeableObjectRegistry':
        return ChangeableObjectRegistry()
    
    def register(self, model: Type[Model], serializer: Type[Serializer], path: Optional[str], single_view: Optional[Type[APIView]], list_view: Optional[Type[APIView]]) -> None:
        '''
        Register an owned object for more generic use.
        `single_view` and `list_view` are optional as for some types a separate view is useless
        (e.g. abstract models).
        '''
        name = model.__name__
        if name in ChangeableObjectRegistry.__instance.registry:
            return
        ChangeableObjectRegistry.__instance.registry[name] = ChangeableObjectEntry(model, serializer, path, single_view, list_view)

    def get(self, name: str) -> Optional[ChangeableObjectEntry]:
        '''
        Retrieve a registered type and it's meta information.
        '''
        if name in ChangeableObjectRegistry.__instance.registry:
            return ChangeableObjectRegistry.__instance.registry[name]

    def all(self) -> List[ChangeableObjectEntry]:
        '''
        Retrieve all registered types.
        '''
        return list(ChangeableObjectRegistry.registry.values())

    def create_url_patterns(self) -> List[URLPattern]:
        '''
        Creates url patterns for all registered types.
        '''
        rtn = []
        for changeable_object_type in ChangeableObjectRegistry.__instance.registry.values():
            if changeable_object_type.path:
                if changeable_object_type.list_view:
                    rtn.append(path(changeable_object_type.path, changeable_object_type.list_view.as_view()))
                if changeable_object_type.single_view:
                    rtn.append(path(changeable_object_type.path + '/<uuid:uuid>', changeable_object_type.single_view.as_view()))
        return rtn

