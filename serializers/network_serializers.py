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
from vycinity.models.network_models import Network, ManagedInterface, ManagedVRRPInterface

class NetworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Network
        fields = ['id', 'owner', 'ipv4_network_address', 'ipv4_network_bits', 'ipv6_network_address', 'ipv6_network_bits', 'layer2_network_id', 'name', 'vrrp_password']
        read_only_fields = ['id']

class ManagedInterfaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagedInterface
        fields = ['id', 'router', 'ipv4_address', 'ipv6_address', 'network']
        read_only_fields = ['id']

class ManagedVRRPInterfaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagedVRRPInterface
        fields = ['id', 'router', 'ipv4_address', 'ipv6_address', 'network', 'ipv4_service_address', 'ipv6_service_address', 'priority', 'vrid']
        read_only_fields = ['id']
