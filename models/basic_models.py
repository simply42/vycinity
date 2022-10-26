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
from django.db import models
from polymorphic.models import PolymorphicModel

class StaticConfigSection(PolymorphicModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    context = models.JSONField()
    description = models.TextField(null=True)
    absolute = models.BooleanField()

class Vyos13StaticConfigSection(StaticConfigSection):
    content = models.JSONField()

class Router(PolymorphicModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=64, unique=True, blank=False)
    loopback = models.GenericIPAddressField(unique=True, unpack_ipv4=True, blank=False)
    deploy = models.BooleanField(default=False)
    managed_interface_context = models.JSONField()

class Vyos13Router(Router):
    token = models.CharField(max_length=256, blank=False)
    fingerprint = models.CharField(max_length=256, blank=False)
    active_static_configs = models.ManyToManyField(Vyos13StaticConfigSection, blank=True)

class LiveRouterConfig(PolymorphicModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    retrieved = models.DateTimeField(null=True)
    router = models.ForeignKey(Router, on_delete=models.CASCADE, null=False)

class Vyos13LiveRouterConfig(LiveRouterConfig):
    config = models.JSONField(null=True)

class RouterConfig(PolymorphicModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    router = models.ForeignKey(Router, on_delete=models.CASCADE, null=False)

class Vyos13RouterConfig(RouterConfig):
    config = models.JSONField()

DEPLOYMENT_STATE_PREPARATION = 'preparation'
DEPLOYMENT_STATE_READY = 'ready'
DEPLOYMENT_STATE_RUNNING = 'running'
DEPLOYMENT_STATE_FAILED = 'failed'
DEPLOYMENT_STATE_SUCCEED = 'succeed'
DEPLOYMENT_STATES = [
    (DEPLOYMENT_STATE_PREPARATION, 'preparation'),
    (DEPLOYMENT_STATE_READY, 'ready to run'),
    (DEPLOYMENT_STATE_RUNNING, 'running'),
    (DEPLOYMENT_STATE_FAILED, 'failed'),
    (DEPLOYMENT_STATE_SUCCEED, 'succeed')
]

class Deployment(PolymorphicModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    triggered = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)
    configs = models.ManyToManyField(RouterConfig)
    change = models.JSONField()
    state = models.CharField(max_length=32, choices=DEPLOYMENT_STATES)
    errors = models.TextField(null=True)
