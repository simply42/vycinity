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

from rest_framework import exceptions, permissions, status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.views import APIView
from vycinity.models import change_models
from vycinity.models.customer_models import User
from vycinity.serializers import change_serializers
from vycinity.meta import change_management

class ChangeSetListSchema(AutoSchema):
    '''
    A schema generator for the ChangeSetList.
    '''

    def get_serializer(self, path, method):
        return change_serializers.ChangeSetSerializer()

    def get_request_serializer(self, path, method):
        return change_serializers.ChangeSetSerializer()

    def get_response_serializer(self, path, method):
        return change_serializers.ChangeSetSerializer()


class ChangeSetList(ListCreateAPIView):
    '''
    A changeset is a collection of changes.

    get:
    Retrieve changesets.

    post:
    Create an empty changeset.
    '''

    permission_classes = [permissions.IsAuthenticated]
    schema = ChangeSetListSchema(tags=['changeset'], operation_id_base='ChangeSet', component_name='ChangeSet')
    serializer_class = change_serializers.ChangeSetSerializer

    def get_queryset(self):
        assert isinstance(self.request, Request), "current request has wrong type."
        assert isinstance(self.request.user, User), "current requests user has wrong type."
        return change_models.ChangeSet.objects.filter(owner__in=self.request.user.customer.get_visible_customers())

    def perform_create(self, serializer):
        assert isinstance(self.request, Request), "current request has wrong type."
        assert isinstance(self.request.user, User), "current requests user has wrong type."
        assert isinstance(serializer, change_serializers.ChangeSetSerializer), 'Serializer of wrong type'
        assert isinstance(serializer.validated_data, dict), 'serializer not validated before'
        serializer.validated_data['owner'] = self.request.user.customer
        serializer.validated_data['user'] = self.request.user
        serializer.validated_data['owner_name'] = self.request.user.customer.name
        serializer.validated_data['user_name'] = self.request.user.name
        serializer.save()

class ChangeSetOwned(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if not isinstance(request, Request):
            raise AssertionError('request is not a rest_framework.request.Request')
        user = request.user
        if not user:
            return False
        if not isinstance(user, User):
            raise AssertionError('requests\' user is not of a usable type')
        if not isinstance(obj, change_models.ChangeSet):
            raise AssertionError('obj of interest is not of expected kind ChangeSet')
        if obj.owner not in user.customer.get_visible_customers():
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        elif request.method in ['PUT', 'DELETE']:
            return obj.applied is None
        return False
        

class ChangeSetDetailView(RetrieveUpdateDestroyAPIView):
    '''
    A changeset is a collection of changes.

    get:
    Retrieve a single changeset.

    put:
    Apply a changeset. The changeset included in the request is ignored (prefectly fine to send
    just `{}`). Only unapplied changesets may be applied.

    delete:
    Delete a changeset. As a changeset does also document changes, only non-applied changesets may be deleted.
    '''
    
    permission_classes = [ChangeSetOwned]
    schema = ChangeSetListSchema(tags=['changeset'], operation_id_base='ChangeSet', component_name='ChangeSet')
    queryset = change_models.ChangeSet.objects.all()
    serializer_class = change_serializers.ChangeSetSerializer

    def perform_update(self, serializer):
        if not isinstance(serializer, change_serializers.ChangeSetSerializer):
            raise AssertionError('Serializer is of unkown type.')
        changeset: change_models.ChangeSet = serializer.instance # type: ignore
        try:
            change_management.apply_changeset(changeset)
            changeset.refresh_from_db()
        except change_management.ChangeConflictError as cce:
            raise exceptions.APIException({'failure': cce.message}, status.HTTP_400_BAD_REQUEST) from cce


class ChangeList(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        changes = change_models.Change.objects.filter(changeset__owner__in=request.user.customer.get_visible_customers())
        return Response(change_serializers.ChangeSerializer(changes, many=True).data)


class ChangeDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id, format=None):
        try:
            change = change_models.Change.objects.get(pk=id)
            if not change.changeset.owner in request.user.customer.get_visible_customers():
                return Response({'general': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)
            return Response(change_serializers.ChangeSerializer(change).data)
        except change_models.Change.DoesNotExist:
            return Response({'general': 'Not Found.'}, status=status.HTTP_404_NOT_FOUND)