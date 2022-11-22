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
import unittest
from vycinity.s42.routerconfig.vyos13 import Vyos13RouterConfig, Vyos13RouterConfigDiff

class TestVyos13RouterConfig(unittest.TestCase):
    def test_subConfig(self):
        traversedConfig = Vyos13RouterConfig(['firewall'], {'name':{'fw1':{'default-action': 'accept'}}})
        with self.assertRaises(ValueError):
            traversedConfig.getSubConfig(['interfaces'])
        
        result = traversedConfig.getSubConfig(['firewall', 'name', 'fw1'])
        self.assertEqual({'default-action': 'accept'}, result.config)
        self.assertEqual(['firewall', 'name', 'fw1'], result.context)
    
    def test_diff1(self):
        config1 = Vyos13RouterConfig([], {'name':{'fw2':{'default-action': 'accept'}}})
        config2 = Vyos13RouterConfig([], {'name':{'fw2':{'default-action': 'drop'}}})
        diff = config1.diff(config2)
        self.assertEqual({'name':{'fw2':{'default-action': 'accept'}}}, diff.left)
        self.assertEqual({'name':{'fw2':{'default-action': 'drop'}}}, diff.right)
        self.assertEqual([], diff.context)

    def test_diff2(self):
        config3 = Vyos13RouterConfig([], {'system':{'ntp':{'servers': ['ptbtime1.ptb.de', 'time1.google.com']}}})
        config4 = Vyos13RouterConfig([], {'system':{'ntp':{'servers': ['ptbtime1.ptb.de', '0.de.pool.ntp.org']}}})
        diff2 = config3.diff(config4)
        self.assertEqual({'system':{'ntp':{'servers': ['time1.google.com']}}}, diff2.left)
        self.assertEqual({'system':{'ntp':{'servers': ['0.de.pool.ntp.org']}}}, diff2.right)
        self.assertEqual([], diff2.context)

    def test_diff3(self):
        config5 = Vyos13RouterConfig([], {'firewall':{'name':{'fw3':{'default-action': 'accept'}}}, 'system':{'ntp':{'servers': ['ptbtime1.ptb.de', 'time1.google.com']}}})
        config6 = Vyos13RouterConfig([], {'system':{'ntp':{'servers': ['ptbtime1.ptb.de', '0.de.pool.ntp.org']}}})
        diff3 = config5.diff(config6)
        self.assertEqual({'firewall':{'name':{'fw3':{'default-action': 'accept'}}, '__complete':True}, 'system':{'ntp':{'servers': ['time1.google.com']}}}, diff3.left)
        self.assertEqual({'system':{'ntp':{'servers': ['0.de.pool.ntp.org']}}}, diff3.right)
        self.assertEqual([], diff3.context)

    def test_diff4(self):
        config7 = Vyos13RouterConfig([], {'system':{'ntp':{'servers': ['ptbtime1.ptb.de', 'time1.google.com'], 'source-interface': 'eth0'}}})
        config8 = Vyos13RouterConfig([], {'system':{'ntp':{'servers': ['ptbtime1.ptb.de', '0.de.pool.ntp.org']}}})
        diff4 = config7.diff(config8)
        self.assertEqual({'system':{'ntp':{'servers': ['time1.google.com'], 'source-interface': 'eth0'}}}, diff4.left)
        self.assertEqual({'system':{'ntp':{'servers': ['0.de.pool.ntp.org']}}}, diff4.right)
        self.assertEqual([], diff4.context)

    def test_diff5(self):
        config1 = Vyos13RouterConfig([], {'system':{'ntp':{'servers': ['ptbtime1.ptb.de', 'time1.google.com'], 'source-interface': 'eth0'}}})
        config2 = Vyos13RouterConfig(['system'], {'ntp':{'servers': ['ptbtime1.ptb.de', '0.de.pool.ntp.org']}})
        diff = config1.diff(config2)
        self.assertEqual({'ntp':{'servers': ['time1.google.com'], 'source-interface': 'eth0'}}, diff.left)
        self.assertEqual({'ntp':{'servers': ['0.de.pool.ntp.org']}}, diff.right)
        self.assertEqual(['system'], diff.context)
    
    def test_diff6(self):
        config1 = Vyos13RouterConfig(['system'], {'ntp':{'servers': ['ptbtime1.ptb.de', 'time1.google.com'], 'source-interface': 'eth0'}})
        config2 = Vyos13RouterConfig(['firewall'], {'name':{'my-firewall': {'default-action': 'accept'}}})
        with self.assertRaises(ValueError):
            config1.diff(config2)

    def test_diff7(self):
        config1 = Vyos13RouterConfig(['system'], {'ntp':{'servers': 'ptbtime1.ptb.de', 'source-interface': 'eth0'}})
        config2 = Vyos13RouterConfig(['system'], {'ntp':{'servers': ['ptbtime1.ptb.de', 'time1.google.com'], 'source-interface': 'eth0'}})
        diff = config1.diff(config2)
        self.assertEqual(['system'], diff.context)
        self.assertIsNone(diff.left)
        self.assertEqual({'ntp':{'servers': {'time1.google.com': {'__complete': True}}}}, diff.right)

    def test_diff8(self):
        config1 = Vyos13RouterConfig(['system'], {'ntp':{'servers': 'ptbtime1.ptb.de', 'source-interface': 'eth0'}})
        config2 = Vyos13RouterConfig(['system'], {'ntp':{'servers': {'ptbtime1.ptb.de': {}, 'time1.google.com': {}}, 'source-interface': 'eth0'}})
        diff = config1.diff(config2)
        self.assertEqual(['system'], diff.context)
        self.assertIsNone(diff.left)
        self.assertEqual({'ntp':{'servers': {'time1.google.com': { '__complete': True }}}}, diff.right)

    def test_diff9(self):
        config1 = Vyos13RouterConfig(['system'], {'ntp':{'servers': ['ptbtime1.ptb.de', 'time1.google.com'], 'source-interface': 'eth0'}})
        config2 = Vyos13RouterConfig(['system'], {'ntp':{'servers': {'ptbtime1.ptb.de': {}, 'time1.google.com': {}}, 'source-interface': 'eth0'}})
        diff = config1.diff(config2)
        self.assertEqual(['system'], diff.context)
        self.assertTrue(diff.isEmpty())

    def test_merge1(self):
        config1 = Vyos13RouterConfig(['system'], {'ntp':{'servers': ['ptbtime1.ptb.de', 'time1.google.com'], 'source-interface': 'eth0'}})
        config2 = Vyos13RouterConfig(['firewall'], {'name':{'my-firewall': {'default-action': 'accept'}}})
        with self.assertRaises(ValueError):
            config1.merge(config2, False)

    def test_merge2(self):
        config1 = Vyos13RouterConfig(['system'], {'ntp':{'servers': ['ptbtime1.ptb.de', 'time1.google.com'], 'source-interface': 'eth0'}})
        config2 = Vyos13RouterConfig(['system'], {'ntp':{'servers': ['ptbtime1.ptb.de', 'time1.google.com']}})
        merged_config = config1.merge(config2, False)
        self.assertEqual(config1.context, merged_config.context)
        self.assertEqual(config1.config, merged_config.config)

    def test_merge3(self):
        config1 = Vyos13RouterConfig(['system'], {'ntp':{'servers': ['ptbtime1.ptb.de', 'time1.google.com'], 'source-interface': 'eth0'}})
        config2 = Vyos13RouterConfig(['system'], {'ntp':{'servers': ['ptbtime1.ptb.de', 'time1.google.com', '0.de.pool.ntp.org']}})
        merged_config = config1.merge(config2, False)
        self.assertEqual(config1.context, merged_config.context)
        self.assertEqual({'ntp':{'servers': ['ptbtime1.ptb.de', 'time1.google.com', '0.de.pool.ntp.org'], 'source-interface': 'eth0'}}, merged_config.config)

    def test_merge4(self):
        config1 = Vyos13RouterConfig(['system'], {'ntp':{'servers': ['ptbtime1.ptb.de', 'time1.google.com'], 'source-interface': 'eth0'}})
        config2 = Vyos13RouterConfig(['system'], {'ntp':{'servers': ['0.de.pool.ntp.org']}})
        merged_config = config1.merge(config2, False)
        self.assertEqual(config1.context, merged_config.context)
        self.assertEqual({'ntp':{'servers': ['ptbtime1.ptb.de', 'time1.google.com', '0.de.pool.ntp.org'], 'source-interface': 'eth0'}}, merged_config.config)
    
    def test_merge5(self):
        config1 = Vyos13RouterConfig(['system'], {'ntp':{'servers': ['ptbtime1.ptb.de', 'time1.google.com'], 'source-interface': 'eth0'}})
        config2 = Vyos13RouterConfig(['system'], {'ntp':{'servers': ['0.de.pool.ntp.org']}})
        merged_config = config1.merge(config2, True)
        self.assertEqual(config1.context, merged_config.context)
        self.assertEqual({'ntp':{'servers': ['0.de.pool.ntp.org']}}, merged_config.config)

    def test_merge6(self):
        config1 = Vyos13RouterConfig(['system'], {'ntp':{'servers': ['ptbtime1.ptb.de', 'time1.google.com'], 'source-interface': 'eth0'}, 'name-servers': ['9.9.9.9', '9.9.9.10']})
        config2 = Vyos13RouterConfig(['system', 'ntp'], {'servers': ['0.de.pool.ntp.org']})
        merged_config = config1.merge(config2, True)
        self.assertEqual(config1.context, merged_config.context)
        self.assertEqual({'ntp':{'servers': ['0.de.pool.ntp.org']}, 'name-servers': ['9.9.9.9', '9.9.9.10']}, merged_config.config)

