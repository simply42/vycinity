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

from django.http import Http404, HttpResponseForbidden, HttpResponseBadRequest
from django.db.models import Q
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.schemas.openapi import AutoSchema
from rest_framework import status
from vycinity.models.customer_models import Customer
from vycinity.serializers.customer_serializers import CustomerSerializer

class CustomerSchema(AutoSchema):
    def get_serializer(self, path, method):
        return CustomerSerializer()

class CustomerList(APIView):
    '''
    get:
        Returns visible customers for the current user.

    post:
        Creates a new customer.
    '''
    schema = CustomerSchema(tags=['customer'], operation_id_base='Customer', component_name='Customer')
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        all_customers = request.user.customer.get_visible_customers()
        return Response(CustomerSerializer(all_customers, many=True).data)

    def post(self, request, format=None):
        customer_serializer = CustomerSerializer(data=request.data)
        if customer_serializer.is_valid():
            if (not 'parent_customer' in customer_serializer.validated_data or
                    customer_serializer.validated_data['parent_customer'] is None):
                return Response(data={'parent_customer':['creating root customers is not allowed.']}, status=status.HTTP_400_BAD_REQUEST)
            if (not customer_serializer.validated_data['parent_customer'] in 
                    request.user.customer.get_visible_customers()):
                return Response(data={'parent_customer':['access to referred customer is forbidden.']}, status=status.HTTP_403_FORBIDDEN)
            customer_serializer.save()
            return Response(data=customer_serializer.data, status=status.HTTP_201_CREATED)
        return Response(data=customer_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomerDetailView(APIView):
    '''
    get:
        Return a specific customer.

    put:
        Update a customer.

    delete:
        Delete a customer.
    '''
    schema = CustomerSchema(tags=['customer'], operation_id_base='Customer', component_name='Customer')
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id, format=None):
        try:
            customer = Customer.objects.get(pk=id)
            if not customer in request.user.customer.get_visible_customers():
                return HttpResponseForbidden()
            return Response(CustomerSerializer(customer).data)
        except Customer.DoesNotExist:
            raise Http404()
    
    def put(self, request, id, format=None):
        try:
            customer = Customer.objects.get(pk=id)
            serializer = CustomerSerializer(customer, data=request.data)
            if serializer.is_valid():
                visible_customers = request.user.customer.get_visible_customers()
                if not customer in visible_customers:
                    return Response(data={'id':['access denied']}, status=status.HTTP_403_FORBIDDEN)
                if not "parent_customer" in serializer.validated_data:
                    return Response(data={'parent_customer':['changing to a root customer is not allowed.']}, status=status.HTTP_400_BAD_REQUEST)
                if not serializer.validated_data["parent_customer"] in visible_customers:
                    return Response(data={'parent_customer':['access to customer is denied']}, status=status.HTTP_403_FORBIDDEN)
                if id == request.user.customer.id:
                    return Response(data={'id':['modifying the own customer is not allowed.']}, status=status.HTTP_400_BAD_REQUEST)
                serializer.save()
                return Response(data=serializer.data)
            return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Customer.DoesNotExist:
            raise Http404()

    def delete(self, request, id, format=None):
        try:
            customer = Customer.objects.get(pk=id)
            if id == request.user.customer.id:
                return Response(data={'id':['Can\'t delete own customer.']}, status=status.HTTP_400_BAD_REQUEST)
            if not customer in request.user.customer.get_visible_customers():
                return Response(data={'id':['access denied.']}, status=status.HTTP_403_FORBIDDEN)
            customer.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Customer.DoesNotExist:
            raise Http404()