# -*- coding: utf-8 -*-
"""
    tornadio2.conn
    ~~~~~~~~~~~~~~

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import logging, time

from tornadio2 import session, proto

class SocketConnection(object):
    def __init__(self, session, io_loop, endpoint=None):
        self.session = session
        self.endpoint = endpoint
        self.io_loop = io_loop

        self.is_closed = False

    # Public API
    def on_open(self, *args, **kwargs):
        """Default on_open() handler"""
        pass

    def on_message(self, message):
        """Default on_message handler. Must be overridden"""
        raise NotImplementedError()

    def on_close(self):
        """Default on_close handler."""
        pass

    def send(self, message):
        """Send message to the client.

        `message`
            Message to send.
        """
        self.session.send(self.endpoint, message)

    def close(self):
        """Focibly close client connection"""
        self.session.close()

class ConnectionSession(session.Session):
    def __init__(self, conn, io_loop, session_id=None, expiry=None):
        # Initialize session
        super(SocketConnection, self).__init__(session_id, expiry)

        self.send_queue = []
        self.handler = None
        self.is_opened = False

        # Create connection instance
        self.conn = conn(io_loop)

    # Internal API
    # Session callbacks
    def on_delete(self, forced):
        if not forced and self._handler is not None and not self.is_closed:
            self.promote()
        else:
            self.close()

    def set_handler(self, handler, *args, **kwargs):
        if self.handler is not None:
            raise Exception('Attempted to overwrite handler')

        self.handler = handler
        self.promote()

        # Send any queued messages right away
        self.flush()

        if not self.is_opened:
            self.is_opened = True

            self.conn.on_open(*args, **kwargs)

    def remove_handler(self, handler):
        if self.handler != handler:
            raise Exception('Attempted to remove invalid handler')

        self.handler = None
        self.promote()

    def send(self, endpoint, msg):
        self.send_queue.append(proto.message(endpoint, msg))
        self.flush()

    def flush(self):
        if self.handler is None:
            return

        if not self.send_queue:
            return

        self.handler.send(msg)

        self.send_queue = []

    def close(self):
        if not self.conn.is_closed:
            try:
                self.conn.on_close()
            finally:
                self.conn.is_closed = True

