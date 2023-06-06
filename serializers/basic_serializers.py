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
from vycinity.models import basic_models

class Vyos13RouterSerializer(serializers.ModelSerializer):
    class Meta:
        model = basic_models.Vyos13Router
        fields = ['id', 'name', 'loopback', 'deploy', 'token', 'fingerprint', 'active_static_configs', 'managed_interface_context']
        read_only_fields = ['id']

class Vyos13StaticConfigSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = basic_models.Vyos13StaticConfigSection
        fields = ['id', 'context', 'description', 'absolute', 'content']
        read_only_fields = ['id']

class Vyos13LiveRouterConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = basic_models.Vyos13LiveRouterConfig
        fields = ['id', 'retrieved', 'config']
        read_only_fields = fields

class Vyos13RouterConfigDiffSerializer(serializers.Serializer):
    left = serializers.DictField(allow_empty=True)
    right = serializers.DictField(allow_empty=True)

class Vyos13RouterConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = basic_models.Vyos13RouterConfig
        fields = ['id', 'created', 'router', 'config']
        read_only_fields = fields

class DeploymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = basic_models.Deployment
        fields = ['id', 'triggered', 'last_update', 'configs', 'change', 'state', 'errors', 'comment']
        read_only_fields = fields