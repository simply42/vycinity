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
import vycinity.views
from vycinity.models import OWNED_OBJECT_STATE_LIVE, OWNED_OBJECT_STATE_OUTDATED, OWNED_OBJECT_STATE_PREPARED, basic_models, customer_models, firewall_models, change_models, network_models
import vycinity.meta.change_management
import vycinity.meta.registries

class ChangeManagementBasicTest(TestCase):
    '''
    Tests the API for a generic owned object. Here a Ruleset is tested, as the logic of other owned
    object is the same, testing of them can be reduced or skipped. The Rulesets are tested here
    because they are quite complex as they have references to other owned objects.
    '''

    @classmethod
    def setUpTestData(cls):
        cls.main_customer = customer_models.Customer.objects.create(name = 'Test-Root customer')
        cls.main_user = customer_models.User.objects.create(name='testuser', customer=cls.main_customer)
        cls.firewall_main_user = firewall_models.Firewall.objects.create(name='main firewall', stateful=False, default_action_into=firewall_models.ACTION_ACCEPT, default_action_from=firewall_models.ACTION_ACCEPT, owner=cls.main_customer, public=False, state=OWNED_OBJECT_STATE_LIVE)
        cls.private_ruleset_main_user = firewall_models.RuleSet.objects.create(comment='main private ruleset', priority=10, owner=cls.main_customer, public=False, state=OWNED_OBJECT_STATE_LIVE)
        cls.private_ruleset_main_user.firewalls.set([cls.firewall_main_user])
        cls.changeset_ruleset_main_user = change_models.ChangeSet.objects.create(owner=cls.main_customer, user=cls.main_user, owner_name=cls.main_customer.name, user_name=cls.main_user.name)
        cls.ruleset_main_user_modified = firewall_models.RuleSet.objects.get(pk=cls.private_ruleset_main_user.pk)
        cls.ruleset_main_user_modified.id = None
        cls.ruleset_main_user_modified.pk = None
        cls.ruleset_main_user_modified._state.adding = True
        cls.ruleset_main_user_modified.state = OWNED_OBJECT_STATE_PREPARED
        cls.ruleset_main_user_modified.comment = 'main private ruleset modified'
        cls.ruleset_main_user_modified.save()
        cls.ruleset_main_user_modified.firewalls.set([cls.firewall_main_user])
        cls.change_ruleset_main_user_name = change_models.Change.objects.create(changeset=cls.changeset_ruleset_main_user, entity='RuleSet', pre=cls.private_ruleset_main_user, post=cls.ruleset_main_user_modified, action=change_models.ACTION_MODIFIED)

   
    def test_apply_changeset(self):
        # Positive test with simple changeset
        vycinity.meta.change_management.apply_changeset(self.changeset_ruleset_main_user)
        changed_ruleset = firewall_models.RuleSet.objects.get(uuid=self.change_ruleset_main_user_name.pre.uuid, state=OWNED_OBJECT_STATE_LIVE)
        self.assertEqual(self.ruleset_main_user_modified.pk, changed_ruleset.pk)
        self.private_ruleset_main_user.refresh_from_db()
        self.assertEqual(OWNED_OBJECT_STATE_OUTDATED, self.private_ruleset_main_user.state)
        self.ruleset_main_user_modified.refresh_from_db()
        self.assertEqual(OWNED_OBJECT_STATE_LIVE, self.ruleset_main_user_modified.state)
        self.changeset_ruleset_main_user.refresh_from_db()
        self.assertIsNotNone(self.changeset_ruleset_main_user.applied)

        # Positive with dependencies
        new_ruleset_w_rule = change_models.ChangeSet.objects.create(owner=self.main_customer, owner_name=self.main_customer.name, user=self.main_user, user_name=self.main_user.name)
        new_ruleset = firewall_models.RuleSet.objects.create(owner=self.main_customer, public=False, priority=20, state=OWNED_OBJECT_STATE_PREPARED)
        new_change_ruleset = change_models.Change.objects.create(changeset=new_ruleset_w_rule, entity=firewall_models.RuleSet.__name__, post=new_ruleset, action=change_models.ACTION_CREATED)
        new_dest_address = firewall_models.HostAddressObject.objects.create(name='my address object', owner=self.main_customer, public=False, ipv4_address='1.2.3.4', state=OWNED_OBJECT_STATE_PREPARED)
        new_change_dest_address = change_models.Change.objects.create(changeset=new_ruleset_w_rule, entity=firewall_models.HostAddressObject.__name__, post=new_dest_address, action=change_models.ACTION_CREATED)
        new_basic_rule = firewall_models.BasicRule.objects.create(related_ruleset=new_ruleset, priority=10, disable=False, destination_address=new_dest_address, action=firewall_models.ACTION_ACCEPT, log=False, state=OWNED_OBJECT_STATE_PREPARED)
        new_change_rule = change_models.Change.objects.create(changeset=new_ruleset_w_rule, entity=firewall_models.BasicRule.__name__, post=new_basic_rule, action=change_models.ACTION_CREATED)
        new_change_rule.dependencies.add(new_change_ruleset)
        new_change_rule.dependencies.add(new_change_dest_address)
        vycinity.meta.change_management.apply_changeset(new_ruleset_w_rule)
        new_ruleset.refresh_from_db()
        new_dest_address.refresh_from_db()
        new_basic_rule.refresh_from_db()
        self.assertEqual(OWNED_OBJECT_STATE_LIVE, new_ruleset.state)
        self.assertEqual(OWNED_OBJECT_STATE_LIVE, new_dest_address.state)
        self.assertEqual(OWNED_OBJECT_STATE_LIVE, new_basic_rule.state)
        
        # Positive Test with hook call
        a_network_changeset = change_models.ChangeSet.objects.create(owner=self.main_customer, owner_name=self.main_customer.name, user=self.main_user, user_name=self.main_user.name)
        a_network = network_models.Network.objects.create(owner=self.main_customer, public=False, ipv4_network_address='1.2.3.0', ipv4_network_bits=24, name='a network', layer2_network_id=27, state=OWNED_OBJECT_STATE_LIVE)
        a_network_changed = network_models.Network.objects.create(owner=self.main_customer, public=False, ipv4_network_address='4.5.6.0', ipv4_network_bits=24, name='a network', layer2_network_id=27, state=OWNED_OBJECT_STATE_PREPARED)
        change_models.Change.objects.create(changeset=a_network_changeset, entity=network_models.Network.__name__, pre=a_network, post=a_network_changed, action=change_models.ACTION_MODIFIED)
        test_router = basic_models.Router.objects.create(name='a test router', loopback='3.4.5.6', managed_interface_context=[])
        test_interface = network_models.ManagedInterface.objects.create(router=test_router, ipv4_address='1.2.3.5', network=a_network)
        vycinity.meta.change_management.apply_changeset(a_network_changeset)
        test_interface.refresh_from_db()
        a_network.refresh_from_db()
        a_network_changed.refresh_from_db()
        self.assertEqual(a_network_changed.pk, test_interface.network.pk)
        self.assertEqual(OWNED_OBJECT_STATE_LIVE, a_network_changed.state)
        self.assertEqual(OWNED_OBJECT_STATE_OUTDATED, a_network.state)

        # Negative Test Collision on a change should raise an exception
        ruleset_main_user_modified2 = firewall_models.RuleSet.objects.get(pk=self.private_ruleset_main_user.pk)
        ruleset_main_user_modified2.id = None
        ruleset_main_user_modified2.pk = None
        ruleset_main_user_modified2._state.adding = True
        ruleset_main_user_modified2.state = OWNED_OBJECT_STATE_PREPARED
        ruleset_main_user_modified2.comment = 'main private ruleset modified another time'
        ruleset_main_user_modified2.save()
        ruleset_main_user_modified2.firewalls.set([self.firewall_main_user])
        changeset_ruleset_main_user_modified2 = change_models.ChangeSet.objects.create(owner=self.main_customer, owner_name=self.main_customer.name, user=self.main_user, user_name=self.main_user.name)
        change_models.Change.objects.create(changeset=changeset_ruleset_main_user_modified2, entity=firewall_models.RuleSet.__name__, pre=self.private_ruleset_main_user, post=ruleset_main_user_modified2, action=change_models.ACTION_MODIFIED)
        try:
            vycinity.meta.change_management.apply_changeset(changeset_ruleset_main_user_modified2)
            self.fail('application should fail because it\'s conflicting, but it did not.')
        except vycinity.meta.change_management.ChangeConflictError:
            ruleset_main_user_modified2.refresh_from_db()
            self.assertEqual(OWNED_OBJECT_STATE_PREPARED, ruleset_main_user_modified2.state)
            

