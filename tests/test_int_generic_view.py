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

import copy
import uuid
from django.test import Client, TestCase
from rest_framework import serializers
from vycinity.models import customer_models, firewall_models, change_models
from vycinity.serializers import firewall_serializers
from django.contrib.auth.hashers import make_password
from base64 import b64encode
import json

class GenericAPITest(TestCase):
    '''
    Tests the API for a generic owned object. Here a Ruleset is tested, as the logic of other owned
    object is the same, testing of them can be reduced or skipped. The Rulesets are tested here
    because they are quite complex as they have references to other owned objects.
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
        cls.changeset_ruleset_main_user = change_models.ChangeSet.objects.create(owner=cls.main_customer, user=cls.main_user, owner_name=cls.main_customer.name, user_name=cls.main_user.name)
        serialized_ruleset_main_user = firewall_serializers.RuleSetSerializer(cls.private_ruleset_main_user).data
        serialized_ruleset_main_user_modified = copy.deepcopy(serialized_ruleset_main_user)
        serialized_ruleset_main_user_modified['comment'] = 'main private ruleset modified'
        cls.change_ruleset_main_user_name = change_models.Change.objects.create(changeset=cls.changeset_ruleset_main_user, entity='RuleSet', pre=serialized_ruleset_main_user, post=serialized_ruleset_main_user_modified)

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

        response = c.get('/api/v1/rulesets?changeset=%s' % self.changeset_ruleset_main_user.id, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, list))
        self.assertEqual(2, len(content))
        self.assertEqual(self.change_ruleset_main_user_name.post['comment'], content[0]['comment'])
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

        # correct list of parents and childs rulesets, without parallel customer ones
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

        # correct liste of childs rulesets
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

        # correct case of getting an own Ruleset
        response = c.get('/api/v1/rulesets/%s' % self.private_ruleset_main_user.id, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual(self.private_ruleset_main_user.comment, content['comment'])
        self.assertListEqual([str(self.firewall_main_user.id)], content['firewalls'])
        self.assertEqual(10, content['priority'])
        self.assertEqual(str(self.main_customer.id), content['owner'])
        self.assertFalse(content['public'])

        # correct case for getting a public Ruleset
        response = c.get('/api/v1/rulesets/%s' % self.public_ruleset_other_user.id, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual(self.public_ruleset_other_user.comment, content['comment'])
        self.assertListEqual([], content['firewalls'])
        self.assertEqual(11, content['priority'])
        self.assertEqual(str(self.other_customer.id), content['owner'])
        self.assertTrue(content['public'])

        # case for getting a modified one
        response = c.get('/api/v1/rulesets/%s?changeset=%s' % (self.private_ruleset_main_user.id, self.changeset_ruleset_main_user.id), HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual(self.change_ruleset_main_user_name.post['comment'], content['comment'])
        self.assertListEqual([str(self.firewall_main_user.id)], content['firewalls'])
        self.assertEqual(10, content['priority'])
        self.assertEqual(str(self.main_customer.id), content['owner'])
        self.assertFalse(content['public'])

        # case without access
        response2 = c.get('/api/v1/rulesets/%s' % self.private_ruleset_other_user.id, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response2.status_code)

    def test_post_ruleset(self):
        c = Client()

        # correct case
        response = c.post('/api/v1/rulesets', {'comment': 'another ruleset', 'owner': self.main_customer.id, 'firewalls': [self.firewall_main_user.id], 'public': False, 'priority': 13}, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(201, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual('another ruleset', content['comment'])
        self.assertEqual(str(self.main_customer.id), content['owner'])
        self.assertEqual([str(self.firewall_main_user.id)], content['firewalls'])
        self.assertFalse(content['public'])
        self.assertEqual(13, content['priority'])
        self.assertIsNotNone(content['changeset'])
        new_changeset = change_models.ChangeSet.objects.get(id=content['changeset'])
        self.assertEqual(1, len(new_changeset.changes))
        self.assertIsNone(new_changeset.changes[0].pre)
        self.assertEqual('another ruleset', new_changeset.changes[0].post['comment'])
        self.assertEqual(str(self.main_customer.id), new_changeset.changes[0].post['owner'])
        self.assertEqual([str(self.firewall_main_user.id)], new_changeset.changes[0].post['firewalls'])
        self.assertFalse(new_changeset.changes[0].post['public'])
        self.assertEqual(13, new_changeset.changes[0].post['priority'])
        
        # wrong case: ruleset must not be created for other authorized customers
        response = c.post('/api/v1/rulesets', {'comment': 'yet another ruleset', 'owner': str(self.other_customer.id), 'firewalls': [], 'public': False, 'priority': 13}, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response.status_code)

        # wrong case: ruleset must not be created with references to inaccessible items
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

        # correct case
        ruleset_before_modification = firewall_serializers.RuleSetSerializer(sub_customer_ruleset).data
        response = c.put('/api/v1/rulesets/%s' % sub_customer_ruleset.id, json.dumps({'comment': 'sub customer ruleset 2', 'owner': str(sub_customer.id), 'priority': 12, 'public': False}), content_type='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual('sub customer ruleset 2', content['comment'])
        self.assertEqual(str(sub_customer.id), content['owner'])
        self.assertEqual(12, content['priority'])
        self.assertFalse(content['public'])
        self.assertListEqual([], content['firewalls'])
        self.assertIsNotNone(content['changeset'])
        new_changeset = change_models.ChangeSet.objects.get(id=content['changeset'])
        self.assertEqual(1, len(new_changeset.changes))
        self.assertEqual(ruleset_before_modification, new_changeset.changes[0].pre)
        self.assertEqual(content['comment'], new_changeset.changes[0].post['comment'])
        self.assertEqual(content['owner'], new_changeset.changes[0].post['owner'])
        self.assertEqual(content['firewalls'], new_changeset.changes[0].post['firewalls'])
        self.assertEqual(content['public'], new_changeset.changes[0].post['public'])
        self.assertEqual(content['priority'], new_changeset.changes[0].post['priority'])

        # correct case for already modified ruleset
        response = c.put('/api/v1/rulesets/%s?changeset=%s' % (self.private_ruleset_main_user.id, self.changeset_ruleset_main_user.id), json.dumps({'comment': 'main private ruleset modified', 'owner': str(self.private_ruleset_main_user.owner.id), 'priority': self.private_ruleset_main_user.priority, 'public': self.private_ruleset_main_user.public}), content_type='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual('sub customer ruleset 2', content['comment'])
        self.assertEqual(str(sub_customer.id), content['owner'])
        self.assertEqual(12, content['priority'])
        self.assertFalse(content['public'])
        self.assertListEqual([], content['firewalls'])
        self.assertEqual(str(self.changeset_ruleset_main_user.id), content['changeset'])
        modified_changeset = change_models.ChangeSet.objects.get(id=self.changeset_ruleset_main_user.id)
        self.assertEqual(1, len(new_changeset.changes))
        self.assertEqual(ruleset_before_modification, new_changeset.changes[0].pre)
        self.assertEqual(content['comment'], new_changeset.changes[0].post['comment'])
        self.assertEqual(content['owner'], new_changeset.changes[0].post['owner'])
        self.assertEqual(content['firewalls'], new_changeset.changes[0].post['firewalls'])
        self.assertEqual(content['public'], new_changeset.changes[0].post['public'])
        self.assertEqual(content['priority'], new_changeset.changes[0].post['priority'])

        # wrong case: sub customer must not use firewall which is not accessible
        response = c.put('/api/v1/rulesets/%s' % sub_customer_ruleset.id, json.dumps({'comment': 'sub customer ruleset 2', 'owner': str(sub_customer.id), 'priority': 12, 'public': False, 'firewalls':[str(self.firewall_main_user.id)]}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response.status_code)
        
        # wrong case: other customers ruleset must not be changable
        response = c.put('/api/v1/rulesets/%s' % self.private_ruleset_other_user.id, json.dumps({'comment': 'my ruleset 2', 'owner': str(self.other_customer.id), 'priority': 10, 'public': False, 'firewalls':[str(self.firewall_other_user.id)]}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response.status_code)
        
        # wrong case: ruleset must not be transferable to customer which is not accessible
        response = c.put('/api/v1/rulesets/%s' % self.private_ruleset_main_user.id, json.dumps({'comment': 'my ruleset 2', 'owner': str(self.other_customer.id), 'priority': 10, 'public': False, 'firewalls':[str(self.firewall_other_user.id)]}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response.status_code)
        
        # wrong case: ruleset must be consistent
        response = c.put('/api/v1/rulesets/%s' % self.private_ruleset_main_user.id, json.dumps({'comment': 'sub customer ruleset 2', 'owner': str(self.main_customer.id), 'priority': 12, 'public': False, 'firewalls': [str(uuid.uuid4())]}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(400, response.status_code)

    def test_delete_customer(self):
        c = Client()

        # correct case
        own_private_ruleset_id = self.private_ruleset_main_user.id
        response = c.delete('/api/v1/rulesets/%s' % own_private_ruleset_id, HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertIsNotNone(content['changeset'])
        changeset_containing_change = change_models.ChangeSet.objects.get(id=content['changeset'])
        self.assertEqual(1, len(changeset_containing_change.changes))
        self.assertEqual('Ruleset', changeset_containing_change.changes[0].entity)
        self.assertIsNone(changeset_containing_change.changes[0].post)
        
        # wrong case: rulesets of other customer must not be deleted
        other_customers_public_ruleset_id = self.public_ruleset_other_user.id
        response = c.delete('/api/v1/rulesets/%s' % other_customers_public_ruleset_id, HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response.status_code)