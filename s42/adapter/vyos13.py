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
from vycinity.models import OWNED_OBJECT_STATE_LIVE, basic_models, network_models, firewall_models
from vycinity.models.firewall_models import DIRECTION_FROM, DIRECTION_INTO, BasicRule, CIDRAddressObject, CustomRule, HostAddressObject, ListAddressObject, ListServiceObject, NetworkAddressObject, RangeServiceObject, SimpleServiceObject
from ..routerconfig import vyos13 as configurator

import ipaddress
import logging
import re
from typing import Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)
DESCR_INVALID_RE = re.compile(r'[^A-Za-z0-9\-_.]')

def getDirection(src: List[Union[ipaddress.IPv4Address,ipaddress.IPv6Address,ipaddress.IPv4Network,ipaddress.IPv6Network]], dst: List[Union[ipaddress.IPv4Address,ipaddress.IPv6Address,ipaddress.IPv4Network,ipaddress.IPv6Network]], v4_network: Optional[ipaddress.IPv4Network], v6_network: Optional[ipaddress.IPv6Network]) -> Tuple[Optional[str], Optional[str]]:
    v4_direction = None
    v6_direction = None
    for addr in src:
        if not v4_network is None:
            if isinstance(addr, ipaddress.IPv4Address):
                if addr in v4_network:
                    v4_direction = firewall_models.DIRECTION_FROM
            elif isinstance(addr, ipaddress.IPv4Network):
                if addr.subnet_of(v4_network) or addr == v4_network:
                    v4_direction = firewall_models.DIRECTION_FROM
        if not v6_network is None:
            if isinstance(addr, ipaddress.IPv6Address):
                if addr in v6_network:
                    v6_direction = firewall_models.DIRECTION_FROM
            elif isinstance(addr, ipaddress.IPv6Network):
                if addr.subnet_of(v6_network) or addr == v6_network:
                    v6_direction = firewall_models.DIRECTION_FROM
    for addr in dst:
        if not v4_network is None:
            if isinstance(addr, ipaddress.IPv4Address):
                if addr in v4_network:
                    v4_direction = firewall_models.DIRECTION_INTO
            elif isinstance(addr, ipaddress.IPv4Network):
                if addr.subnet_of(v4_network) or addr == v4_network:
                    v4_direction = firewall_models.DIRECTION_INTO
        if not v6_network is None:
            if isinstance(addr, ipaddress.IPv6Address):
                if addr in v6_network:
                    v6_direction = firewall_models.DIRECTION_INTO
            elif isinstance(addr, ipaddress.IPv6Network):
                if addr.subnet_of(v6_network) or addr == v6_network:
                    v6_direction = firewall_models.DIRECTION_INTO
    return (v4_direction, v6_direction)

def resolveAddress(address: firewall_models.AddressObject, _accumulator:List[firewall_models.AddressObject]=[]) -> List[Union[ipaddress.IPv4Address,ipaddress.IPv6Address,ipaddress.IPv4Network,ipaddress.IPv6Network]]:
    rtn = []
    if not address in _accumulator and address.state == OWNED_OBJECT_STATE_LIVE:
        if isinstance(address, NetworkAddressObject):
            network = address.related_network
            if (network.ipv4_network_address and network.ipv4_network_bits):
                rtn.append(ipaddress.IPv4Network((network.ipv4_network_address, network.ipv4_network_bits), strict=False))
            if (network.ipv6_network_address and network.ipv6_network_bits):
                rtn.append(ipaddress.IPv6Network((network.ipv6_network_address, network.ipv6_network_bits), strict=False))
        elif isinstance(address, ListAddressObject):
            for list_object in address.elements.filter(state=OWNED_OBJECT_STATE_LIVE):
                resolved = resolveAddress(list_object, _accumulator + [address])
                if resolved is None:
                    return None
                rtn += resolved
        elif isinstance(address, HostAddressObject):
            if not address.ipv4_address is None:
                rtn.append(ipaddress.IPv4Address(address.ipv4_address))
            if not address.ipv6_address is None:
                rtn.append(ipaddress.IPv6Address(address.ipv6_address))
        elif isinstance(address, CIDRAddressObject):
            if not address.ipv4_network_address is None and not address.ipv4_network_bits is None:
                rtn.append(ipaddress.IPv4Network((address.ipv4_network_address, address.ipv4_network_bits), strict=False))
            if not address.ipv6_network_address is None and not address.ipv6_network_bits is None:
                rtn.append(ipaddress.IPv6Network((address.ipv6_network_address, address.ipv6_network_bits), strict=False))
        else:
            return None
    return rtn

