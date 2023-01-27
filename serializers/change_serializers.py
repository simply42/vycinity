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

from rest_framework.serializers import ModelSerializer, PrimaryKeyRelatedField
from vycinity import models
from vycinity.models import change_models

class ChangeSetSerializer(ModelSerializer):
    class Meta:
        model = change_models.ChangeSet
        fields = ['id', 'owner', 'owner_name', 'user', 'user_name', 'created', 'modified', 'applied', 'changes']
        read_only_fields = fields

    changes = PrimaryKeyRelatedField(many=True, read_only=True)

class ChangeSerializer(ModelSerializer):
    class Meta:
        model = change_models.Change
        fields = ['id', 'changeset', 'entity', 'pre', 'post', 'new_uuid']
        read_only_fields = fields