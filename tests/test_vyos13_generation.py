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

import json
from django.test import TestCase
from vycinity.models import OWNED_OBJECT_STATE_LIVE, basic_models, customer_models, firewall_models, network_models
from vycinity.s42.adapter.vyos13 import generateConfig
from vycinity.s42.routerconfig.vyos13 import Vyos13RouterConfigDiff, Vyos13RouterConfig

class Vyos13GenerationSCSTest(TestCase):
    def test_generateConfigSingleSCS(self):
        router = basic_models.Vyos13Router(name="A", loopback='127.0.1.1', deploy=False, token='1234', fingerprint='5678', managed_interface_context=[])
        router.save()
        #TODO: description
        scs = basic_models.Vyos13StaticConfigSection(description='bla', absolute=False, context=[], content={'system':{'ntp':{'servers':{'1.1.1.1':{}, '2.2.2.2':{}}}}})
        scs.save()
        router.active_static_configs.add(scs)
        router.save()

        config = generateConfig(router)
        diff = Vyos13RouterConfig([], {'system':{'ntp':{'servers':{'1.1.1.1':{}, '2.2.2.2':{}}}}}).diff(config)
        self.assertTrue(diff.isEmpty(), 'Diff is not empty: ' + str(diff))

    def test_generateConfigMultiSCS(self):
        router = basic_models.Vyos13Router(name="A", loopback='127.0.1.1', deploy=False, token='1234', fingerprint='5678', managed_interface_context=[])
        router.save()
        #TODO: description
        scs1 = basic_models.Vyos13StaticConfigSection(description='bla', absolute=False, context=[], content={'system':{'ntp':{'servers':{'1.1.1.1':{}, '2.2.2.2':{}}}}})
        scs1.save()
        #TODO: description
        scs2 = basic_models.Vyos13StaticConfigSection(description='blub', absolute=False, context=[], content={'system':{'ntp':{'servers':{'3.3.3.3':{}}}}})
        scs2.save()
        router.active_static_configs.add(scs1)
        router.active_static_configs.add(scs2)
        router.save()

        config = generateConfig(router)
        diff = Vyos13RouterConfig([], {'system':{'ntp':{'servers':{'1.1.1.1':{}, '2.2.2.2':{}, '3.3.3.3':{}}}}}).diff(config)
        self.assertTrue(diff.isEmpty(), 'Diff is not empty: ' + str(diff))

    def test_generateConfigMultiSCSAbsolute(self):
        router = basic_models.Vyos13Router(name="A", loopback='127.0.1.1', deploy=False, token='1234', fingerprint='5678', managed_interface_context=[])
        router.save()
        #TODO: description
        scs1 = basic_models.Vyos13StaticConfigSection(description='bla', absolute=False, context=[], content={'system':{'ntp':{'servers':{'1.1.1.1':{}, '2.2.2.2':{}}}, 'name-servers': ['8.8.8.8', '8.8.4.4']}})
        scs1.save()
        #TODO: description
        scs2 = basic_models.Vyos13StaticConfigSection(description='blub', absolute=True, context=['system','ntp'], content={'servers':{'3.3.3.3':{}}})
        scs2.save()
        router.active_static_configs.add(scs1)
        router.active_static_configs.add(scs2)
        router.save()

        config = generateConfig(router)
        diff = Vyos13RouterConfig([], {'system':{'ntp':{'servers':{'3.3.3.3':{}}}, 'name-servers':['8.8.8.8','8.8.4.4']}}).diff(config)
        self.assertTrue(diff.isEmpty(), 'Diff is not empty: ' + str(diff))


