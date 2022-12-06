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

'''
Tasks for VyCinity
'''

import datetime
import ipaddress
import logging
import subprocess
import traceback
from time import sleep
from uuid import UUID
from celery import shared_task

from vycinity.models import basic_models
from .s42.routerconfig import vyos13 as configurator

logger = logging.getLogger(__name__)

GRACE_PERIOD = 60
'''
Grace period for deploying a router. If a router is still alive after this time, consider as sane.
'''

def check_router_alive(ip_address: str) -> bool:
    '''
    Checks whether the ip is alive. Returns boolean result.

    Parameters:
        ip_address {str} -- The ip address to check.

    Returns:
        bool -- Whether the ip is reachable
    '''
    address = ipaddress.ip_address(ip_address)
    check_command = 'ping'
    if isinstance(address, ipaddress.IPv6Address):
        check_command = 'ping6'
    params = [check_command, '-c1', str(ip_address)]
    try:
        logger.debug('Checking Communication to %s', str(address))
        subprocess.run(params, timeout=10, check=True, stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL)
        return True
    except:
        return False

@shared_task
def deploy(deployment_id: int):
    '''
    Deploy a set of routers using a defined deployment. Quickly fail if the deployment fails.
    Write the result back to the deployment.

    Arguments:
        deployment_id {int}: The id of the deployment in the database.
    '''
    logger.debug('Starting deployment %d', deployment_id)
    deployment = basic_models.Deployment.objects.get(id=deployment_id)
    deployment.state = basic_models.DEPLOYMENT_STATE_RUNNING
    deployment.save()

    previous_configs = {}
    configured_routers = {}
    database_routers = {}
    logger.debug('Retrieving old config from routers')
    try:
        for config in deployment.configs.all():
            router = config.router
            rid = router.id
            database_routers[rid] = router
            try:
                if router.vyos13router:
                    configured_router = configurator.Vyos13Router(
                        'https://%s:443' % router.vyos13router.loopback,
                        router.vyos13router.token,
                        False)
                    configured_routers[rid] = configured_router
                    previous_configs[rid] = configured_router.getConfig()
            except basic_models.Vyos13Router.DoesNotExist as dne_exc:
                raise Exception('Unknown type of router (pk=%d).' % router.pk) from dne_exc
    except Exception:
        logger.warning('Failed to retrieve configuration, not deploying (pk=%d).', deployment.pk,
            exc_info=True)
        deployment.state = basic_models.DEPLOYMENT_STATE_FAILED
        deployment.errors = 'Failed to retrieve configuration.'
        deployment.save()
        return

    planned_configs = {}
    for config in deployment.configs.all():
        planned_configs[config.router.id] = configurator.Vyos13RouterConfig(context=[],
            plain_config=config.vyos13routerconfig.config)
        logger.debug('Configuration for id=%d will be %s', config.router.id,
            planned_configs[config.router.id].config)

    changed_routers = []
    try:
        for (rid, config) in planned_configs.items():
            changed_routers.append(rid)
            logging.info('Deploying router "%s" (id=%d)', database_routers[rid].name, rid)
            configured_routers[rid].putConfig(config)
            sleep(GRACE_PERIOD)
            if not check_router_alive(database_routers[rid].loopback):
                raise configurator.RouterCommunicationError('Ping after deployment failed')
    except (configurator.RouterCommunicationError, configurator.RouterConfigError):
        logger.error('Deployment failed. Trying to roll back to old config.', exc_info=True)
        for rid in changed_routers:
            logging.info('Rolling back to old config on id=%d', rid)
            try:
                configured_routers[rid].putConfig(previous_configs[rid])
            except (configurator.RouterCommunicationError, configurator.RouterConfigError):
                logger.critical('Rollback failed on id=%d. This is a disaster!', rid)
        deployment.state = basic_models.DEPLOYMENT_STATE_FAILED
        deployment.errors = ("Failed while deployment to router. Stacktrace:\n" +
            traceback.format_exc())
        deployment.save()
        return

    deployment.state = basic_models.DEPLOYMENT_STATE_SUCCEED
    deployment.save()

@shared_task
def retrieve_vyos13_live_router_config(lrc: UUID):
    live_router_config = None
    router = None
    try:
        live_router_config = basic_models.Vyos13LiveRouterConfig.objects.get(pk=lrc)
        router = live_router_config.router
    except (basic_models.Vyos13LiveRouterConfig.DoesNotExist|basic_models.Vyos13Router.DoesNotExist|basic_models.Router.DoesNotExist) as e:
        logger.error('Router config cannot be retrieved because a resource was not found in the database', exc_info=e)
        return
    
    try:
        configured_router = configurator.Vyos13Router(
            'https://%s:443' % router.loopback,
            router.token,
            False)
        currentRouterConfig = configured_router.getConfig()
        live_router_config.config = currentRouterConfig.config
        live_router_config.retrieved = datetime.datetime.now(tz=datetime.timezone.utc)
        live_router_config.save()
    except Exception as e:
        logger.error('Failed to retrieve configuration from router %s', router.id, exc_info=e)
        live_router_config.delete()
