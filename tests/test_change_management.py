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
import vycinity.views
from vycinity.models import customer_models, firewall_models, change_models, network_models
from vycinity.serializers import firewall_serializers
import vycinity.meta.change_management
from django.contrib.auth.hashers import make_password
from base64 import b64encode
import json

class ChangeManagementTest(TestCase):
    '''
    Tests the API for a generic owned object. Here a Ruleset is tested, as the logic of other owned
    object is the same, testing of them can be reduced or skipped. The Rulesets are tested here
    because they are quite complex as they have references to other owned objects.
    '''

    @classmethod
    def setUpTestData(cls):
        cls.main_customer = customer_models.Customer.objects.create(name = 'Test-Root customer')
        cls.main_user = customer_models.User.objects.create(name='testuser', customer=cls.main_customer)
        cls.firewall_main_user = firewall_models.Firewall.objects.create(name='main firewall', stateful=False, default_action_into=firewall_models.ACTION_ACCEPT, default_action_from=firewall_models.ACTION_ACCEPT, owner=cls.main_customer, public=False)
        cls.private_ruleset_main_user = firewall_models.RuleSet.objects.create(comment='main private ruleset', priority=10, owner=cls.main_customer, public=False)
        cls.private_ruleset_main_user.firewalls.set([cls.firewall_main_user])
        cls.changeset_ruleset_main_user = change_models.ChangeSet.objects.create(owner=cls.main_customer, user=cls.main_user, owner_name=cls.main_customer.name, user_name=cls.main_user.name)
        serialized_ruleset_main_user = firewall_serializers.RuleSetSerializer(cls.private_ruleset_main_user).data
        serialized_ruleset_main_user_modified = copy.deepcopy(serialized_ruleset_main_user)
        serialized_ruleset_main_user_modified['comment'] = 'main private ruleset modified'
        cls.change_ruleset_main_user_name = change_models.Change.objects.create(changeset=cls.changeset_ruleset_main_user, entity='RuleSet', pre=serialized_ruleset_main_user, post=serialized_ruleset_main_user_modified)

   
    def test_apply_changeset(self):
        vycinity.meta.change_management.apply_changeset(self.changeset_ruleset_main_user)
        changed_ruleset = firewall_models.RuleSet.objects.get(id=uuid.UUID(self.change_ruleset_main_user_name.pre['id']))
        self.assertEquals(self.private_ruleset_main_user.owner, changed_ruleset.owner)
        self.assertEquals(self.private_ruleset_main_user.public, changed_ruleset.public)
        self.assertEquals(self.private_ruleset_main_user.priority, changed_ruleset.priority)
        self.assertEquals('main private ruleset modified', changed_ruleset.comment)

        new_ruleset_w_rule = change_models.ChangeSet(owner=self.main_customer, owner_name=self.main_customer.name, user=self.main_user, user_name=self.main_user.name)
        new_ruleset_w_rule.save()
        new_changeset_ruleset = change_models.Change(changeset=new_ruleset_w_rule, entity=firewall_models.RuleSet.__name__, post={'owner': str(self.main_customer.id), 'public': False, 'priority': 20}, new_uuid=uuid.uuid4())
        new_changeset_ruleset.save()
        new_changeset_dest_address = change_models.Change(changeset=new_ruleset_w_rule, entity=firewall_models.HostAddressObject.__name__, post={'name': 'my address object', 'owner': str(self.main_customer.id), 'public': False, 'ipv4_address': '1.2.3.4'}, new_uuid=uuid.uuid4())
        new_changeset_dest_address.save()
        new_changeset_rule = change_models.Change(changeset=new_ruleset_w_rule, entity=firewall_models.BasicRule.__name__, post={'ruleset': str(new_changeset_ruleset.new_uuid), 'priority': 10, 'disable': False, 'owner': str(self.main_customer.id), 'public': False, 'destination_address': str(new_changeset_dest_address.new_uuid), 'action': 'accept', 'log': False}, new_uuid=uuid.uuid4())
        new_changeset_rule.save()
        new_changeset_rule.dependencies.add(new_changeset_ruleset)
        new_changeset_rule.dependencies.add(new_changeset_dest_address)
        new_changeset_dest_address_changed = change_models.Change(changeset=new_ruleset_w_rule, entity=firewall_models.HostAddressObject.__name__, pre=copy.deepcopy(new_changeset_dest_address.post), post=copy.deepcopy(new_changeset_dest_address.post))
        new_changeset_dest_address_changed.pre['id'] = str(new_changeset_dest_address.new_uuid)
        new_changeset_dest_address_changed.post['id'] = str(new_changeset_dest_address.new_uuid)
        new_changeset_dest_address_changed.post['ipv4_address'] = '5.6.7.8'
        new_changeset_dest_address_changed.save()
        new_changeset_dest_address_changed.dependencies.add(new_changeset_dest_address)
        vycinity.meta.change_management.apply_changeset(new_ruleset_w_rule)
        new_rule = firewall_models.Rule.objects.get(id=new_changeset_rule.new_uuid)
        resulting_address_object = new_rule.basicrule.destination_address.hostaddressobject
        self.assertEquals(new_changeset_dest_address_changed.post['ipv4_address'], resulting_address_object.ipv4_address)
        self.assertEquals(new_changeset_ruleset.new_uuid, new_rule.ruleset.id)