class Vyos13GenerationNetworkTest(TestCase):
    def test_generateConfigWithManagedNetwork(self):
        router = basic_models.Vyos13Router(name="A", loopback='127.0.1.1', deploy=False, token='1234', fingerprint='5678', managed_interface_context=['interfaces', 'ethernet', 'eth0'])
        router.save()
        #TODO: description
        scs = basic_models.Vyos13StaticConfigSection(description='bla', absolute=False, context=[], content={'interfaces':{'ethernet':{'eth0':{}}}})
        scs.save()
        router.active_static_configs.add(scs)
        router.save()
        customer = customer_models.Customer(name='B')
        customer.save()
        network = network_models.Network(ipv4_network_address='10.20.30.0', ipv4_network_bits=24, layer2_network_id=38, owner=customer, name='net', state=OWNED_OBJECT_STATE_LIVE)
        network.save()
        managed_interface = network_models.ManagedInterface(ipv4_address='10.20.30.1', router=router, network=network)
        managed_interface.save()

        config = generateConfig(router)
        diff = Vyos13RouterConfig([], {
                'interfaces':{
                    'ethernet': {
                        'eth0': {
                            'vif': {
                                '38': {
                                    'description': 'autogen_id'+ str(network.id) +'_net',
                                    'address': ['10.20.30.1/24']
                                }
                            }
                        }
                    }
                }
            }).diff(config)
        self.assertTrue(diff.isEmpty(), 'Diff is not empty: ' + str(diff))

    def test_generateConfigWithManagedNetworkOverwritten(self):
        router = basic_models.Vyos13Router(name="A", loopback='127.0.1.1', deploy=False, token='1234', fingerprint='5678', managed_interface_context=['interfaces', 'ethernet', 'eth0'])
        router.save()
        #TODO: description
        scs1 = basic_models.Vyos13StaticConfigSection(description='bla', absolute=False, context=[], content={'interfaces':{'ethernet':{'eth0':{}}}})
        scs1.save()
        #TODO: description
        scs2 = basic_models.Vyos13StaticConfigSection(description='bla', absolute=True, context=['interfaces', 'ethernet', 'eth0', 'vif', '38', 'address'], content={'10.20.30.2/24':{}})
        scs2.save()
        router.active_static_configs.add(scs1)
        router.active_static_configs.add(scs2)
        router.save()
        customer = customer_models.Customer(name='B')
        customer.save()
        network = network_models.Network(ipv4_network_address='10.20.30.0', ipv4_network_bits=24, layer2_network_id=38, owner=customer, name='net', state=OWNED_OBJECT_STATE_LIVE)
        network.save()
        managed_interface = network_models.ManagedInterface(ipv4_address='10.20.30.1', router=router, network=network)
        managed_interface.save()

        config = generateConfig(router)
        diff = Vyos13RouterConfig([], {
                'interfaces':{
                    'ethernet': {
                        'eth0': {
                            'vif': {
                                '38': {
                                    'description': 'autogen_id'+ str(network.id) +'_net',
                                    'address': ['10.20.30.2/24']
                                }
                            }
                        }
                    }
                }
            }).diff(config)
        self.assertTrue(diff.isEmpty(), 'Diff is not empty: ' + str(diff))

    def test_generateConfigWithVRRPInterface(self):
        router1 = basic_models.Vyos13Router(name="A", loopback='127.0.1.1', deploy=False, token='1234', fingerprint='5678', managed_interface_context=['interfaces', 'ethernet', 'eth0'])
        router1.save()
        router2 = basic_models.Vyos13Router(name="B", loopback='127.0.1.2', deploy=False, token='2345', fingerprint='6789', managed_interface_context=['interfaces', 'ethernet', 'eth0'])
        router2.save()
        #TODO: description
        scs1 = basic_models.Vyos13StaticConfigSection(description='bla', absolute=False, context=[], content={'interfaces':{'ethernet':{'eth0':{}}}})
        scs1.save()
        router1.active_static_configs.add(scs1)
        router1.save()
        router2.active_static_configs.add(scs1)
        router2.save()
        customer = customer_models.Customer(name='C')
        customer.save()
        network = network_models.Network(ipv4_network_address='10.20.30.0', ipv4_network_bits=24, layer2_network_id=38, owner=customer, name='net', vrrp_password='secret1337', state=OWNED_OBJECT_STATE_LIVE)
        network.save()
        managed_interface1 = network_models.ManagedVRRPInterface(ipv4_address='10.20.30.2', router=router1, network=network, vrid=25, priority=100, ipv4_service_address='10.20.30.1')
        managed_interface1.save()
        managed_interface2 = network_models.ManagedVRRPInterface(ipv4_address='10.20.30.3', router=router2, network=network, vrid=25, priority=101, ipv4_service_address='10.20.30.1')
        managed_interface2.save()

        config = generateConfig(router1)
        diff = Vyos13RouterConfig([], {
                'interfaces':{
                    'ethernet': {
                        'eth0': {
                            'vif': {
                                '38': {
                                    'description': 'autogen_id'+ str(network.id) +'_net',
                                    'address': ['10.20.30.2/24']
                                }
                            }
                        }
                    }
                },
                'high-availability': {
                    'vrrp': {
                        'group': {
                            'autogen_id'+ str(network.id) +'_net_v4': {
                                'interface': 'eth0.38',
                                'vrid': '25',
                                'virtual-address': ['10.20.30.1/24'],
                                'priority': '100',
                                'authentication': {
                                    'type': 'plaintext-password',
                                    'password': 'secret1337'
                                }
                            }
                        }
                    }
                }
            }).diff(config)
        self.assertTrue(diff.isEmpty(), 'Diff is not empty: ' + str(diff))


    def test_generateConfigWithWrongVRRPInterface(self):
        router1 = basic_models.Vyos13Router(name="A", loopback='127.0.1.1', deploy=False,
            token='1234', fingerprint='5678', 
            managed_interface_context=['interfaces', 'ethernet', 'eth0'])
        router1.save()
        #TODO: description
        scs1 = basic_models.Vyos13StaticConfigSection(description='bla', absolute=False,
            context=[], content={'interfaces':{'ethernet':{'eth0':{}}}})
        scs1.save()
        router1.active_static_configs.add(scs1)
        router1.save()
        customer = customer_models.Customer(name='C')
        customer.save()
        network = network_models.Network(ipv4_network_address='10.20.30.0', ipv4_network_bits=24,
            layer2_network_id=38, owner=customer, name='net', vrrp_password='secret1338', state=OWNED_OBJECT_STATE_LIVE)
        network.save()
        managed_interface1 = network_models.ManagedVRRPInterface(ipv4_address='10.21.30.2',
            router=router1, network=network, vrid=25, priority=100,
            ipv4_service_address='10.20.30.1')
        managed_interface1.save()

        config = generateConfig(router1)
        diff = Vyos13RouterConfig([], {
                'interfaces':{
                    'ethernet': {
                        'eth0': {
                            'vif': {
                                '38': {
                                    'description': 'autogen_id'+ str(network.id) +'_net'
                                }
                            }
                        }
                    }
                }
            }).diff(config)
        self.assertTrue(diff.isEmpty(), 'Diff is not empty: ' + str(diff))

    def test_generateConfigWithFirewall(self):
        router = basic_models.Vyos13Router(name="A", loopback='127.0.1.1', deploy=False, token='1234', fingerprint='5678', managed_interface_context=['interfaces', 'ethernet', 'eth0'])
        router.save()
        #TODO: description
        scs1 = basic_models.Vyos13StaticConfigSection(description='bla', absolute=False, context=[], content={'interfaces':{'ethernet':{'eth0':{}}}})
        scs1.save()
        router.active_static_configs.add(scs1)
        router.save()
        customer = customer_models.Customer(name='B')
        customer.save()
        network = network_models.Network(ipv4_network_address='10.20.30.0', ipv4_network_bits=24, layer2_network_id=38, owner=customer, name='net', state=OWNED_OBJECT_STATE_LIVE)
        network.save()
        managed_interface = network_models.ManagedInterface(ipv4_address='10.20.30.1', router=router, network=network)
        managed_interface.save()
        firewall = firewall_models.Firewall(name='my firewall', stateful=True, related_network=network, default_action_into=firewall_models.ACTION_DROP, default_action_from=firewall_models.ACTION_ACCEPT, owner=customer, public=False, state=OWNED_OBJECT_STATE_LIVE)
        firewall.save()
        ruleset1 = firewall_models.RuleSet(priority=100, owner=customer, public=False, state=OWNED_OBJECT_STATE_LIVE)
        ruleset1.save()
        ruleset1.firewalls.add(firewall)
        ruleset1.save()
        rule1 = firewall_models.CustomRule(related_ruleset=ruleset1, priority=1, disable=False, ip_version=firewall_models.IP_VERSION_4, direction=firewall_models.DIRECTION_INTO, rule_definition={'source':{'address':'10.11.12.8/29'}, 'action':'accept'}, state=OWNED_OBJECT_STATE_LIVE)
        rule1.save()
        
        config = generateConfig(router)
        fw_from_name = 'autogen_from_'+str(firewall.id)+'_my_firewall'
        fw_from_name = fw_from_name[:27]
        fw_into_name = 'autogen_into_'+str(firewall.id)+'_my_firewall'
        fw_into_name = fw_into_name[:27]
        diff = Vyos13RouterConfig([], {
                'interfaces':{
                    'ethernet': {
                        'eth0': {
                            'vif': {
                                '38': {
                                    'description': 'autogen_id'+ str(network.id) +'_net',
                                    'address': '10.20.30.1/24',
                                    'firewall': {
                                        'in': {'name': fw_from_name},
                                        'out': {'name': fw_into_name}
                                    }
                                }
                            }
                        }
                    }
                },
                'firewall': {
                    'name': {
                        fw_from_name: {
                            'default-action': 'accept',
                            'rule': {
                                '9999': {
                                    'action': 'accept',
                                    'state': {
                                        'established': 'enable',
                                        'related': 'enable'
                                    }
                                }
                            }
                        },
                        fw_into_name: {
                            'default-action': 'drop',
                            'rule': {
                                '10': {
                                    'action': 'accept',
                                    'source': {
                                        'address': '10.11.12.8/29'
                                    }
                                },
                                '9999': {
                                    'action': 'accept',
                                    'state': {
                                        'established': 'enable',
                                        'related': 'enable'
                                    }
                                }
                            }
                        }
                    }
                }
            }).diff(config)
        self.assertTrue(diff.isEmpty(), 'Diff is not empty: ' + str(diff))

    def test_generateConfigWithFirewallBasicRule(self):
        router = basic_models.Vyos13Router(name="A", loopback='127.0.1.1', deploy=False, token='1234', fingerprint='5678', managed_interface_context=['interfaces', 'ethernet', 'eth0'])
        router.save()
        #TODO: description
        scs1 = basic_models.Vyos13StaticConfigSection(description='bla', absolute=False, context=[], content={'interfaces':{'ethernet':{'eth0':{}}}})
        scs1.save()
        router.active_static_configs.add(scs1)
        router.save()
        customer = customer_models.Customer(name='B')
        customer.save()
        network = network_models.Network(ipv4_network_address='10.20.30.0', ipv4_network_bits=24, layer2_network_id=38, owner=customer, name='net', state=OWNED_OBJECT_STATE_LIVE)
        network.save()
        managed_interface = network_models.ManagedInterface(ipv4_address='10.20.30.1', router=router, network=network)
        managed_interface.save()
        firewall = firewall_models.Firewall(name='my firewall', stateful=True, related_network=network, default_action_into=firewall_models.ACTION_DROP, default_action_from=firewall_models.ACTION_ACCEPT, owner=customer, public=False, state=OWNED_OBJECT_STATE_LIVE)
        firewall.save()
        ruleset1 = firewall_models.RuleSet(priority=100, owner=customer, public=False, state=OWNED_OBJECT_STATE_LIVE)
        ruleset1.save()
        ruleset1.firewalls.add(firewall)
        ruleset1.save()
        source_address_host = firewall_models.HostAddressObject.objects.create(owner=customer, public=False, name='a host', ipv4_address='10.1.2.3', ipv6_address='2001:db8:1111::10', state=OWNED_OBJECT_STATE_LIVE)
        source_address_net = firewall_models.CIDRAddressObject.objects.create(owner=customer, public=False, name='a network', ipv4_network_address='10.2.3.0', ipv4_network_bits=24, ipv6_network_address='2001:db8:1234::', ipv6_network_bits=64, state=OWNED_OBJECT_STATE_LIVE)
        source_address_list = firewall_models.ListAddressObject.objects.create(owner=customer, public=False, name='valid hosts', state=OWNED_OBJECT_STATE_LIVE)
        source_address_list.elements.add(source_address_host)
        source_address_list.elements.add(source_address_net)
        source_address_list.save()
        network_address_object = firewall_models.NetworkAddressObject.objects.create(owner=customer, public=False, name='my network', related_network=network, state=OWNED_OBJECT_STATE_LIVE)
        rule1 = firewall_models.BasicRule(related_ruleset=ruleset1, priority=1, disable=False, source_address=source_address_list, destination_address=network_address_object, log=False, action=firewall_models.ACTION_ACCEPT, state=OWNED_OBJECT_STATE_LIVE)
        rule1.save()
        
        config = generateConfig(router)
        fw_from_name = 'autogen_from_'+str(firewall.id)+'_my_firewall'
        fw_from_name = fw_from_name[:27]
        fw_into_name = 'autogen_into_'+str(firewall.id)+'_my_firewall'
        fw_into_name = fw_into_name[:27]
        diff = Vyos13RouterConfig([], {
                'interfaces':{
                    'ethernet': {
                        'eth0': {
                            'vif': {
                                '38': {
                                    'description': 'autogen_id'+ str(network.id) +'_net',
                                    'address': '10.20.30.1/24',
                                    'firewall': {
                                        'in': {'name': fw_from_name},
                                        'out': {'name': fw_into_name}
                                    }
                                }
                            }
                        }
                    }
                },
                'firewall': {
                    'name': {
                        fw_from_name: {
                            'default-action': 'accept',
                            'rule': {
                                '9999': {
                                    'action': 'accept',
                                    'state': {
                                        'established': 'enable',
                                        'related': 'enable'
                                    }
                                }
                            }
                        },
                        fw_into_name: {
                            'default-action': 'drop',
                            'rule': {
                                '10': {
                                    'action': 'accept',
                                    'source': {
                                        'address': '10.1.2.3'
                                    },
                                    'destination' : {
                                        'address': '10.20.30.0/24'
                                    }
                                },
                                '20': {
                                    'action': 'accept',
                                    'source': {
                                        'address': '10.2.3.0/24'
                                    },
                                    'destination' : {
                                        'address': '10.20.30.0/24'
                                    }
                                },
                                '9999': {
                                    'action': 'accept',
                                    'state': {
                                        'established': 'enable',
                                        'related': 'enable'
                                    }
                                }
                            }
                        }
                    }
                }
            }).diff(config)
        self.assertTrue(diff.isEmpty(), 'Diff is not empty: ' + str(diff))