class ChangeManagementConflictTest(TestCase):
    '''
    Tests if the application of a changeset detects a conflicting, already changed object properly.
    A separate test class is required as the changeset relies on transactions itself and thus
    destroys django's testing logic with transactions.
    '''

    @classmethod
    def setUpTestData(cls):
        cls.main_customer = customer_models.Customer.objects.create(name = 'Test-Root customer')
        cls.main_user = customer_models.User.objects.create(name='testuser', customer=cls.main_customer)
        cls.firewall_main_user = firewall_models.Firewall.objects.create(name='main firewall', stateful=False, default_action_into=firewall_models.ACTION_ACCEPT, default_action_from=firewall_models.ACTION_ACCEPT, owner=cls.main_customer, public=False, state=OWNED_OBJECT_STATE_LIVE)
        cls.private_ruleset_main_user = firewall_models.RuleSet.objects.create(comment='main private ruleset', priority=10, owner=cls.main_customer, public=False, state=OWNED_OBJECT_STATE_LIVE)
        cls.private_ruleset_main_user.firewalls.set([cls.firewall_main_user])
        cls.changeset_ruleset_main_user = change_models.ChangeSet.objects.create(owner=cls.main_customer, user=cls.main_user, owner_name=cls.main_customer.name, user_name=cls.main_user.name)
        cls.ruleset_main_user_modified = firewall_models.RuleSet.objects.get(pk=cls.private_ruleset_main_user.pk)
        cls.ruleset_main_user_modified.id = None
        cls.ruleset_main_user_modified.pk = None
        cls.ruleset_main_user_modified._state.adding = True
        cls.ruleset_main_user_modified.state = OWNED_OBJECT_STATE_PREPARED
        cls.ruleset_main_user_modified.comment = 'main private ruleset modified'
        cls.ruleset_main_user_modified.save()
        cls.ruleset_main_user_modified.firewalls.set([cls.firewall_main_user])
        cls.change_ruleset_main_user_name = change_models.Change.objects.create(changeset=cls.changeset_ruleset_main_user, entity='RuleSet', pre=cls.private_ruleset_main_user, post=cls.ruleset_main_user_modified, action=change_models.ACTION_MODIFIED)


    def test_apply_changeset_conflict(self):
        second_changeset = change_models.ChangeSet.objects.create(owner=self.main_customer, owner_name=self.main_customer.name, user=self.main_user, user_name=self.main_user.name)
        ruleset_main_user_conflict_modified = firewall_models.RuleSet.objects.get(pk=self.private_ruleset_main_user.pk)
        ruleset_main_user_conflict_modified.pk = None
        ruleset_main_user_conflict_modified.id = None
        ruleset_main_user_conflict_modified._state.adding = True
        ruleset_main_user_conflict_modified.state = OWNED_OBJECT_STATE_PREPARED
        ruleset_main_user_conflict_modified.comment = "Another comment"
        ruleset_main_user_conflict_modified.save()
        second_change = change_models.Change.objects.create(changeset=second_changeset, entity=firewall_models.RuleSet.__name__, pre=self.private_ruleset_main_user, post=ruleset_main_user_conflict_modified, action=change_models.ACTION_MODIFIED)
        vycinity.meta.change_management.apply_changeset(self.changeset_ruleset_main_user)
        with self.assertRaises(vycinity.meta.change_management.ChangeConflictError):
            vycinity.meta.change_management.apply_changeset(second_changeset)
        self.assertEqual(self.ruleset_main_user_modified.pk, firewall_models.RuleSet.objects.get(uuid=self.private_ruleset_main_user.uuid, state=OWNED_OBJECT_STATE_LIVE).pk)
        second_changeset.refresh_from_db()
        self.assertIsNone(second_changeset.applied)

