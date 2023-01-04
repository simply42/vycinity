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
from rest_framework import status
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.serializers import Serializer
from vycinity.models import OWNED_OBJECT_STATE_DELETED, OWNED_OBJECT_STATE_PREPARED, customer_models, change_models, OwnedObject, OWNED_OBJECT_STATE_LIVE
from vycinity.permissions import IsOwnerOfObjectOrPublicObject
from typing import Any, List, Dict, Optional, Type
from uuid import UUID


CHANGESET_APPLIED_ERROR = 'Changeset is already applied.'

class ValidationResult:
    '''
    Ergebnis einer Eingabe-Validierung.
    '''

    def __init__(self, access_ok: bool = True, errors: Dict[str,List[str]] = []):
        '''
        Erstellt ein Ergebnis.

        params:
            access_ok: Ob der Zugang für die zusätzlich angegebene Entität
                       erlaubt ist.
            errors: Eine Liste mit sonstigen, semantischen Fehlern in den
                    Angaben.
        '''
        self.access_ok = access_ok
        self.errors = errors

    def is_ok(self) -> bool:
        '''
        Gibt zurück ob das gegebene Objekt logisch und aus Zugangssicht
        speicherbar ist.
        '''
        return self.access_ok and len(self.errors) == 0

VALIDATION_OK = ValidationResult(access_ok=True, errors=[])

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

