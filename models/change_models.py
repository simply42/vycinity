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

import uuid
from django.db import models
from vycinity.models import customer_models

ACTION_CREATED = 'created'
ACTION_MODIFIED = 'modified'
ACTION_DELETED = 'deleted'
CHANGE_ACTIONS = [
    (ACTION_CREATED, ACTION_CREATED),
    (ACTION_MODIFIED, ACTION_MODIFIED),
    (ACTION_DELETED, ACTION_DELETED)
]

class ChangeSet(models.Model):
    '''
    ChangeSet describes a list of changes to different entities.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(customer_models.Customer, on_delete=models.SET_NULL, null=True)
    user = models.ForeignKey(customer_models.User, on_delete=models.SET_NULL, null=True)
    owner_name = models.CharField(max_length=customer_models.NAME_LENGTH, editable=False)
    user_name = models.CharField(max_length=customer_models.NAME_LENGTH, editable=False)
    created = models.DateTimeField(editable=False, auto_now_add=True)
    modified = models.DateTimeField(editable=False, auto_now=True)
    applied = models.DateTimeField(null=True)

class Change(models.Model):
    '''
    A Change describes a changed entity by linking to a previous version with a newer one. The
    deletion-change is a bit special, as the pre and post may be the same entities.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    changeset = models.ForeignKey(ChangeSet, related_name='changes', on_delete=models.CASCADE)
    entity = models.CharField(max_length=255)
    pre = models.ForeignKey('vycinity.AbstractOwnedObject', null=True, related_name='+', on_delete=models.SET_NULL)
    post = models.OneToOneField('vycinity.AbstractOwnedObject', related_name='change', on_delete=models.CASCADE)
    action = models.CharField(max_length=8, choices=CHANGE_ACTIONS)
    dependencies = models.ManyToManyField(to='Change', related_name='dependents')
    
