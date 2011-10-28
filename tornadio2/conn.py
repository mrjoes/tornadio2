# -*- coding: utf-8 -*-
"""
    tornadio2.conn
    ~~~~~~~~~~~~~~

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
from tornadio2 import proto


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
        self.session.close(self.endpoint)

    def get_endpoint(self, endpoint):
        return None
