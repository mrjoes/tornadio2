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
        """Forcibly close client connection"""
        self.session.close()

class ConnectionSession(session.Session):
    def __init__(self, conn, io_loop, session_id=None, expiry=None):
        # Initialize session
        super(ConnectionSession, self).__init__(session_id, expiry)

        self.send_queue = []
        self.handler = None

        self.last_message_id = 0

        # Create connection instance
        self.conn = conn(self, io_loop)

    def open(self, *args, **kwargs):
        self.conn.on_open(*args, **kwargs)

    # Session callbacks
    def on_delete(self, forced):
        # Do not remove connection if it was not forced and there's running connection
        if not forced and self._handler is not None and not self.is_closed:
            self.promote()
        else:
            self.close()

    # Add session
    def set_handler(self, handler, *args, **kwargs):
        if self.handler is not None:
            raise Exception('Attempted to overwrite handler')

        self.handler = handler
        self.promote()

        return True

    def remove_handler(self, handler):
        if self.handler != handler:
            raise Exception('Attempted to remove invalid handler')

        self.handler = None
        self.promote()

    def send(self, endpoint, msg):
        self.raw_send(proto.message(endpoint, msg))

    def raw_send(self, pack):
        self.send_queue.append(pack)
        self.flush()

    def flush(self):
        if self.handler is None:
            return

        if not self.send_queue:
            return

        self.handler.raw_send(self.send_queue)

        self.send_queue = []

    def close(self, endpoint=None):
        if not self.conn.is_closed:
            try:
                self.conn.on_close()
            finally:
                self.conn.is_closed = True

            # Send disconnection message
            self.raw_send(proto.disconnect(endpoint))

    @property
    def is_closed(self):
        return self.conn.is_closed

    def raw_message(self, msg):
        parts = msg.split(':')

        msg_type = parts[0]
        msg_id = parts[1]
        msg_endpoint = parts[2]
        msg_data = ':'.join(parts[3:])

        if msg_type == proto.DISCONNECT:
            self.close()
        elif msg_type == proto.CONNECT:
            self.raw_send(proto.error('', 'Not supported', ''))
        elif msg_type == proto.HEARTBEAT:
            self.raw_send(proto.error('', 'Not supported', ''))
        elif msg_type == proto.MESSAGE:
            self.conn.on_message(msg_data)
        elif msg_type == proto.JSON:
            self.conn.on_message(json.loads(msg_data))
        elif msg_type == proto.EVENT:
            self.raw_send(proto.error('', 'Not supported', ''))
        elif msg_type == proto.ACK:
            self.raw_send(proto.error('', 'Not supported', ''))
        elif msg_type == proto.ERROR:
            self.raw_send(proto.error('', 'Not supported', ''))
        elif msg_type == proto.NOOP:
            pass
