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

from typing import Type
from django.forms import ValidationError
from django.http import HttpRequest
from rest_framework import serializers
from rest_framework.fields import Field
from vycinity.models import OWNED_OBJECT_STATE_LIVE, OWNED_OBJECT_STATE_PREPARED, AbstractOwnedObject, OwnedObject
from vycinity.models.change_models import ChangeSet, ACTION_DELETED, ACTION_MODIFIED
from vycinity.models.customer_models import Customer, User
from vycinity.views import CHANGESET_APPLIED_ERROR
import uuid

class BaseOwnedObjectSerializer(serializers.ModelSerializer):
    def update(self, instance, validated_data):
        if not isinstance(instance, OwnedObject):
            raise AssertionError('Instance is no OwnedObject. This is a programming issue.')
        request: HttpRequest = self._context['request']
        if not request:
            raise AssertionError('request is not set as context for this serializer. This makes operation impossible.')
        if not isinstance(request.user, User):
            raise AssertionError('request\'s user is not based on internal user definition. This makes changes impossible.')
        if not hasattr(self, 'Meta'):
            raise AssertionError('Meta is missing in this serializer')
        if not hasattr(self.Meta, 'model'): # type: ignore
            raise AssertionError('Meta\'s model is missing in this serializer')
        
        changeset = None
        change = None
        if 'changeset' in request.GET:
            changeset = ChangeSet.objects.get(pk=uuid.UUID(request.GET['changeset']), owner__in=request.user.customer.get_visible_customers())
            if changeset.applied is not None:
                raise ValidationError(message = CHANGESET_APPLIED_ERROR)
            model: type[OwnedObject] = self.Meta.model # type: ignore
            thisname = model.__name__
            for actual_change in changeset.changes.all():
                if actual_change.entity == thisname and actual_change.post.uuid == instance.uuid:
                    instance = model.objects.get(pk=actual_change.post.pk)
                    change = actual_change
                    if change.action == ACTION_DELETED:
                        change.action = ACTION_MODIFIED
                    break
        else:
            changeset = ChangeSet(owner=request.user.customer, user=request.user, owner_name=request.user.customer.name, user_name=request.user.name)
        
        modified_instance = None
        if instance.state == OWNED_OBJECT_STATE_LIVE:
            modified_instance = self._model.objects.get(pk=instance.pk)
            modified_instance.pk = None
            modified_instance.id = None
            modified_instance._state.adding = True
            
        elif instance.state == OWNED_OBJECT_STATE_PREPARED:
            modified_instance = instance

        raise NotImplementedError()

    def create(self, validated_data):
        raise NotImplementedError()