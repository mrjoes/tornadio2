# -*- coding: utf-8 -*-
#
# Copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
    tornadio2.preflight
    ~~~~~~~~~~~~~~~~~~~

    Transport protocol router and main entry point for all socket.io clients.
"""
from tornado.web import RequestHandler, asynchronous


class PreflightHandler(RequestHandler):
    """CORS preflight handler"""

    @asynchronous
    def options(self, *args, **kwargs):
        """XHR cross-domain OPTIONS handler"""
        self.preflight()
        self.finish()

    def preflight(self):
        """Handles request authentication"""
        if 'Origin' in self.request.headers:
            if self.verify_origin():
                self.set_header('Access-Control-Allow-Origin',
                                self.request.headers['Origin'])

                self.set_header('Access-Control-Allow-Credentials', 'true')
                self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

                return True
            else:
                return False
        else:
            return True

    def verify_origin(self):
        """Verify if request can be served"""
        # TODO: Verify origin
        return True