class TestVyos13RouterConfigDiff(unittest.TestCase):
    def test_getApiCommands1(self):
        config1 = Vyos13RouterConfig([], {'firewall':{'name':{'bla':{'default-action': 'accept'}}}, 'system':{'ntp':{'servers': ['ptbtime1.ptb.de', 'time1.google.com']}}})
        config2 = Vyos13RouterConfig([], {'system':{'ntp':{'servers': ['ptbtime1.ptb.de', '0.de.pool.ntp.org']}}})
        cmds = config1.diff(config2).genApiCommands()
        self.assertIn({'op': 'delete', 'path': ['firewall']}, cmds)
        self.assertIn({'op': 'delete', 'path': ['system', 'ntp', 'servers', 'time1.google.com']}, cmds)
        self.assertIn({'op': 'set', 'path': ['system', 'ntp', 'servers'], 'value': '0.de.pool.ntp.org'}, cmds)
    

    def test_getApiCommands2(self):
        config1 = Vyos13RouterConfig([], {'system':{'ntp':{'servers': ['ptbtime1.ptb.de', 'time1.google.com']}}})
        config2 = Vyos13RouterConfig([], {'system':{'ntp':{'update-source': 'eth0'}}})
        cmds = config1.diff(config2).genApiCommands()
        self.assertIn({'op': 'delete', 'path': ['system', 'ntp', 'servers']}, cmds)
        self.assertIn({'op': 'set', 'path': ['system', 'ntp', 'update-source'], 'value': 'eth0'}, cmds)

    
    def test_getApiCommands3(self):
        config1 = Vyos13RouterConfig(['firewall', 'name', 'my-firewall'], {'default-action': 'accept', 'rule': {'10': {'action': 'reject', 'destination': {'address': '1.2.3.4'}}}})
        config2 = Vyos13RouterConfig([], {'firewall':{'name':{'my-firewall': {'default-action': 'drop', 'rule': {'10': {'action': 'reject', 'destination': {'address': '1.2.3.4'}}}}}}})
        cmds = config1.diff(config2).genApiCommands()
        self.assertIn({'op': 'set', 'path': ['firewall', 'name', 'my-firewall', 'default-action'], 'value': 'drop'}, cmds)


    def test_getApiCommands4(self):
        config1 = Vyos13RouterConfig(['firewall', 'name', 'my-firewall'], {'default-action': 'accept', 'rule': {'10': {'action': 'reject', 'destination': {'address': '1.2.3.4'}}}})
        config2 = Vyos13RouterConfig(['firewall', 'name', 'my-firewall'], {'default-action': 'drop', 'rule': {'10': {'action': 'reject', 'destination': {'address': '1.2.3.4'}}}})
        cmds = config1.diff(config2).genApiCommands()
        self.assertIn({'op': 'set', 'path': ['firewall', 'name', 'my-firewall', 'default-action'], 'value': 'drop'}, cmds)

    def test_getApiCommands5(self):
        config1 = Vyos13RouterConfig([], {'interfaces':{'ethernet':{'eth0':{'address':'1.2.3.4/28'}}}})
        config2 = Vyos13RouterConfig([], {'interfaces':{'ethernet':{'eth0':{'address':['1.2.3.4/28', '2.3.4.5/24']}}}})
        cmds = config1.diff(config2).genApiCommands()
        self.assertIn({'op': 'set', 'path': ['interfaces', 'ethernet', 'eth0', 'address', '2.3.4.5/24']}, cmds)

    def test_getApiCommands6(self):
        config1 = Vyos13RouterConfig(['system'], {'ntp': {}})
        config2 = Vyos13RouterConfig(['system'], {'ntp': {'server': {'0.pool.ntp.org': {}, '1.pool.ntp.org': {}, '2.pool.ntp.org': {}}}})
        diff = config1.diff(config2)
        cmds = diff.genApiCommands()
        self.assertIn({'op': 'set', 'path': ['system', 'ntp', 'server', '0.pool.ntp.org']}, cmds)
        self.assertIn({'op': 'set', 'path': ['system', 'ntp', 'server', '1.pool.ntp.org']}, cmds)
        self.assertIn({'op': 'set', 'path': ['system', 'ntp', 'server', '2.pool.ntp.org']}, cmds)
        self.assertEqual(3, len(cmds))

    def test_getApiCommands7(self):
        diff = Vyos13RouterConfigDiff([], {'interfaces':{'ethernet':{'eth1':{'ip':{'ospf':{'bandwith':'1000'}, '__complete':True}}}}}, None)
        cmds = diff.genApiCommands()
        self.assertEqual(1, len(cmds))
        self.assertIn({'op': 'delete', 'path': ['interfaces', 'ethernet', 'eth1', 'ip']}, cmds)

    def test_getApiCommands8(self):
        '''
        This configuration diff created commands that were unexpected and is taken from a real use
        case.
        '''
        diff = Vyos13RouterConfigDiff([], 
            {
                "system": {
                    "ntp": {
                        "server": {
                            "rz1-time.example.net": {},
                            "rz2-time.example.net": {}
                        }
                    },
                    "login": {
                        "user": {
                            "otheruser": {
                                "authentication": {
                                    "encrypted-password": "$6$9Smh65RxGTQyhXvo$redacted"
                                }
                            }
                        }
                    },
                    "syslog": {
                        "host": {
                            "212.11.229.1": {
                                "facility": {
                                    "all": {
                                        "level": "info",
                                        "protocol": "udp"
                                    },
                                    "protocols": {
                                        "level": "debug",
                                        "protocol": "udp"
                                    }
                                }
                            }
                        },
                        "global": {
                            "facility": {
                                "all": {
                                    "level": "info"
                                },
                                "protocols": {
                                    "level": "debug"
                                }
                            }
                        }
                    },
                    "conntrack": {
                        "modules": {
                            "ftp": {},
                            "nfs": {},
                            "sip": {},
                            "h323": {},
                            "pptp": {},
                            "tftp": {},
                            "sqlnet": {}
                        }
                    },
                    "host-name": "rz0-rt1",
                    "config-management": {
                        "commit-revisions": "100"
                    }
                },
                "service": {
                    "ssh": {},
                    "https": {
                        "api": {
                            "keys": {
                                "id": {
                                    "routerdeployment": {
                                    "key": "rd123456"
                                    }
                                }
                            },
                            "debug": {}
                        },
                        "api-restrict": {
                            "virtual-host": "loopback-191"
                        },
                        "virtual-host": {
                            "loopback-191": {
                                "listen-port": "443",
                                "server-name": "10.07.2.191",
                                "listen-address": "10.1.2.191"
                            }
                        }
                    }
                },
                "interfaces": {
                    "ethernet": {
                        "eth0": {
                            "hw-id": "3c:a8:2a:a0:26:11",
                            "address": "dhcp"
                        },
                        "eth1": {
                            "hw-id": "3c:a8:2a:a0:26:22"
                        },
                        "eth2": {
                            "hw-id": "f4:52:14:44:5d:33",
                            "disable": {}
                        }
                    },
                    "loopback": {
                        "lo": {
                            "address": "10.2.0.4/32"
                        }
                    }
                }
            },
            {
                "system": {
                    "ntp": {
                        "server": {
                            "rz1-time.example.net": {},
                            "rz2-time.example.net": {}
                        }
                    },
                    "login": {
                        "user": {
                            "otheruser": {
                                "authentication": {
                                    "encrypted-password": "$6$9Smh65RxGTQyhXvo$redacted"
                                }
                            }
                        }
                    },
                    "syslog": {
                        "host": {
                            "212.11.229.1": {
                                "facility": {
                                    "all": {
                                        "level": "info",
                                        "protocol": "udp"
                                    },
                                    "protocols": {
                                        "level": "debug",
                                        "protocol": "udp"
                                    }
                                }
                            }
                        },
                        "global": {
                            "facility": {
                                "all": {
                                    "level": "info"
                                },
                                "protocols": {
                                    "level": "debug"
                                }
                            }
                        }
                    },
                    "conntrack": {
                        "modules": {
                            "ftp": {},
                            "nfs": {},
                            "sip": {},
                            "h323": {},
                            "pptp": {},
                            "tftp": {},
                            "sqlnet": {}
                        }
                    },
                    "host-name": "rz0-rt1",
                    "config-management": {
                        "commit-revisions": "100"
                    }
                },
                "service": {
                    "ssh": {},
                    "https": {
                        "api": {
                            "debug": {}
                        },
                        "api-restrict": {
                            "virtual-host": "loopback-191"
                        },
                        "virtual-host": {
                            "loopback-191": {
                            "listen-port": "443",
                            "server-name": [
                                "10.1.2.191"
                            ],
                            "listen-address": "10.1.2.191"
                            }
                        }
                    }
                },
                "interfaces": {
                    "ethernet": {
                    "eth0": {
                        "hw-id": "3c:a8:2a:a0:26:11",
                        "address": "dhcp"
                    },
                    "eth1": {
                        "hw-id": "3c:a8:2a:a0:26:22"
                    },
                    "eth2": {
                        "hw-id": "f4:52:14:44:5d:33",
                        "disable": {}
                    }
                    },
                    "loopback": {
                        "lo": {
                            "address": "10.2.0.4/32"
                        }
                    }
                }
            })
        cmds = diff.genApiCommands()
        self.assertEqual(3, len(cmds), f"API-Commands are {json.dumps(cmds)} (count is different from 3)")
        self.assertIn({'op': 'delete', 'path': ['service', 'https', 'virtual-host', 'loopback-191', 'server-name', '10.07.2.191']}, cmds)
        self.assertIn({'op': 'set', 'path': ['service', 'https', 'virtual-host', 'loopback-191', 'server-name', '10.1.2.191']}, cmds)
        self.assertIn({'op': 'delete', 'path': ['service', 'https', 'api', 'keys']}, cmds)
        

    def test_isEmpty1(self):
        config1 = Vyos13RouterConfig(['system'], {'ntp': ['1.2.3.4', '5.6.7.8']})
        config2 = Vyos13RouterConfig([], {'system': {'ntp': ['1.2.3.4', '5.6.7.8']}})
        diff = config1.diff(config2)
        self.assertTrue(diff.isEmpty())

    def test_isEmpty2(self):
        config1 = Vyos13RouterConfig(['system'], {'ntp': ['1.2.3.4', '5.6.7.8']})
        config2 = Vyos13RouterConfig(['system'], {'ntp': ['1.2.3.4', '5.6.7.8']})
        diff = config1.diff(config2)
        self.assertTrue(diff.isEmpty())

    def test_isEmpty3(self):
        config1 = Vyos13RouterConfig(['system'], {'ntp': ['1.2.3.4']})
        config2 = Vyos13RouterConfig(['system'], {'ntp': ['1.2.3.4', '5.6.7.8']})
        diff = config1.diff(config2)
        self.assertFalse(diff.isEmpty())

if __name__ == '__main__':
    unittest.main()