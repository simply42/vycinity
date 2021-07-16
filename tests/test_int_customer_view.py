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

from django.test import Client, TestCase
from vycinity.models import customer_models
from django.contrib.auth.hashers import make_password
from base64 import b64encode
import json

class CustomerAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.main_customer = customer_models.Customer.objects.create(name = 'Test-Root customer')
        cls.main_user = customer_models.User.objects.create(name='testuser', customer=cls.main_customer)
        cls.other_root_customer = customer_models.Customer.objects.create(name='Other Root customer')
        cls.main_user_pw = 'testpw'
        customer_models.LocalUserAuth.objects.create(user=cls.main_user, auth=make_password(cls.main_user_pw))
        cls.authorization = 'Basic ' + b64encode((cls.main_user.name + ':' + cls.main_user_pw).encode('utf-8')).decode('ascii')

    def test_list_customer_just_root(self):
        c = Client()
        response = c.get('/api/v1/customers', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, list))
        self.assertEqual(1, len(content))
        self.assertEqual(self.main_customer.name, content[0]['name'])
        self.assertIsNone(content[0]['parent_customer'])
        self.assertEqual(str(self.main_customer.id), content[0]['id'])

    def test_list_customer_multiple(self):
        sub_customer = customer_models.Customer.objects.create(name='Test Sub customer', parent_customer=self.main_customer)
        sub_user = customer_models.User.objects.create(name='testuser2', customer=sub_customer)
        sub_user_pw = 'testpw2'
        customer_models.LocalUserAuth.objects.create(user=sub_user, auth=make_password(sub_user_pw))
        sub_auth = 'Basic ' + b64encode((sub_user.name + ':' + sub_user_pw).encode('utf-8')).decode('ascii') 
        c = Client()

# TODO: translate
        # korrekte Liste mit Eltern- und Kind-Customer, aber ohne parallelem Customer 
        response = c.get('/api/v1/customers', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, list))
        self.assertEqual(2, len(content))
        self.assertEqual(self.main_customer.name, content[0]['name'])
        self.assertIsNone(content[0]['parent_customer'])
        self.assertEqual(str(self.main_customer.id), content[0]['id'])
        self.assertEqual(sub_customer.name, content[1]['name'])
        self.assertEqual(str(self.main_customer.id), content[1]['parent_customer'])
        self.assertEqual(str(sub_customer.id), content[1]['id'])

# TODO: translate
        # korrekte Liste nur mit Kind-Customer
        response = c.get('/api/v1/customers', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=sub_auth)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, list))
        self.assertEqual(1, len(content))
        self.assertEqual(sub_customer.name, content[0]['name'])
        self.assertEqual(str(self.main_customer.id), content[0]['parent_customer'])
        self.assertEqual(str(sub_customer.id), content[0]['id'])

    def test_get_single_customer(self):
        c = Client()

# TODO: translate
        # korrekter Fall
        response = c.get('/api/v1/customers/%s' % self.main_customer.id, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual(self.main_customer.name, content['name'])
        self.assertIsNone(content['parent_customer'])
        self.assertEqual(str(self.main_customer.id), content['id'])

# TODO: translate
        # Fall ohne Zugang
        response2 = c.get('/api/v1/customers/%s' % self.other_root_customer.id, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response2.status_code)

    def test_post_customer(self):
        c = Client()

# TODO: translate
        # korrekter Fall
        response = c.post('/api/v1/customers', {'name': 'sub customer', 'parent_customer': str(self.main_customer.id)}, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(201, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual('sub customer', content['name'])
        self.assertEqual(str(self.main_customer.id), content['parent_customer'])

# TODO: translate
        # Falscher Fall: Root customer sollen nicht über API erstellbar sein
        response = c.post('/api/v1/customers', {'name': 'sub customer 2'}, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(400, response.status_code)
        
# TODO: translate
        # Falscher Fall: Customer darf nicht für wen anders anlegbar sein
        response = c.post('/api/v1/customers', {'name': 'sub customer 3', 'parent_customer': str(self.other_root_customer.id)}, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response.status_code)
        
# TODO: translate
        # Falscher Fall: Customer dürfen nicht doppelt angelegt werden
        response = c.post('/api/v1/customers', {'name': 'sub customer', 'parent_customer': str(self.main_customer.id)}, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(400, response.status_code)
        
    def test_put_customer(self):
        c = Client()
        sub_customer = customer_models.Customer.objects.create(name='sub customer', parent_customer=self.main_customer)

# TODO: translate
        # korrekter Fall
        response = c.put('/api/v1/customers/%s' % sub_customer.id, json.dumps({'name': 'sub customer 1', 'parent_customer': str(self.main_customer.id)}), content_type='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual('sub customer 1', content['name'])
        self.assertEqual(str(self.main_customer.id), content['parent_customer'])

# TODO: translate
        # Falscher Fall: Eigener Kunde nicht modifizierbar
        response = c.put('/api/v1/customers/%s' % self.main_customer.id, json.dumps({'name': 'sub customer 2'}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(400, response.status_code)
        
# TODO: translate
        # Falscher Fall: Customer darf nicht für wen anders veränderbar sein
        response = c.put('/api/v1/customers/%s' % self.other_root_customer.id, json.dumps({'name': 'other customer'}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response.status_code)
        
# TODO: translate
        # Falscher Fall: Customer darf nicht überschrieben werden auf einen Customer, der einem nicht gehört
        response = c.put('/api/v1/customers/%s' % sub_customer.id, json.dumps({'name': 'sub customer', 'parent_customer': str(self.other_root_customer.id)}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response.status_code)
        
# TODO: translate
        # Falscher Fall: Customer dürfen nicht doppelt angelegt werden
        response = c.put('/api/v1/customers/%s' % sub_customer.id, json.dumps({'name': self.main_customer.name, 'parent_customer': str(self.main_customer.id)}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(400, response.status_code)

    def test_delete_customer(self):
        c = Client()
        sub_customer = customer_models.Customer.objects.create(name='sub customer', parent_customer=self.main_customer)

# TODO: translate
        # korrekter Fall
        sub_customer_id = sub_customer.id
        response = c.delete('/api/v1/customers/%s' % sub_customer_id, HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(204, response.status_code)
        try:
            customer_models.Customer.objects.get(id=sub_customer_id)
            self.fail('customer not deleted')
        except customer_models.Customer.DoesNotExist:
            pass

# TODO: translate
        # Falscher Fall: Eigener Kunde nicht modifizierbar
        main_customer_id = self.main_customer.id
        response = c.delete('/api/v1/customers/%s' % main_customer_id, HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(400, response.status_code)
        try:
            customer_models.Customer.objects.get(id=main_customer_id)
        except customer_models.Customer.DoesNotExist:
            self.fail('customer deleted, but should exist')
        
# TODO: translate
        # Falscher Fall: Customer dürfen nicht doppelt angelegt werden
        other_customer_id = self.other_root_customer.id
        response = c.delete('/api/v1/customers/%s' % other_customer_id, HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response.status_code)
        try:
            customer_models.Customer.objects.get(id=other_customer_id)
        except customer_models.Customer.DoesNotExist:
            self.fail('customer deleted, but should exist')