class ChangeManagementDoubleApplicationTest(TestCase):
    '''
    Tests double application of the same changeset. A separate test class is required as the
    changeset relies on transactions itself an thus destroys django's testing logic with
    transactions.
    '''

    @classmethod
    def setUpTestData(cls):
        cls.main_customer = customer_models.Customer.objects.create(name = 'Test-Root customer')
        cls.main_user = customer_models.User.objects.create(name='testuser', customer=cls.main_customer)
        cls.firewall_main_user = firewall_models.Firewall.objects.create(name='main firewall', stateful=False, default_action_into=firewall_models.ACTION_ACCEPT, default_action_from=firewall_models.ACTION_ACCEPT, owner=cls.main_customer, public=False, state=OWNED_OBJECT_STATE_LIVE)
        cls.private_ruleset_main_user = firewall_models.RuleSet.objects.create(comment='main private ruleset', priority=10, owner=cls.main_customer, public=False, state=OWNED_OBJECT_STATE_LIVE)
        cls.private_ruleset_main_user.firewalls.set([cls.firewall_main_user])
        cls.changeset_ruleset_main_user = change_models.ChangeSet.objects.create(owner=cls.main_customer, user=cls.main_user, owner_name=cls.main_customer.name, user_name=cls.main_user.name)
        cls.ruleset_main_user_modified = firewall_models.RuleSet.objects.get(pk=cls.private_ruleset_main_user.pk)
        cls.ruleset_main_user_modified.id = None
        cls.ruleset_main_user_modified.pk = None
        cls.ruleset_main_user_modified._state.adding = True
        cls.ruleset_main_user_modified.state = OWNED_OBJECT_STATE_PREPARED
        cls.ruleset_main_user_modified.comment = 'main private ruleset modified'
        cls.ruleset_main_user_modified.save()
        cls.ruleset_main_user_modified.firewalls.set([cls.firewall_main_user])
        cls.change_ruleset_main_user_name = change_models.Change.objects.create(changeset=cls.changeset_ruleset_main_user, entity='RuleSet', pre=cls.private_ruleset_main_user, post=cls.ruleset_main_user_modified, action=change_models.ACTION_MODIFIED)

    def test_apply_changeset_double_application(self):
        vycinity.meta.change_management.apply_changeset(self.changeset_ruleset_main_user)
        self.changeset_ruleset_main_user.refresh_from_db()
        application_date = self.changeset_ruleset_main_user.applied
        with self.assertRaises(vycinity.meta.change_management.ChangeConflictError):
            vycinity.meta.change_management.apply_changeset(self.changeset_ruleset_main_user)
        self.changeset_ruleset_main_user.refresh_from_db()
        self.assertEquals(application_date, self.changeset_ruleset_main_user.applied)


