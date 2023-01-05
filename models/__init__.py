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

from abc import abstractmethod, abstractstaticmethod
from django.db import models
from polymorphic.models import PolymorphicModel
from django.db.models import constraints, manager, query
from rest_framework import serializers
from vycinity.models import customer_models, change_models
from typing import Any, List, Union
import uuid

OWNED_OBJECT_STATE_PREPARED = 'prepared'
OWNED_OBJECT_STATE_LIVE = 'live'
OWNED_OBJECT_STATE_OUTDATED = 'outdated'
OWNED_OBJECT_STATE_DELETED = 'deleted'
OWNED_OBJECT_STATES = [
    (OWNED_OBJECT_STATE_PREPARED, OWNED_OBJECT_STATE_PREPARED),
    (OWNED_OBJECT_STATE_LIVE, OWNED_OBJECT_STATE_LIVE),
    (OWNED_OBJECT_STATE_OUTDATED, OWNED_OBJECT_STATE_OUTDATED),
    (OWNED_OBJECT_STATE_DELETED, OWNED_OBJECT_STATE_DELETED)
]

class AbstractOwnedObject(PolymorphicModel):
    '''
    Abstract base model.
    '''

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    state = models.CharField(choices=OWNED_OBJECT_STATES, max_length=10)

    class Meta:
        constraints = [
            constraints.UniqueConstraint(fields=['uuid', 'state'], name='%(app_label)s_max_one_%(class)s_live', condition=models.Q(state=OWNED_OBJECT_STATE_LIVE))
        ]

    def owned_by(self, customer: customer_models.Customer):
        '''
        Checks, whether the given customer owns this object in a implicit way. The implementing
        class has to have the attribute `owner` of type Customer.
        '''

        if customer is None:
            return True
        current_customer = self.owner
        while not current_customer is None:
            if current_customer.id == customer.id:
                return True
            current_customer = current_customer.parent_customer
        return False

    @property
    @abstractmethod
    def owner(self):
        raise NotImplementedError('Owner is not defined')

    @abstractmethod
    def get_related_owned_objects(self) -> List['AbstractOwnedObject']:
        '''
        Returns a List with related AbstractOwnedObject instances directly associated.

        returns: Directly associated AbstractOwnedObjects as list.
        '''
        raise NotImplementedError('get_related_owned_objects not yet implemented')

    @abstractmethod
    def get_dependent_owned_objects(self) -> List['AbstractOwnedObject']:
        '''
        Returns a List with dependent AbstractOwnedObject instances directly associated, where
        the instance depends on.

        returns: Directly associated and dependent AbstractOwnedObjects as list.
        '''
        raise NotImplementedError('get_dependent_owned_objects not yet implemented')

    @abstractstaticmethod
    def filter_query_by_customers_or_public(query: Any, customers: List[customer_models.Customer]):
        '''
        Filters a given query for the model against given the list of customers or the attribute
        `public`.

        params:
            query: the query to extend with the filter
            customers: the list of customers, that should be appended

        returns: The modified QuerySet.
        '''
        raise NotImplementedError('filter_query_by_customers not yet implemented')

    @staticmethod
    def filter_query_by_liveness_or_changeset(query: Any, changeset: change_models.ChangeSet):
        '''
        Filters a query by liveness or the given changeset.

        params:
            query: the query to extend.
            changeset: the changeset which also may contain the target object.
        '''
        return query.filter(models.Q(state=OWNED_OBJECT_STATE_LIVE) | models.Q(change__changeset=changeset))

    @classmethod
    def filter_by_changeset_and_visibility(cls, query: Union[manager.Manager, query.QuerySet], changeset: change_models.ChangeSet, visible_customers: list[customer_models.Customer]) -> Union[manager.Manager, query.QuerySet]:
        '''
        Returns a filtered queryset or manager (depends on what the implementing class provides)
        for elements in same changeset and modified or live elements for the current user.

        params:
            query: A query to filter.
            changeset: A Changeset for finding additional instances that are not live.
            visible_customers: A list of customers the retriever is able to see.
        
        returns: The filtered queryset-like object.
        '''
        referenced_modified_changes = changeset.changes.filter(entity=cls.__name__, pre__isnull=False).only('pre')
        pk_referenced_modified_objects_list = map(lambda change: change.pre.pk, referenced_modified_changes)
        return cls.filter_query_by_customers_or_public(
            query.filter(
                (models.Q(state=OWNED_OBJECT_STATE_LIVE) & (~models.Q(pk__in=pk_referenced_modified_objects_list))) | 
                models.Q(state=OWNED_OBJECT_STATE_PREPARED, change__changeset=changeset, change__action__in=[change_models.ACTION_CREATED, change_models.ACTION_MODIFIED])),
            visible_customers)

    @abstractstaticmethod
    def get_serializer() -> serializers.Serializer:
        '''
        Returns a Serializer for this Model.

        returns: The Serializer for this Model.
        '''
        raise NotImplementedError('get_serializer not yet implemented')


class OwnedObject(AbstractOwnedObject):
    '''
    Abstract object describing relation to a `Customer`.
    '''
    
    owner = models.ForeignKey(customer_models.Customer, on_delete=models.CASCADE) # type: ignore
    public = models.BooleanField(default=False)

    class Meta:
        abstract = True

    @staticmethod
    def filter_query_by_customers_or_public(query: Any, customers: List[customer_models.Customer]):
        return query.filter(models.Q(public=True) | models.Q(owner__in=customers))


class SemiOwnedObject(AbstractOwnedObject):
    '''
    Abstract object for approximating the relation to a `Customer`. This is required when the
    object itself does not have a direct relation to a `Customer`, but a related has.
    '''
    
    class Meta:
        abstract = True
    
    @property
    def public(self):
        raise NotImplementedError('Public is not defined')