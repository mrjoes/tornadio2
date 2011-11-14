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
    tornadio2.server
    ~~~~~~~~~~~~~~~~

    Implements handy wrapper to start FlashSocket server (if FlashSocket
    protocol is enabled). Shamesly borrowed from the SocketTornad.IO project.
"""

import logging

from tornado import ioloop
from tornado.httpserver import HTTPServer

from tornadio2.flashserver import FlashPolicyServer


class SocketServer(HTTPServer):
    """HTTP Server which does some configuration and automatic setup
    of Socket.IO based on configuration.
    Starts the IOLoop and listening automatically
    in contrast to the Tornado default behavior.
    If FlashSocket is enabled, starts up the policy server also."""

    def __init__(self, application,
                 no_keep_alive=False, io_loop=None,
                 xheaders=False, ssl_options=None,
                 auto_start=True
                 ):
        """Initializes the server with the given request callback.

        If you use pre-forking/start() instead of the listen() method to
        start your server, you should not pass an IOLoop instance to this
        constructor. Each pre-forked child process will create its own
        IOLoop instance after the forking process.

        `application`
            Tornado application
        `no_keep_alive`
            Support keep alive for HTTP connections or not
        `io_loop`
            Optional io_loop instance.
        `xheaders`
            Extra headers
        `ssl_options`
            Tornado SSL options
        `auto_start`
            Set auto_start to False in order to have opportunities
            to work with server object and/or perform some actions
            after server is already created but before ioloop will start.
            Attention: if you use auto_start param set to False
            you should start ioloop manually
        """
        settings = application.settings

        flash_policy_file = settings.get('flash_policy_file', None)
        flash_policy_port = settings.get('flash_policy_port', None)
        socket_io_port = settings.get('socket_io_port', 8001)
        socket_io_address = settings.get('socket_io_address', '')

        io_loop = io_loop or ioloop.IOLoop.instance()

        HTTPServer.__init__(self,
                            application,
                            no_keep_alive,
                            io_loop,
                            xheaders,
                            ssl_options)

        logging.info('Starting up tornadio server on port \'%s\'',
                     socket_io_port)

        self.listen(socket_io_port, socket_io_address)

        if flash_policy_file is not None and flash_policy_port is not None:
            try:
                logging.info('Starting Flash policy server on port \'%d\'',
                             flash_policy_port)

                FlashPolicyServer(
                    io_loop=io_loop,
                    port=flash_policy_port,
                    policy_file=flash_policy_file)
            except Exception, ex:
                logging.error('Failed to start Flash policy server: %s', ex)

        if auto_start:
            logging.info('Entering IOLoop...')
            io_loop.start()
