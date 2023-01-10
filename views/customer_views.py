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

from rest_framework import permissions
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.request import Request
from rest_framework.schemas.openapi import AutoSchema
from vycinity.models.customer_models import Customer, User
from vycinity.serializers.customer_serializers import CustomerSerializer

class CustomerSchema(AutoSchema):
    def get_serializer(self, path, method):
        return CustomerSerializer()

class CustomerList(ListCreateAPIView):
    '''
    get:
        Returns visible customers for the current user.

    post:
        Creates a new customer.
    '''
    schema = CustomerSchema(tags=['customer'], operation_id_base='Customer', component_name='Customer')
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CustomerSerializer

    def get_queryset(self):
        '''
        Overrides ListCreateAPIView.get_queryset(). Returns a queryset including the current changeset.
        '''
        if not isinstance(self.request.user, User):
            raise AssertionError('Non usable user tries to retrieve an owned object.')

        request: Request = self.request # type: ignore
        pk_list = map(lambda c: c.pk, request.user.customer.get_visible_customers())
        return Customer.objects.filter(pk__in=pk_list)


class IsOwnedCustomerForReadAndNotSameForWrite(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if not isinstance(request, Request):
            raise AssertionError('request is of wrong type.', request)
        if not request.user:
            return False
        if not isinstance(request.user, User):
            raise AssertionError('request\'s user is not of a usable type.', request.user)
        if obj not in request.user.customer.get_visible_customers():
            return False
        if request.method in ['PATCH', 'PUT', 'DELETE']:
            if obj.pk == request.user.customer.pk:
                return False
        return True

class CustomerDetailView(RetrieveUpdateDestroyAPIView):
    schema = CustomerSchema(tags=['customer'], operation_id_base='Customer', component_name='Customer')
    permission_classes = [IsOwnedCustomerForReadAndNotSameForWrite]
    serializer_class = CustomerSerializer
    queryset = Customer.objects.all()