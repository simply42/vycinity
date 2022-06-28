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

import base64
import binascii
from django.contrib.auth.hashers import check_password
import logging
import re
from rest_framework import authentication
from rest_framework import exceptions
from vycinity.models import customer_models

logger = logging.getLogger(__name__)
invalid_auth_chars = re.compile(r'[\x00-\x1F\x7F]')

class LocalUserAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        authorization = request.META.get("HTTP_AUTHORIZATION")
        if not authorization:
            return None
        authsplit = authorization.split(' ')
        if authsplit[0] != 'Basic' or len(authsplit) != 2:
            return None
        username = None
        password = None
        try:
            decoded_auth = base64.b64decode(authsplit[1], validate=True).decode('utf-8')
            if invalid_auth_chars.search(decoded_auth):
                logger.info('Authentifizierung enthält ungültige Zeichen')
                return None
            (username, password) = decoded_auth.split(':', 1)
            if password is None:
                logger.info('Passwort ist nicht gesetzt')
                return None
        except (binascii.Error, UnicodeDecodeError) as e:
            logger.info('Dekodieren von Authorization fehlgeschlagen', exc_info = e)
            return None

        user = None
        try:
            user = customer_models.User.objects.get(name = username)
        except customer_models.User.DoesNotExist:
            logger.debug('Nutzer "%s" existiert nicht', username)
            return None
        for localauth in user.localuserauth_set.all():
            if check_password(password, localauth.auth):
                return (user, localauth)
        
        raise exceptions.AuthenticationFailed('Authentication failed')

    def authenticate_header(self, request):
        return 'Basic realm="VyCinity User", charset="UTF-8"'