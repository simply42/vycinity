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

from base64 import b64encode
from celery import Task
from django.test import Client, TestCase
from django.contrib.auth.hashers import make_password
import uuid
from vycinity.models import OWNED_OBJECT_STATE_PREPARED, basic_models, customer_models, change_models, network_models, OWNED_OBJECT_STATE_LIVE
from unittest.mock import Mock, patch

class ManagedInterfaceAPITest(TestCase):
    '''
    This is a test for Managed interfaces API set.
    '''

    @classmethod
    def setUpTestData(cls):
        cls.test_router: basic_models.Vyos13Router = basic_models.Vyos13Router.objects.create(name = "testrouter", loopback = "1.2.3.4", deploy = False, managed_interface_context = ['interfaces', 'ethernet', 'eth1'], token = 'dev123', fingerprint = '1234567890abcdef0')
        cls.root_customer: customer_models.Customer = customer_models.Customer.objects.create(name = "root customer")
        cls.child_customer: customer_models.Customer = customer_models.Customer.objects.create(name = "child customer", parent_customer = cls.root_customer)
        cls.root_user: customer_models.User = customer_models.User.objects.create(name = 'root', display_name = 'root', customer = cls.root_customer)
        cls.child_user: customer_models.User = customer_models.User.objects.create(name = 'child', display_name = 'child', customer = cls.child_customer)
        cls.root_auth: customer_models.LocalUserAuth = customer_models.LocalUserAuth.objects.create(user = cls.root_user, auth=make_password('root'))
        cls.child_auth: customer_models.LocalUserAuth = customer_models.LocalUserAuth.objects.create(user = cls.child_user, auth=make_password('child'))
        cls.root_authorization: str = 'Basic ' + b64encode('root:root'.encode('utf-8')).decode('ascii')
        cls.child_authorization: str = 'Basic ' + b64encode('child:child'.encode('utf-8')).decode('ascii')
        cls.test_network: network_models.Network = network_models.Network.objects.create(owner = cls.root_customer, state = OWNED_OBJECT_STATE_LIVE, name = 'network 1', ipv4_network_address = '10.1.1.0', ipv4_network_bits = 24, layer2_network_id = 2)
        cls.test_managed_interface: network_models.ManagedInterface = network_models.ManagedInterface.objects.create(network = cls.test_network, router = cls.test_router, ipv4_address = '10.1.1.254')

    def test_list_managedinterfaces_good(self):
        c = Client()
        response = c.get('/api/v1/managedinterfaces', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.root_authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertEqual(1, len(content))
        self.assertEqual(str(self.test_managed_interface.id), content[0]['id'])
        self.assertEqual(self.test_managed_interface.ipv4_address, content[0]['ipv4_address'])
        self.assertEqual(self.test_managed_interface.ipv6_address, content[0]['ipv6_address'])
        self.assertEqual(str(self.test_router.id), content[0]['router'])
        self.assertEqual(str(self.test_network.uuid), content[0]['network'])

    def test_list_managedinterfaces_non_root_customer(self):
        c = Client()
        response = c.get('/api/v1/managedinterfaces', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.child_authorization)
        self.assertEqual(403, response.status_code)
    
    def test_create_managedinterfaces_good(self):
        additional_network: network_models.Network = network_models.Network.objects.create(owner = self.root_customer, state = OWNED_OBJECT_STATE_LIVE, name = 'network 2', ipv4_network_address = '10.1.2.0', ipv4_network_bits = 24, layer2_network_id = 3)
        c = Client()
        new_mi = {
            'ipv4_address': '10.1.2.254',
            'router': str(self.test_router.id),
            'network': str(additional_network.uuid),
        }
        response = c.post('/api/v1/managedinterfaces', data=new_mi, content_type="application/json", HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.root_authorization)
        self.assertEqual(201, response.status_code)
        content = response.json()
        for (key, value) in new_mi.items():
            self.assertEqual(value, content[key], 'key {} is different: "{}" vs. "{}"'.format(key, value, content[key]))

    def test_create_managedinterfaces_non_root_customer(self):
        additional_network: network_models.Network = network_models.Network.objects.create(owner = self.root_customer, state = OWNED_OBJECT_STATE_LIVE, name = 'network 2', ipv4_network_address = '10.1.2.0', ipv4_network_bits = 24, layer2_network_id = 3)
        c = Client()
        new_mi = {
            'ipv4_address': '10.1.2.254',
            'router': str(self.test_router.id),
            'network': str(additional_network.uuid),
        }
        response = c.post('/api/v1/managedinterfaces', content_type="application/json", data=new_mi, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.child_authorization)
        self.assertEqual(403, response.status_code)

    def test_create_managedinterfaces_non_live_network(self):
        additional_network: network_models.Network = network_models.Network.objects.create(owner = self.root_customer, state = OWNED_OBJECT_STATE_PREPARED, name = 'network 2', ipv4_network_address = '10.1.2.0', ipv4_network_bits = 24, layer2_network_id = 3)
        c = Client()
        new_mi = {
            'ipv4_address': '10.1.2.254',
            'router': str(self.test_router.id),
            'network': str(additional_network.uuid),
        }
        response = c.post('/api/v1/managedinterfaces', content_type="application/json", data=new_mi, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.root_authorization)
        self.assertEqual(400, response.status_code)

    def test_read_managedinterface_good(self):
        c = Client()
        response = c.get('/api/v1/managedinterfaces/{}'.format(self.test_managed_interface.id), HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.root_authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertEqual(str(self.test_managed_interface.id), content['id'])
        self.assertEqual(self.test_managed_interface.ipv4_address, content['ipv4_address'])
        self.assertEqual(self.test_managed_interface.ipv6_address, content['ipv6_address'])
        self.assertEqual(str(self.test_router.id), content['router'])
        self.assertEqual(str(self.test_network.uuid), content['network'])

    def test_read_managedinterface_non_root_customer(self):
        c = Client()
        response = c.get('/api/v1/managedinterfaces/{}'.format(self.test_managed_interface.id), HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.child_authorization)
        self.assertEqual(403, response.status_code)

    def test_read_managedinterface_non_existent(self):
        c = Client()
        response = c.get('/api/v1/managedinterfaces/{}'.format(uuid.uuid4()), HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.child_authorization)
        self.assertEqual(404, response.status_code)

    def test_update_managedinterfaces_good(self):
        additional_network: network_models.Network = network_models.Network.objects.create(owner = self.root_customer, state = OWNED_OBJECT_STATE_LIVE, name = 'network 2', ipv4_network_address = '10.1.2.0', ipv4_network_bits = 24, layer2_network_id = 3)
        c = Client()
        new_mi = {
            'ipv4_address': '10.1.2.254',
            'router': str(self.test_router.id),
            'network': str(additional_network.uuid),
        }
        response = c.put('/api/v1/managedinterfaces/{}'.format(self.test_managed_interface.id), content_type="application/json", data=new_mi, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.root_authorization)
        self.assertEqual(201, response.status_code)
        content = response.json()
        for (key, value) in new_mi.items():
            self.assertEqual(value, content[key], 'key {} is different: "{}" vs. "{}"'.format(key, value, content[key]))

    def test_update_managedinterfaces_non_root_customer(self):
        additional_network: network_models.Network = network_models.Network.objects.create(owner = self.root_customer, state = OWNED_OBJECT_STATE_LIVE, name = 'network 2', ipv4_network_address = '10.1.2.0', ipv4_network_bits = 24, layer2_network_id = 3)
        c = Client()
        new_mi = {
            'ipv4_address': '10.1.2.254',
            'router': str(self.test_router.id),
            'network': str(additional_network.uuid),
        }
        response = c.put('/api/v1/managedinterfaces/{}'.format(self.test_managed_interface.id), content_type="application/json", data=new_mi, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.child_authorization)
        self.assertEqual(403, response.status_code)

    def test_update_managedinterfaces_non_live_network(self):
        additional_network: network_models.Network = network_models.Network.objects.create(owner = self.root_customer, state = OWNED_OBJECT_STATE_PREPARED, name = 'network 2', ipv4_network_address = '10.1.2.0', ipv4_network_bits = 24, layer2_network_id = 3)
        c = Client()
        new_mi = {
            'ipv4_address': '10.1.2.254',
            'router': str(self.test_router.id),
            'network': str(additional_network.uuid),
        }
        response = c.put('/api/v1/managedinterfaces/{}'.format(self.test_managed_interface.id), content_type="application/json", data=new_mi, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.root_authorization)
        self.assertEqual(400, response.status_code)

    def test_update_managedinterface_non_existent(self):
        additional_network: network_models.Network = network_models.Network.objects.create(owner = self.root_customer, state = OWNED_OBJECT_STATE_LIVE, name = 'network 2', ipv4_network_address = '10.1.2.0', ipv4_network_bits = 24, layer2_network_id = 3)
        c = Client()
        new_mi = {
            'ipv4_address': '10.1.2.254',
            'router': str(self.test_router.id),
            'network': str(additional_network.uuid),
        }
        response = c.put('/api/v1/managedinterfaces/{}'.format(uuid.uuid4()), content_type="application/json", data=new_mi, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.root_authorization)
        self.assertEqual(404, response.status_code)

    def test_delete_managedinterfaces_good(self):
        mi_uuid = self.test_managed_interface.id
        c = Client()
        response = c.delete('/api/v1/managedinterfaces/{}'.format(mi_uuid), HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.root_authorization)
        self.assertEqual(204, response.status_code)

        try:
            network_models.ManagedInterface.objects.get(id=mi_uuid)
            self.fail('ManagedInterface deleted, but is still there.')
        except network_models.ManagedInterface.DoesNotExist:
            pass

    def test_delete_managedinterfaces_non_root_customer(self):
        mi_uuid = self.test_managed_interface.id
        c = Client()
        response = c.delete('/api/v1/managedinterfaces/{}'.format(mi_uuid), HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.child_authorization)
        self.assertEqual(403, response.status_code)

        try:
            network_models.ManagedInterface.objects.get(id=mi_uuid)
        except network_models.ManagedInterface.DoesNotExist:
            self.fail('ManagedInterface deleted, but is still there.')

    def test_delete_managedinterface_non_existent(self):
        mi_uuid = self.test_managed_interface.id
        c = Client()
        response = c.delete('/api/v1/managedinterfaces/{}'.format(mi_uuid), HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.child_authorization)
        self.assertEqual(404, response.status_code)