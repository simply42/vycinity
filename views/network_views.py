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
from rest_framework import status
from vycinity.models.network_models import Network, ManagedInterface, ManagedVRRPInterface
from vycinity.serializers.network_serializers import NetworkSerializer, ManagedInterfaceSerializer, ManagedVRRPInterfaceSerializer

class NetworkList(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        all_networks = Network.objects.all()
        return Response(NetworkSerializer(all_networks, many=True).data)

    def post(self, request, format=None):
        network_serializer = NetworkSerializer(data=request.data)
        if network_serializer.is_valid():
            network_serializer.save()
            return Response(data=network_serializer.data, status=status.HTTP_201_CREATED)
        return Response(data=network_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class NetworkDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id, format=None):
        try:
            network = Network.objects.get(pk=id)
            return Response(NetworkSerializer(network).data)
        except Network.DoesNotExist:
            raise Http404()
    
    def put(self, request, id, format=None):
        try:
            network = Network.objects.get(pk=id)
            serializer = NetworkSerializer(network, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(data=serializer.data)
            return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Network.DoesNotExist:
            raise Http404()

    def delete(self, request, id, format=None):
        try:
            network = Network.objects.get(pk=id)
            network.delete()
            return Response(status.HTTP_204_NO_CONTENT)
        except Network.DoesNotExist:
            raise Http404()


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