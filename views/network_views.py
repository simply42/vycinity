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

from django.http import Http404
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework import status
from typing import Any, List, Type
from vycinity.models import OWNED_OBJECT_STATE_LIVE, OWNED_OBJECT_STATE_PREPARED, change_models, customer_models, OwnedObject
from vycinity.models.network_models import Network, ManagedInterface, ManagedVRRPInterface
from vycinity.serializers.network_serializers import NetworkSerializer, ManagedInterfaceSerializer, ManagedVRRPInterfaceSerializer
from vycinity.views import GenericOwnedObjectDetail, GenericOwnedObjectList, ValidationResult


class NetworkList(GenericOwnedObjectList):
    def filter_attributes(self, object_list: List[Any], customer: customer_models.Customer):
        return object_list

    def get_model(self) -> Type[OwnedObject]:
        return Network

    def get_serializer(self) -> Type[Serializer]:
        return NetworkSerializer

    def post_validate(self, object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        return NetworkList.validate_network_semantically(object, customer, changeset)

    @staticmethod
    def validate_network_semantically(object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        rtn = ValidationResult()
        if object['owner'] not in customer.get_visible_customers():
            rtn.access_ok = False
        if 'ipv4_network_address' in object:
            if 'ipv4_network_bits' not in object:
                rtn.errors.append('Bits for IPv4 need to be set if network is used.')
            else:
                for potentially_colliding_network in Network.filter_query_by_liveness_or_changeset(Network.objects.filter(ipv4_network_address=object['ipv4_network_address'], ipv4_network_bits=object['ipv4_network_bits']), changeset).all():
                    if potentially_colliding_network.state == OWNED_OBJECT_STATE_LIVE or (potentially_colliding_network.state == OWNED_OBJECT_STATE_PREPARED and potentially_colliding_network.change.changeset == changeset):
                        rtn.errors.append('Collision in IPv4 Network')
        if 'ipv6_network_address' in object:
            if 'ipv6_network_bits' not in object:
                rtn.errors.append('Bits for IPv6 need to be set if network is used.')
            else:
                for potentially_colliding_network in Network.filter_query_by_liveness_or_changeset(Network.objects.filter(ipv6_network_address=object['ipv6_network_address'], ipv6_network_bits=object['ipv6_network_bits']), changeset).all():
                    if potentially_colliding_network.state == OWNED_OBJECT_STATE_LIVE or (potentially_colliding_network.state == OWNED_OBJECT_STATE_PREPARED and potentially_colliding_network.change.changeset == changeset):
                        rtn.errors.append('Collision in IPv6 Network')
        return rtn


class NetworkDetailView(GenericOwnedObjectDetail):
    def filter_attributes(self, object: Any, customer: customer_models.Customer):
        return object

    def get_model(self) -> Type[OwnedObject]:
        return Network
    
    def get_serializer(self):
        return NetworkSerializer

    def put_validate(self, object: Any, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        return NetworkList.validate_network_semantically(object, customer, changeset)


class ManagedInterfaceList(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        all_managed_interfaces = ManagedInterface.objects.all()
        return Response(ManagedInterfaceSerializer(all_managed_interfaces, many=True).data)

    def post(self, request, format=None):
        serializer = ManagedInterfaceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_201_CREATED)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ManagedInterfaceDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id, format=None):
        try:
            managed_interface = ManagedInterface.objects.get(pk=id)
            return Response(ManagedInterfaceSerializer(managed_interface).data)
        except ManagedInterface.DoesNotExist:
            raise Http404()
    
    def put(self, request, id, format=None):
        try:
            managed_interface = ManagedInterface.objects.get(pk=id)
            serializer = ManagedInterfaceSerializer(managed_interface, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(data=serializer.data)
            return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except ManagedInterface.DoesNotExist:
            raise Http404()

    def delete(self, request, id, format=None):
        try:
            managed_interface = ManagedInterface.objects.get(pk=id)
            managed_interface.delete()
            return Response(status.HTTP_204_NO_CONTENT)
        except ManagedInterface.DoesNotExist:
            raise Http404()


class ManagedVRRPInterfaceList(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        all_managed_vrrp_interfaces = ManagedVRRPInterface.objects.all()
        return Response(ManagedVRRPInterfaceSerializer(all_managed_vrrp_interfaces, many=True).data)

    def post(self, request, format=None):
        serializer = ManagedVRRPInterfaceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_201_CREATED)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ManagedVRRPInterfaceDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id, format=None):
        try:
            managed_vrrp_interface = ManagedVRRPInterface.objects.get(pk=id)
            return Response(ManagedVRRPInterfaceSerializer(managed_vrrp_interface).data)
        except ManagedVRRPInterface.DoesNotExist:
            raise Http404()
    
    def put(self, request, id, format=None):
        try:
            managed_vrrp_interface = ManagedVRRPInterface.objects.get(pk=id)
            serializer = ManagedVRRPInterfaceSerializer(managed_vrrp_interface, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(data=serializer.data)
            return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except ManagedVRRPInterface.DoesNotExist:
            raise Http404()

    def delete(self, request, id, format=None):
        try:
            managed_vrrp_interface = ManagedVRRPInterface.objects.get(pk=id)
            managed_vrrp_interface.delete()
            return Response(status.HTTP_204_NO_CONTENT)
        except ManagedVRRPInterface.DoesNotExist:
            raise Http404()