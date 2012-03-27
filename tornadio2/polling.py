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
    tornadio2.polling
    ~~~~~~~~~~~~~~~~~

    This module implements socket.io polling transports.
"""
import time
import logging
import urllib

from tornado.web import HTTPError, asynchronous

from tornadio2 import proto, preflight, stats


class TornadioPollingHandlerBase(preflight.PreflightHandler):
    """Polling handler base"""
    def initialize(self, server):
        self.server = server
        self.session = None

        logging.debug('Initializing %s transport.' % self.name)

    def _get_session(self, session_id):
        """Get session if exists and checks if session is closed.
        """
        # Get session
        session = self.server.get_session(session_id)

        # If session was not found, ignore it
        if session is None:
            raise HTTPError(401, 'Invalid session')

        # If session is closed, but there are some pending messages left - make sure to send them
        if session.is_closed and not session.send_queue:
            raise HTTPError(401, 'Invalid session')

        return session

    def _detach(self):
        """Detach from the session"""
        if self.session:
            if not self.server.settings['global_heartbeats']:
                self.session.stop_heartbeat()

            self.session.remove_handler(self)

            self.session = None

    @asynchronous
    def get(self, session_id):
        """Default GET handler."""
        raise NotImplementedError()

    def post(self, session_id):
        """Handle incoming POST request"""
        try:
            # Stats
            self.server.stats.connection_opened()

            # Get session
            self.session = self._get_session(session_id)

            # Can not send messages to closed session or if preflight() failed
            if self.session.is_closed or not self.preflight():
                raise HTTPError(401)

            # Grab body and decode it (socket.io always sends data in utf-8)
            data = self.request.body.decode('utf-8')

            # IE XDomainRequest support
            if data.startswith(u'data='):
                data = data[5:]

            # Process packets one by one
            packets = proto.decode_frames(data)

            # Tracking
            self.server.stats.on_packet_recv(len(packets))

            for p in packets:
                try:
                    self.session.raw_message(p)
                except Exception:
                    # Close session if something went wrong
                    self.session.close()

            self.set_header('Content-Type', 'text/plain; charset=UTF-8')
            self.finish()
        finally:
            self.server.stats.connection_closed()

    def check_xsrf_cookie(self):
        pass

    def send_messages(self, messages):
        """Called by the session when some data is available"""
        raise NotImplementedError()

    def session_closed(self):
        """Called by the session when it was closed"""
        self._detach()

    def on_connection_close(self):
        """Called by Tornado, when connection was closed"""
        self._detach()


class TornadioXHRPollingHandler(TornadioPollingHandlerBase):
    """xhr-polling transport implementation"""

    # Transport name
    name = 'xhr-polling'

    def initialize(self, server):
        super(TornadioXHRPollingHandler, self).initialize(server)

        self._timeout = None

        # TODO: Move me out, there's no need to read timeout for POST requests
        self._timeout_interval = self.server.settings['xhr_polling_timeout']

    @asynchronous
    def get(self, session_id):
        # Get session
        self.session = self._get_session(session_id)

        if not self.session.set_handler(self):
            # TODO: Error logging
            raise HTTPError(401)

        if not self.session.send_queue:
            self._bump_timeout()
        else:
            self.session.flush()

    def _stop_timeout(self):
        if self._timeout is not None:
            self.server.io_loop.remove_timeout(self._timeout)
            self._timeout = None

    def _bump_timeout(self):
        self._stop_timeout()

        self._timeout = self.server.io_loop.add_timeout(
                                time.time() + self._timeout_interval,
                                self._polling_timeout
                                )

    def _polling_timeout(self):
        try:
            self.send_messages([proto.noop()])
        except Exception:
            logging.debug('Exception', exc_info=True)
        finally:
            self._detach()

    def _detach(self):
        self._stop_timeout()

        super(TornadioXHRPollingHandler, self)._detach()

    def send_messages(self, messages):
        # Tracking
        self.server.stats.on_packet_sent(len(messages))

        # Encode multiple messages as UTF-8 string
        data = proto.encode_frames(messages)

        # Send data to client
        self.preflight()
        self.set_header('Content-Type', 'text/plain; charset=UTF-8')
        self.set_header('Content-Length', len(data))
        self.write(data)

        # Detach connection from session
        self._detach()

        # Close connection
        self.finish()

    def session_closed(self):
        try:
            self.finish()
        except Exception:
            logging.debug('Exception', exc_info=True)
        finally:
            self._detach()


class TornadioHtmlFileHandler(TornadioPollingHandlerBase):
    """IE HtmlFile protocol implementation.

    Uses hidden frame to stream data from the server in one connection.
    """
    # Transport name
    name = 'htmlfile'

    @asynchronous
    def get(self, session_id):
        # Get session
        self.session = self._get_session(session_id)

        if not self.session.set_handler(self):
            raise HTTPError(401)

        self.set_header('Content-Type', 'text/html; charset=UTF-8')
        self.set_header('Connection', 'keep-alive')
        self.write('<html><body><script>var _ = function (msg) { parent.s._(msg, document); };</script>' + (' ' * 174))
        self.flush()

        # Dump any queued messages
        self.session.flush()

        # If hearbeats were not started by `HandshakeHandler`, start them.
        if not self.server.settings['global_heartbeats']:
            self.session.reset_heartbeat()

    def send_messages(self, messages):
        # Tracking
        self.server.stats.on_packet_sent(len(messages))

        # Encode frames and send data
        data = proto.encode_frames(messages)

        self.write(
            '<script>_(%s);</script>' % proto.json_dumps(data)
            )
        self.flush()

        if not self.server.settings['global_heartbeats']:
            self.session.delay_heartbeat()

    def session_closed(self):
        try:
            self.finish()
        except Exception:
            logging.debug('Exception', exc_info=True)
        finally:
            self._detach()


class TornadioJSONPHandler(TornadioXHRPollingHandler):
    # Transport name
    name = 'jsonp'

    def initialize(self, server):
        self._index = None

        super(TornadioJSONPHandler, self).initialize(server)

    @asynchronous
    def get(self, session_id):
        self._index = self.get_argument('i', 0)

        super(TornadioJSONPHandler, self).get(session_id)

    def post(self, session_id):
        try:
            # Stats
            self.server.stats.connection_opened()

            # Get session
            self.session = self._get_session(session_id)

            # Can not send messages to closed session or if preflight() failed
            if self.session.is_closed or not self.preflight():
                raise HTTPError(401)

            # Socket.io always send data utf-8 encoded.
            data = self.request.body

            # IE XDomainRequest support
            if not data.startswith('d='):
                logging.error('Malformed JSONP POST request')
                raise HTTPError(403)

            # Grab data
            data = urllib.unquote_plus(data[2:]).decode('utf-8')

            # If starts with double quote, it is json encoded (socket.io workaround)
            if data.startswith(u'"'):
                data = proto.json_load(data)

            # Process packets one by one
            packets = proto.decode_frames(data)

            # Tracking
            self.server.stats.on_packet_recv(len(packets))

            for p in packets:
                try:
                    self.session.raw_message(p)
                except Exception:
                    # Close session if something went wrong
                    self.session.close()

            self.set_header('Content-Type', 'text/plain; charset=UTF-8')
            self.finish()
        finally:
            self.server.stats.connection_closed()

    def send_messages(self, messages):
        if self._index is None:
            raise HTTPError(401)

        # Tracking
        self.server.stats.on_packet_sent(len(messages))

        data = proto.encode_frames(messages)

        message = 'io.j[%s](%s);' % (
            self._index,
            proto.json_dumps(data)
            )

        self.preflight()
        self.set_header('Content-Type', 'text/javascript; charset=UTF-8')
        self.set_header('Content-Length', len(message))
        self.set_header('X-XSS-Protection', '0')
        self.set_header('Connection', 'Keep-Alive')
        self.write(message)

        self._detach()

        self.finish()
