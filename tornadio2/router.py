# -*- coding: utf-8 -*-
"""
    tornadio2.router
    ~~~~~~~~~~~~~~~~

    Transport protocol router and main entry point for all socket.io clients.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
from tornado import ioloop
from tornado.web import RequestHandler, HTTPError

from tornadio2 import persistent, polling, sessioncontainer, session, proto

PROTOCOLS = {
    'websocket': persistent.TornadioWebSocketHandler,
    'flashsocket': persistent.TornadioFlashSocketHandler,
    'xhr-polling': polling.TornadioXHRPollingHandler,
    'htmlfile': polling.TornadioHtmlFileHandler,
    'jsonp-polling': polling.TornadioJSONPHandler,
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
    'enabled_protocols': ['websocket', 'flashsocket', 'xhr-polling', 
                          'jsonp-polling', 'htmlfile'],
    # XHR-Polling request timeout, in seconds
    'xhr_polling_timeout': 20,
    }


class HandshakeHandler(RequestHandler):
    def initialize(self, server):
        self.server = server

    def get(self, version, *args, **kwargs):
        # Only version 1 is supported now
        if version != '1':
            raise HTTPError(503, "Invalid socket.io protocol version")

        sess = self.server.create_session()

        # TODO: Support for heartbeat
        # TODO: Fix heartbeat timeout
        data = '%s:%d:%d:%s' % (
            sess.session_id,
            self.server.settings['heartbeat_interval'],
            # TODO: Fix me somehow.
            self.server.settings['xhr_polling_timeout'] + 3,
            ','.join(t for t in self.server.settings.get('enabled_protocols'))
            )

        jsonp = self.get_argument('jsonp', None)
        if jsonp is not None:
            self.set_header('Content-Type', 'application/javascript; charset=UTF-8')
            
            data = 'io.j[%s](%s);' % (jsonp, proto.json_dumps(data))
        else:
            self.set_header('Content-Type', 'text/plain; charset=UTF-8')
        
        self.write(data)
        self.finish()

        # Session is considered to be opened, according to docs
        sess.open(*args, **kwargs)


class TornadioServer(object):
    def __init__(self,
                 connection,
                 user_settings=dict(),
                 namespace='socket.io',
                 io_loop=None):
        # Store connection class
        self._connection = connection

        # Initialize io_loop
        self.io_loop = io_loop or ioloop.IOLoop.instance()

        # Settings
        self.settings = DEFAULT_SETTINGS.copy()
        if user_settings:
            self.settings.update(user_settings)

        # Sessions
        self._sessions = sessioncontainer.SessionContainer()

        check_interval = self.settings['session_check_interval']
        self._sessions_cleanup = ioloop.PeriodicCallback(self._sessions.expire,
                                                         check_interval,
                                                         self.io_loop)
        self._sessions_cleanup.start()

        # Initialize URLs
        self._transport_urls = [
            (r'/%s/(?P<version>\d+)/$' % namespace,
                HandshakeHandler,
                dict(server=self))
            ]

        for t in self.settings.get('enabled_protocols', dict()):
            proto = PROTOCOLS.get(t)

            if not proto:
                # TODO: Error logging
                continue

            # Only version 1 is supported
            self._transport_urls.append(
                (r'/%s/1/%s/(?P<session_id>[^/]+)/?' %
                    (namespace, t),
                    proto,
                    dict(server=self))
                )

    @property
    def urls(self):
        return self._transport_urls

    def create_session(self):
        # TODO: Possible optimization here for settings.get
        s = session.Session(self._connection,
                            self,
                            None,
                            self.settings.get('session_expiry')
                            )

        self._sessions.add(s)

        return s

    def get_session(self, session_id):
        return self._sessions.get(session_id)
