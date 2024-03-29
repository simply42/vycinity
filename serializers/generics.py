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
from vycinity.models.change_models import Change, ChangeSet, ACTION_CREATED, ACTION_DELETED, ACTION_MODIFIED
from vycinity.models.customer_models import Customer, User
import uuid

class AbstractOwnedObjectSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ['uuid', 'changeset']
        read_only_fields = fields

    changeset = serializers.SerializerMethodField()
    
    def get_changeset(self, obj: OwnedObject):
        request: Request = self._context['request']
        if not request or not isinstance(request, Request):
            raise AssertionError('request is not set as context for this serializer (or has wrong type). This causes errors while serialization.', request)
        if request.method == 'GET' and 'changeset' not in request.query_params:
            return None
        if 'changeset' in request.query_params:
            changeset_uuid = uuid.UUID(request.query_params['changeset'])
            try:
                change = obj.change.get()
                if change.changeset.id == changeset_uuid:
                    return changeset_uuid
            except Change.DoesNotExist:
                # This should not happen, but is not necessary an error.
                return None
        elif request.method in ['POST', 'PATCH', 'PUT']:
            try:
                change = obj.change.get()
                return change.changeset.id
            except Change.DoesNotExist:
                # This should not happen, but is not necessary an error.
                return None
        return None

    def update(self, instance, validated_data):
        if not isinstance(instance, AbstractOwnedObject):
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
        model: type[AbstractOwnedObject] = self.Meta.model # type: ignore

        changeset = None
        change = None
        if 'changeset' in request.query_params:
            changeset = ChangeSet.objects.get(pk=uuid.UUID(request.query_params['changeset']), owner__in=request.user.customer.get_visible_customers())
            if changeset.applied is not None:
                raise serializers.ValidationError('Changeset is already applied.')
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
        if change is None:
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
        request: Request = self._context['request']
        if not request or not isinstance(request, Request):
            raise AssertionError('request is not set as context for this serializer (or has wrong type). This makes operation impossible.', request)
        if not isinstance(request.user, User):
            raise AssertionError('request\'s user is not based on internal user definition. This makes changes impossible.')
        if not hasattr(self, 'Meta'):
            raise AssertionError('Meta is missing in this serializer')
        if not hasattr(self.Meta, 'model'): # type: ignore
            raise AssertionError('Meta\'s model is missing in this serializer')
        model: type[AbstractOwnedObject] = self.Meta.model # type: ignore

        changeset = None
        if 'changeset' in request.query_params:
            changeset = ChangeSet.objects.get(pk=uuid.UUID(request.query_params['changeset']), owner__in=request.user.customer.get_visible_customers())
            if changeset.applied is not None:
                raise serializers.ValidationError('Changeset is already applied')
        else:
            changeset = ChangeSet(owner=request.user.customer, user=request.user, owner_name=request.user.customer.name, user_name=request.user.name)
        change = Change(changeset=changeset, entity=model.__name__, action=ACTION_CREATED)

        instance = model()
        instance.state = OWNED_OBJECT_STATE_PREPARED
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
            setattr(instance, key, validated_value)
        instance.save()
        for key, validated_value in later_put_fields.items():
            manager = getattr(instance, key)
            manager.set(validated_value)
        changeset.save()
        change.post = instance
        change.save()
        return instance


class BaseOwnedObjectSerializer(AbstractOwnedObjectSerializer):
    class Meta:
        fields = AbstractOwnedObjectSerializer.Meta.fields + ['owner', 'public']
        read_only_fields = AbstractOwnedObjectSerializer.Meta.read_only_fields

    owner = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), pk_field=serializers.UUIDField(format='hex_verbose'), required=True)

    def validate_owner(self, value):
        request: Request = self._context['request']
        if not request or not isinstance(request, Request):
            raise AssertionError('request is not set as context for this serializer (or has wrong type). This causes errors while validation.', request)
        if value not in request.user.customer.get_visible_customers():
            raise serializers.ValidationError(['Owner is not accessible by current user.'])
        return value
