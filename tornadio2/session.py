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
    tornadio2.session
    ~~~~~~~~~~~~~~~~~

    Active TornadIO2 connection session.
"""

import urlparse
import logging

from tornado.web import HTTPError

from tornadio2 import sessioncontainer, proto, periodic, stats


class ConnectionInfo(object):
    """Connection information object.

    Will be passed to the ``on_open`` handler of your connection class.

    Has few properties:

    `ip`
        Caller IP address
    `cookies`
        Collection of cookies
    `arguments`
        Collection of the query string arguments
    """
    def __init__(self, ip, arguments, cookies):
        self.ip = ip
        self.cookies = cookies
        self.arguments = arguments

    def get_argument(self, name):
        """Return single argument by name"""
        val = self.arguments.get(name)
        if val:
            return val[0]
        return None

    def get_cookie(self, name):
        """Return single cookie by its name"""
        return self.cookies.get(name)


class Session(sessioncontainer.SessionBase):
    """Socket.IO session implementation.

    Session has some publicly accessible properties:

    `server`
        Server association. Server contains io_loop instance, settings, etc.
    `remote_ip`
        Remote IP
    `is_closed`
        Check if session is closed or not.
    """
    def __init__(self, conn, server, request, expiry=None):
        """Session constructor.

        `conn`
            Default connection class
        `server`
            Associated server
        `handler`
            Request handler that created new session
        `expiry`
            Session expiry
        """
        # Initialize session
        super(Session, self).__init__(None, expiry)

        self.server = server
        self.send_queue = []
        self.handler = None

        # Stats
        server.stats.session_opened()

        self.remote_ip = request.remote_ip

        # Create connection instance
        self.conn = conn(self)

        # Call on_open.
        self.info = ConnectionInfo(request.remote_ip,
                              request.arguments,
                              request.cookies)

        # If everything is fine - continue
        self.send_message(proto.connect())

        # Heartbeat related stuff
        self._heartbeat_timer = None
        self._heartbeat_interval = self.server.settings['heartbeat_interval'] * 1000
        self._missed_heartbeats = 0

        # Endpoints
        self.endpoints = dict()

        result = self.conn.on_open(self.info)
        if result is not None and not result:
            raise HTTPError(401)

    # Session callbacks
    def on_delete(self, forced):
        """Session expiration callback

        `forced`
            If session item explicitly deleted, forced will be set to True. If
            item expired, will be set to False.
        """
        # Do not remove connection if it was not forced and there's running connection
        if not forced and self.handler is not None and not self.is_closed:
            self.promote()
        else:
            self.close()

    # Add session
    def set_handler(self, handler):
        """Set active handler for the session

        `handler`
            Associate active Tornado handler with the session
        """
        # Check if session already has associated handler
        if self.handler is not None:
            return False

        # If IP address don't match - refuse connection
        if handler.request.remote_ip != self.remote_ip:
            logging.error('Attempted to attach to session %s (%s) from different IP (%s)' % (
                          self.session_id,
                          self.remote_ip,
                          handler.request.remote_ip
                          ))
            return False

        # Associate handler and promote
        self.handler = handler
        self.promote()

        # Stats
        self.server.stats.connection_opened()

        return True

    def remove_handler(self, handler):
        """Remove active handler from the session

        `handler`
            Handler to remove
        """
        # Attempt to remove another handler
        if self.handler != handler:
            raise Exception('Attempted to remove invalid handler')

        self.handler = None
        self.promote()

        self.server.stats.connection_closed()

    def send_message(self, pack):
        """Send socket.io encoded message

        `pack`
            Encoded socket.io message
        """
        logging.debug('<<< ' + pack)

        # TODO: Possible optimization if there's on-going connection - there's no
        # need to queue messages?

        self.send_queue.append(pack)
        self.flush()

    def flush(self):
        """Flush message queue if there's an active connection running"""
        if self.handler is None:
            return

        if not self.send_queue:
            return

        self.handler.send_messages(self.send_queue)

        self.send_queue = []

        # If session was closed, detach connection
        if self.is_closed and self.handler is not None:
            self.handler.session_closed()

    # Close connection with all endpoints or just one endpoint
    def close(self, endpoint=None):
        """Close session or endpoint connection.

        `endpoint`
            If endpoint is passed, will close open endpoint connection. Otherwise
            will close whole socket.
        """
        if endpoint is None:
            if not self.conn.is_closed:
                # Close child connections
                for k in self.endpoints.keys():
                    self.disconnect_endpoint(k)

                # Close parent connections
                try:
                    self.conn.on_close()
                finally:
                    self.conn.is_closed = True

                    # Stats
                    self.server.stats.session_closed()

                # Stop heartbeats
                self.stop_heartbeat()

                # Send disconnection message
                self.send_message(proto.disconnect())

                # Notify transport that session was closed
                if self.handler is not None:
                    self.handler.session_closed()
        else:
            # Disconnect endpoint
            self.disconnect_endpoint(endpoint)

    @property
    def is_closed(self):
        """Check if session was closed"""
        return self.conn.is_closed

    # Heartbeats
    def reset_heartbeat(self):
        """Reset hearbeat timer"""
        self.stop_heartbeat()

        self._heartbeat_timer = periodic.Callback(self._heartbeat,
                                                  self._heartbeat_interval,
                                                  self.server.io_loop)
        self._heartbeat_timer.start()

    def stop_heartbeat(self):
        """Stop active heartbeat"""
        if self._heartbeat_timer is not None:
            self._heartbeat_timer.stop()
            self._heartbeat_timer = None

    def delay_heartbeat(self):
        """Delay active heartbeat"""
        if self._heartbeat_timer is not None:
            self._heartbeat_timer.delay()

    def _heartbeat(self):
        """Heartbeat callback"""
        self.send_message(proto.heartbeat())

        self._missed_heartbeats += 1

        # TODO: Configurable
        if self._missed_heartbeats > 2:
            self.close()

    # Endpoints
    def connect_endpoint(self, url):
        """Connect endpoint from URL.

        `url`
            socket.io endpoint URL.
        """
        urldata = urlparse.urlparse(url)

        endpoint = urldata.path

        conn = self.endpoints.get(endpoint, None)
        if conn is None:
            conn_class = self.conn.get_endpoint(endpoint)
            if conn_class is None:
                logging.error('There is no handler for endpoint %s' % endpoint)
                return

            conn = conn_class(self, endpoint)
            self.endpoints[endpoint] = conn

        self.send_message(proto.connect(endpoint))

        if conn.on_open(self.info) == False:
            self.disconnect_endpoint(endpoint)

    def disconnect_endpoint(self, endpoint):
        """Disconnect endpoint

        `endpoint`
            endpoint name
        """
        if endpoint not in self.endpoints:
            logging.error('Invalid endpoint for disconnect %s' % endpoint)
            return

        conn = self.endpoints[endpoint]

        del self.endpoints[endpoint]

        conn.on_close()
        self.send_message(proto.disconnect(endpoint))

    def get_connection(self, endpoint):
        """Get connection object.

        `endpoint`
            Endpoint name. If set to None, will return default connection object.
        """
        if endpoint:
            return self.endpoints.get(endpoint)
        else:
            return self.conn

    # Message handler
    def raw_message(self, msg):
        """Socket.IO message handler.

        `msg`
            Raw socket.io message to handle
        """
        try:
            logging.debug('>>> ' + msg)

            parts = msg.split(':', 3)
            if len(parts) == 3:
                msg_type, msg_id, msg_endpoint = parts
                msg_data = None
            else:
                msg_type, msg_id, msg_endpoint, msg_data = parts

            # Packets that don't require valid endpoint
            if msg_type == proto.DISCONNECT:
                if not msg_endpoint:
                    self.close()
                else:
                    self.disconnect_endpoint(msg_endpoint)
                return
            elif msg_type == proto.CONNECT:
                if msg_endpoint:
                    self.connect_endpoint(msg_endpoint)
                else:
                    # TODO: Disconnect?
                    logging.error('Invalid connect without endpoint')
                return

            # All other packets need endpoints
            conn = self.get_connection(msg_endpoint)
            if conn is None:
                logging.error('Invalid endpoint: %s' % msg_endpoint)
                return

            if msg_type == proto.HEARTBEAT:
                self._missed_heartbeats = 0
            elif msg_type == proto.MESSAGE:
                # Handle text message
                conn.on_message(msg_data)

                if msg_id:
                    self.send_message(proto.ack(msg_endpoint, msg_id))
            elif msg_type == proto.JSON:
                # Handle json message
                conn.on_message(proto.json_load(msg_data))

                if msg_id:
                    self.send_message(proto.ack(msg_endpoint, msg_id))
            elif msg_type == proto.EVENT:
                # Javascript event
                event = proto.json_load(msg_data)

                # TODO: Verify if args = event.get('args', []) won't be slower.
                args = event.get('args')
                if args is None:
                    args = []

                ack_response = None

                # It is kind of magic - if there's only one parameter
                # and it is dict, unpack dictionary. Otherwise, pass
                # in args
                if len(args) == 1 and isinstance(args[0], dict):
                    # Fix for the http://bugs.python.org/issue4978 for older Python versions
                    str_args = dict((str(x), y) for x, y in args[0].iteritems())

                    ack_response = conn.on_event(event['name'], kwargs=str_args)
                else:
                    ack_response = conn.on_event(event['name'], args=args)

                if msg_id:
                    if msg_id.endswith('+'):
                        msg_id = msg_id[:-1]

                    self.send_message(proto.ack(msg_endpoint, msg_id, ack_response))
            elif msg_type == proto.ACK:
                # Handle ACK
                ack_data = msg_data.split('+', 2)

                data = None
                if len(ack_data) > 1:
                    data = proto.json_load(ack_data[1])

                conn.deque_ack(int(ack_data[0]), data)
            elif msg_type == proto.ERROR:
                # TODO: Pass it to handler?
                logging.error('Incoming error: %s' % msg_data)
            elif msg_type == proto.NOOP:
                pass
        except Exception, ex:
            logging.exception(ex)

            # TODO: Add global exception callback?

            raise
