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

import uuid
from django.db import models
from django.core.exceptions import ValidationError

from vycinity.models import customer_models
from vycinity.models import basic_models
from vycinity.models import OwnedObject

def validate_ipv6_network_bits(value):
    if value < 0 or value > 64:
        raise ValidationError('Bit length is not in valid range 0-64')

def validate_ipv4_network_bits(value):
    if value < 0 or value > 30:
        raise ValidationError('Bit length is not in valid range 0-30')

def validate_layer2_id(value):
    if value < 1 or value > 4093:
        raise ValidationError('Layer2 network id is not in valid range 1-4093')

class Network(OwnedObject):
    ipv4_network_address = models.GenericIPAddressField(null=True, unique=True, protocol='IPv4')
    ipv4_network_bits = models.IntegerField(null=True, validators=[validate_ipv4_network_bits])
    ipv6_network_address = models.GenericIPAddressField(null=True, unique=True, protocol='IPv6')
    ipv6_network_bits = models.IntegerField(null=True, validators=[validate_ipv6_network_bits])
    layer2_network_id = models.IntegerField(validators=[validate_layer2_id])
    name = models.CharField(max_length=64)
    vrrp_password = models.CharField(max_length=8, null=True)

class ManagedInterface(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    router = models.ForeignKey(to=basic_models.Router, on_delete=models.CASCADE)
    ipv4_address = models.GenericIPAddressField(null=True, protocol='IPv4')
    ipv6_address = models.GenericIPAddressField(null=True, protocol='IPv6')
    network = models.ForeignKey(to=Network, on_delete=models.CASCADE)

class ManagedVRRPInterface(ManagedInterface):
    ipv4_service_address = models.GenericIPAddressField(null=True, protocol='IPv4')
    ipv6_service_address = models.GenericIPAddressField(null=True, protocol='IPv6')
    priority = models.IntegerField()
    vrid = models.IntegerField()
