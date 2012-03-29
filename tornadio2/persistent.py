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
    tornadio2.persistent
    ~~~~~~~~~~~~~~~~~~~~

    Persistent transport implementations.
"""
import logging
import time
import traceback

import tornado
from tornado.web import HTTPError
from tornado import stack_context
from tornado.websocket import WebSocketHandler

from tornadio2 import proto


class TornadioWebSocketHandler(WebSocketHandler):
    """Websocket protocol handler"""

    # Transport name
    name = 'websocket'

    def initialize(self, server):
        self.server = server
        self.session = None

        self._is_active = not self.server.settings['websocket_check']
        self._global_heartbeats = self.server.settings['global_heartbeats']

        logging.debug('Initializing %s handler.' % self.name)

    # Additional verification of the websocket handshake
    # For now it will stay here, till https://github.com/facebook/tornado/pull/415
    # is merged.
    def _execute(self, transforms, *args, **kwargs):
        with stack_context.ExceptionStackContext(self._handle_websocket_exception):
            # Websocket only supports GET method
            if self.request.method != 'GET':
                self.stream.write(tornado.escape.utf8(
                    "HTTP/1.1 405 Method Not Allowed\r\n\r\n"
                ))
                self.stream.close()
                return

            # Upgrade header should be present and should be equal to WebSocket
            if self.request.headers.get("Upgrade", "").lower() != 'websocket':
                self.stream.write(tornado.escape.utf8(
                    "HTTP/1.1 400 Bad Request\r\n\r\n"
                    "Can \"Upgrade\" only to \"WebSocket\"."
                ))
                self.stream.close()
                return

            # Connection header should be upgrade. Some proxy servers/load balancers
            # might mess with it.
            if self.request.headers.get("Connection", "").lower().find('upgrade') == -1:
                self.stream.write(tornado.escape.utf8(
                    "HTTP/1.1 400 Bad Request\r\n\r\n"
                    "\"Connection\" must be \"Upgrade\"."
                ))
                self.stream.close()
                return

            super(TornadioWebSocketHandler, self)._execute(transforms, *args, **kwargs)

    def open(self, session_id):
        """WebSocket open handler"""
        self.session = self.server.get_session(session_id)
        if self.session is None:
            raise HTTPError(401, "Invalid Session")

        if not self._is_active:
            # Need to check if websocket connection was really established by sending hearbeat packet
            # and waiting for response
            self.write_message(proto.heartbeat())
            self.server.io_loop.add_timeout(time.time() + self.server.settings['client_timeout'],
                                            self._connection_check)
        else:
            # Associate session handler
            self.session.set_handler(self)
            self.session.reset_heartbeat()

            # Flush messages, if any
            self.session.flush()

    def _connection_check(self):
        if not self._is_active:
            self._detach()

            try:
                # Might throw exception if connection was closed already
                self.close()
            except:
                pass

    def _detach(self):
        if self.session is not None:
            if self._is_active:
                self.session.stop_heartbeat()
                self.session.remove_handler(self)

            self.session = None

    def on_message(self, message):
        # Tracking
        self.server.stats.on_packet_recv(1)

        # Fix for late messages (after connection was closed)
        if not self.session:
            return

        # Mark that connection is active and flush any pending messages
        if not self._is_active:
            # Associate session handler and flush queued messages
            self.session.set_handler(self)
            self.session.reset_heartbeat()
            self.session.flush()

            self._is_active = True

        if not self._global_heartbeats:
            self.session.delay_heartbeat()

        try:
            self.session.raw_message(message)
        except Exception, ex:
            logging.error('Failed to handle message: ' + traceback.format_exc(ex))

            # Close session on exception
            if self.session is not None:
                self.session.close()

    def on_close(self):
        self._detach()

    def send_messages(self, messages):
        # Tracking
        self.server.stats.on_packet_sent(len(messages))

        try:
            for m in messages:
                self.write_message(m)
        except IOError:
            if self.ws_connection and self.ws_connection.client_terminated:
                logging.debug('Dropping active websocket connection due to IOError.')

            self._detach()

    def session_closed(self):
        try:
            self.close()
        except Exception:
            logging.debug('Exception', exc_info=True)
        finally:
            self._detach()

    def _handle_websocket_exception(self, type, value, traceback):
        if type is IOError:
            self.server.io_loop.add_callback(self.on_connection_close)

            # raise (type, value, traceback)
            logging.debug('Exception', exc_info=(type, value, traceback))
            return True

    # Websocket overrides
    def allow_draft76(self):
        return True


class TornadioFlashSocketHandler(TornadioWebSocketHandler):
    # Transport name
    name = 'flashsocket'
