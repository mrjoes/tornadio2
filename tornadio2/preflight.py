# -*- coding: utf-8 -*-
"""
    tornadio2.preflight
    ~~~~~~~~~~~~~~~~~~~

    Transport protocol router and main entry point for all socket.io clients.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
from tornado.web import RequestHandler, asynchronous


class PreflightHandler(RequestHandler):
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

                if 'Cookie' in self.request.headers:
                    self.set_header('Access-Control-Allow-Credentials', True)

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
