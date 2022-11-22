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
import logging
import requests
from typing import Dict, List, Union
from . import Router, RouterConfig, RouterConfigDiff, RouterConfigError, RouterCommunicationError

logger = logging.getLogger(__name__)

class Vyos13RouterConfigDiff(RouterConfigDiff):
    def __init__(self, context: List[str] = [], left = None, right = None):
        self.left = left
        self.right = right
        self.context = context


    def isEmpty(self) -> bool:
        return (self.left is None and self.right is None)

    
    def displayString(self) -> str:
        '''
        see parent:
        '''
        Vyos13RouterConfigDiff.displayString.__doc__ += RouterConfigDiff.displayString.__doc__
        raise NotImplementedError()

    @staticmethod
    def __objectizeConf(obj: Union[list, str, dict]):
        if isinstance(obj, str):
            return { obj: {} }
        if isinstance(obj, list):
            rtn = {}
            for current_item in obj:
                for k, v in Vyos13RouterConfigDiff.__objectizeConf(current_item).items():
                    rtn[k] = v
            return rtn
        if isinstance(obj, dict):
            rtn = {}
            for current_key, current_value in obj.items():
                rtn[current_key] = Vyos13RouterConfigDiff.__objectizeConf(current_value) 
            return rtn
    
    def genApiCommands(self) -> List[Dict[str,Union[List[str],str]]]:
        '''
        Generates a list of get and set operations from this diff.

        The right side of the diff is the destination state. Items in the left side not replaced
        will be removed.

        returns: A list of operations applicable via VyOS 1.3 API
        '''

        rtn = []
        if self.isEmpty():
            return rtn
        elif self.right is None:
            if self.left is not None:
                if '__complete' in self.left or (len(self.left) == 0 and isinstance(self.left, dict)):
                    rtn.append({'op':'delete', 'path':self.context})
                elif isinstance(self.left, dict):
                    for (leftkey, leftvalue) in self.left.items():
                        rtn += Vyos13RouterConfigDiff(self.context + [leftkey], leftvalue, None).genApiCommands()
                elif isinstance(self.left, list):
                    for leftitem in self.left:
                        rtn.append({'op': 'delete', 'path': self.context + [leftitem]})
                else:
                    rtn.append({'op': 'delete', 'path': self.context + [self.left]})
        elif self.left is None:
            if isinstance(self.right, dict):
                sub_commands = []
                for right_key in self.right.keys():
                    if right_key != '__complete':
                        sub_commands += Vyos13RouterConfigDiff(self.context + [right_key], None, self.right[right_key]).genApiCommands()
                if len(sub_commands) == 0:
                    sub_commands.append({'op': 'set', 'path': self.context})
                rtn += sub_commands
            elif isinstance(self.right, list):
                for item in self.right:    
                    rtn.append({'op': 'set', 'path': self.context, 'value': str(item)})
            else:
                rtn.append({'op': 'set', 'path': self.context, 'value': str(self.right)})
        elif isinstance(self.left, dict) and isinstance(self.right, dict):
            if '__complete' in self.left and self.left['__complete']:
                rtn.append({'op': 'delete', 'path': self.context})
            else:
                shared_keys = []
                for leftKey in self.left.keys():
                    if leftKey == '__complete':
                        continue
                    if leftKey in self.right:
                        shared_keys.append(leftKey)
                    else:
                        rtn.append({'op': 'delete', 'path': self.context + [leftKey]})
                for shared_key in shared_keys:
                    rtn += Vyos13RouterConfigDiff(self.context + [shared_key], self.left[shared_key], self.right[shared_key]).genApiCommands()
                for right_key in self.right.keys():
                    if not right_key in shared_keys:
                        rtn += Vyos13RouterConfigDiff(self.context + [right_key], None, self.right[right_key]).genApiCommands()               
        elif isinstance(self.left, list) and isinstance(self.right, list):
            for left_item in self.left:
                if not left_item in self.right:
                    rtn.append({'op': 'delete', 'path': self.context + [left_item]})
            for right_item in self.right:
                if not right_item in self.left:
                    rtn.append({'op': 'set', 'path': self.context, 'value': right_item})
        else:
            if type(self.left) != type(self.right):
                rtn += Vyos13RouterConfigDiff(self.context, Vyos13RouterConfigDiff.__objectizeConf(self.left), Vyos13RouterConfigDiff.__objectizeConf(self.right)).genApiCommands()
            elif isinstance(self.left, str) and isinstance(self.right, str) and self.left != self.right:
                rtn.append({'op': 'delete', 'path': self.context})
                rtn.append({'op': 'set', 'path': self.context, 'value': str(self.right)})

        return rtn


    def __str__(self):
        return 'Vyos13RouterConfigDiff(context=%s, left=%s, right=%s)' % (str(self.context), str(self.left), str(self.right))
    


