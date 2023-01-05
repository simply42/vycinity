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

from django.http import HttpRequest
from rest_framework.permissions import BasePermission
from vycinity.models import AbstractOwnedObject, customer_models

class IsRootCustomer(BasePermission):
    """
    Allows actions if the authenticated user is part of the root customer.
    """

    def has_permission(self, request, view):
        return (isinstance(request.user, customer_models.User) and request.user.customer.parent_customer is None)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)

class IsOwnerOfObjectOrPublicObject(BasePermission):
    """
    Allows to access a specific object, when the object is public and it's a
    read request or when the object belongs to the users customer.
    """
    
    def has_object_permission(self, request: HttpRequest, view, obj):
        user = request.user
        if not user or not isinstance(user, customer_models.User) or not isinstance(obj, AbstractOwnedObject):
            return False
        if obj.owned_by(user.customer):
            return True
        if hasattr(obj, 'public') and obj.public and request.method == 'GET':
            return True
        return False