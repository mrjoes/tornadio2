# -*- coding: utf-8 -*-
"""
    tornadio2.conn
    ~~~~~~~~~~~~~~

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
from tornadio2 import session, proto, periodic


class SocketConnection(object):
    def __init__(self, session, endpoint=None):
        self.session = session
        self.endpoint = endpoint

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
        self.session.send_message(proto.message(self.endpoint, message))

    def emit(self, name, **kwargs):
        """Send socket.io event

        `name`
            Name of the event
        `kwargs`
            Optional event parameters
        """
        self.session.send_message(proto.event(self.endpoint, name, **kwargs))

    def close(self):
        """Forcibly close client connection"""
        self.session.close()


class ConnectionSession(session.Session):
    def __init__(self, conn, server, session_id=None, expiry=None):
        # Initialize session
        super(ConnectionSession, self).__init__(session_id, expiry)

        self.server = server
        self.send_queue = []
        self.handler = None

        self.last_message_id = 0

        # Create connection instance
        self.conn = conn(self)

        # Heartbeat related stuff
        self._heartbeat_timer = None
        self._heartbeat_interval = self.server.settings['heartbeat_interval'] * 1000
        self._missed_heartbeats = 0

    def open(self, *args, **kwargs):
        self.conn.on_open(*args, **kwargs)

    # Session callbacks
    def on_delete(self, forced):
        # Do not remove connection if it was not forced and there's running connection
        if not forced and self.handler is not None and not self.is_closed:
            self.promote()
        else:
            self.close()

        print 'Deleted'

    # Add session
    def set_handler(self, handler, *args, **kwargs):
        if self.handler is not None:
            # Attempted to override handler
            return False

        self.handler = handler
        self.promote()

        return True

    def remove_handler(self, handler):
        if self.handler != handler:
            raise Exception('Attempted to remove invalid handler')

        self.handler = None
        self.promote()

    def send_message(self, pack):
        self.send_queue.append(pack)
        self.flush()

    def flush(self):
        if self.handler is None:
            return

        if not self.send_queue:
            return

        self.handler.send_messages(self.send_queue)

        self.send_queue = []

    def close(self, endpoint=None):
        print 'Close'

        if not self.conn.is_closed:
            try:
                self.conn.on_close()
            finally:
                self.conn.is_closed = True

            # Send disconnection message
            self.send_message(proto.disconnect(endpoint))

    @property
    def is_closed(self):
        return self.conn.is_closed

    # Heartbeats
    def reset_heartbeat(self):
        self.stop_heartbeat()

        self._heartbeat_timer = periodic.Callback(self._heartbeat,
                                                  self._heartbeat_interval,
                                                  self.io_loop)
        self._heartbeat_timer.start()

    def stop_heartbeat(self):
        if self._heartbeat_timer is not None:
            self._heartbeat_timer.stop()
            self._heartbeat_timer = None

    def delay_heartbeat(self):
        if self._heartbeat_timer is not None:
            self._heartbeat_timer.delay()

    def _heartbeat(self):
        self.send_message(proto.heartbeat())

        self._missed_heartbeats += 1

        # TODO: Configurable
        if self._missed_heartbeats > 5:
            self.close()

    # Message handler
    def raw_message(self, msg):
        parts = msg.split(':')

        msg_type = parts[0]
        msg_id = parts[1]
        msg_endpoint = parts[2]
        msg_data = ':'.join(parts[3:])

        if msg_type == proto.DISCONNECT:
            self.close()
        elif msg_type == proto.CONNECT:
            self.send_message(proto.error('', 'Not supported', ''))
        elif msg_type == proto.HEARTBEAT:
            print 'HEARTBEAT'
            self._missed_heartbeats = 0
        elif msg_type == proto.MESSAGE:
            self.conn.on_message(msg_data)
        elif msg_type == proto.JSON:
            self.conn.on_message(proto.json_load(msg_data))
        elif msg_type == proto.EVENT:
            self.send_message(proto.error('', 'Not supported', ''))
        elif msg_type == proto.ACK:
            self.send_message(proto.error('', 'Not supported', ''))
        elif msg_type == proto.ERROR:
            self.send_message(proto.error('', 'Not supported', ''))
        elif msg_type == proto.NOOP:
            pass