class Vyos13RouterConfig(RouterConfig):

    def __init__(self, context: List[str], plain_config: Dict[str, Union[str, Dict, List[str]]]):
        self.context = context
        self.config = plain_config


    def diff(self, other: RouterConfig) -> RouterConfigDiff:
        '''
        See parent:
        '''
        Vyos13RouterConfig.diff.__doc__ += RouterConfig.diff.__doc__

        rtn = Vyos13RouterConfigDiff()

        
        if other is None:
            rtn.left = self.config
        else:
            assert isinstance(other, Vyos13RouterConfig)

            left_config = self.config
            right_config = other.config
            current_context = self.context
            if self.context != other.context:
                if len(self.context) > len(other.context):
                    right_config = other.getSubConfig(self.context).config
                elif len(self.context) < len(other.context):
                    left_config = self.getSubConfig(other.context).config
                    current_context = other.context
                else:
                    raise ValueError('Context of the configurations is too different to create a diff.')
            
            rtn.context = current_context
            shared_keys = []
            left_not_in_right = {}
            for left_key in left_config.keys():
                if left_key in right_config:
                    shared_keys.append(left_key)
                else:
                    left_not_in_right[left_key] = left_config[left_key]
                    if isinstance(left_not_in_right[left_key], dict):
                        left_not_in_right[left_key]['__complete'] = True
            
            right_not_in_left = {}
            for right_key in right_config.keys():
                if not right_key in left_config:
                    right_not_in_left[right_key] = right_config[right_key]
                    if isinstance(right_not_in_left[right_key], dict):
                        right_not_in_left[right_key]['__complete'] = True
            
            for key in shared_keys:
                if isinstance(left_config[key], list) and isinstance(right_config[key], list):
                    right_things_not_in_left = right_config[key].copy()
                    for item in left_config[key]:
                        if item in right_things_not_in_left:
                            right_things_not_in_left.remove(item)
                    left_things_not_in_right = left_config[key].copy()
                    for item in right_config[key]:
                        if item in left_things_not_in_right:
                            left_things_not_in_right.remove(item)
                    if len(left_things_not_in_right) > 0:
                        left_not_in_right[key] = left_things_not_in_right
                    if len(right_things_not_in_left) > 0:
                        right_not_in_left[key] = right_things_not_in_left
                elif type(left_config[key]) != type(right_config[key]) or (isinstance(left_config[key], dict) and isinstance(right_config[key], dict)):
                    left_config_value_dict = {}
                    right_config_value_dict = {}
                    if isinstance(left_config[key], dict):
                        left_config_value_dict = left_config[key].copy()
                    elif isinstance(left_config[key], list):
                        for key_inside_left in left_config[key]:
                            left_config_value_dict[key_inside_left] = {}
                    else:
                        left_config_value_dict[str(left_config[key])] = {}

                    if isinstance(right_config[key], dict):
                        right_config_value_dict = right_config[key].copy()
                    elif isinstance(right_config[key], list):
                        for key_inside_right in right_config[key]:
                            right_config_value_dict[key_inside_right] = {}
                    else:
                        right_config_value_dict[str(right_config[key])] = {}

                    sub_left_config = Vyos13RouterConfig(current_context + [key], left_config_value_dict)
                    sub_right_config = Vyos13RouterConfig(current_context + [key], right_config_value_dict)
                    sub_diff = sub_left_config.diff(sub_right_config)
                    if not sub_diff.isEmpty():
                        if not sub_diff.left is None:
                            left_not_in_right[key] = sub_diff.left
                        if not sub_diff.right is None:
                            right_not_in_left[key] = sub_diff.right
                else:
                    if str(left_config[key]) != str(right_config[key]):
                        left_not_in_right[key] = str(left_config[key])
                        right_not_in_left[key] = str(right_config[key])
    

            if len(left_not_in_right) > 0:
                rtn.left = left_not_in_right
            if len(right_not_in_left) > 0:
                rtn.right = right_not_in_left

        return rtn


    @staticmethod
    def getType() -> str:
        '''
        See parent:
        '''
        Vyos13RouterConfig.getType.__doc__ += RouterConfig.getType.__doc__

        return "vyos13config"


    def getContext(self) -> List[str]:
        return self.context.copy()
    
    
    def getSubConfig(self, context: List[str]):
        '''
        Extracts a sub configuration. Useful to create diffs on subcontexts.

        returns: a `Vyos13RouterConfig` containing only the configuration section.
        '''
        if len(context) < len(self.context) or self.context != context[:len(self.context)]:
            raise ValueError("Sub config not contained inside of this config")
        sub_context = context[len(self.context):]
        if len(sub_context) == 0:
            return self
        else:
            if sub_context[0] in self.config and isinstance(self.config[sub_context[0]], dict):                
                return Vyos13RouterConfig(self.context + [sub_context[0]], self.config[sub_context[0]]).getSubConfig(context)
            else:
                raise ValueError("Sub config not contained inside of this config")

    
    def merge(self, other, absolute: bool):
        '''
        See parent:
        '''
        Vyos13RouterConfig.merge.__doc__ += RouterConfig.merge.__doc__

        rtn = Vyos13RouterConfig(self.context.copy(), self.config.copy())
        if other is None:
            other = Vyos13RouterConfig(self.context, {})
        
        assert isinstance(other, Vyos13RouterConfig)
        if len(other.context) < len(self.context) or other.context[0:len(self.context)] != self.context:
            raise ValueError("Config to merge not mergeable with this one because of too different contexts.")
        
        if other.context == rtn.context:
            if absolute:
                rtn.config = other.config
            else:
                for (key, value) in other.config.items():
                    if key in rtn.config:
                        rtnvalue = rtn.config[key]
                        if isinstance(value, dict) and isinstance(rtnvalue, dict):
                            merged_config = Vyos13RouterConfig(rtn.context + [key], rtnvalue).merge(Vyos13RouterConfig(rtn.context + [key], value), False)
                            rtn.config[key] = merged_config.config
                        elif isinstance(value, list) and isinstance(rtnvalue, list):
                            for valueitem in value:
                                if not valueitem in rtnvalue:
                                    rtn.config[key].append(valueitem)
                        else:
                            rtn.config[key] = value
                    else:
                        rtn.config[key] = value
        else:
            next_context_hop = other.context[len(rtn.context)]
            rtn_sub_config = Vyos13RouterConfig(rtn.context + [next_context_hop], {})
            if next_context_hop in rtn.config:
                rtn_sub_config.config = rtn.config[next_context_hop]
            merged_config = rtn_sub_config.merge(other, absolute)
            rtn.config[next_context_hop] = merged_config.config
                
        return rtn


