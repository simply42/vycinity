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
import copy
from django.http import Http404, HttpResponseForbidden
from rest_framework import status
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from vycinity.models import customer_models, change_models
from vycinity.meta.change_management import get_known_changed_ids, ChangedObjectCollection
from typing import Any, List, Dict, Type
from uuid import UUID, uuid4


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

class GenericOwnedObjectList(APIView, ABC):
    permission_classes = [IsAuthenticated]

    @abstractmethod
    def get_model(self) -> Type['OwnedObject']:
        raise NotImplementedError('Model is not set.')

    @abstractmethod
    def get_serializer(self) -> Type[Serializer]:
        raise NotImplementedError('Serializer is not set.')

    @abstractmethod
    def filter_attributes(self, object_list: List[Any], customer: customer_models.Customer):
        raise NotImplementedError('filter_attributes is not defined.')

    @abstractmethod
    def post_validate(self, object: dict, customer: customer_models.Customer, changed_objects: ChangedObjectCollection) -> ValidationResult:
        raise NotImplementedError('post_allowed is not defined.')

    def validate_owner(self):
        return True

    def get(self, request, format=None):
        model = self.get_model()
        relevant_changes = []
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
        instances = model.filter_query_by_customers_or_public(model.objects, 
            request.user.customer.get_visible_customers())
        serialized_data = self.get_serializer()(instances, many=True).data
        for relevant_change in relevant_changes:
            if relevant_change.pre == None and not relevant_change.post is None:
                additional_object = copy.deepcopy(relevant_change.post)
                additional_object['id'] = str(relevant_change.new_uuid)
                serialized_data.append(additional_object)
            elif not relevant_change.pre is None:
                for index in range(len(serialized_data)):
                    if serialized_data[index]['id'] == relevant_change.pre['id']:
                        if relevant_change.post is None:
                            serialized_data.pop(index)
                        else:
                            serialized_data[index] = copy.deepcopy(relevant_change.post)
                        break

        return Response(self.filter_attributes(serialized_data, request.user.customer))


    def post(self, request, format=None):
        serializer = self.get_serializer()(data=request.data)
        changeset = change_models.ChangeSet(owner=request.user.customer, user=request.user, owner_name=request.user.customer.name, user_name=request.user.name)
        change = change_models.Change(entity=self.get_model().__name__)
        
        serializer_valid = serializer.is_valid()
        if not serializer_valid:
            all_invalid_ok = True
            for field_name in serializer.errors.keys():
                all_fields = serializer.fields()
                if field_name in all_fields:
                    pass
                all_invalid_ok = False
            if all_invalid_ok:
                serializer_valid = True
        if serializer_valid:
            if self.validate_owner():
                visible_customers = request.user.customer.get_visible_customers()
                if not serializer.validated_data['owner'] in visible_customers:
                    return Response(data={'owner':['access to the owner is denied']}, status=status.HTTP_403_FORBIDDEN)
            semantic_validation = self.post_validate(serializer.validated_data, request.user.customer)
            if semantic_validation.is_ok():
                serialized_object = serializer.data
                changeset.save()
                change.changeset = changeset
                change.new_uuid = uuid4()
                change.post = serialized_object
                change.save()
                serialized_object['changeset'] = str(changeset.id)
                return Response(data=serialized_object, status=status.HTTP_201_CREATED)
            else:
                rtn_status = status.HTTP_400_BAD_REQUEST
                if not semantic_validation.access_ok:
                    rtn_status = status.HTTP_403_FORBIDDEN
                return Response(data=semantic_validation.errors, status=rtn_status)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GenericOwnedObjectDetail(APIView):
    permission_classes = [IsAuthenticated]

    @abstractmethod
    def get_model(self) -> Type['OwnedObject']:
        raise NotImplementedError('Model is not set.')

    @abstractmethod
    def get_serializer(self):
        raise NotImplementedError('Serializer is not set.')

    @abstractmethod
    def filter_attributes(self, object: Any, customer: customer_models.Customer):
        raise NotImplementedError('filter_attributes is not defined.')

    @abstractmethod
    def put_validate(self, object: Any, customer: customer_models.Customer, changed_objects: ChangedObjectCollection) -> ValidationResult:
        raise NotImplementedError('put_allowed is not defined.')

    def validate_owner(self):
        return True

    def get(self, request, id, format=None):
        serialized_data = None
        if 'changeset' in request.GET:
            try:
                changeset = change_models.ChangeSet.objects.get(id=request.GET['changeset'])
                if not changeset.owner in request.user.customer.get_visible_customers():
                    return HttpResponseForbidden()
                for change in changeset.changes.all():
                    thisname = self.get_model().__name__
                    if change.entity == thisname and (change.new_uuid == id or (not change.pre is None and UUID(change.pre['id']) == id)):
                        serialized_data = change.post
                        break
            except change_models.ChangeSet.DoesNotExist as dne_exc:
                raise Http404() from dne_exc
        if serialized_data is None:
            try:
                instance = self.get_model().objects.get(id=id)
                if not instance.owned_by(request.user.customer) and not instance.public:
                    return HttpResponseForbidden()
                serialized_data = self.get_serializer()(instance).data
            except (self.get_model().DoesNotExist, change_models.ChangeSet.DoesNotExist) as dne_exc:
                raise Http404() from dne_exc
        return Response(self.filter_attributes(serialized_data, request.user.customer))

    def put(self, request, id, format=None):
        try:
            instance = self.get_model().objects.get(id=id)
            changeset = change_models.ChangeSet(owner=request.user.customer, user=request.user, owner_name=request.user.customer.name, user_name=request.user.name)
            if 'changeset' in request.GET:
                changeset = change_models.ChangeSet.objects.get(id=UUID(request.GET['changeset']))
                if changeset.owner != request.user.customer:
                    return Response(data={'changeset':['Access to object denied']}, status=status.HTTP_403_FORBIDDEN)
            change = change_models.Change(entity=self.get_model().__name__, pre=self.get_serializer()(instance).data)
            for existing_change in changeset.changes.all():
                if existing_change.entity == self.get_model().__name__ and ((existing_change.pre is not None and existing_change.pre['id'] == str(id)) or (existing_change.pre is None and existing_change.new_uuid == id)):
                    change = existing_change
                    break
            if not instance.owned_by(request.user.customer):
                return Response(data={'id':['Access to object denied']}, status=status.HTTP_403_FORBIDDEN)
            serializer = self.get_serializer()(instance, data=request.data)
            if serializer.is_valid():
                if self.validate_owner():
                    if not serializer.validated_data['owner'] in request.user.customer.get_visible_customers():
                        return Response(data={'owner':['access to the owner is denied']}, status=status.HTTP_403_FORBIDDEN)
                semantic_validation = self.put_validate(serializer.validated_data, request.user.customer)
                if semantic_validation.is_ok():
                    serialized_data = copy.deepcopy(request.data)
                    changeset.save()
                    change.changeset = changeset
                    change.post = serialized_data
                    change.save()
                    serialized_data['changeset'] = str(changeset.id)
                    return Response(serialized_data)
                else:
                    rtncode = status.HTTP_400_BAD_REQUEST
                    if not semantic_validation.access_ok:
                        rtncode = status.HTTP_403_FORBIDDEN
                    return Response(data=semantic_validation.errors, status=rtncode)
            else:
                return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except (self.get_model().DoesNotExist, change_models.ChangeSet.DoesNotExist) as dne_exc:
            raise Http404() from dne_exc

    def delete(self, request, id, format=None):
        try:
            instance = self.get_model().objects.get(id=id)
            if not instance.owned_by(request.user.customer):
                return Response(data={'id':['Access to object denied']}, status=status.HTTP_403_FORBIDDEN)
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except self.get_model().DoesNotExist as dne_exc:
            raise Http404() from dne_exc

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