class ChangeManagementSemanticsTest(TestCase):
    '''
    Tests, if application of changesets checks semantics again. Altough the semantics get checked
    when adding a change, it's more secure to check it again, when the thing is going live. A
    separate test class is required as the changeset relies on transactions itself and thus
    destroys django's testing logic with transactions.
    '''

    @classmethod
    def setUpTestData(cls):
        cls.main_customer = customer_models.Customer.objects.create(name = 'Test-Root customer')
        cls.our_customer = customer_models.Customer.objects.create(name = 'Our customer', parent_customer=cls.main_customer)
        cls.other_customer = customer_models.Customer.objects.create(name = 'Other customer', parent_customer=cls.main_customer)
        cls.main_user = customer_models.User.objects.create(name='testuser', customer=cls.our_customer)
        cls.firewall_main_user = firewall_models.Firewall.objects.create(name='main firewall', stateful=False, default_action_into=firewall_models.ACTION_ACCEPT, default_action_from=firewall_models.ACTION_ACCEPT, owner=cls.our_customer, public=False, state=OWNED_OBJECT_STATE_LIVE)
        cls.private_ruleset_main_user = firewall_models.RuleSet.objects.create(comment='main private ruleset', priority=10, owner=cls.our_customer, public=False, state=OWNED_OBJECT_STATE_LIVE)
        cls.private_ruleset_main_user.firewalls.set([cls.firewall_main_user])
        cls.changeset_ruleset_main_user = change_models.ChangeSet.objects.create(owner=cls.our_customer, user=cls.main_user, owner_name=cls.our_customer.name, user_name=cls.main_user.name)
        cls.ruleset_main_user_modified = firewall_models.RuleSet.objects.get(pk=cls.private_ruleset_main_user.pk)
        cls.ruleset_main_user_modified.id = None
        cls.ruleset_main_user_modified.pk = None
        cls.ruleset_main_user_modified._state.adding = True
        cls.ruleset_main_user_modified.state = OWNED_OBJECT_STATE_PREPARED
        cls.ruleset_main_user_modified.comment = 'main private ruleset modified'
        cls.ruleset_main_user_modified.owner = cls.other_customer
        cls.ruleset_main_user_modified.save()
        cls.ruleset_main_user_modified.firewalls.set([cls.firewall_main_user])
        cls.change_ruleset_main_user_name = change_models.Change.objects.create(changeset=cls.changeset_ruleset_main_user, entity='RuleSet', pre=cls.private_ruleset_main_user, post=cls.ruleset_main_user_modified, action=change_models.ACTION_MODIFIED)

    def test_apply_changeset_with_semantics_check(self):
        with self.assertRaises(vycinity.meta.change_management.ChangeConflictError):
            vycinity.meta.change_management.apply_changeset(self.changeset_ruleset_main_user)
        self.changeset_ruleset_main_user.refresh_from_db()
        self.assertIsNone(self.changeset_ruleset_main_user.applied)