class Vyos13Router(Router):
    '''
    A router based on VyOS 1.3 (using the HTTP API).
    '''

    def __init__(self, endpoint: str, api_key: str, verify: Union[str, bool]):
        self.endpoint = endpoint
        self.api_key = api_key
        self.verify = verify


    def getName(self) -> str:
        raise NotImplementedError()
    
    
    @staticmethod
    def getType() -> str:
        return 'vyos13'


    @staticmethod
    def isCompatibleToConfig(config: RouterConfig) -> bool:
        return (config.getType() == 'vyos13config')
    
    
    def getConfig(self) -> Vyos13RouterConfig:
        try:
            response = requests.post(self.endpoint + '/retrieve', {'data': json.dumps({'op': 'showConfig', 'path':[]}), 'key': self.api_key }, verify = self.verify)
            response.raise_for_status()
            r = response.json()
            if not 'success' in r or not r['success']:
                message = 'Retrieving config failed with unknown reason, answer: %s' % (json.dumps(r))
                if 'error' in r:
                    message = 'Retrieving config failed with error: %s' % (r['error'])
                raise Exception(message)
            if not 'data' in r:
                raise Exception('Configuration is missing when retrieving it from router')
            
            return Vyos13RouterConfig([], r['data'])
        except Exception as e:
            raise RouterCommunicationError("Communication failed while retrieving configuration") from e
    
    
    def putConfig(self, config: RouterConfig):
        if not self.isCompatibleToConfig(config) or not isinstance(config, Vyos13RouterConfig):
            raise RouterConfigError('Configuration is not compatible to this router')
        current_config = self.getConfig()
        logger.debug('Current config of router: %s', str(current_config.config))
        current_sub_config = None
        try:
            current_sub_config = current_config.getSubConfig(config.getContext())
        except ValueError:
            current_sub_config = Vyos13RouterConfig(config.getContext(), {})
        
        config_diff_to_apply = current_sub_config.diff(config)
        if not isinstance(config_diff_to_apply, Vyos13RouterConfigDiff) and not config_diff_to_apply.isEmpty():
            raise RouterConfigError('It was not possible to build a diff between active and wanted configuration, can\'t apply')
        logger.debug('Diff: %s', config_diff_to_apply)
        commands = config_diff_to_apply.genApiCommands()
        logger.debug('Commands to apply: %s', str(commands))

        try:
            response = requests.post(self.endpoint + '/configure', {'data': json.dumps(commands), 'key': self.api_key}, verify = self.verify)
            r = None
            try:
                r = response.json()
            except requests.exceptions.JSONDecodeError as jde:
                message = 'Could not decode answer, assuming an error.'
                logger.warning('requests.exceptions.JSONDecodeError occured on "%s"', response.content)
                raise Exception(message)
            if not 'success' in r or not r['success'] or response.status_code < 200 or response.status_code >= 300:
                message = 'Setting configuation failed with unknown reason, answer: %s' % (json.dumps(r))
                if 'error' in r and len(r['error']) > 0:
                    message = 'Router failed while setting configuration with error: %s' % (r['error'])
                raise Exception(message)
        except Exception as e:
            raise RouterCommunicationError("Communication failed while setting configuration") from e