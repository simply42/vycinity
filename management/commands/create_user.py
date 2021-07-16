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
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.contrib.auth.hashers import make_password
from vycinity.models.customer_models import Customer, User, LocalUserAuth
from typing import Any, Optional

class Command(BaseCommand):
    help = 'Creates a user together with a local authentication'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--name', dest='username', required=True, help='username')
        parser.add_argument('--pass', dest='password', required=True, help='password')
        parser.add_argument('--customer', dest='customer', type=uuid.UUID, required=True, help='customer id')

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        customer = None
        try:
            customer = Customer.objects.get(id = options['customer'])
        except Customer.DoesNotExist:
            raise CommandError('Customer does not exist')
        user = User(name=options['username'], customer=customer)
        user.save()
        localuserauth = LocalUserAuth(user=user, auth=make_password(options['password']))
        localuserauth.save()
        self.stdout.write('New user id: %s' % user.id)