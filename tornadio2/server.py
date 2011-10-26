# -*- coding: utf-8 -*-
"""
    tornadio2.server
    ~~~~~~~~~~~~~~~~

    Implements handy wrapper to start FlashSocket server (if FlashSocket
    protocol is enabled). Shamesly borrowed from the SocketTornad.IO project.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
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

        # Set auto_start to False in order to have opportunities
        # to work with server object and/or perform some actions
        # after server is already created but before ioloop will start.
        # Attention: if you use auto_start param set to False
        # you should start ioloop manually
        if auto_start:
            logging.info('Entering IOLoop...')
            io_loop.start()
