# -*- coding: utf-8 -*-
"""
    tornadio2.conn
    ~~~~~~~~~~~~~~

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import time

from tornadio2 import proto


class SocketConnection(object):
    def __init__(self, session, endpoint=None):
        self.session = session
        self.endpoint = endpoint

        self.is_closed = False

        self.ack_id = 1
        self.ack_queue = dict()

    # Public API
    def on_open(self, *args, **kwargs):
        """Default on_open() handler"""
        pass

    def on_message(self, message):
        """Default on_message handler. Must be overridden"""
        raise NotImplementedError()

    def on_event(self, name, **kwargs):
        raise NotImplementedError()

    def on_close(self):
        """Default on_close handler."""
        pass    

    def send(self, message, callback=None):
        """Send message to the client.

        `message`
            Message to send.
        """
        if callback is not None:
            msg = proto.message(self.endpoint,
                                message,
                                self.queue_ack(callback, message))
        else:
            msg = proto.message(self.endpoint, message)

        self.session.send_message(msg)

    def emit(self, name, callback=None, **kwargs):
        """Send socket.io event

        `name`
            Name of the event
        `kwargs`
            Optional event parameters
        """
        if callback is not None:
            msg = proto.event(self.endpoint,
                              name,
                              self.queue_ack(callback, (name, kwargs)),
                              **kwargs)
        else:
            msg = proto.event(self.endpoint, name, **kwargs)

        self.session.send_message(msg)

    def close(self):
        """Forcibly close client connection"""
        self.session.close(self.endpoint)

    # ACKS
    def queue_ack(self, callback, message):
        ack_id = self.ack_id

        self.ack_queue[ack_id] = (time.time(),
                                  callback,
                                  message)

        self.ack_id += 1

        return ack_id

    def deque_ack(self, msg_id):
        if msg_id in self.ack_queue:
            time_stamp, callback, message = self.ack_queue.pop(msg_id)

            callback(message)
        else:
            print 'Invalid msg_id for ACK'

    # Endpoint factory
    def get_endpoint(self, endpoint):
        return None


class RouterMixin(object):
    _endpoints_ = dict()

    def get_endpoint(self, endpoint):
        if endpoint in self._endpoints_:
            return self._endpoints_[endpoint]

