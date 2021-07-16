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

from django.test import TestCase
from vycinity.models import customer_models, firewall_models

class ModelOwnedByTest(TestCase):
    def test_customer_inheritance(self):
        customer_a = customer_models.Customer(name='A', parent_customer=None)
        customer_a.save()
        customer_b = customer_models.Customer(name='B', parent_customer=customer_a)
        customer_b.save()
        customer_c = customer_models.Customer(name='C', parent_customer=customer_b)
        customer_c.save()
        customer_d = customer_models.Customer(name='D', parent_customer=customer_a)
        customer_d.save()

        firewall_b = firewall_models.Firewall(stateful=True, name='fw_b', default_action_into=firewall_models.ACTION_ACCEPT, default_action_from=firewall_models.ACTION_ACCEPT, owner=customer_b)
        firewall_b.save()

        self.assertTrue(firewall_b.owned_by(customer_b))
        self.assertTrue(firewall_b.owned_by(customer_a))
        self.assertFalse(firewall_b.owned_by(customer_c))
        self.assertFalse(firewall_b.owned_by(customer_d))

    def test_customer_visibility(self):
        customer_a = customer_models.Customer(name='A', parent_customer=None)
        customer_a.save()
        customer_b = customer_models.Customer(name='B', parent_customer=customer_a)
        customer_b.save()
        customer_c = customer_models.Customer(name='C', parent_customer=customer_b)
        customer_c.save()
        customer_d = customer_models.Customer(name='D', parent_customer=customer_a)
        customer_d.save()

        self.assertListEqual([customer_a, customer_b, customer_c, customer_d], customer_a.get_visible_customers())
        self.assertListEqual([customer_b, customer_c], customer_b.get_visible_customers())
        self.assertListEqual([customer_c], customer_c.get_visible_customers())
        self.assertListEqual([customer_d], customer_d.get_visible_customers())