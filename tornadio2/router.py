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
    tornadio2.router
    ~~~~~~~~~~~~~~~~

    Transport protocol router and main entry point for all socket.io clients.
"""

from tornado import ioloop, version_info
from tornado.web import HTTPError

from tornadio2 import persistent, polling, sessioncontainer, session, proto, preflight, stats

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
    # Some antivirus software messed up with HTTP traffic and, as a result, websockets
    # to port 80 stop to work. If you enable this setting, TornadIO will try to send
    # ping packet and wait for response. If nothing will happen during 5 seconds,
    # TornadIO considers connection not working.
    'websocket_check': False,
    # Starting from socket.io 0.9.2, client started verifying heartbeats for all transports.
    # Disable this if you're on 0.9.1 or lower, as this settings will significantly increase
    # your server load for clients with polling transports.
    'global_heartbeats': True,
    # Client timeout adjustment in seconds. If you see your clients disconnect without a
    # reason, increase this value.
    'client_timeout': 5
    }


class HandshakeHandler(preflight.PreflightHandler):
    """socket.io handshake handler"""

    def initialize(self, server):
        self.server = server

    def get(self, version, *args, **kwargs):
        try:
            self.server.stats.connection_opened()

            # Only version 1 is supported now
            if version != '1':
                raise HTTPError(503, "Invalid socket.io protocol version")

            sess = self.server.create_session(self.request)

            settings = self.server.settings

            # TODO: Fix heartbeat timeout. For now, it is adding 5 seconds to the client timeout.
            data = '%s:%d:%d:%s' % (
                sess.session_id,
                # TODO: Fix me somehow a well. 0.9.2 will drop connection is no
                # heartbeat was sent over
                settings['heartbeat_interval'] + settings['client_timeout'],
                # TODO: Fix me somehow.
                settings['xhr_polling_timeout'] + settings['client_timeout'],
                ','.join(t for t in self.server.settings.get('enabled_protocols'))
                )

            if self.server.settings['global_heartbeats']:
                sess.reset_heartbeat()

            jsonp = self.get_argument('jsonp', None)
            if jsonp is not None:
                self.set_header('Content-Type', 'application/javascript; charset=UTF-8')

                data = 'io.j[%s](%s);' % (jsonp, proto.json_dumps(data))
            else:
                self.set_header('Content-Type', 'text/plain; charset=UTF-8')

            self.preflight()

            self.write(data)
            self.finish()
        finally:
            self.server.stats.connection_closed()


class TornadioRouter(object):
    """TornadIO2 router implementation"""

    def __init__(self,
                 connection,
                 user_settings=dict(),
                 namespace='socket.io',
                 io_loop=None):
        """Constructor.

        `connection`
            SocketConnection class instance
        `user_settings`
            Settings
        `namespace`
            Router namespace, defaulted to 'socket.io'
        `io_loop`
            IOLoop instance, optional.
        """

        # TODO: Version check
        if version_info[0] < 2:
            raise Exception('TornadIO2 requires Tornado 2.0 or higher.')

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

        check_interval = self.settings['session_check_interval'] * 1000
        self._sessions_cleanup = ioloop.PeriodicCallback(self._sessions.expire,
                                                         check_interval,
                                                         self.io_loop)
        self._sessions_cleanup.start()

        # Stats
        self.stats = stats.StatsCollector()
        self.stats.start(self.io_loop)

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
        """List of the URLs to be added to the Tornado application"""
        return self._transport_urls

    def apply_routes(self, routes):
        """Feed list of the URLs to the routes list. Returns list"""
        routes.extend(self._transport_urls)
        return routes

    def create_session(self, request):
        """Creates new session object and returns it.

        `request`
            Request that created the session. Will be used to get query string
            parameters and cookies.
        """
        # TODO: Possible optimization here for settings.get
        s = session.Session(self._connection,
                            self,
                            request,
                            self.settings.get('session_expiry')
                            )

        self._sessions.add(s)

        return s

    def get_session(self, session_id):
        """Get session by session id
        """
        return self._sessions.get(session_id)
