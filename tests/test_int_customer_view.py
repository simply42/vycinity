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
        self.assertTrue(isinstance(content['results'], list))
        self.assertEqual(1, len(content['results']))
        self.assertEqual(self.main_customer.name, content['results'][0]['name'])
        self.assertIsNone(content['results'][0]['parent_customer'])
        self.assertEqual(str(self.main_customer.id), content['results'][0]['id'])

    def test_list_customer_multiple(self):
        sub_customer = customer_models.Customer.objects.create(name='Test Sub customer', parent_customer=self.main_customer)
        sub_user = customer_models.User.objects.create(name='testuser2', customer=sub_customer)
        sub_user_pw = 'testpw2'
        customer_models.LocalUserAuth.objects.create(user=sub_user, auth=make_password(sub_user_pw))
        sub_auth = 'Basic ' + b64encode((sub_user.name + ':' + sub_user_pw).encode('utf-8')).decode('ascii') 
        c = Client()

        # correct list including parent-customer and child customer, without "parallel" customer
        response = c.get('/api/v1/customers', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content['results'], list))
        self.assertEqual(2, len(content['results']))
        correct_ids = []
        for result in content['results']:
            if result['id'] == str(self.main_customer.id):
                self.assertEqual(self.main_customer.name, result['name'])
                self.assertIsNone(result['parent_customer'])
                correct_ids.append(result['id'])
            if result['id'] == str(sub_customer.id):
                self.assertEqual(sub_customer.name, result['name'])
                self.assertEqual(str(self.main_customer.id), result['parent_customer'])
                correct_ids.append(result['id'])

        self.assertIn(str(self.main_customer.id), correct_ids)
        self.assertIn(str(sub_customer.id), correct_ids)

        # correct list with child customer
        response = c.get('/api/v1/customers', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=sub_auth)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content['results'], list))
        self.assertEqual(1, len(content['results']))
        self.assertEqual(sub_customer.name, content['results'][0]['name'])
        self.assertEqual(str(self.main_customer.id), content['results'][0]['parent_customer'])
        self.assertEqual(str(sub_customer.id), content['results'][0]['id'])

    def test_get_single_customer(self):
        c = Client()

        # correct case
        response = c.get('/api/v1/customers/%s' % self.main_customer.id, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual(self.main_customer.name, content['name'])
        self.assertIsNone(content['parent_customer'])
        self.assertEqual(str(self.main_customer.id), content['id'])

        # wrong: no access
        response2 = c.get('/api/v1/customers/%s' % self.other_root_customer.id, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response2.status_code)

    def test_post_customer(self):
        c = Client()

        # good
        response = c.post('/api/v1/customers', {'name': 'sub customer', 'parent_customer': str(self.main_customer.id)}, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(201, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual('sub customer', content['name'])
        self.assertEqual(str(self.main_customer.id), content['parent_customer'])

        # wrong: no root customers may be created via api
        response = c.post('/api/v1/customers', {'name': 'sub customer 2'}, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(400, response.status_code)
        
        # wrong: no customer for someone else out of control
        response = c.post('/api/v1/customers', {'name': 'sub customer 3', 'parent_customer': str(self.other_root_customer.id)}, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertLessEqual(400, response.status_code)
        self.assertGreater(500, response.status_code)
        
        # wrong: no double customers
        response = c.post('/api/v1/customers', {'name': 'sub customer', 'parent_customer': str(self.main_customer.id)}, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertLessEqual(400, response.status_code)
        self.assertGreater(500, response.status_code)
        
    def test_put_customer(self):
        c = Client()
        sub_customer = customer_models.Customer.objects.create(name='sub customer', parent_customer=self.main_customer)

        # good
        response = c.put('/api/v1/customers/%s' % sub_customer.id, json.dumps({'name': 'sub customer 1', 'parent_customer': str(self.main_customer.id)}), content_type='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual('sub customer 1', content['name'])
        self.assertEqual(str(self.main_customer.id), content['parent_customer'])

        # wrong: own customer not modifiable
        response = c.put('/api/v1/customers/%s' % self.main_customer.id, json.dumps({'name': 'sub customer 2'}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertLessEqual(400, response.status_code)
        self.assertGreater(500, response.status_code)
        
        # wrong: other customer under control may not be modifiable
        response = c.put('/api/v1/customers/%s' % self.other_root_customer.id, json.dumps({'name': 'other customer'}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertLessEqual(400, response.status_code)
        self.assertGreater(500, response.status_code)
        
        # wrong: no movement of a customer to another one out of control
        response = c.put('/api/v1/customers/%s' % sub_customer.id, json.dumps({'name': 'sub customer', 'parent_customer': str(self.other_root_customer.id)}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertLessEqual(400, response.status_code)
        self.assertGreater(500, response.status_code)
        
        # wrong: no double customers
        response = c.put('/api/v1/customers/%s' % sub_customer.id, json.dumps({'name': self.main_customer.name, 'parent_customer': str(self.main_customer.id)}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertLessEqual(400, response.status_code)
        self.assertGreater(500, response.status_code)

    def test_delete_customer(self):
        c = Client()
        sub_customer = customer_models.Customer.objects.create(name='sub customer', parent_customer=self.main_customer)

        # good
        sub_customer_id = sub_customer.id
        response = c.delete('/api/v1/customers/%s' % sub_customer_id, HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(204, response.status_code)
        try:
            customer_models.Customer.objects.get(id=sub_customer_id)
            self.fail('customer not deleted')
        except customer_models.Customer.DoesNotExist:
            pass

        # wrong: own customer not modifiable
        main_customer_id = self.main_customer.id
        response = c.delete('/api/v1/customers/%s' % main_customer_id, HTTP_AUTHORIZATION=self.authorization)
        self.assertLessEqual(400, response.status_code)
        self.assertGreater(500, response.status_code)
        try:
            customer_models.Customer.objects.get(id=main_customer_id)
        except customer_models.Customer.DoesNotExist:
            self.fail('customer deleted, but should exist')
        
        # wrong: other customer out of control may not be modified
        other_customer_id = self.other_root_customer.id
        response = c.delete('/api/v1/customers/%s' % other_customer_id, HTTP_AUTHORIZATION=self.authorization)
        self.assertLessEqual(400, response.status_code)
        self.assertGreater(500, response.status_code)
        try:
            customer_models.Customer.objects.get(id=other_customer_id)
        except customer_models.Customer.DoesNotExist:
            self.fail('customer deleted, but should exist')