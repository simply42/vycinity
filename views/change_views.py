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

from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from vycinity.models import change_models
from vycinity.serializers import change_serializers

class ChangeSetList(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        change_sets = change_models.ChangeSet.objects.filter(owner__in=request.user.customer.get_visible_customers())
        return Response(change_serializers.ChangeSetSerializer(change_sets, many=True).data)

    def post(self, request, format=None):
        new_changeset = change_models.ChangeSet(owner=request.user.customer, user=request.user, owner_name=request.user.customer.name, user_name=request.user.name)
        new_changeset.save()
        return Response(change_serializers.ChangeSetSerializer(new_changeset).data)


class ChangeSetDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id, format=None):
        try:
            changeset = change_models.ChangeSet.objects.get(pk=id)
            if not changeset.owner in request.user.customer.get_visible_customers():
                return Response({'general': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)
            return Response(change_serializers.ChangeSetSerializer(changeset).data)
        except change_models.ChangeSet.DoesNotExist:
            return Response({'general': 'Not Found.'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, id, format=None):
        try:
            changeset = change_models.ChangeSet.objects.get(pk=id)
            if not changeset.owner in request.user.customer.get_visible_customers():
                return Response({'general': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)
            if changeset.applied:
                return Response({'general': 'Change set was already applied. Deletion is not possible.'}, status=status.HTTP_403_FORBIDDEN)
            changeset.delete()
            return Response(status.HTTP_204_NO_CONTENT)
        except change_models.ChangeSet.DoesNotExist:
            raise Response({'general': 'Not Found.'}, status=status.HTTP_404_NOT_FOUND)


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