# -*- coding: utf-8 -*-
"""
    tornadio2.persistent
    ~~~~~~~~~~~~~~~~~~~~

    Persistent transport implementations.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import logging

import tornado
from tornado.websocket import WebSocketHandler


class TornadioWebSocketHandler(WebSocketHandler):
    # Transport name
    name = 'websocket'

    """Websocket protocol handler"""
    def initialize(self, server):
        self.server = server

        logging.debug('Initializing %s handler.' % self.name)

    def open(self, session_id):
        self.session = self.server.get_session(session_id)
        if self.session is None:
            raise tornado.HTTPError(404, "Invalid Session")

        self.session.set_handler(self)
        self.session.reset_heartbeat()

        # Flush messages, if any
        self.session.flush()

    def _detach(self):
        if self.session is not None:
            self.session.stop_heartbeat()
            self.session.remove_handler(self)

            self.session = None

    def on_message(self, message):
        try:
            self.session.raw_message(message)
        except Exception:
            # Close session on exception
            self.session.close()

    def on_close(self):
        self._detach()

    def send_messages(self, messages):
        for m in messages:
            self.write_message(m)

    def session_closed(self):
        try:
            self.close()
        except Exception:
            logging.debug('Exception', exc_info=True)
        finally:
            self._detach()


class TornadioFlashSocketHandler(WebSocketHandler):
    # Transport name
    name = 'flashsocket'
