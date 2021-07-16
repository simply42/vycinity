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
from django.test import Client, TestCase
from vycinity.models import customer_models, firewall_models
from django.contrib.auth.hashers import make_password
from base64 import b64encode
import json

class GenericAPITest(TestCase):
    # TODO: Translate, wording
    '''
    Tested die API für ein generisches besessenes Objekt. Hier am Beispiel von Rulesets, weil diese
    Referenzen auf Firewalls haben, die wiederum jemandem gehören.
    '''

    @classmethod
    def setUpTestData(cls):
        cls.main_customer = customer_models.Customer.objects.create(name = 'Test-Root customer')
        cls.main_user = customer_models.User.objects.create(name='testuser', customer=cls.main_customer)
        cls.other_customer = customer_models.Customer.objects.create(name='Other Root customer')
        cls.main_user_pw = 'testpw'
        customer_models.LocalUserAuth.objects.create(user=cls.main_user, auth=make_password(cls.main_user_pw))
        cls.authorization = 'Basic ' + b64encode((cls.main_user.name + ':' + cls.main_user_pw).encode('utf-8')).decode('ascii')
        cls.firewall_main_user = firewall_models.Firewall.objects.create(name='main firewall', stateful=False, default_action_into=firewall_models.ACTION_ACCEPT, default_action_from=firewall_models.ACTION_ACCEPT, owner=cls.main_customer, public=False)
        cls.firewall_other_user = firewall_models.Firewall.objects.create(name='other private firewall', stateful=False, default_action_into=firewall_models.ACTION_ACCEPT, default_action_from=firewall_models.ACTION_ACCEPT, owner=cls.other_customer, public=False)
        cls.private_ruleset_main_user = firewall_models.RuleSet.objects.create(comment='main private ruleset', priority=10, owner=cls.main_customer, public=False)
        cls.private_ruleset_main_user.firewalls.set([cls.firewall_main_user])
        cls.private_ruleset_other_user = firewall_models.RuleSet.objects.create(comment='other private ruleset', priority=10, owner=cls.other_customer, public=False)
        cls.private_ruleset_other_user.firewalls.set([cls.firewall_other_user])
        cls.public_ruleset_other_user = firewall_models.RuleSet.objects.create(comment='other public ruleset', priority=11, owner=cls.other_customer, public=True)
        cls.public_ruleset_other_user.firewalls.set([cls.firewall_other_user])

    def test_list_rulesets(self):
        c = Client()
        response = c.get('/api/v1/rulesets', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, list))
        self.assertEqual(2, len(content))
        self.assertEqual(self.private_ruleset_main_user.comment, content[0]['comment'])
        self.assertListEqual([str(self.firewall_main_user.id)], content[0]['firewalls'])
        self.assertEqual(10, content[0]['priority'])
        self.assertEqual(str(self.main_customer.id), content[0]['owner'])
        self.assertFalse(content[0]['public'])
        self.assertEqual(self.public_ruleset_other_user.comment, content[1]['comment'])
        self.assertListEqual([], content[1]['firewalls'])
        self.assertEqual(11, content[1]['priority'])
        self.assertEqual(str(self.other_customer.id), content[1]['owner'])
        self.assertTrue(content[1]['public'])

    def test_list_customer_subcustomer_rulesets(self):
        sub_customer = customer_models.Customer.objects.create(name='Test Sub customer', parent_customer=self.main_customer)
        sub_user = customer_models.User.objects.create(name='testuser2', customer=sub_customer)
        sub_user_pw = 'testpw2'
        customer_models.LocalUserAuth.objects.create(user=sub_user, auth=make_password(sub_user_pw))
        sub_auth = 'Basic ' + b64encode((sub_user.name + ':' + sub_user_pw).encode('utf-8')).decode('ascii')
        sub_customer_ruleset = firewall_models.RuleSet.objects.create(comment='Sub-customer ruleset', priority=12, owner=sub_customer, public=False)
        c = Client()

