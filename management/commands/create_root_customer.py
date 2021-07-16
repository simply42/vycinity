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

from django.core.management.base import BaseCommand, CommandError, CommandParser
from vycinity.models.customer_models import Customer
from typing import Any, Optional

class Command(BaseCommand):
    help = 'Creates a root customer'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--name', dest='customername', required=True, help='Customer name')

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        customer = Customer(name = options['customername'])
        customer.save()
        self.stdout.write('New customer id: %s' % customer.id)