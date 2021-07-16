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

from abc import ABC, abstractmethod, abstractstaticmethod


class RouterCommunicationError(Exception):
    '''Describes an error while communicating with a router'''
    def __init__(self, message):
        self.message = message


class RouterConfigError(Exception):
    '''Describes an error while configuring a router'''

class RouterConfigDiff(ABC):
    '''
    (abstract)
    A diff between two configs.
    '''
    @abstractmethod
    def displayString(self) -> str:
        '''
        creates a string for displaying a diff.
        '''
        raise NotImplementedError()

    @abstractmethod
    def isEmpty(self) -> bool:
        '''
        Checks, if a diff is empty and both sides are identical.
        '''
        raise NotImplementedError()


class RouterConfig(ABC):
    '''
    A configuration of a router.
    '''
    @abstractmethod
    def diff(self, other) -> RouterConfigDiff:
        '''
        Create a diff with another `RouterConfig`, if possible.

        params:
            other: RouterConfig to diff with

        returns: A `RouterConfigDiff` created from this and the other config.
        '''
        raise NotImplementedError()
    
    
    @staticmethod
    @abstractmethod
    def getType() -> str:
        '''
        returns the type of configuration.
        '''
        raise NotImplementedError()

    @abstractmethod
    def merge(self, other, absolute: bool):
        '''
        Merges another configuration into this one, if possible.

        params:
            other: another `RouterConfig` to merge into this one.
            absolute: wheter to replace the part handled in the other config completely. This can
                      be used to remove also parts of the configuration.

        rtn: The merges `RouterConfig`.
        '''
        raise NotImplementedError()


class Router(ABC):
    '''
    Represents a router.
    '''

    @abstractmethod
    def getName(self) -> str:
        '''
        Returns the name of the router.
        '''
        raise NotImplementedError()
    
    
    @staticmethod
    @abstractmethod
    def getType() -> str:
        '''
        Returns the type of the router.
        '''
        raise NotImplementedError()


    @staticmethod
    @abstractmethod
    def isCompatibleToConfig(config: RouterConfig) -> bool:
        '''
        Checks, whether given config is compatible with this router by type.
        '''
        raise NotImplementedError()
    
    
    @abstractmethod
    def getConfig(self) -> RouterConfig:
        '''
        Retrieves the current active configuration from the router.
        '''
        raise NotImplementedError()
    
    
    @abstractmethod
    def putConfig(self, config: RouterConfig):
        '''
        Activates the given configuration on this router.
        '''
        raise NotImplementedError()
