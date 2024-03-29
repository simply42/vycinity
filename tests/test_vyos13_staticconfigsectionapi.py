from base64 import b64encode
from celery import Task
from django.test import Client, TestCase
from django.contrib.auth.hashers import make_password
import uuid
from vycinity.models import basic_models, customer_models
from unittest.mock import Mock, patch

class Vyos13StaticConfigSectionAPITest(TestCase):
    '''
    This is a test for VyOS 13 StaticConfigSection API set.
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
        cls.test_static_config_section: basic_models.Vyos13StaticConfigSection = basic_models.Vyos13StaticConfigSection.objects.create(context = ['system', 'ntp'], description = 'NTP-Configuration', absolute = True, content = { 'server': {'time1.example.com':{}}})
        cls.test_router.active_static_configs.add(cls.test_static_config_section)

    def test_list_staticconfigsections_good(self):
        c = Client()
        response = c.get('/api/v1/scs/vyos13', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.root_authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertEqual(1, len(content['results']))
        self.assertEqual(content['results'][0]['id'], str(self.test_static_config_section.id))
        self.assertEqual(content['results'][0]['description'], self.test_static_config_section.description)
        self.assertTrue(content['results'][0]['absolute'])
        self.assertDictEqual(content['results'][0]['content'], { 'server': {'time1.example.com':{}}})
        self.assertListEqual(content['results'][0]['context'], ['system', 'ntp'])

    def test_list_staticconfigsections_non_root_customer(self):
        c = Client()
        response = c.get('/api/v1/scs/vyos13', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.child_authorization)
        self.assertEqual(403, response.status_code)
    
    def test_create_staticconfigsections_good(self):
        c = Client()
        new_scs = {
            'description': 'domain name',
            'context': ['system'],
            'absolute': False,
            'content': {'domain-name': 'example.com'}
        }
        response = c.post('/api/v1/scs/vyos13', data=new_scs, content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.root_authorization)
        self.assertEqual(201, response.status_code)
        content = response.json()
        self.assertEqual(content['description'], new_scs['description'])
        self.assertFalse(content['absolute'])
        self.assertDictEqual(content['content'], new_scs['content'])
        self.assertListEqual(content['context'], new_scs['context'])
        saved_scs: basic_models.Vyos13StaticConfigSection = basic_models.Vyos13StaticConfigSection.objects.get(id=uuid.UUID(content['id']))
        self.assertEqual(saved_scs.description, new_scs['description'])
        self.assertFalse(saved_scs.absolute)
        self.assertDictEqual(saved_scs.content, new_scs['content'])
        self.assertListEqual(saved_scs.context, new_scs['context'])

    def test_create_staticconfigsections_non_root_customer(self):
        c = Client()
        new_scs = {
            'description': 'domain name',
            'context': ['system'],
            'absolute': False,
            'content': {'domain-name': 'example.com'}
        }
        response = c.post('/api/v1/scs/vyos13', data=new_scs, content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.child_authorization)
        self.assertEqual(403, response.status_code)

    def test_read_staticconfigsection_good(self):
        c = Client()
        response = c.get('/api/v1/scs/vyos13/{}'.format(self.test_static_config_section.id), HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.root_authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertEqual(content['id'], str(self.test_static_config_section.id))
        self.assertEqual(content['description'], self.test_static_config_section.description)
        self.assertTrue(content['absolute'])
        self.assertDictEqual(content['content'], { 'server': {'time1.example.com':{}}})
        self.assertListEqual(content['context'], ['system', 'ntp'])

    def test_read_staticconfigsection_non_root_customer(self):
        c = Client()
        response = c.get('/api/v1/scs/vyos13/{}'.format(self.test_static_config_section.id), HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.child_authorization)
        self.assertEqual(403, response.status_code)
        
    def test_read_staticconfigsection_non_existent(self):
        c = Client()
        response = c.get('/api/v1/scs/vyos13/{}'.format(uuid.uuid4()), HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.root_authorization)
        self.assertEqual(404, response.status_code)

    @patch('vycinity.tasks.deploy', new=Mock(Task))
    @patch('vycinity.views.basic_views.deploy', new=Mock(Task))
    def test_update_staticconfigsection_good(self):
        c = Client()
        new_scs = {
            'description': 'updated ntp config',
            'absolute': True,
            'content': { 'server': {'time2.example.com':{}}},
            'context': ['system', 'ntp']
        }
        response = c.put('/api/v1/scs/vyos13/{}'.format(self.test_static_config_section.id), data=new_scs, content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.root_authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertEqual(content['id'], str(self.test_static_config_section.id))
        self.assertEqual(content['description'], new_scs['description'])
        self.assertTrue(content['absolute'])
        self.assertDictEqual(content['content'], new_scs['content'])
        self.assertListEqual(content['context'], new_scs['context'])
        self.test_static_config_section.refresh_from_db()
        self.assertEqual(content['description'], self.test_static_config_section.description)
        self.assertTrue(self.test_static_config_section.absolute)
        self.assertDictEqual(content['content'], self.test_static_config_section.content)
        self.assertListEqual(content['context'], self.test_static_config_section.context)

    def test_update_staticconfigsection_non_root_customer(self):
        c = Client()
        new_scs = {
            'description': 'updated ntp config',
            'absolute': True,
            'content': { 'server': {'time2.example.com':{}}},
            'context': ['system', 'ntp']
        }
        response = c.put('/api/v1/scs/vyos13/{}'.format(self.test_static_config_section.id), data=new_scs, content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.child_authorization)
        self.assertEqual(403, response.status_code)
        
    def test_update_staticconfigsection_non_existent(self):
        c = Client()
        new_scs = {
            'description': 'updated ntp config',
            'absolute': True,
            'content': { 'server': {'time2.example.com':{}}},
            'context': ['system', 'ntp']
        }
        response = c.put('/api/v1/scs/vyos13/{}'.format(uuid.uuid4()), data=new_scs, content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.root_authorization)
        self.assertEqual(404, response.status_code)
    
    def test_delete_staticconfigsection_good(self):
        c = Client()
        old_scs_id = self.test_static_config_section.id
        response = c.delete('/api/v1/scs/vyos13/{}'.format(old_scs_id), HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.root_authorization)
        self.assertEqual(204, response.status_code)
        
        try:
            basic_models.Vyos13StaticConfigSection.objects.get(id=old_scs_id)
            self.fail('Static config section deleted, but is still there')
        except basic_models.Vyos13StaticConfigSection.DoesNotExist:
            pass

    def test_delete_staticconfigsection_non_root_customer(self):
        c = Client()
        old_scs_id = self.test_static_config_section.id
        response = c.delete('/api/v1/scs/vyos13/{}'.format(old_scs_id), HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.child_authorization)
        self.assertEqual(403, response.status_code)
        
        try:
            basic_models.Vyos13StaticConfigSection.objects.get(id=old_scs_id)
        except basic_models.Vyos13StaticConfigSection.DoesNotExist:
            self.fail('Static config section deleted as non root (should not be allowed), but does not more exist')
        
    def test_delete_staticconfigsection_non_existent(self):
        c = Client()
        response = c.delete('/api/v1/scs/vyos13/{}'.format(uuid.uuid4()), HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.root_authorization)
        self.assertEqual(404, response.status_code)