def resolveService(service: firewall_models.ServiceObject, _accumulator:List[firewall_models.ServiceObject]=[]) -> Optional[Tuple[List[str],str]]:
    rtn_ports = []
    rtn_proto = None
    if service in _accumulator or service.state != OWNED_OBJECT_STATE_LIVE:
        return []
    if isinstance(service, ListServiceObject):
        for element in service.elements.filter(state=OWNED_OBJECT_STATE_LIVE):
            (resolved_ports, resolved_proto) = resolveService(element, _accumulator + [service])
            if resolved_ports is None:
                return None
            if not rtn_proto is None and rtn_proto != resolved_proto:
                return None
            rtn_ports += resolved_ports
            rtn_proto = resolved_proto
    elif isinstance(service, SimpleServiceObject):
        rtn_ports = [service.port]
        rtn_proto = service.protocol
    elif isinstance(service, RangeServiceObject):
        if service.start_port >= service.end_port:
            rtn_ports = ['%d-%d' % (service.start_port, service.end_port)]
            rtn_proto = service.protocol
    if rtn_proto is None:
        return None
    return (rtn_ports, rtn_proto)

def classifyVersionedAddressesAsString(address_list: List[Union[ipaddress.IPv4Address,ipaddress.IPv6Address,ipaddress.IPv4Network,ipaddress.IPv6Network]]) -> Tuple[List[str],List[str]]:
    rtn_v4 = []
    rtn_v6 = []
    for obj in address_list:
        if isinstance(obj, ipaddress.IPv4Address) or isinstance(obj, ipaddress.IPv4Network):
            rtn_v4.append(str(obj))
        elif isinstance(obj, ipaddress.IPv6Address) or isinstance(obj, ipaddress.IPv6Network):
            rtn_v6.append(str(obj))
    return (rtn_v4, rtn_v6)

