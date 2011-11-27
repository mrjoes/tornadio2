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

import tornado
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

        logging.debug('Initializing %s handler.' % self.name)

    def open(self, session_id):
        """WebSocket open handler"""
        self.session = self.server.get_session(session_id)
        if self.session is None:
            raise tornado.HTTPError(401, "Invalid Session")

        if not self._is_active:
            # Need to check if websocket connection was really established by sending hearbeat packet
            # and waiting for response
            self.write_message(proto.heartbeat())
            self.server.io_loop.add_timeout(time.time() + 5, self._connection_check)
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
            self.session.stop_heartbeat()
            self.session.remove_handler(self)

            self.session = None

    def on_message(self, message):
        # Tracking
        self.server.stats.on_packet_recv(1)

        # Mark that connection is active and flush any pending messages
        if not self._is_active:
            # Associate session handler and flush queued messages
            self.session.set_handler(self)
            self.session.reset_heartbeat()
            self.session.flush()

            self._is_active = True

        try:
            self.session.raw_message(message)
        except Exception:
            # Close session on exception
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
            if self.client_terminated:
                logging.debug('Dropping active websocket connection due to IOError.')

            self._detach()

    def session_closed(self):
        try:
            self.close()
        except Exception:
            logging.debug('Exception', exc_info=True)
        finally:
            self._detach()


class TornadioFlashSocketHandler(TornadioWebSocketHandler):
    # Transport name
    name = 'flashsocket'
