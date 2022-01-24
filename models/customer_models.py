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
from polymorphic.models import PolymorphicModel

NAME_LENGTH = 64

class Customer(PolymorphicModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=NAME_LENGTH, unique=True)
    parent_customer = models.ForeignKey(to='Customer', null=True, on_delete=models.CASCADE)

    def get_visible_customers(self):
        rtn = [self]
        for child in Customer.objects.filter(parent_customer=self):
            rtn += child.get_visible_customers()
        return rtn

class User(PolymorphicModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=NAME_LENGTH, unique=True)
    display_name = models.CharField(max_length=64, null=True)
    customer = models.ForeignKey(to=Customer, on_delete=models.CASCADE)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_staff(self):
        return False

class LocalUserAuth(PolymorphicModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(to=User, on_delete=models.CASCADE)
    auth = models.CharField(max_length=256)