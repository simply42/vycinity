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

from django.http import Http404, HttpResponseForbidden
from rest_framework import permissions
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework import status
from typing import Type
from vycinity.models import OwnedObject
from vycinity.models.network_models import Network, ManagedInterface, ManagedVRRPInterface
from vycinity.permissions import IsRootCustomer
from vycinity.serializers.network_serializers import NetworkSerializer, ManagedInterfaceSerializer, ManagedVRRPInterfaceSerializer
from vycinity.views import GenericOwnedObjectDetail, GenericOwnedObjectList, GenericOwnedObjectSchema, GenericSchema


class NetworkList(GenericOwnedObjectList):
    '''
    get:
        Retrieve the list of networks.

    post:
        Create a new network.
    '''
    schema = GenericOwnedObjectSchema(NetworkSerializer, tags=['network'], operation_id_base='Network', component_name='Name')

    def get_model(self) -> Type[OwnedObject]:
        return Network

    def get_serializer_class(self) -> Type[Serializer]:
        return NetworkSerializer


class NetworkDetailView(GenericOwnedObjectDetail):
    '''
    get:
        Retrieve the a network.

    put:
        Update a network.

    delete:
        Delete a network.
    '''
    schema = GenericOwnedObjectSchema(NetworkSerializer, tags=['network'], operation_id_base='Network', component_name='Name')

    def get_model(self) -> Type[OwnedObject]:
        return Network
    
    def get_serializer_class(self):
        return NetworkSerializer


class ManagedInterfaceList(ListCreateAPIView):
    '''
    get:
        Return all managed interfaces.

    post:
        Create a managed interface.
    '''
    schema = GenericSchema(serializer=ManagedInterfaceSerializer, tags=['managed interface'], operation_id_base='ManagedInterface', component_name='ManagedInterface')
    permission_classes = [IsRootCustomer]
    queryset = ManagedInterface.objects.all()
    serializer_class = ManagedInterfaceSerializer

class ManagedInterfaceDetailView(RetrieveUpdateDestroyAPIView):
    '''
    get:
        Return a single managed interfaces.

    put:
        Update a managed interface.
    
    delete:
        Delete a managed interface.
    '''
    schema = GenericSchema(serializer=ManagedInterfaceSerializer, tags=['managed interface'], operation_id_base='ManagedInterface', component_name='ManagedInterface')
    permission_classes = [IsRootCustomer]
    queryset = ManagedInterface.objects.all()
    serializer_class = ManagedInterfaceSerializer

class ManagedVRRPInterfaceList(APIView):
    '''
    get:
        Retrieve all managed interfaces with redundancy via VRRP.

    post:
        Create a managed interface with redundancy via VRRP.
    '''
    schema = GenericSchema(serializer=ManagedVRRPInterfaceSerializer, tags=['managed interface', 'managed vrrp interface'], operation_id_base='ManagedVRRPInterface', component_name='ManagedVRRPInterface')
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        if request.user.customer.parent_customer is not None:
            return HttpResponseForbidden()
        all_managed_vrrp_interfaces = ManagedVRRPInterface.objects.all()
        return Response(ManagedVRRPInterfaceSerializer(all_managed_vrrp_interfaces, many=True).data)

    def post(self, request, format=None):
        if request.user.customer.parent_customer is not None:
            return HttpResponseForbidden()
        serializer = ManagedVRRPInterfaceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_201_CREATED)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ManagedVRRPInterfaceDetailView(APIView):
    '''
    get:
        Retrieve a specific managed VRRP interface.

    put:
        Update a managed VRRP interface.

    delete:
        Update a managed VRRP interface.
    '''
    schema = GenericSchema(serializer=ManagedVRRPInterfaceSerializer, tags=['managed interface', 'managed vrrp interface'], operation_id_base='ManagedVRRPInterface', component_name='ManagedVRRPInterface')
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id, format=None):
        if request.user.customer.parent_customer is not None:
            return HttpResponseForbidden()
        try:
            managed_vrrp_interface = ManagedVRRPInterface.objects.get(pk=id)
            return Response(ManagedVRRPInterfaceSerializer(managed_vrrp_interface).data)
        except ManagedVRRPInterface.DoesNotExist:
            raise Http404()
    
    def put(self, request, id, format=None):
        if request.user.customer.parent_customer is not None:
            return HttpResponseForbidden()
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
        if request.user.customer.parent_customer is not None:
            return HttpResponseForbidden()
        try:
            managed_vrrp_interface = ManagedVRRPInterface.objects.get(pk=id)
            managed_vrrp_interface.delete()
            return Response(status.HTTP_204_NO_CONTENT)
        except ManagedVRRPInterface.DoesNotExist:
            raise Http404()