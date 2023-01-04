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
from datetime import datetime, timezone
import ipaddress
import uuid
from django.db.models.query_utils import Q
from django.test import Client, TestCase
from vycinity.models import OWNED_OBJECT_STATE_DELETED, customer_models, firewall_models, change_models, network_models, OWNED_OBJECT_STATE_LIVE, OWNED_OBJECT_STATE_PREPARED
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
        cls.firewall_main_user = firewall_models.Firewall.objects.create(name='main firewall', stateful=False, default_action_into=firewall_models.ACTION_ACCEPT, default_action_from=firewall_models.ACTION_ACCEPT, owner=cls.main_customer, public=False, state=OWNED_OBJECT_STATE_LIVE)
        cls.firewall_other_user = firewall_models.Firewall.objects.create(name='other private firewall', stateful=False, default_action_into=firewall_models.ACTION_ACCEPT, default_action_from=firewall_models.ACTION_ACCEPT, owner=cls.other_customer, public=False, state=OWNED_OBJECT_STATE_LIVE)
        cls.private_ruleset_main_user = firewall_models.RuleSet.objects.create(comment='main private ruleset', priority=10, owner=cls.main_customer, public=False, state=OWNED_OBJECT_STATE_LIVE)
        cls.private_ruleset_main_user.firewalls.set([cls.firewall_main_user])
        cls.private_ruleset_main_user_wo_ref = firewall_models.RuleSet.objects.create(comment='main private ruleset', priority=10, owner=cls.main_customer, public=False, state=OWNED_OBJECT_STATE_LIVE)
        cls.private_ruleset_other_user = firewall_models.RuleSet.objects.create(comment='other private ruleset', priority=10, owner=cls.other_customer, public=False, state=OWNED_OBJECT_STATE_LIVE)
        cls.private_ruleset_other_user.firewalls.set([cls.firewall_other_user])
        cls.public_ruleset_other_user = firewall_models.RuleSet.objects.create(comment='other public ruleset', priority=11, owner=cls.other_customer, public=True, state=OWNED_OBJECT_STATE_LIVE)
        cls.public_ruleset_other_user.firewalls.set([cls.firewall_other_user])
        cls.changeset_ruleset_main_user = change_models.ChangeSet.objects.create(owner=cls.main_customer, user=cls.main_user, owner_name=cls.main_customer.name, user_name=cls.main_user.name)
        cls.private_ruleset_main_user_modified = firewall_models.RuleSet.objects.get(pk=cls.private_ruleset_main_user.pk)
        cls.private_ruleset_main_user_modified.pk = None
        cls.private_ruleset_main_user_modified.id = None
        cls.private_ruleset_main_user_modified._state.adding = True
        cls.private_ruleset_main_user_modified.comment = 'main private ruleset modified'
        cls.private_ruleset_main_user_modified.state = OWNED_OBJECT_STATE_PREPARED
        cls.private_ruleset_main_user_modified.save()
        cls.private_ruleset_main_user_modified.firewalls.set([cls.firewall_main_user])
        cls.change_ruleset_main_user_name = change_models.Change.objects.create(changeset=cls.changeset_ruleset_main_user, entity='RuleSet', pre=cls.private_ruleset_main_user, post=cls.private_ruleset_main_user_modified, action=change_models.ACTION_MODIFIED)

    def test_list_rulesets(self):
        c = Client()
        response = c.get('/api/v1/rulesets', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, list))
        self.assertEqual(3, len(content))
        found_valid_main_user_ruleset = False
        found_valid_other_user_ruleset = False
        found_valid_main_user_ruleset_wo_ref = False
        for content_object in content:
            if self.private_ruleset_main_user.uuid == uuid.UUID(content_object['uuid']):
                self.assertEqual(self.private_ruleset_main_user.comment, content_object['comment'])
                self.assertListEqual([str(self.firewall_main_user.uuid)], content_object['firewalls'])
                self.assertEqual(10, content_object['priority'])
                self.assertEqual(str(self.main_customer.id), content_object['owner'])
                self.assertFalse(content_object['public'])
                found_valid_main_user_ruleset = True
            elif self.public_ruleset_other_user.uuid == uuid.UUID(content_object['uuid']):
                self.assertEqual(self.public_ruleset_other_user.comment, content_object['comment'])
                self.assertListEqual([], content_object['firewalls'])
                self.assertEqual(11, content_object['priority'])
                self.assertEqual(str(self.other_customer.id), content_object['owner'])
                self.assertTrue(content_object['public'])
                found_valid_other_user_ruleset = True
            elif self.private_ruleset_main_user_wo_ref.uuid == uuid.UUID(content_object['uuid']):
                self.assertEqual(self.private_ruleset_main_user_wo_ref.comment, content_object['comment'])
                self.assertListEqual([], content_object['firewalls'])
                self.assertEqual(10, content_object['priority'])
                self.assertEqual(str(self.main_customer.id), content_object['owner'])
                self.assertFalse(content_object['public'])
                found_valid_main_user_ruleset_wo_ref = True
        self.assertTrue(found_valid_main_user_ruleset)
        self.assertTrue(found_valid_other_user_ruleset)
        self.assertTrue(found_valid_main_user_ruleset_wo_ref)

        response = c.get('/api/v1/rulesets?changeset=%s' % self.changeset_ruleset_main_user.id, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, list))
        self.assertEqual(3, len(content))
        found_valid_main_user_ruleset = False
        found_valid_other_user_ruleset = False
        found_valid_main_user_ruleset_wo_ref = False
        for content_object in content:
            if self.private_ruleset_main_user.uuid == uuid.UUID(content_object['uuid']):
                self.assertEqual(self.private_ruleset_main_user_modified.comment, content_object['comment'])
                self.assertListEqual([str(self.firewall_main_user.uuid)], content_object['firewalls'])
                self.assertEqual(10, content_object['priority'])
                self.assertEqual(str(self.main_customer.id), content_object['owner'])
                self.assertFalse(content_object['public'])
                found_valid_main_user_ruleset = True
            elif self.public_ruleset_other_user.uuid == uuid.UUID(content_object['uuid']):
                self.assertEqual(self.public_ruleset_other_user.comment, content_object['comment'])
                self.assertListEqual([], content_object['firewalls'])
                self.assertEqual(11, content_object['priority'])
                self.assertEqual(str(self.other_customer.id), content_object['owner'])
                self.assertTrue(content_object['public'])
                found_valid_other_user_ruleset = True
            elif self.private_ruleset_main_user_wo_ref.uuid == uuid.UUID(content_object['uuid']):
                self.assertEqual(self.private_ruleset_main_user_wo_ref.comment, content_object['comment'])
                self.assertListEqual([], content_object['firewalls'])
                self.assertEqual(10, content_object['priority'])
                self.assertEqual(str(self.main_customer.id), content_object['owner'])
                self.assertFalse(content_object['public'])
                found_valid_main_user_ruleset_wo_ref = True
        self.assertTrue(found_valid_main_user_ruleset)
        self.assertTrue(found_valid_other_user_ruleset)
        self.assertTrue(found_valid_main_user_ruleset_wo_ref)

    def test_list_customer_subcustomer_rulesets(self):
        sub_customer = customer_models.Customer.objects.create(name='Test Sub customer', parent_customer=self.main_customer)
        sub_user = customer_models.User.objects.create(name='testuser2', customer=sub_customer)
        sub_user_pw = 'testpw2'
        customer_models.LocalUserAuth.objects.create(user=sub_user, auth=make_password(sub_user_pw))
        sub_auth = 'Basic ' + b64encode((sub_user.name + ':' + sub_user_pw).encode('utf-8')).decode('ascii')
        sub_customer_ruleset = firewall_models.RuleSet.objects.create(comment='Sub-customer ruleset', priority=12, owner=sub_customer, public=False, state=OWNED_OBJECT_STATE_LIVE)
        c = Client()

        # correct list of parents and childs rulesets, without parallel customer ones
        response = c.get('/api/v1/rulesets', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, list))
        self.assertEqual(4, len(content))
        valid_comparisons = []
        for current_content in content:
            comparison_object: firewall_models.RuleSet = None
            if current_content['uuid'] == str(self.private_ruleset_main_user.uuid):
                comparison_object = self.private_ruleset_main_user
            elif current_content['uuid'] == str(self.public_ruleset_other_user.uuid):
                comparison_object = self.public_ruleset_other_user
            elif current_content['uuid'] == str(sub_customer_ruleset.uuid):
                comparison_object = sub_customer_ruleset
            elif current_content['uuid'] == str(self.private_ruleset_main_user_wo_ref.uuid):
                comparison_object = self.private_ruleset_main_user_wo_ref
            self.assertIsNotNone(comparison_object)
            self.assertNotIn(comparison_object, valid_comparisons)
            self.assertEqual(comparison_object.comment, current_content['comment'])
            self.assertListEqual(list(map(lambda ref: str(ref.uuid), comparison_object.firewalls.filter(Q(owner__in=self.main_customer.get_visible_customers()) | Q(public=True)))), current_content['firewalls'])
            self.assertEqual(comparison_object.priority, current_content['priority'])
            self.assertEqual(str(comparison_object.owner.id), current_content['owner'])
            self.assertEqual(comparison_object.public, current_content['public'])
            valid_comparisons.append(comparison_object)
        self.assertEqual(4, len(valid_comparisons))

        # correct list of childs rulesets
        response = c.get('/api/v1/rulesets', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=sub_auth)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, list))
        self.assertEqual(2, len(content))
        valid_comparisons = []
        for current_content in content:
            comparison_object: firewall_models.RuleSet = None
            if current_content['uuid'] == str(self.public_ruleset_other_user.uuid):
                comparison_object = self.public_ruleset_other_user
            elif current_content['uuid'] == str(sub_customer_ruleset.uuid):
                comparison_object = sub_customer_ruleset
            self.assertIsNotNone(comparison_object)
            self.assertNotIn(comparison_object, valid_comparisons)
            self.assertEqual(comparison_object.comment, current_content['comment'])
            self.assertListEqual(list(map(lambda ref: str(ref.uuid), comparison_object.firewalls.filter(Q(owner__in=sub_customer.get_visible_customers()) | Q(public=True)))), current_content['firewalls'])
            self.assertEqual(comparison_object.priority, current_content['priority'])
            self.assertEqual(str(comparison_object.owner.id), current_content['owner'])
            self.assertEqual(comparison_object.public, current_content['public'])
            valid_comparisons.append(comparison_object)
        self.assertEqual(2, len(valid_comparisons))

    def test_get_single_ruleset(self):
        c = Client()

        # correct case of getting an own Ruleset
        response = c.get('/api/v1/rulesets/%s' % self.private_ruleset_main_user.uuid, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual(self.private_ruleset_main_user.comment, content['comment'])
        self.assertListEqual([str(self.firewall_main_user.uuid)], content['firewalls'])
        self.assertEqual(10, content['priority'])
        self.assertEqual(str(self.main_customer.id), content['owner'])
        self.assertFalse(content['public'])

        # correct case for getting a public Ruleset
        response = c.get('/api/v1/rulesets/%s' % self.public_ruleset_other_user.uuid, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual(self.public_ruleset_other_user.comment, content['comment'])
        self.assertListEqual([], content['firewalls'])
        self.assertEqual(11, content['priority'])
        self.assertEqual(str(self.other_customer.id), content['owner'])
        self.assertTrue(content['public'])

        # case for getting a modified one
        response = c.get('/api/v1/rulesets/%s?changeset=%s' % (self.private_ruleset_main_user.uuid, self.changeset_ruleset_main_user.id), HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual(self.change_ruleset_main_user_name.post.comment, content['comment'])
        self.assertListEqual([str(self.firewall_main_user.uuid)], content['firewalls'])
        self.assertEqual(10, content['priority'])
        self.assertEqual(str(self.main_customer.id), content['owner'])
        self.assertFalse(content['public'])

        # case without access
        response2 = c.get('/api/v1/rulesets/%s' % self.private_ruleset_other_user.uuid, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertLess(400, response2.status_code)

    def test_post_ruleset(self):
        c = Client()

        # correct case
        response = c.post('/api/v1/rulesets', {'comment': 'another ruleset', 'owner': self.main_customer.id, 'firewalls': [str(self.firewall_main_user.uuid)], 'public': False, 'priority': 13}, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(201, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual('another ruleset', content['comment'])
        self.assertEqual(str(self.main_customer.id), content['owner'])
        self.assertEqual([str(self.firewall_main_user.uuid)], content['firewalls'])
        self.assertFalse(content['public'])
        self.assertEqual(13, content['priority'])
        self.assertIsNotNone(content['changeset'])
        new_changeset = change_models.ChangeSet.objects.get(id=content['changeset'])
        self.assertEqual(1, new_changeset.changes.count())
        change_in_set = new_changeset.changes.first()
        self.assertIsNone(change_in_set.pre)
        self.assertEqual(firewall_models.RuleSet.objects.get(uuid=content['uuid'], state=OWNED_OBJECT_STATE_PREPARED), change_in_set.post.ruleset)
        
        # wrong case: ruleset must not be created for other authorized customers
        response = c.post('/api/v1/rulesets', {'comment': 'yet another ruleset', 'owner': str(self.other_customer.id), 'firewalls': [], 'public': False, 'priority': 13}, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response.status_code)

        # wrong case: ruleset must not be created with references to inaccessible items
        response = c.post('/api/v1/rulesets', {'comment': 'yet another ruleset', 'owner': str(self.main_customer.id), 'firewalls': [str(self.firewall_other_user.uuid)], 'public': False, 'priority': 13}, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response.status_code)

        # wrong case: changeset may not be changed after application
        applied_changeset = change_models.ChangeSet.objects.create(owner=self.main_customer, owner_name=self.main_customer.name, user=self.main_user, user_name=self.main_user.name)
        applied_changeset.applied = datetime.now(timezone.utc)
        applied_changeset.save()
        response = c.post('/api/v1/rulesets?changeset=%s' % applied_changeset.id, {'comment': 'just another ruleset', 'owner': self.main_customer.id, 'firewalls': [str(self.firewall_main_user.uuid)], 'public': False, 'priority': 13}, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(400, response.status_code)
        applied_changeset.refresh_from_db()
        self.assertEqual(0, applied_changeset.changes.count())

    def test_post_rule_in_new_ruleset(self):
        c = Client()

        # correct case: the referenced Object was created in the changeset
        any_address_object = firewall_models.CIDRAddressObject.objects.create(owner=self.main_customer, name='any', ipv4_network_address='0.0.0.0', ipv4_network_bits=0, state=OWNED_OBJECT_STATE_LIVE)
        changeset = change_models.ChangeSet.objects.create(owner=self.main_customer, user=self.main_user, owner_name=self.main_customer.name, user_name=self.main_user.name)
        ruleset_in_changeset: firewall_models.RuleSet = firewall_models.RuleSet.objects.create(comment='my ruleset', owner=self.main_customer, public=False, priority=14, state=OWNED_OBJECT_STATE_PREPARED)
        ruleset_in_changeset.firewalls.set([self.firewall_main_user])
        change_models.Change.objects.create(changeset=changeset, entity=firewall_models.RuleSet.__name__, post=ruleset_in_changeset)
        
        response = c.post('/api/v1/rules/basic?changeset={}'.format(changeset.id), {'related_ruleset': str(ruleset_in_changeset.uuid), 'priority': 10, 'disable': False, 'destination_address': str(any_address_object.uuid), 'log': False, 'action': 'accept'}, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(201, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual(str(ruleset_in_changeset.uuid), content['related_ruleset'])
        self.assertEqual(10, content['priority'])
        self.assertEqual(str(any_address_object.uuid), content['destination_address'])
        self.assertFalse(content['disable'])
        self.assertFalse(content['log'])
        self.assertEquals(str(changeset.id), content['changeset'])
        self.assertIsNotNone(content['uuid'])
        found_new_change = False
        for change in changeset.changes.all():
            if change.post.uuid == uuid.UUID(content['uuid']):
                found_new_change = True
                self.assertIsNone(change.pre)
                self.assertEqual(change_models.ACTION_CREATED, change.action)
                self.assertEqual(ruleset_in_changeset.pk, change.post.rule.related_ruleset.pk)
                self.assertEqual(10, change.post.rule.priority)
                self.assertEqual(any_address_object.pk, change.post.rule.basicrule.destination_address.pk)
                self.assertEqual(content['disable'], change.post.rule.disable)
                self.assertEqual(content['log'], change.post.rule.basicrule.log)
                break
        self.assertTrue(found_new_change)

        # bad case: the referenced object was already deleted in the changeset
        self.changeset_ruleset_main_user.post = None
        self.changeset_ruleset_main_user.save()
        response = c.post('/api/v1/rules/basic?changeset={}'.format(self.changeset_ruleset_main_user.id), {'related_ruleset': str(self.private_ruleset_main_user.id), 'priority': 10, 'disable': False, 'destination_address': str(any_address_object.id), 'log': False, 'action': 'accept'}, HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(400, response.status_code)
        
    def test_put_ruleset(self):
        sub_customer = customer_models.Customer.objects.create(name='Test Sub customer', parent_customer=self.main_customer)
        sub_user = customer_models.User.objects.create(name='testuser2', customer=sub_customer)
        sub_user_pw = 'testpw2'
        customer_models.LocalUserAuth.objects.create(user=sub_user, auth=make_password(sub_user_pw))
        sub_auth = 'Basic ' + b64encode((sub_user.name + ':' + sub_user_pw).encode('utf-8')).decode('ascii')
        sub_customer_ruleset = firewall_models.RuleSet.objects.create(comment='Sub-customer ruleset', priority=12, owner=sub_customer, public=False, state=OWNED_OBJECT_STATE_LIVE)
        c = Client()

        # correct case
        #ruleset_before_modification = firewall_serializers.RuleSetSerializer(sub_customer_ruleset)
        response = c.put('/api/v1/rulesets/%s' % sub_customer_ruleset.uuid, json.dumps({'comment': 'sub customer ruleset 2', 'owner': str(sub_customer.id), 'priority': 12, 'public': False}), content_type='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual('sub customer ruleset 2', content['comment'])
        self.assertEqual(str(sub_customer.id), content['owner'])
        self.assertEqual(12, content['priority'])
        self.assertFalse(content['public'])
        self.assertEqual(0, len(content['firewalls']))
        self.assertIsNotNone(content['changeset'])
        new_changeset = change_models.ChangeSet.objects.get(id=uuid.UUID(content['changeset']))
        self.assertEqual(1, new_changeset.changes.count())
        change_in_set = new_changeset.changes.first()
        self.assertEqual(sub_customer_ruleset.pk, change_in_set.pre.pk)
        self.assertEqual(content['comment'], change_in_set.post.ruleset.comment)
        self.assertEqual(content['owner'], str(change_in_set.post.ruleset.owner.id))
        self.assertEqual(0, change_in_set.post.ruleset.firewalls.count())
        self.assertEqual(content['public'], change_in_set.post.ruleset.public)
        self.assertEqual(content['priority'], change_in_set.post.ruleset.priority)

        # correct case for already modified ruleset
        #ruleset_before_modification = firewall_serializers.RuleSetSerializer(self.private_ruleset_main_user).data
        response = c.put('/api/v1/rulesets/%s?changeset=%s' % (self.private_ruleset_main_user.uuid, self.changeset_ruleset_main_user.id), json.dumps({'comment': 'main private ruleset modified again', 'owner': str(self.private_ruleset_main_user.owner.id), 'priority': 27, 'public': False}), content_type='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertTrue(isinstance(content, dict))
        self.assertEqual('main private ruleset modified again', content['comment'])
        self.assertEqual(str(self.private_ruleset_main_user.owner.id), content['owner'])
        self.assertEqual(27, content['priority'])
        self.assertFalse(content['public'])
        self.assertListEqual([str(self.private_ruleset_main_user.firewalls.first().uuid)], content['firewalls'])
        self.assertEqual(str(self.changeset_ruleset_main_user.id), content['changeset'])
        modified_changeset = change_models.ChangeSet.objects.get(id=self.changeset_ruleset_main_user.id)
        self.assertEqual(1, modified_changeset.changes.count())
        change_in_modified_set = modified_changeset.changes.first()
        self.assertEqual(self.private_ruleset_main_user.pk, change_in_modified_set.pre.pk)
        self.assertEqual(content['comment'], change_in_modified_set.post.ruleset.comment)
        self.assertEqual(content['owner'], str(change_in_modified_set.post.ruleset.owner.id))
        self.assertEqual(1, change_in_modified_set.post.ruleset.firewalls.count())
        self.assertEqual(self.private_ruleset_main_user.firewalls.first().uuid, change_in_modified_set.post.ruleset.firewalls.first().uuid)
        self.assertEqual(content['public'], change_in_modified_set.post.ruleset.public)
        self.assertEqual(content['priority'], change_in_modified_set.post.ruleset.priority)

        # wrong case for deleted ruleset in changeset, resurrection is not possible
        changeset_w_deleted_ruleset = change_models.ChangeSet.objects.create(owner=self.main_customer, owner_name=self.main_customer.name, user=self.main_user, user_name=self.main_user.name)
        deleted_ruleset = firewall_models.RuleSet.objects.get(pk=self.private_ruleset_main_user.pk)
        deleted_ruleset.id = None
        deleted_ruleset.pk = None
        deleted_ruleset._state.adding = True
        deleted_ruleset.state = OWNED_OBJECT_STATE_DELETED
        deleted_ruleset.save()
        change_models.Change.objects.create(changeset=changeset_w_deleted_ruleset, entity=firewall_models.RuleSet.__name__, pre=self.private_ruleset_main_user, post=deleted_ruleset, action=change_models.ACTION_DELETED)
        response = c.put('/api/v1/rulesets/%s?changeset=%s' % (self.private_ruleset_main_user.uuid, changeset_w_deleted_ruleset.id), json.dumps({'comment': 'main private ruleset resurrected', 'owner': str(self.private_ruleset_main_user.owner.id), 'priority': 27, 'public': False}), content_type='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(404, response.status_code)

        # wrong case: sub customer must not use firewall which is not accessible
        response = c.put('/api/v1/rulesets/%s' % sub_customer_ruleset.uuid, json.dumps({'comment': 'sub customer ruleset 2', 'owner': str(sub_customer.id), 'priority': 12, 'public': False, 'firewalls':[str(self.firewall_main_user.uuid)]}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertLessEqual(400, response.status_code)
        self.assertGreater(500, response.status_code)
        
        # wrong case: other customers ruleset must not be changable
        response = c.put('/api/v1/rulesets/%s' % self.private_ruleset_other_user.uuid, json.dumps({'comment': 'my ruleset 2', 'owner': str(self.other_customer.id), 'priority': 10, 'public': False, 'firewalls':[str(self.firewall_other_user.uuid)]}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertLess(400, response.status_code)
        self.assertGreater(500, response.status_code)
        
        # wrong case: ruleset must not be transferable to customer which is not accessible
        response = c.put('/api/v1/rulesets/%s' % self.private_ruleset_main_user.uuid, json.dumps({'comment': 'my ruleset 2', 'owner': str(self.other_customer.id), 'priority': 10, 'public': False, 'firewalls':[str(self.firewall_other_user.uuid)]}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertLessEqual(400, response.status_code)
        self.assertGreater(500, response.status_code)
        
        # wrong case: ruleset must be consistent
        response = c.put('/api/v1/rulesets/%s' % self.private_ruleset_main_user.uuid, json.dumps({'comment': 'sub customer ruleset 2', 'owner': str(self.main_customer.id), 'priority': 12, 'public': False, 'firewalls': [str(uuid.uuid4())]}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(400, response.status_code)

        # wrong case: changeset may not be changed after application
        applied_changeset = change_models.ChangeSet.objects.create(owner=self.main_customer, owner_name=self.main_customer.name, user=self.main_user, user_name=self.main_user.name)
        applied_changeset.applied = datetime.now(timezone.utc)
        applied_changeset.save()
        response = c.put('/api/v1/rulesets/%s?changeset=%s' % (self.private_ruleset_main_user.uuid, applied_changeset.id), json.dumps({'comment': 'sub customer ruleset 2', 'owner': str(self.main_customer.id), 'priority': 12, 'public': False, 'firewalls': []}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(400, response.status_code)
        applied_changeset.refresh_from_db()
        self.assertEqual(0, applied_changeset.changes.count())


    def test_delete_customer(self):
        c = Client()

        # correct case: simple
        own_private_ruleset_id = self.private_ruleset_main_user_wo_ref.uuid
        response = c.delete('/api/v1/rulesets/%s' % own_private_ruleset_id, HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        content = response.json()
        self.assertIsNotNone(content['changeset'])
        changeset_containing_change = change_models.ChangeSet.objects.get(id=content['changeset'])
        self.assertEqual(1, changeset_containing_change.changes.count())
        self.assertEqual(firewall_models.RuleSet.__name__, changeset_containing_change.changes.first().entity)
        self.assertNotEqual(self.private_ruleset_main_user_wo_ref.pk, changeset_containing_change.changes.first().post.pk)
        self.assertEqual(OWNED_OBJECT_STATE_DELETED, changeset_containing_change.changes.first().post.state)
        self.assertEqual(self.private_ruleset_main_user_wo_ref.pk, changeset_containing_change.changes.first().pre.pk)

        # correct case: changed object
        changeset_w_unlinked_ruleset = change_models.ChangeSet.objects.create(owner=self.main_customer, owner_name=self.main_customer.name, user=self.main_user, user_name=self.main_user.name)
        unlinked_ruleset = firewall_models.RuleSet.objects.get(pk=self.private_ruleset_main_user)
        unlinked_ruleset.id = None
        unlinked_ruleset.pk = None
        unlinked_ruleset._state.adding = True
        unlinked_ruleset.state = OWNED_OBJECT_STATE_PREPARED
        unlinked_ruleset.save()
        unlinked_ruleset.firewalls.set([])
        change_unlinked_ruleset = change_models.Change.objects.create(changeset=changeset_w_unlinked_ruleset, entity=firewall_models.RuleSet.__name__, pre=self.private_ruleset_main_user, post=unlinked_ruleset, action=change_models.ACTION_DELETED)
        response = c.delete('/api/v1/rulesets/%s?changeset=%s' % (self.private_ruleset_main_user.uuid, changeset_w_unlinked_ruleset.id), HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(404, response.status_code)

        # wrong case: rulesets of other customer must not be deleted
        other_customers_public_ruleset_id = self.public_ruleset_other_user.uuid
        response = c.delete('/api/v1/rulesets/%s' % other_customers_public_ruleset_id, HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response.status_code)

        # wrong case: changeset may not be changed after application
        applied_changeset = change_models.ChangeSet.objects.create(owner=self.main_customer, owner_name=self.main_customer.name, user=self.main_user, user_name=self.main_user.name)
        applied_changeset.applied = datetime.now(timezone.utc)
        applied_changeset.save()
        response = c.delete('/api/v1/rulesets/%s?changeset=%s' % (self.private_ruleset_main_user.uuid, applied_changeset.id), HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(400, response.status_code)
        applied_changeset.refresh_from_db()
        self.assertEqual(0, applied_changeset.changes.count())
