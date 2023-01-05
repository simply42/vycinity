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

from abc import ABC, abstractmethod
from django.http import Http404, HttpResponseForbidden
from django.db.models import Q
from rest_framework import exceptions, status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.serializers import Serializer, ValidationError
from vycinity.models import OWNED_OBJECT_STATE_DELETED, OWNED_OBJECT_STATE_PREPARED, customer_models, change_models, AbstractOwnedObject, OWNED_OBJECT_STATE_LIVE
from vycinity.permissions import IsOwnerOfObjectOrPublicObject
from typing import Any, List, Dict, Optional, Type
from uuid import UUID


CHANGESET_APPLIED_ERROR = 'Changeset is already applied.'

class GenericOwnedObjectSchema(AutoSchema):
    def __init__(self, serializer: Type[Serializer], **kwargs):
        super().__init__(**kwargs)
        self.serializer = serializer

    def get_operation(self, path, method):
        current_operation = super().get_operation(path, method)
        current_operation['parameters'].append({'name': 'changeset', 'in': 'query', 'description': 'The changeset as context for the current operation', 'required': False, 'schema': {'type': 'string', 'example': 'fe056b4b-9ca6-43c1-91e3-74b80fcca7da'}})
        return current_operation

    def get_serializer(self, path, method):
        return self.serializer()

class GenericSchema(AutoSchema):
    def __init__(self, serializer: Type[Serializer], **kwargs):
        super().__init__(**kwargs)
        self.serializer = serializer
    
    def get_serializer(self, path, method):
        return self.serializer()

class GenericOwnedObjectList(ListCreateAPIView, ABC):
    permission_classes = [IsOwnerOfObjectOrPublicObject]

    @abstractmethod
    def get_model(self) -> Type[AbstractOwnedObject]:
        raise NotImplementedError('Model is not set.')

    def get_queryset(self):
        '''
        Overrides ListCreateAPIView.get_queryset(). Returns a queryset including the current changeset.
        '''
        if not isinstance(self.request.user, customer_models.User):
            raise AssertionError('Non usable user tries to retrieve an owned object.')

        request: Request = self.request # type: ignore
        visible_customers = request.user.customer.get_visible_customers()
        if 'changeset' in request.query_params:
            try:
                changeset = change_models.ChangeSet.objects.get(pk=UUID(self.request.GET['changeset']), owner__in=visible_customers)
                return self.get_model().filter_by_changeset_and_visibility(query=self.get_model().objects.all(), changeset=changeset, visible_customers=visible_customers)
            except ValueError as e:
                raise e
            except change_models.ChangeSet.DoesNotExist as e:
                raise Http404 from e
        else:
            return self.get_model().filter_query_by_customers_or_public(self.get_model().objects.filter(state=OWNED_OBJECT_STATE_LIVE), visible_customers)


class GenericOwnedObjectDetail(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsOwnerOfObjectOrPublicObject]
    lookup_field = 'uuid'
    lookup_url_kwarg = 'uuid'

    @abstractmethod
    def get_model(self) -> Type[AbstractOwnedObject]:
        raise NotImplementedError('Model is not set.')

    def get_queryset(self):
        '''
        Overrides RetrieveUpdateDestroyAPIView.get_queryset(). Returns a queryset including the current changeset.
        '''
        if not isinstance(self.request.user, customer_models.User):
            raise AssertionError('Non usable user tries to retrieve an owned object.')

        request: Request = self.request # type: ignore
        visible_customers = request.user.customer.get_visible_customers()
        if 'changeset' in request.query_params:
            try:
                changeset = change_models.ChangeSet.objects.get(pk=UUID(self.request.GET['changeset']), owner__in=visible_customers)
                return self.get_model().filter_by_changeset_and_visibility(query=self.get_model().objects.all(), changeset=changeset, visible_customers=visible_customers)
            except ValueError as e:
                raise e
            except change_models.ChangeSet.DoesNotExist as e:
                raise Http404 from e
        else:
            return self.get_model().filter_query_by_customers_or_public(self.get_model().objects.filter(state=OWNED_OBJECT_STATE_LIVE), visible_customers)


    def destroy(self, request, *args, **kwargs):
        '''
        Overwritten as deletion does complete different things from standardized rest apis.

        A changeset will be returned Instead of a typical "204 No Content" if everything goes well.

        A better way would be to move the changeset parameter to a header, DRF currently does not
        allow that without rewriting much more.
        '''
        instance = self.get_object()
        changeset = self.perform_destroy(instance)
        return Response(status=status.HTTP_200_OK, data={'changeset': changeset.id})

    def perform_destroy(self, instance):
        if not isinstance(instance, AbstractOwnedObject):
            raise AssertionError(f'An OwnedObject should be given, but got {type(instance).__name__}')
        request: Request = self.request # type: ignore

        changeset = None
        change = None

        if 'changeset' in request.query_params:
            try:
                changeset_uuid = UUID(request.query_params['changeset'])
                changeset = change_models.ChangeSet.objects.get(id=changeset_uuid, owner__in=request.user.customer.get_visible_customers())
                if changeset.applied is not None:
                    raise ValidationError({'changeset': CHANGESET_APPLIED_ERROR})
                thisname = self.get_model().__name__
                for actual_change in changeset.changes.all():
                    if actual_change.entity == thisname and actual_change.post.uuid == instance.uuid:
                        instance = self.get_model().objects.get(pk=actual_change.post.pk)
                        change = actual_change
                        break
            except change_models.ChangeSet.DoesNotExist as dne_exc:
                raise exceptions.NotFound(detail='Change set could not be found') from dne_exc
            except ValueError as ve:
                raise exceptions.ParseError(detail='Change set could not be parsed') from ve
        if changeset is None:
            changeset = change_models.ChangeSet(owner=request.user.customer, user=request.user, owner_name=request.user.customer.name, user_name=request.user.name)
        if change is None:
            change = change_models.Change(changeset=changeset, entity=self.get_model().__name__, action=change_models.ACTION_DELETED)
        if instance.state == OWNED_OBJECT_STATE_LIVE:
            try:
                change.pre = instance # type: ignore
                instance = self.get_model().objects.get(pk=change.pre.pk)
                instance.id = None
                instance.pk = None
                instance._state.adding = True
            except self.get_model().DoesNotExist as dne_exc:
                raise AssertionError('This error should not happen as the instance with same pk was already found.') from dne_exc
        
        changeset.save()
        instance.state = OWNED_OBJECT_STATE_DELETED
        instance.save()
        change.post = instance
        change.save()

        return changeset


# def scan_for_owned_objects(module, _allowed_package: Optional[List[str]] = None, _accumulator: List[ModuleType] = []):
#     rtn = {}
#     if _allowed_package is None:
#         _allowed_package = module.__name__.split('.')
#     for child_name in dir(module):
#         child = getattr(module, child_name)
#         if inspect.isclass(child) and issubclass(child, AbstractOwnedObject) and child not in [AbstractOwnedObject, OwnedObject, SemiOwnedObject]:
#             rtn[child.__name__] = child
#         elif inspect.ismodule(child):
#             if child in _accumulator or child.__package__.split('.')[0:len(_allowed_package)] != _allowed_package:
#                 continue
#             for (name, cls) in scan_for_owned_objects(child, _allowed_package, _accumulator + [module]).items():
#                 rtn[name] = cls
#     return rtn