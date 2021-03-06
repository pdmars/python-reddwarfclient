# Copyright (c) 2011 OpenStack, LLC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import time
import urlparse

try:
    import json
except ImportError:
    import simplejson as json


from novaclient.client import HTTPClient
from novaclient.v1_1.client import Client

from reddwarfclient import exceptions

class ReddwarfHTTPClient(HTTPClient):
    """
    Class for overriding the HTTP authenticate call and making it specific to
    reddwarf
    """

    def __init__(self, user, apikey, tenant, auth_url, service_name,
                 service_type=None, service_url=None, timeout=None):
        super(ReddwarfHTTPClient, self).__init__(user, apikey, tenant,
                                                 auth_url,
                                                 service_type=service_type,
                                                 timeout=timeout)
        self.api_key = apikey
        self.tenant = tenant
        self.service = service_name
        self.management_url = service_url


    def _get_token(self, path, req_body):
        """Set the management url and auth token"""
        token_url = urlparse.urljoin(self.auth_url, path)
        resp, body = self.request(token_url, "POST", body=req_body)
        if 'access' in body:
            if not self.management_url:
                # Assume the new Keystone lite:
                catalog = body['access']['serviceCatalog']
                for service in catalog:
                    if service['name'] == self.service:
                        self.management_url = service['adminURL']
            self.auth_token = body['access']['token']['id']
        else:
            # Assume pre-Keystone Light:
            try:
                if not self.management_url:
                    self.management_url = body['auth']['serviceCatalog'] \
                                          [self.service][0]['publicURL']
                self.auth_token = body['auth']['token']['id']
            except KeyError:
                raise NotImplementedError("Service: %s is not available"
                                          % self.service)

    def request(self, *args, **kwargs):
        #TODO(tim.simpson): Copy and pasted from novaclient, since we raise
        # extra exception subclasses not raised there.
        kwargs.setdefault('headers', kwargs.get('headers', {}))
        kwargs['headers']['User-Agent'] = self.USER_AGENT
        kwargs['headers']['Accept'] = 'application/json'
        if 'body' in kwargs:
            kwargs['headers']['Content-Type'] = 'application/json'
            kwargs['body'] = json.dumps(kwargs['body'])

        resp, body = super(HTTPClient, self).request(*args, **kwargs)

        self.http_log(args, kwargs, resp, body)

        if body:
            try:
                body = json.loads(body)
            except ValueError:
                pass
        else:
            body = None

        if resp.status in (400, 401, 403, 404, 408, 409, 413, 500, 501):
            raise exceptions.from_response(resp, body)

        return resp, body


class Dbaas(Client):
    """
    Top-level object to access the Rackspace Database as a Service API.

    Create an instance with your creds::

        >>> red = Dbaas(USERNAME, API_KEY, TENANT, AUTH_URL, SERVICE_NAME,
                        SERVICE_URL)

    Then call methods on its managers::

        >>> red.instances.list()
        ...
        >>> red.flavors.list()
        ...

    &c.
    """

    def __init__(self, username, api_key, tenant=None, auth_url=None,
                 service_type='reddwarf', service_name='Reddwarf Service',
                 service_url=None):
        from reddwarfclient.versions import Versions
        from reddwarfclient.databases import Databases
        from reddwarfclient.flavors import Flavors
        from reddwarfclient.instances import Instances
        from reddwarfclient.users import Users
        from reddwarfclient.root import Root
        from reddwarfclient.hosts import Hosts
        from reddwarfclient.storage import StorageInfo
        from reddwarfclient.management import Management
        from reddwarfclient.accounts import Accounts
        from reddwarfclient.config import Configs
        from reddwarfclient.diagnostics import Interrogator

        super(Dbaas, self).__init__(self, username, api_key, tenant, auth_url)
        self.client = ReddwarfHTTPClient(username, api_key, tenant, auth_url,
                                         service_type=service_type,
                                         service_name=service_name,
                                         service_url=service_url)
        self.versions = Versions(self)
        self.databases = Databases(self)
        self.flavors = Flavors(self)
        self.instances = Instances(self)
        self.users = Users(self)
        self.root = Root(self)
        self.hosts = Hosts(self)
        self.storage = StorageInfo(self)
        self.management = Management(self)
        self.accounts = Accounts(self)
        self.configs = Configs(self)
        self.diagnostics = Interrogator(self)


