# -*- coding: utf-8 -*-
"""
    tornadio2.router
    ~~~~~~~~~~~~~~~~

    Transport protocol router and main entry point for all socket.io clients.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import logging

from tornado import ioloop
from tornado.web import RequestHandler, HTTPError

from tornadio2 import conn, persistent, polling, session

PROTOCOLS = {
    'websocket': persistent.TornadioWebSocketHandler,
    'flashsocket': persistent.TornadioFlashSocketHandler,
    #'xhr-polling': polling.TornadioXHRPollingSocketHandler,
    #'xhr-multipart': polling.TornadioXHRMultipartSocketHandler,
    #'htmlfile': polling.TornadioHtmlFileSocketHandler,
    #'jsonp-polling': polling.TornadioJSONPSocketHandler,
    }

DEFAULT_SETTINGS = {
    # Sessions check interval in seconds
    'session_check_interval': 15,
    # Session expiration in seconds
    'session_expiry': 30,
    # Heartbeat time in seconds. Do not change this value unless
    # you absolutely sure that new value will work.
    'heartbeat_interval': 12,
    # Enabled protocols
    #'enabled_protocols': ['websocket', 'flashsocket', 'xhr-multipart',
    #                      'xhr-polling', 'jsonp-polling', 'htmlfile'],
    'enabled_protocols': ['websocket', 'flashsocket'],
    # XHR-Polling request timeout, in seconds
    'xhr_polling_timeout': 20,
    }


class HandshakeHandler(RequestHandler):
    def initialize(self, server):
        self.server = server

    def get(self, version):
        v = int(version)

        # Only version 1 is supported now
        if v != 1:
            raise HTTPError(503, "Invalid socket.io protocol version")

        session = self.server.create_session()

        # TODO: Support for heartbeat and close timeouts
        return '%s::%s' % (
            session.session_id,
            ','.join(t for t in self.server.settings.get('enabled_protocols'))
            )

class TornadioServer(object):
    def __init__(connection, user_settings, namespace='socket.io', io_loop=None):
        # Store connection class
        self._connection = connection

        # Initialize io_loop
        self.io_loop = io_loop or ioloop.IOLoop.instance()

        # Settings
        self.settings = DEFAULT_SETTINGS.copy()
        if user_settings:
            settings.update(user_settings)

        # Session
        self._sessions = session.SessionContainer()

        # Initialize transports
        self._transport_urls = [
            (r'/%s/(\d*)/$', HandshakeHandler, dict(server=self))
            ]

        for t in self.settings.get('enabled_protocols', dict()):
            proto = PROTOCOLS.get(t)

            if not proto:
                # TODO: Error logging
                continue

            self._transport_urls.append(
                (r'/%s/(\d*)/%s/([^/]+)/', proto, dict(server=self))
                )

    @property
    def urls(self):
        return self._transport_urls

    def create_session(self):
        # TODO: Possible optimization here for settings.get
        conn = ConnectionSession(self._connection,
                                 self.io_loop,
                                 None,
                                 self.settings.get('session_expiry')
                                 )

        self._sessions.add(conn)

        return conn

