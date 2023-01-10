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

from rest_framework import serializers
from rest_framework.request import Request
from vycinity.models.customer_models import Customer

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'parent_customer']
        read_only_fields = ['id']

    parent_customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), allow_null=False, pk_field=serializers.UUIDField(format='hex_verbose'))

    def validate_parent_customer(self, value):
        request: Request = self._context['request']
        if not request or not isinstance(request, Request):
            raise AssertionError('request is not set as context for this serializer (or has wrong type). This causes errors while validation.', request)
        if value not in request.user.customer.get_visible_customers():
            raise serializers.ValidationError(['Owner is not accessible by current user.'])
        return value