class GenericOwnedObjectList(APIView, ABC):
    permission_classes = [IsOwnerOfObjectOrPublicObject]

    @abstractmethod
    def get_model(self) -> Type[OwnedObject]:
        raise NotImplementedError('Model is not set.')

    @abstractmethod
    def get_serializer(self) -> Type[Serializer]:
        raise NotImplementedError('Serializer is not set.')

    @abstractmethod
    def filter_attributes(self, object_list: List[Any], customer: customer_models.Customer):
        raise NotImplementedError('filter_attributes is not defined.')

    @abstractmethod
    def post_validate(self, object: dict, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        raise NotImplementedError('post_validate is not defined.')

    def validate_owner(self):
        return True

    def get(self, request, format=None):
        model = self.get_model()
        relevant_changes: List[change_models.Change] = []
        if 'changeset' in request.GET:
            try:
                changeset = change_models.ChangeSet.objects.get(id=request.GET['changeset'])
                if not changeset.owner in request.user.customer.get_visible_customers():
                    return HttpResponseForbidden()
                for change in changeset.changes.all():
                    if change.entity == self.get_model().__name__:
                        relevant_changes.append(change)
                        break
            except change_models.ChangeSet.DoesNotExist as dne_exc:
                raise Http404() from dne_exc
        instances = model.filter_query_by_customers_or_public(model.objects.filter(state=OWNED_OBJECT_STATE_LIVE), 
            request.user.customer.get_visible_customers())
        for relevant_change in relevant_changes:
            if relevant_change.action == change_models.ACTION_CREATED:
                instances.append(self.get_model().objects.get(pk=relevant_change.post.pk))
            elif relevant_change.action == change_models.ACTION_MODIFIED:
                instances = list(filter(lambda i: relevant_change.pre.uuid != i.uuid, instances))
                instances.append(self.get_model().objects.get(pk=relevant_change.post.pk))
            elif relevant_change.action == change_models.ACTION_DELETED:
                instances = list(filter(lambda i: relevant_change.post.uuid != i.uuid, instances))
            else:
                raise ValueError('Action %s is not defined.' % relevant_change.action)
        serialized_data = self.get_serializer()(instances, many=True).data

        return Response(self.filter_attributes(serialized_data, request.user.customer))


    def post(self, request, format=None):
        serializer = self.get_serializer()(data=request.data)
        changeset = change_models.ChangeSet(owner=request.user.customer, user=request.user, owner_name=request.user.customer.name, user_name=request.user.name)
        if 'changeset' in request.GET:
            changeset_id = UUID(request.GET['changeset'])
            changeset = change_models.ChangeSet.objects.get(id=changeset_id)
            if changeset.owner != request.user.customer:
                return Response(data={'changeset':['access to this changeset is denied']}, status=status.HTTP_403_FORBIDDEN)
            if changeset.applied is not None:
                return Response({'changeset': CHANGESET_APPLIED_ERROR}, status=status.HTTP_400_BAD_REQUEST)
        change = change_models.Change(entity=self.get_model().__name__, action=change_models.ACTION_CREATED)
        
        if serializer.is_valid():
            if self.validate_owner():
                visible_customers = request.user.customer.get_visible_customers()
                if not serializer.validated_data['owner'] in visible_customers:
                    return Response(data={'owner':['access to the owner is denied']}, status=status.HTTP_403_FORBIDDEN)
            semantic_validation = self.post_validate(serializer.validated_data, request.user.customer, changeset)
            if semantic_validation.is_ok():
                changeset.save()
                created_obj = serializer.save(state=OWNED_OBJECT_STATE_PREPARED)
                change.changeset = changeset
                change.post = created_obj
                change.save()

                serialized_object = self.get_serializer()(created_obj).data
                serialized_object['changeset'] = str(changeset.id)
                return Response(data=serialized_object, status=status.HTTP_201_CREATED)
            else:
                rtn_status = status.HTTP_400_BAD_REQUEST
                if not semantic_validation.access_ok:
                    rtn_status = status.HTTP_403_FORBIDDEN
                return Response(data=semantic_validation.errors, status=rtn_status)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GenericOwnedObjectDetail(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsOwnerOfObjectOrPublicObject]
    lookup_field = 'uuid'
    lookup_url_kwarg = 'uuid'

    @abstractmethod
    def get_model(self) -> Type[OwnedObject]:
        raise NotImplementedError('Model is not set.')

    #@abstractmethod
    #def get_serializer(self):
    #    raise NotImplementedError('Serializer is not set.')

    @abstractmethod
    def filter_attributes(self, object: Any, customer: customer_models.Customer):
        raise NotImplementedError('filter_attributes is not defined.')

    @abstractmethod
    def put_validate(self, object: Any, customer: customer_models.Customer, changeset: change_models.ChangeSet) -> ValidationResult:
        raise NotImplementedError('put_validate is not defined.')

    def validate_owner(self):
        return True

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

    # def put(self, request, uuid, format=None):
    #     instance = None
    #     changeset = None
    #     change = None
    #     if 'changeset' in request.GET:
    #         try:
    #             changeset = change_models.ChangeSet.objects.get(id=request.GET['changeset'])
    #             if not changeset.owner in request.user.customer.get_visible_customers():
    #                 return HttpResponseForbidden()
    #             if changeset.applied is not None:
    #                 return Response({'changeset': CHANGESET_APPLIED_ERROR}, status=status.HTTP_400_BAD_REQUEST)
    #             thisname = self.get_model().__name__
    #             for actual_change in changeset.changes.all():
    #                 if actual_change.entity == thisname and actual_change.post.uuid == uuid:
    #                     instance = self.get_model().objects.get(pk=actual_change.post.pk)
    #                     change = actual_change
    #                     if change.action == change_models.ACTION_DELETED:
    #                         change.action = change_models.ACTION_MODIFIED
    #                     break
    #         except change_models.ChangeSet.DoesNotExist as dne_exc:
    #             raise Http404() from dne_exc
    #     if instance is None:
    #         try:
    #             pre_instance = self.get_model().objects.get(uuid=uuid, state=OWNED_OBJECT_STATE_LIVE)
    #             change = change_models.Change(entity=self.get_model().__name__, pre=pre_instance, action=change_models.ACTION_MODIFIED)
    #             instance = self.get_model().objects.get(pk=pre_instance.pk)
    #             instance.pk = None
    #             instance.id = None
    #             instance._state.adding = True
    #         except self.get_model().DoesNotExist as dne_exc:
    #             raise Http404() from dne_exc
    #     if changeset is None:
    #         changeset = change_models.ChangeSet(owner=request.user.customer, user=request.user, owner_name=request.user.customer.name, user_name=request.user.name)
        
    #     if not instance.owned_by(request.user.customer):
    #         return Response(data={'id':['Access to object denied']}, status=status.HTTP_403_FORBIDDEN)
    #     serializer = self.get_serializer()(instance, data=request.data)
    #     if serializer.is_valid():
    #         if self.validate_owner():
    #             if not serializer.validated_data['owner'] in request.user.customer.get_visible_customers():
    #                 return Response(data={'owner':['access to the owner is denied']}, status=status.HTTP_403_FORBIDDEN)
    #         semantic_validation = self.put_validate(serializer.validated_data, request.user.customer, changeset)
    #         if semantic_validation.is_ok():
    #             prepared_object = serializer.save(state=OWNED_OBJECT_STATE_PREPARED)
    #             changeset.save()
    #             change.changeset = changeset
    #             change.post = prepared_object
    #             change.save()
    #             serialized_data = self.get_serializer()(prepared_object).data
    #             serialized_data['changeset'] = str(changeset.id)
    #             return Response(serialized_data)
    #         else:
    #             rtncode = status.HTTP_400_BAD_REQUEST
    #             if not semantic_validation.access_ok:
    #                 rtncode = status.HTTP_403_FORBIDDEN
    #             return Response(data=semantic_validation.errors, status=rtncode)
    #     else:
    #         return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

    def delete(self, request, uuid, format=None):
        instance = None
        changeset = None
        change = None
        if 'changeset' in request.GET:
            try:
                changeset = change_models.ChangeSet.objects.get(id=request.GET['changeset'])
                if not changeset.owner in request.user.customer.get_visible_customers():
                    return HttpResponseForbidden()
                if changeset.applied is not None:
                    return Response({'changeset': CHANGESET_APPLIED_ERROR}, status=status.HTTP_400_BAD_REQUEST)
                thisname = self.get_model().__name__
                for actual_change in changeset.changes.all():
                    if actual_change.entity == thisname and actual_change.post.uuid == uuid:
                        instance = self.get_model().objects.get(pk=actual_change.post.pk)
                        change = actual_change
                        break
            except change_models.ChangeSet.DoesNotExist as dne_exc:
                raise Http404() from dne_exc
        if changeset is None:
            changeset = change_models.ChangeSet(owner=request.user.customer, user=request.user, owner_name=request.user.customer.name, user_name=request.user.name)
        if instance is None:
            try:
                pre_instance = self.get_model().objects.get(uuid=uuid, state=OWNED_OBJECT_STATE_LIVE)
                instance = self.get_model().objects.get(pk=pre_instance.pk)
                instance.id = None
                instance.pk = None
                instance._state.adding = True
                change = change_models.Change(changeset=changeset, entity=self.get_model().__name__, pre=pre_instance, post=instance, action=change_models.ACTION_DELETED)
            except self.get_model().DoesNotExist as dne_exc:
                raise Http404() from dne_exc
        
        if not instance.owned_by(request.user.customer):
            return Response(data={'uuid':['Access to object denied']}, status=status.HTTP_403_FORBIDDEN)
        
        changeset.save()
        instance.state = OWNED_OBJECT_STATE_DELETED
        instance.save()
        change.save()
        
        return Response(data={'changeset':str(changeset.id)}, status=status.HTTP_200_OK)

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