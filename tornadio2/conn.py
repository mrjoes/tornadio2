# -*- coding: utf-8 -*-
"""
    tornadio2.conn
    ~~~~~~~~~~~~~~

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import time
import logging

from tornadio2 import proto

class LightweightConnection(object):
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
        """Default on_event handler. Must be overridden.
        SocketConnection class already implements it through EventMagicMixin.
        """
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

        # TODO: Notify unconfirmed messages?

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
            logging.error('Received invalid msg_id for ACK: %s' % msg_id)

    # Endpoint factory
    def get_endpoint(self, endpoint):
        """Called by TornadIO code when there's incoming endpoint connection request.
        You should either implement this method or use SocketConnection class, which
        has this method implemented through RouterMixin"""
        return None


class RouterMixin(object):
    """Implements simple endpoint management mixin.

    To use this mixin, define `_endpoints_` dictionary on class level, where key
    is endpoint name and value is connection class:
    ::
        class MyConnection(SocketConnection):
            __endpoints__ = dict(clock=ClockConnection,
                                 game=GameConnection)
    """
    __endpoints__ = dict()

    def get_endpoint(self, endpoint):
        if endpoint in self._endpoints_:
            return self._endpoints_[endpoint]


def event(name):
    def handler(f):
        f._event_name = name
        return f    
    return handler

class EventMagicMeta(type):
    def __init__(cls, name, bases, attrs):
        events = {}

        for a in attrs:    
            attr = getattr(cls, a)        
            name = getattr(attr, '_event_name', None)

            if name:
                events[name] = attr

        setattr(cls, '_events', events)

        super(EventMagicMeta, cls).__init__(name, bases, attrs)

class EventMagicMixin(object):
    """Implements decorator-based event handlers.

    For example:
    ::
        class MyConnection(SocketConnection):
            @event('test')
            def test(self, msg):
                print msg

    When you run following client code:
    ::
        sock.emit('test', {msg:'Hello World'});

    server should print 'Hello World'.
    """

    __metaclass__ = EventMagicMeta

    def on_event(self, name, **kwargs):
        handler = self._events.get(name)

        if handler:
            handler(self, **kwargs)
        else:
            logging.error('Invalid event name: %s' % name)


class SocketConnection(EventMagicMixin, RouterMixin, LightweightConnection):
    pass