def generateFirewallConfig(router: basic_models.Router) -> Tuple[configurator.Vyos13RouterConfig, Dict[int, str], Dict[int, str]]:
    networks = []
    for managed_interface in network_models.ManagedInterface.objects.filter(router=router):
        networks.append(managed_interface.network)
    networks_to_firewall_into = {}
    networks_to_firewall_from = {}
    fw_cfg = configurator.Vyos13RouterConfig(['firewall'], {})
    for firewall in firewall_models.Firewall.objects.filter(related_network__in=networks, state=OWNED_OBJECT_STATE_LIVE):
        suffix = '%s_%s' % (firewall.id, DESCR_INVALID_RE.sub('_', firewall.name))
        current_firewall_into_name = 'autogen_into_'+suffix
        current_firewall_from_name = 'autogen_from_'+suffix
        if len(current_firewall_into_name) > 28:
            current_firewall_into_name = current_firewall_into_name[:27]
            current_firewall_from_name = current_firewall_from_name[:27]
        current_fw_raw_cfg = {
            DIRECTION_INTO: {
                4: { 'default-action': firewall.default_action_into, 'rule': {}}, 
                6: { 'default-action': firewall.default_action_into, 'rule': {}}
            }, 
            DIRECTION_FROM: {
                4: { 'default-action': firewall.default_action_from, 'rule': {}}, 
                6: { 'default-action': firewall.default_action_from, 'rule': {}}
            }
        }

        if firewall.stateful:
            stateful_rule = {'9999': {'action': firewall_models.ACTION_ACCEPT, 'state': {'established': 'enable', 'related': 'enable'}}}
            current_fw_raw_cfg[DIRECTION_INTO][4]['rule'] = copy.deepcopy(stateful_rule)
            current_fw_raw_cfg[DIRECTION_INTO][6]['rule'] = copy.deepcopy(stateful_rule)
            current_fw_raw_cfg[DIRECTION_FROM][4]['rule'] = copy.deepcopy(stateful_rule)
            current_fw_raw_cfg[DIRECTION_FROM][6]['rule'] = copy.deepcopy(stateful_rule)
        
        rule_counter = {
            DIRECTION_INTO: { 4:0, 6:0 },
            DIRECTION_FROM: { 4:0, 6:0 }
        }

        v4_network_address = None
        v6_network_address = None
        if not firewall.related_network.ipv4_network_address is None and not firewall.related_network.ipv4_network_bits is None:
            v4_network_address = ipaddress.IPv4Network((firewall.related_network.ipv4_network_address, firewall.related_network.ipv4_network_bits), strict=False)
        if not firewall.related_network.ipv6_network_address is None and not firewall.related_network.ipv6_network_bits is None:
            v6_network_address = ipaddress.IPv6Network((firewall.related_network.ipv6_network_address, firewall.related_network.ipv6_network_bits), strict=False)
        if v4_network_address is None and v6_network_address is None:
            logger.warning('Network of firewall %s has neither IPv4 nor IPv6 address. Ignoring firewall.', firewall.id)
            continue

        for ruleset in firewall_models.RuleSet.objects.filter(firewalls__in=[firewall.id], state=OWNED_OBJECT_STATE_LIVE).order_by('priority'):
            for rule in firewall_models.Rule.objects.filter(related_ruleset=ruleset, state=OWNED_OBJECT_STATE_LIVE).order_by('priority'):
                if rule.disable:
                    continue
                if isinstance(rule, BasicRule):
                    source_addresses = []
                    if rule.source_address:
                        source_addresses = resolveAddress(rule.source_address)
                    destination_addresses = []
                    if rule.destination_address:
                        destination_addresses = resolveAddress(rule.destination_address)
                    if source_addresses is None or destination_addresses is None:
                        logger.warning('Source or destination address of basic rule %s could not be resolved. Ignoring rule.', rule.id)
                        continue
                    (v4_direction, v6_direction) = getDirection(source_addresses, destination_addresses, v4_network_address, v6_network_address)
                    if v4_direction is None and v6_direction is None:
                        logger.warning('basic rule %s has no clear direction. Ignoring rule.', rule.id)
                        continue
                    
                    (v4_sources, v6_sources) = classifyVersionedAddressesAsString(source_addresses)
                    (v4_destinations, v6_destinations) = classifyVersionedAddressesAsString(destination_addresses)
                    if rule.destination_service:
                        resolvedService = resolveService(rule.destination_service)
                        if resolvedService is None:
                            logger.warning('Service %s in basic rule %s could not be resolved. Ignoring rule.', rule.destination_service.id, rule.id)
                            continue
                        (ports, proto) = resolvedService
                    else:
                        ports = None
                        proto = None
                    if not v4_direction is None:
                        gen_raw_rules = []
                        for src in v4_sources:
                            for dst in v4_destinations:
                                raw_rule = {'source':{'address':src}, 'destination':{'address':dst}, 'action':rule.action}
                                if not proto is None:
                                    raw_rule['destination']['port'] = ','.join(ports)
                                    raw_rule['protocol'] = proto
                                gen_raw_rules.append(raw_rule)
                        for raw_rule in gen_raw_rules:
                            rule_counter[v4_direction][4] += 10
                            current_fw_raw_cfg[v4_direction][4]['rule'][str(rule_counter[v4_direction][4])] = raw_rule
                    if not v6_direction is None:
                        gen_raw_rules = []
                        for src in v6_sources:
                            for dst in v6_destinations:
                                raw_rule = {'source':{'address':src}, 'destination':{'address':dst}, 'action':rule.action}
                                if not proto is None:
                                    raw_rule['destination']['port'] = ','.join(ports)
                                    raw_rule['protocol'] = proto
                                gen_raw_rules.append(raw_rule)
                        for raw_rule in gen_raw_rules:
                            rule_counter[v6_direction][6] += 10
                            current_fw_raw_cfg[v6_direction][6]['rule'][str(rule_counter[v6_direction][6])] = raw_rule
                elif isinstance(rule, CustomRule):
                    if (rule.ip_version in [firewall_models.IP_VERSION_4, firewall_models.IP_VERSION_6] and 
                            rule.direction in [DIRECTION_INTO, DIRECTION_FROM]):
                        rule_counter[rule.direction][rule.ip_version] += 10
                        current_fw_raw_cfg[rule.direction][rule.ip_version]['rule'][str(rule_counter[rule.direction][rule.ip_version])] = rule.rule_definition
                    else:
                        logger.warning('CustomRule %s has invalid ip version or direction. Ignoring rule.', rule.id)
                else:
                    logger.warning('Rule %s of unknown type. Ignoring rule.', rule.id)

        networks_to_firewall_into[firewall.related_network.id] = {}
        networks_to_firewall_from[firewall.related_network.id] = {}

        if v4_network_address:
            fw_cfg = fw_cfg.merge(configurator.Vyos13RouterConfig(['firewall', 'name', current_firewall_into_name], current_fw_raw_cfg[DIRECTION_INTO][4]), False)
            fw_cfg = fw_cfg.merge(configurator.Vyos13RouterConfig(['firewall', 'name', current_firewall_from_name], current_fw_raw_cfg[DIRECTION_FROM][4]), False)
            networks_to_firewall_into[firewall.related_network.id][4] = current_firewall_into_name
            networks_to_firewall_from[firewall.related_network.id][4] = current_firewall_from_name
        if v6_network_address:
            fw_cfg = fw_cfg.merge(configurator.Vyos13RouterConfig(['firewall', 'ipv6-name', current_firewall_into_name], current_fw_raw_cfg[DIRECTION_INTO][6]), False)
            fw_cfg = fw_cfg.merge(configurator.Vyos13RouterConfig(['firewall', 'ipv6-name', current_firewall_from_name], current_fw_raw_cfg[DIRECTION_FROM][6]), False)
            networks_to_firewall_into[firewall.related_network.id][6] = current_firewall_into_name
            networks_to_firewall_from[firewall.related_network.id][6] = current_firewall_from_name

    return (fw_cfg, networks_to_firewall_into, networks_to_firewall_from)

