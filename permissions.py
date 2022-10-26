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

from rest_framework.permissions import BasePermission
from vycinity.models import customer_models

class IsRootCustomer(BasePermission):
    """
    Allows actions if the authenticated user is part of the root customer.
    """

    def has_permission(self, request, view):
        return (isinstance(request.user, customer_models.User) and request.user.customer.parent_customer is None)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)