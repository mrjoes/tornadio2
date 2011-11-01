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


def event(name):
    """Event handler decorator"""
    def handler(f):
        f._event_name = name
        return f

    return handler


class EventMagicMeta(type):
    """Event handler metaclass"""
    def __init__(cls, name, bases, attrs):
        events = {}

        for a in attrs:
            attr = getattr(cls, a)
            name = getattr(attr, '_event_name', None)

            if name:
                events[name] = attr

        setattr(cls, '_events', events)

        super(EventMagicMeta, cls).__init__(name, bases, attrs)


class SocketConnection(object):
    """Socket connection class.

    To support socket.io connection multiplexing, define `_endpoints_`
    dictionary on class level, where key is endpoint name and value is
    connection class:
    ::
        class MyConnection(SocketConnection):
            __endpoints__ = dict(clock=ClockConnection,
                                 game=GameConnection)

    SocketConnection has useful event decorator. To use it, wrap method with an
    event() decorator:
    ::
        class MyConnection(SocketConnection):
            @event('test')
            def test(self, msg):
                print msg

    And then, when you run following client code server should print 'Hello World':
    ::
        sock.emit('test', {msg:'Hello World'});
    """
    __metaclass__ = EventMagicMeta

    __endpoints__ = dict()

    def __init__(self, session, endpoint=None):
        """Connection constructor.

        `session`
            Associated session
        `endpoint`
            Endpoint name

        """
        self.session = session
        self.endpoint = endpoint

        self.is_closed = False

        self.ack_id = 1
        self.ack_queue = dict()

    # Public API
    def on_open(self, request):
        """Default on_open() handler.

        Override when you need to do some initialization or request validation.
        If you return False, connection will be rejected.

        You can also throw Tornado HTTPError to close connection.

        `request`
            Tornado request handler object which you can use to read cookie,
            remote IP address, etc.

        For example:
        ::
            class MyConnection(SocketConnection):
                def on_open(self, request):
                    self.user_id = request.get_argument('id', None)

                    if not self.user_id:
                        return False
        """
        pass

    def on_message(self, message):
        """Default on_message handler. Must be overridden in your application"""
        raise NotImplementedError()

    def on_event(self, name, *args, **kwargs):
        """Default on_event handler.

        By default, it uses decorator-based approach to handle events,
        but you can override it to implement custom event handling.

        `name`
            Event name
        `args`
            Event args
        `kwargs`
            Event kwargs

        There's small magic around event handling.
        If you send exactly one parameter from the client side and it is dict,
        then you will receive parameters in dict in `kwargs`. In all other
        cases you will have `args` list.

        For example, if you emit event like this on client-side:
        ::
            sock.emit('test', {msg='Hello World'})

        you will have following parameter values in your on_event callback:

            name = 'test'
            args = []
            kwargs = {msg: 'Hello World'}

        However, if you emit event like this:
        ::
            sock.emit('test', 'a', 'b', {msg='Hello World'})

        you will have following parameter values:

            name = 'test'
            args = ['a', 'b', {msg: 'Hello World'}]
            kwargs = {}
        """
        handler = self._events.get(name)

        if handler:
            # TODO: Catch exception
            handler(self, **kwargs)
        else:
            logging.error('Invalid event name: %s' % name)

    def on_close(self):
        """Default on_close handler."""
        pass

    def send(self, message, callback=None):
        """Send message to the client.

        `message`
            Message to send.
        `callback`
            Optional callback. If passed, callback will be called
            when client received sent message and sent acknowledgment
            back.
        """
        if callback is not None:
            msg = proto.message(self.endpoint,
                                message,
                                self.queue_ack(callback, message))
        else:
            msg = proto.message(self.endpoint, message)

        self.session.send_message(msg)

    def emit(self, name, callback=None, **kwargs):
        """Send socket.io event.

        `name`
            Name of the event
        `callback`
            Optional callback. If passed, callback will be called
            when client received event and sent acknowledgment back.
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
        """Queue acknowledgment callback"""
        ack_id = self.ack_id

        self.ack_queue[ack_id] = (time.time(),
                                  callback,
                                  message)

        self.ack_id += 1

        return ack_id

    def deque_ack(self, msg_id):
        """Dequeue acknowledgment callback"""
        if msg_id in self.ack_queue:
            time_stamp, callback, message = self.ack_queue.pop(msg_id)

            callback(message)
        else:
            logging.error('Received invalid msg_id for ACK: %s' % msg_id)

    # Endpoint factory
    def get_endpoint(self, endpoint):
        """Get connection class by endpoint name.

        By default, will get endpoint from associated list of endpoints
        (from __endpoints__ class level variable).

        You can override this method to implement different endpoint
        connection class creation logic.
        """
        if endpoint in self.__endpoints__:
            return self.__endpoints__[endpoint]