# TODO: translate
        # korrekte Liste mit Eltern- und Kind-Customer, aber ohne parallelem Customer 
        response = c.get('/api/v1/rulesets', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, list))
        self.assertEqual(3, len(content))
        self.assertEqual(self.private_ruleset_main_user.comment, content[0]['comment'])
        self.assertListEqual([str(self.firewall_main_user.id)], content[0]['firewalls'])
        self.assertEqual(10, content[0]['priority'])
        self.assertEqual(str(self.main_customer.id), content[0]['owner'])
        self.assertFalse(content[0]['public'])
        self.assertEqual(self.public_ruleset_other_user.comment, content[1]['comment'])
        self.assertListEqual([], content[1]['firewalls'])
        self.assertEqual(11, content[1]['priority'])
        self.assertEqual(str(self.other_customer.id), content[1]['owner'])
        self.assertTrue(content[1]['public'])
        self.assertEqual(sub_customer_ruleset.comment, content[2]['comment'])
        self.assertListEqual([], content[2]['firewalls'])
        self.assertEqual(12, content[2]['priority'])
        self.assertEqual(str(sub_customer.id), content[2]['owner'])
        self.assertFalse(content[2]['public'])

# TODO: translate
        # korrekte Liste nur mit Kind-Customer
        response = c.get('/api/v1/rulesets', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=sub_auth)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, list))
        self.assertEqual(2, len(content))
        self.assertEqual(self.public_ruleset_other_user.comment, content[0]['comment'])
        self.assertListEqual([], content[0]['firewalls'])
        self.assertEqual(11, content[0]['priority'])
        self.assertEqual(str(self.other_customer.id), content[0]['owner'])
        self.assertTrue(content[0]['public'])
        self.assertEqual(sub_customer_ruleset.comment, content[1]['comment'])
        self.assertListEqual([], content[1]['firewalls'])
        self.assertEqual(12, content[1]['priority'])
        self.assertEqual(str(sub_customer.id), content[1]['owner'])
        self.assertFalse(content[1]['public'])

    def test_get_single_ruleset(self):
        c = Client()

