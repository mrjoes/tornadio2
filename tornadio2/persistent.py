# -*- coding: utf-8 -*-
"""
    tornadio.persistent
    ~~~~~~~~~~~~~~~~~~~

    Persistent transport implementations.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import logging

import tornado
from tornado.websocket import WebSocketHandler


class TornadioWebSocketHandler(WebSocketHandler):
    def initialize(self, server):
        logging.debug('Initializing WebSocket handler...')

        self.server = server

    def open(self, session_id):
        self.session = self.server.get_session(session_id)
        if self.session is None:
            raise tornado.HTTPError(404, "Invalid Session")

        self.session.set_handler(self)
        self.session.reset_heartbeat()

        # Flush messages, if any
        self.session.flush()

    def on_message(self, message):
        try:
            self.session.raw_message(message)
        except Exception:
            # Close session on exception
            self.session.close()            

    def on_close(self):
        if self.session is not None:
            self.session.stop_heartbeat()
            self.session.remove_handler(self)

    def send_messages(self, messages):
        for m in messages:
            self.write_message(m)


class TornadioFlashSocketHandler(WebSocketHandler):
    def initialize(self, server):
        logging.debug('Initializing FlashSocket handler...')

        super(TornadioFlashSocketHandler, self).initialize(server)