def generateConfig(router: basic_models.Router) -> configurator.Vyos13RouterConfig:
    planned_config = configurator.Vyos13RouterConfig([], {})
    absolute_config_sections = []
    for config_section in router.vyos13router.active_static_configs.all():
        if not config_section.absolute:
            planned_config = planned_config.merge(
                configurator.Vyos13RouterConfig(config_section.context, config_section.content),
                False)
        else:
            absolute_config_sections.append(config_section)

    (firewall_config, networks_to_firewall_into, networks_to_firewall_from) = generateFirewallConfig(router)
    if firewall_config.config:
        planned_config = planned_config.merge(firewall_config, False)

    if len(router.managed_interface_context) > 0:
        for managed_interface in network_models.ManagedInterface.objects.filter(router=router, network__state=OWNED_OBJECT_STATE_LIVE):
            network = managed_interface.network
            addresses = []
            ipv4_net = None
            if not managed_interface.ipv4_address is None:
                ipv4_net = ipaddress.IPv4Network(network.ipv4_network_address + '/' + str(network.ipv4_network_bits))
                ipv4_addr = ipaddress.IPv4Address(managed_interface.ipv4_address)
                if ipv4_addr in ipv4_net:
                    addresses.append(ipv4_addr.compressed + '/' + str(ipv4_net.prefixlen))
                else:
                    ipv4_net = None
            ipv6_net = None
            if not managed_interface.ipv6_address is None:
                ipv6_net = ipaddress.IPv6Network(network.ipv6_network_address + '/' + str(network.ipv6_network_bits))
                ipv6_addr = ipaddress.IPv6Address(managed_interface.ipv6_address)
                if ipv6_addr in ipv6_net:
                    addresses.append(ipv6_addr.compressed + '/' + str(ipv6_net.prefixlen))
                else:
                    ipv6_net = None
            
            subif_raw_config = {}
            if network.name is None:
                subif_raw_config['description'] = 'autogen_id' + str(network.id)
            else:
                subif_raw_config['description'] = 'autogen_id' + str(network.id) + '_' + DESCR_INVALID_RE.sub('_', network.name)

            vrrp_config = None
            try:
                if managed_interface.managedvrrpinterface:
                    vrrp_interface = managed_interface.managedvrrpinterface
                    vrrp_config = {}

                    if not vrrp_interface.ipv4_service_address is None:
                        v4_addr = ipaddress.IPv4Address(vrrp_interface.ipv4_service_address)
                        if not ipv4_net is None and v4_addr in ipv4_net:
                            vrrp_config[subif_raw_config['description'] + '_v4'] = {
                                'interface': '%s.%d' % (router.managed_interface_context[-1], network.layer2_network_id),
                                'vrid': '%d' % vrrp_interface.vrid,
                                'virtual-address': [v4_addr.compressed + '/' + str(network.ipv4_network_bits)],
                                'priority': '%d' % vrrp_interface.priority
                            }
                            if not network.vrrp_password is None:
                                vrrp_config[subif_raw_config['description'] + '_v4']['authentication'] = {
                                    'type': 'plaintext-password',
                                    'password': network.vrrp_password
                                }
                    if not vrrp_interface.ipv6_service_address is None:
                        v6_addr = ipaddress.IPv6Address(vrrp_interface.ipv6_service_address)
                        if not ipv6_net is None and v6_addr in ipv6_net:
                            vrrp_config[subif_raw_config['description'] + '_v6'] = {
                                'interface': '%s.%d' % (router.managed_interface_context[-1], network.layer2_network_id),
                                'vrid': '%d' % vrrp_interface.vrid,
                                'virtual-address': [v6_addr.compressed + '/' + str(network.ipv6_network_bits)],
                                'priority': '%d' % vrrp_interface.priority
                            }
                            if not network.vrrp_password is None:
                                vrrp_config[subif_raw_config['description'] + '_v6']['authentication'] = {
                                    'type': 'plaintext-password',
                                    'password': network.vrrp_password
                                }
            except network_models.ManagedVRRPInterface.DoesNotExist:
                # Kein Fehler, nur kein spezielles Interface
                pass
            if len(addresses) > 0:
                subif_raw_config['address'] = addresses

            if not vrrp_config is None and len(vrrp_config) > 0:
                vrrp_config = configurator.Vyos13RouterConfig(['high-availability', 'vrrp', 'group'], vrrp_config)
                planned_config = planned_config.merge(vrrp_config, False)

            if network.id in networks_to_firewall_into:
                if 4 in networks_to_firewall_into[network.id]:
                    subif_raw_config['firewall'] = {'out': {'name':networks_to_firewall_into[network.id][4]}}
                if 4 in networks_to_firewall_from[network.id]:
                    if not 'firewall' in subif_raw_config:
                        subif_raw_config['firewall'] = {}
                    subif_raw_config['firewall']['in'] = {'name':networks_to_firewall_from[network.id][4]}
                if 6 in networks_to_firewall_into[network.id]:
                    if not 'firewall' in subif_raw_config:
                        subif_raw_config['firewall'] = {'out':{}}
                    if not 'out' in subif_raw_config['firewall']:
                        subif_raw_config['firewall']['out'] = {}
                    subif_raw_config['firewall']['out']['ipv6-name'] = networks_to_firewall_into[network.id][6]
                if 6 in networks_to_firewall_from[network.id]:
                    if not 'firewall' in subif_raw_config:
                        subif_raw_config['firewall'] = {'in':{}}
                    if not 'in' in subif_raw_config['firewall']:
                        subif_raw_config['firewall']['in'] = {}
                    subif_raw_config['firewall']['in']['ipv6-name'] = networks_to_firewall_from[network.id][6]

            subif_config = configurator.Vyos13RouterConfig(router.managed_interface_context + ['vif', str(network.layer2_network_id)], subif_raw_config)
            planned_config = planned_config.merge(subif_config, False)


    for config_section in absolute_config_sections:
        planned_config = planned_config.merge(
            configurator.Vyos13RouterConfig(config_section.context, config_section.content),
            True)
    logger.debug('Configuration for id=%s will be %s', router.id, str(planned_config.config))
    return planned_config