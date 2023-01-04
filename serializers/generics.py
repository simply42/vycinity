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
from rest_framework import serializers
from rest_framework.relations import ManyRelatedField
from rest_framework.request import Request
from vycinity.models import OWNED_OBJECT_STATE_LIVE, OWNED_OBJECT_STATE_PREPARED, AbstractOwnedObject, OwnedObject
from vycinity.models.change_models import Change, ChangeSet, ACTION_DELETED, ACTION_MODIFIED
from vycinity.models.customer_models import Customer, User
from vycinity.views import CHANGESET_APPLIED_ERROR
import uuid

class BaseOwnedObjectSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ['uuid', 'changeset']
        read_only_fields = ['uuid', 'changeset']

    changeset = serializers.SerializerMethodField()

    def get_changeset(self, obj: OwnedObject):
        if obj.change is None:
            return None
        return str(obj.change.get().changeset.id)

    def update(self, instance, validated_data):
        if not isinstance(instance, OwnedObject):
            raise AssertionError('Instance is no OwnedObject. This is a programming issue.')
        request: Request = self._context['request']
        if not request or not isinstance(request, Request):
            raise AssertionError('request is not set as context for this serializer (or has wrong type). This makes operation impossible.', request)
        if not isinstance(request.user, User):
            raise AssertionError('request\'s user is not based on internal user definition. This makes changes impossible.')
        if not hasattr(self, 'Meta'):
            raise AssertionError('Meta is missing in this serializer')
        if not hasattr(self.Meta, 'model'): # type: ignore
            raise AssertionError('Meta\'s model is missing in this serializer')
        model: type[OwnedObject] = self.Meta.model # type: ignore

        changeset = None
        change = None
        if 'changeset' in request.query_params:
            changeset = ChangeSet.objects.get(pk=uuid.UUID(request.query_params['changeset']), owner__in=request.user.customer.get_visible_customers())
            if changeset.applied is not None:
                raise serializers.ValidationError('nope!')
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
            change = Change(changeset=changeset, entity=model.__name__, action=ACTION_MODIFIED)
        
        modified_instance: OwnedObject
        if instance.state == OWNED_OBJECT_STATE_LIVE:
            modified_instance: OwnedObject = model.objects.get(pk=instance.pk)
            modified_instance.pk = None
            modified_instance.id = None
            modified_instance._state.adding = True
            change.pre = instance # type: ignore
        elif instance.state == OWNED_OBJECT_STATE_PREPARED:
            modified_instance = instance
        else:
            raise AssertionError('Update called on object with state neither live or prepared', instance)

        modified_instance.state = OWNED_OBJECT_STATE_PREPARED
        later_put_fields = {}
        all_fields = self.fields
        for key, validated_value in validated_data.items():
            if key not in all_fields.keys():
                raise AssertionError(f'Field {key} is not defined.')
            if all_fields[key].read_only:
                continue
            if isinstance(self.fields[key], ManyRelatedField):
                later_put_fields[key] = validated_value
                continue
            setattr(modified_instance, key, validated_value)
        modified_instance.save()
        for key, validated_value in later_put_fields.items():
            manager = getattr(modified_instance, key)
            manager.set(validated_value)
        changeset.save()
        change.post = modified_instance
        change.save()

        return modified_instance

    def create(self, validated_data):
        raise NotImplementedError()