# TODO: translate
        # korrekter Fall eigenes Ruleset
        response = c.get('/api/v1/rulesets/%s' % self.private_ruleset_main_user.id, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual(self.private_ruleset_main_user.comment, content['comment'])
        self.assertListEqual([str(self.firewall_main_user.id)], content['firewalls'])
        self.assertEqual(10, content['priority'])
        self.assertEqual(str(self.main_customer.id), content['owner'])
        self.assertFalse(content['public'])

# TODO: translate
        # korrekter Fall anderes, öffentliches Ruleset
        response = c.get('/api/v1/rulesets/%s' % self.public_ruleset_other_user.id, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual(self.public_ruleset_other_user.comment, content['comment'])
        self.assertListEqual([], content['firewalls'])
        self.assertEqual(11, content['priority'])
        self.assertEqual(str(self.other_customer.id), content['owner'])
        self.assertTrue(content['public'])

# TODO: translate
        # Fall ohne Zugang
        response2 = c.get('/api/v1/rulesets/%s' % self.private_ruleset_other_user.id, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response2.status_code)

    def test_post_ruleset(self):
        c = Client()

# TODO: translate
        # korrekter Fall
        response = c.post('/api/v1/rulesets', {'comment': 'another ruleset', 'owner': self.main_customer.id, 'firewalls': [self.firewall_main_user.id], 'public': False, 'priority': 13}, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(201, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual('another ruleset', content['comment'])
        self.assertEqual(str(self.main_customer.id), content['owner'])
        self.assertEqual([str(self.firewall_main_user.id)], content['firewalls'])
        self.assertFalse(content['public'])
        self.assertEqual(13, content['priority'])
        
# TODO: translate
        # Falscher Fall: Ruleset darf nicht für wen anders anlegbar sein
        response = c.post('/api/v1/rulesets', {'comment': 'yet another ruleset', 'owner': str(self.other_customer.id), 'firewalls': [], 'public': False, 'priority': 13}, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response.status_code)

# TODO: translate
        # Falscher Fall: Ruleset darf nicht mit Daten ohne Zugang anlegbar sein
        response = c.post('/api/v1/rulesets', {'comment': 'yet another ruleset', 'owner': str(self.main_customer.id), 'firewalls': [str(self.firewall_other_user.id)], 'public': False, 'priority': 13}, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response.status_code)
        
    def test_put_ruleset(self):
        sub_customer = customer_models.Customer.objects.create(name='Test Sub customer', parent_customer=self.main_customer)
        sub_user = customer_models.User.objects.create(name='testuser2', customer=sub_customer)
        sub_user_pw = 'testpw2'
        customer_models.LocalUserAuth.objects.create(user=sub_user, auth=make_password(sub_user_pw))
        sub_auth = 'Basic ' + b64encode((sub_user.name + ':' + sub_user_pw).encode('utf-8')).decode('ascii')
        sub_customer_ruleset = firewall_models.RuleSet.objects.create(comment='Sub-customer ruleset', priority=12, owner=sub_customer, public=False)
        c = Client()

# TODO: translate
        # korrekter Fall
        response = c.put('/api/v1/rulesets/%s' % sub_customer_ruleset.id, json.dumps({'comment': 'sub customer ruleset 2', 'owner': str(sub_customer.id), 'priority': 12, 'public': False}), content_type='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual('sub customer ruleset 2', content['comment'])
        self.assertEqual(str(sub_customer.id), content['owner'])
        self.assertEqual(12, content['priority'])
        self.assertFalse(content['public'])
        self.assertListEqual([], content['firewalls'])

# TODO: translate
        # Falscher Fall: Sub Kunde darf keine Firewalls verwenden, die er nicht sehen kann
        response = c.put('/api/v1/rulesets/%s' % sub_customer_ruleset.id, json.dumps({'comment': 'sub customer ruleset 2', 'owner': str(sub_customer.id), 'priority': 12, 'public': False, 'firewalls':[str(self.firewall_main_user.id)]}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response.status_code)
        
# TODO: translate
        # Falscher Fall: Ruleset darf nicht für wen anders veränderbar sein
        response = c.put('/api/v1/rulesets/%s' % self.private_ruleset_other_user.id, json.dumps({'comment': 'my ruleset 2', 'owner': str(self.other_customer.id), 'priority': 10, 'public': False, 'firewalls':[str(self.firewall_other_user.id)]}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response.status_code)
        
# TODO: translate
        # Falscher Fall: Ruleset darf nicht überschrieben werden auf einen Customer, der einem nicht gehört
        response = c.put('/api/v1/rulesets/%s' % self.private_ruleset_main_user.id, json.dumps({'comment': 'my ruleset 2', 'owner': str(self.other_customer.id), 'priority': 10, 'public': False, 'firewalls':[str(self.firewall_other_user.id)]}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response.status_code)
        
# TODO: translate
        # Falscher Fall: Rulesets müssen konsistent sein
        response = c.put('/api/v1/rulesets/%s' % self.private_ruleset_main_user.id, json.dumps({'comment': 'sub customer ruleset 2', 'owner': str(self.main_customer.id), 'priority': 12, 'public': False, 'firewalls': [str(uuid.uuid4())]}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(400, response.status_code)

    def test_delete_customer(self):
        c = Client()

# TODO: translate
        # korrekter Fall
        own_private_ruleset_id = self.private_ruleset_main_user.id
        response = c.delete('/api/v1/rulesets/%s' % own_private_ruleset_id, HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(204, response.status_code)
        try:
            firewall_models.RuleSet.objects.get(id=own_private_ruleset_id)
            self.fail('Ruleset not deleted')
        except firewall_models.RuleSet.DoesNotExist:
            pass
        
# TODO: translate
        # Falscher Fall: Anderer Customer RuleSets dürfen nicht gelöscht werden
        other_customers_public_ruleset_id = self.public_ruleset_other_user.id
        response = c.delete('/api/v1/rulesets/%s' % other_customers_public_ruleset_id, HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response.status_code)
        try:
            firewall_models.RuleSet.objects.get(id=other_customers_public_ruleset_id)
        except firewall_models.RuleSet.DoesNotExist:
            self.fail('ruleset deleted, but should exist')