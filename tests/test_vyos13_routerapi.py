from base64 import b64encode
from django.test import Client, TestCase
from django.contrib.auth.hashers import make_password
import uuid
from vycinity.models import basic_models, customer_models

class Vyos13RouterAPITest(TestCase):
    '''
    This is a test for VyOS 13 router API set.
    '''

    @classmethod
    def setUpTestData(cls):
        cls.test_router = basic_models.Vyos13Router.objects.create(name = "testrouter", loopback = "1.2.3.4", deploy = False, managed_interface_context = ['interfaces', 'ethernet', 'eth1'], token = 'dev123', fingerprint = '1234567890abcdef0')
        cls.root_customer = customer_models.Customer.objects.create(name = "root customer")
        cls.child_customer = customer_models.Customer.objects.create(name = "child customer", parent_customer = cls.root_customer)
        cls.root_user = customer_models.User.objects.create(name = 'root', display_name = 'root', customer = cls.root_customer)
        cls.child_user = customer_models.User.objects.create(name = 'child', display_name = 'child', customer = cls.child_customer)
        cls.root_auth = customer_models.LocalUserAuth.objects.create(user = cls.root_user, auth=make_password('root'))
        cls.child_auth = customer_models.LocalUserAuth.objects.create(user = cls.child_user, auth=make_password('child'))
        cls.root_authorization = 'Basic ' + b64encode('root:root'.encode('utf-8')).decode('ascii')
        cls.child_authorization = 'Basic ' + b64encode('child:child'.encode('utf-8')).decode('ascii')

    def test_list_routers_good(self):
        c = Client()
        response = c.get('/api/v1/routers/vyos13', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.root_authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertEqual(1, len(content))
        self.assertEqual(str(self.test_router.id), content[0]['id'])
        self.assertEqual('testrouter', content[0]['name'])
        self.assertEqual('1.2.3.4', content[0]['loopback'])
        self.assertFalse(content[0]['deploy'])
        self.assertListEqual(['interfaces', 'ethernet', 'eth1'], content[0]['managed_interface_context'])
        self.assertEqual('dev123', content[0]['token'])
        self.assertEqual('1234567890abcdef0', content[0]['fingerprint'])

    def test_list_routers_non_root_customer(self):
        c = Client()
        response = c.get('/api/v1/routers/vyos13', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.child_authorization)
        self.assertEqual(403, response.status_code)

    def test_add_router_good(self):
        c = Client()
        response = c.post('/api/v1/routers/vyos13', data={
            'name': 'testrouter2',
            'loopback': '3.4.5.6',
            'deploy': True,
            'managed_interface_context': ['interfaces', 'ethernet', 'eth3'],
            'token': 'dev345',
            'fingerprint': 'fedcba9876543210'
        }, content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.root_authorization)
        self.assertEqual(201, response.status_code)
        content = response.json()
        self.assertEqual('testrouter2', content['name'])
        self.assertEqual('3.4.5.6', content['loopback'])
        self.assertFalse(content['deploy'])
        self.assertListEqual(['interfaces', 'ethernet', 'eth3'], content['managed_interface_context'])
        self.assertEqual('dev345', content['token'])
        self.assertEqual('fedcba9876543210', content['fingerprint'])
        saved_object: basic_models.Vyos13Router = basic_models.Vyos13Router.objects.get(id=uuid.UUID(content['id']))
        self.assertIsNotNone(saved_object)
        self.assertEqual(content['name'], saved_object.name)
        self.assertEqual(content['loopback'], saved_object.loopback)
        self.assertFalse(saved_object.deploy)
        self.assertListEqual(content['managed_interface_context'], saved_object.managed_interface_context)
        self.assertEqual(content['token'], saved_object.token)
        self.assertEqual(content['fingerprint'], saved_object.fingerprint)
