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
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from vycinity.models import OwnedObject, customer_models
from typing import Any, List, Dict

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
    def get_model(self):
        raise NotImplementedError('Model is not set.')

    @abstractmethod
    def get_serializer(self):
        raise NotImplementedError('Serializer is not set.')

    @abstractmethod
    def filter_attributes(self, object_list: List[Any], customer: customer_models.Customer):
        raise NotImplementedError('filter_attributes is not defined.')

    @abstractmethod
    def post_validate(self, object: dict, customer: customer_models.Customer) -> ValidationResult:
        raise NotImplementedError('post_allowed is not defined.')

    def validate_owner(self):
        return True

    def get(self, request, format=None):
        model = self.get_model()
        instances = model.filter_query_by_customers_or_public(model.objects, 
            request.user.customer.get_visible_customers())
        return Response(self.filter_attributes(self.get_serializer()(instances, many=True).data, request.user.customer))

    def post(self, request, format=None):
        serializer = self.get_serializer()(data=request.data)
        if serializer.is_valid():
            if self.validate_owner():
                visible_customers = request.user.customer.get_visible_customers()
                if not serializer.validated_data['owner'] in visible_customers:
                    return Response(data={'owner':['access to the owner is denied']}, status=status.HTTP_403_FORBIDDEN)
            semantic_validation = self.post_validate(serializer.validated_data, request.user.customer)
            if semantic_validation.is_ok():
                serializer.save()
                return Response(data=serializer.data, status=status.HTTP_201_CREATED)
            else:
                rtn_status = status.HTTP_400_BAD_REQUEST
                if not semantic_validation.access_ok:
                    rtn_status = status.HTTP_403_FORBIDDEN
                return Response(data=semantic_validation.errors, status=rtn_status)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GenericOwnedObjectDetail(APIView):
    permission_classes = [IsAuthenticated]

    @abstractmethod
    def get_model(self) -> OwnedObject:
        raise NotImplementedError('Model is not set.')

    @abstractmethod
    def get_serializer(self):
        raise NotImplementedError('Serializer is not set.')

    @abstractmethod
    def filter_attributes(self, object: Any, customer: customer_models.Customer):
        raise NotImplementedError('filter_attributes is not defined.')

    @abstractmethod
    def put_validate(self, object: Any, customer: customer_models.Customer) -> ValidationResult:
        raise NotImplementedError('put_allowed is not defined.')

    def validate_owner(self):
        return True

    def get(self, request, id, format=None):
        try:
            instance = self.get_model().objects.get(id=id)
            if not instance.owned_by(request.user.customer) and not instance.public:
                return HttpResponseForbidden()
            return Response(self.filter_attributes(self.get_serializer()(instance).data, request.user.customer))
        except self.get_model().DoesNotExist as dne_exc:
            raise Http404() from dne_exc

    def put(self, request, id, format=None):
        try:
            instance = self.get_model().objects.get(id=id)
            if not instance.owned_by(request.user.customer):
                return Response(data={'id':['Access to object denied']}, status=status.HTTP_403_FORBIDDEN)
            serializer = self.get_serializer()(instance, data=request.data)
            if serializer.is_valid():
                if self.validate_owner():
                    if not serializer.validated_data['owner'] in request.user.customer.get_visible_customers():
                        return Response(data={'owner':['access to the owner is denied']}, status=status.HTTP_403_FORBIDDEN)
                semantic_validation = self.put_validate(serializer.validated_data, request.user.customer)
                if semantic_validation.is_ok():
                    serializer.save()
                    return Response(serializer.data)
                else:
                    rtncode = status.HTTP_400_BAD_REQUEST
                    if not semantic_validation.access_ok:
                        rtncode = status.HTTP_403_FORBIDDEN
                    return Response(data=semantic_validation.errors, status=rtncode)
            else:
                return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except self.get_model().DoesNotExist as dne_exc:
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
