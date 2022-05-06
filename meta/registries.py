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

from typing import Callable, List, Type, Optional
from collections import namedtuple
from django.db.models import Model
from django.urls import URLPattern, path
from rest_framework.views import APIView
from rest_framework.serializers import Serializer

from vycinity.models.change_models import ACTION_CREATED, ACTION_DELETED, ACTION_MODIFIED, Change


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
            ChangeableObjectRegistry.__instance.update_hook_registy = {}

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

            ChangeableObjectRegistry.__instance.register_for_version_change(network_models.Network, network_models.ManagedInterface.update_networks)
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

    def register_for_version_change(self, model: Type[Model], hook: Callable[[Optional[Model],Optional[Model]],None]) -> None:
        '''
        Registers a hook for getting notified when a generic object gets changed.

        As generic objects versions work by duplicating them on change, references should be
        updated to ensure there are no broken references. This should be done in the registered
        hook.

        Params:
            model: The type the hook should be triggered for.
            hook: A callable with following parameters:
                    - pre: The old object. Set to None if the Object is created.
                    - post: The new object. Set to None if the Object is deleted.
                  The result of the callable is ignored.
        '''
        name = model.__name__
        if name not in ChangeableObjectRegistry.__instance.registry:
            return
        if name not in ChangeableObjectRegistry.__instance.update_hook_registy:
            ChangeableObjectRegistry.__instance.update_hook_registy[name] = []
        ChangeableObjectRegistry.__instance.update_hook_registy[name].append(hook)

    def get(self, name: str) -> Optional[ChangeableObjectEntry]:
        '''
        Retrieve a registered type and it's meta information.
        '''
        if name in ChangeableObjectRegistry.__instance.registry:
            return ChangeableObjectRegistry.__instance.registry[name]

    def notify_about_change(self, change: Change) -> None:
        '''
        Notify registered hooks about a change.
        '''
        name = type(change.post).__name__
        if name in ChangeableObjectRegistry.__instance.update_hook_registy:
            for hook in ChangeableObjectRegistry.__instance.update_hook_registy[name]:
                if change.action == ACTION_CREATED:
                    hook(None, change.post)
                elif change.action == ACTION_MODIFIED:
                    hook(change.pre, change.post)
                elif change.action == ACTION_DELETED:
                    hook(change.pre, None)


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

