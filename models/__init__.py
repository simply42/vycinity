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

from abc import abstractstaticmethod
from django.db import models
from rest_framework import serializers
from vycinity.models import customer_models
from typing import Any, List

class AbstractOwnedObject:
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

    @abstractstaticmethod
    def get_serializer() -> serializers.Serializer:
        '''
        Returns a Serializer for this Model.

        returns: The Serializer for this Model.
        '''
        raise NotImplementedError('get_serializer not yet implemented')


class OwnedObject(models.Model, AbstractOwnedObject):
    '''
    Abstract object describing relation to a `Customer`.
    '''
    
    owner = models.ForeignKey(customer_models.Customer, on_delete=models.CASCADE)
    public = models.BooleanField(default=False)

    class Meta:
        abstract = True

    @staticmethod
    def filter_query_by_customers_or_public(query: Any, customers: List[customer_models.Customer]):
        return query.filter(models.Q(public=True) | models.Q(owner__in=customers))


class SemiOwnedObject(models.Model, AbstractOwnedObject):
    '''
    Abstract object for approximating the relation to a `Customer`. This is required when the
    object itself does not have a direct relation to a `Customer`, but a related has.
    '''
    
    class Meta:
        abstract = True
    
    @property
    def owner(self):
        raise NotImplementedError('Owner is not defined')

    @property
    def public(self):
        raise NotImplementedError('Public is not defined')