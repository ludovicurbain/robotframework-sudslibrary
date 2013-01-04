# Copyright 2012 Kevin Ormbrek
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import urllib
from suds.xsd.doctor import ImportDoctor
from suds.transport.http import HttpAuthenticated
from urlparse import urlparse
from suds.client import Client
from .utils import *


class _ClientManagementKeywords(object):

    def create_client(self, url_or_path, alias=None, autoblend=False):
        """Loads the WSDL from the given URL or path and creates a Suds client.

        Returns the index of this client instance which can be used later to
        switch back to it. See `Switch Client` for example.

        Optional alias is an alias for the client instance and it can be used
        for switching between clients (just as index can be used). See `Switch
        Client` for more details.
        
        Autoblend ensures that the schema(s) defined within the WSDL import 
        each other.

        | Create Client | http://localhost:8080/ws/Billing.asmx?WSDL |
        | Create Client | ${CURDIR}/../wsdls/tracking.wsdl |
        """
        url = self._get_url(url_or_path)
        autoblend = to_bool(autoblend)
        kwargs = {'autoblend': autoblend}
        imports = self._imports
        if imports:
            self._log_imports()
            kwargs['doctor'] = ImportDoctor(*imports)
        client = Client(url, **kwargs)
        return self._add_client(client, alias)

    def switch_client(self, index_or_alias):
        """Switches between clients using index or alias.

        Index is returned from `Create Client` and alias can be given to it.

        Example:
        | Create Client  | http://localhost:8080/Billing?wsdl   | Billing   |
        | Create Client  | http://localhost:8080/Marketing?wsdl | Marketing |
        | Call           | sendSpam                             |           |
        | Switch Client  | Billing                              | # alias   |
        | Call           | sendInvoices                         |           |
        | Switch Client  | 2                                    | # index   |

        Above example expects that there was no other clients created when
        creating the first one because it used index '1' when switching to it
        later. If you aren't sure about that you can store the index into
        a variable as below.

        | ${id} =            | Create Client  | ... |
        | # Do something ... |                |     |
        | Switch Client      | ${id}          |     |
        """
        client = self._cache.switch(index_or_alias)
        self._listener.log = self._logging_option[client]

    # PyAPI
    
    def _client(self):
        """Returns the current suds.client.Client instance."""
        return self._cache.current

    def _add_client(self, client, alias=None):
        """Puts a client into the cache and returns the index.
        
        The added client becomes the current one."""
        client.options.plugins.append(self._listener)
        client.set_options(faults=True)
        self._logger.info('Using WSDL at %s%s' % (client.wsdl.url, client))
        self._imports = []
        self._logging_option[client] = True
        return self._cache.register(client, alias)

    # private

    def _log_imports(self):
        if self._imports:
            msg = "Using Imports for ImportDoctor:"
            for imp in self._imports:
                msg += "\n   Namespace: '%s' Location: '%s'" % (imp.ns, imp.location)
                for ns in imp.filter.tns:
                    msg += "\n      Filtering for namespace '%s'" % ns
            self._logger.info(msg)

    def _get_url(self, url_or_path):
        if not len(urlparse(url_or_path).scheme) > 1:
            if not os.path.isfile(url_or_path):
                raise IOError("File '%s' not found." % url_or_path)
            url_or_path = 'file:' + urllib.pathname2url(url_or_path)
        return url_or_path