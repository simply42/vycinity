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
from requests import Response
from vycinity.meta import change_management
from vycinity.models import OWNED_OBJECT_STATE_LIVE, customer_models, change_models
from django.contrib.auth.hashers import make_password
from base64 import b64encode
import json

from vycinity.models.firewall_models import ACTION_ACCEPT, Firewall

class ChangeAPITest(TestCase):
    '''
    This test class expects a successful GenericAPITest, as the tested functionality is used to
    modify some entities.
    '''

    @classmethod
    def setUpTestData(cls):
        cls.main_customer: customer_models.Customer = customer_models.Customer.objects.create(name = 'Test-Root customer')
        cls.main_user: customer_models.User = customer_models.User.objects.create(name='testuser', customer=cls.main_customer)
        cls.other_root_customer: customer_models.Customer = customer_models.Customer.objects.create(name='Other Root customer')
        cls.other_root_user: customer_models.User = customer_models.User.objects.create(name='otheruser', customer=cls.other_root_customer)
        cls.main_user_pw = 'testpw'
        customer_models.LocalUserAuth.objects.create(user=cls.main_user, auth=make_password(cls.main_user_pw))
        cls.authorization = 'Basic ' + b64encode((cls.main_user.name + ':' + cls.main_user_pw).encode('utf-8')).decode('ascii')
        cls.firewall1: Firewall = Firewall.objects.create(stateful=True, name="firewall1", default_action_into=ACTION_ACCEPT, default_action_from=ACTION_ACCEPT, owner=cls.main_customer, public=False, state=OWNED_OBJECT_STATE_LIVE)

    def testGetChangesetOwnInstance(self):
        c = Client()
        responsePrep: Response = c.put('/api/v1/firewalls/{}'.format(self.firewall1.uuid), json.dumps({'stateful': False, 'name': 'firewall1', 'default_action_into': ACTION_ACCEPT, 'default_action_from': ACTION_ACCEPT, 'owner': str(self.main_customer.id), 'public': False}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, responsePrep.status_code)
        resultPrep = responsePrep.json()
        response: Response = c.get('/api/v1/changesets/{}'.format(resultPrep['changeset']), HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        result = response.json()
        self.assertEqual(str(self.main_customer.id), result['owner'])
        self.assertEqual(str(self.main_user.id), result['user'])
        self.assertEqual(self.main_customer.name, result['owner_name'])
        self.assertEqual(self.main_user.name, result['user_name'])
        self.assertIsNotNone(result['created'])
        self.assertIsNotNone(result['modified'])
        self.assertIsNone(result['applied'])

    def testGetChangesetOtherInstance(self):
        c = Client()
        changeset: change_models.ChangeSet = change_models.ChangeSet.objects.create(owner=self.other_root_customer, owner_name=self.other_root_customer.name, user=self.other_root_user, user_name=self.other_root_user.name)
        response: Response = c.get('/api/v1/changesets/{}'.format(changeset.id), HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response.status_code)

    def testApplyChangeset(self):
        c = Client()
        responsePrep: Response = c.put('/api/v1/firewalls/{}'.format(self.firewall1.uuid), json.dumps({'stateful': False, 'name': 'firewall1', 'default_action_into': ACTION_ACCEPT, 'default_action_from': ACTION_ACCEPT, 'owner': str(self.main_customer.id), 'public': False}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, responsePrep.status_code)
        resultPrep = responsePrep.json()
        response: Response = c.put('/api/v1/changesets/{}'.format(resultPrep['changeset']), json.dumps({}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, response.status_code)
        result = response.json()
        self.assertEqual(str(self.main_customer.id), result['owner'])
        self.assertEqual(str(self.main_user.id), result['user'])
        self.assertEqual(self.main_customer.name, result['owner_name'])
        self.assertEqual(self.main_user.name, result['user_name'])
        self.assertIsNotNone(result['created'])
        self.assertIsNotNone(result['modified'])
        self.assertIsNotNone(result['applied'])

        response2: Response = c.put('/api/v1/changesets/{}'.format(resultPrep['changeset']), json.dumps({}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(400, response2.status_code)

    def testDeleteChangesetOK(self):
        c = Client()
        responsePrep: Response = c.put('/api/v1/firewalls/{}'.format(self.firewall1.uuid), json.dumps({'stateful': False, 'name': 'firewall1', 'default_action_into': ACTION_ACCEPT, 'default_action_from': ACTION_ACCEPT, 'owner': str(self.main_customer.id), 'public': False}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, responsePrep.status_code)
        resultPrep = responsePrep.json()
        response: Response = c.delete('/api/v1/changesets/{}'.format(resultPrep['changeset']), HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(204, response.status_code)

    def testDeleteChangesetApplied(self):
        c = Client()
        responsePrep: Response = c.put('/api/v1/firewalls/{}'.format(self.firewall1.uuid), json.dumps({'stateful': False, 'name': 'firewall1', 'default_action_into': ACTION_ACCEPT, 'default_action_from': ACTION_ACCEPT, 'owner': str(self.main_customer.id), 'public': False}), content_type='application/json', HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(200, responsePrep.status_code)
        resultPrep = responsePrep.json()
        changeset = change_models.ChangeSet.objects.get(pk=resultPrep['changeset'])
        change_management.apply_changeset(changeset)
        response: Response = c.delete('/api/v1/changesets/{}'.format(resultPrep['changeset']), HTTP_ACCEPT='application/json', HTTP_AUTHORIZATION=self.authorization)
        self.assertEqual(403, response.status_code)