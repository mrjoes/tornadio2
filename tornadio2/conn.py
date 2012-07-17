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
    tornadio2.conn
    ~~~~~~~~~~~~~~

    Tornadio connection implementation.
"""
import time
import logging
from inspect import ismethod, getmembers

from tornadio2 import proto


def event(name_or_func):
    """Event handler decorator.

    Can be used with event name or will automatically use function name
    if not provided::

        # Will handle 'foo' event
        @event('foo')
        def bar(self):
            pass

        # Will handle 'baz' event
        @event
        def baz(self):
            pass
    """

    if callable(name_or_func):
        name_or_func._event_name = name_or_func.__name__
        return name_or_func

    def handler(f):
        f._event_name = name_or_func
        return f

    return handler


class EventMagicMeta(type):
    """Event handler metaclass"""
    def __init__(cls, name, bases, attrs):
        # find events, also in bases
        is_event = lambda x: ismethod(x) and hasattr(x, '_event_name')
        events = [(e._event_name, e) for _, e in getmembers(cls, is_event)]
        setattr(cls, '_events', dict(events))

        # Call base
        super(EventMagicMeta, cls).__init__(name, bases, attrs)


class SocketConnection(object):
    """Subclass this class and define at least `on_message()` method to make a Socket.IO
    connection handler.

    To support socket.io connection multiplexing, define `_endpoints_`
    dictionary on class level, where key is endpoint name and value is
    connection class::

        class MyConnection(SocketConnection):
            __endpoints__ = {'/clock'=ClockConnection,
                             '/game'=GameConnection}

    ``ClockConnection`` and ``GameConnection`` should derive from the ``SocketConnection`` class as well.

    ``SocketConnection`` has useful ``event`` decorator. Wrap method with it::

        class MyConnection(SocketConnection):
            @event('test')
            def test(self, msg):
                print msg

    and then, when client will emit 'test' event, you should see 'Hello World' printed::

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

        self._event_worker = None

    # Public API
    def on_open(self, request):
        """Default on_open() handler.

        Override when you need to do some initialization or request validation.
        If you return False, connection will be rejected.

        You can also throw Tornado HTTPError to close connection.

        `request`
            ``ConnectionInfo`` object which contains caller IP address, query string
            parameters and cookies associated with this request.

        For example::

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

    def on_event(self, name, args=[], kwargs=dict()):
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

        For example, if you emit event like this on client-side::

            sock.emit('test', {msg='Hello World'})

        you will have following parameter values in your on_event callback::

            name = 'test'
            args = []
            kwargs = {msg: 'Hello World'}

        However, if you emit event like this::

            sock.emit('test', 'a', 'b', {msg='Hello World'})

        you will have following parameter values::

            name = 'test'
            args = ['a', 'b', {msg: 'Hello World'}]
            kwargs = {}

        """
        handler = self._events.get(name)

        if handler:
            try:
                if args:
                    return handler(self, *args)
                else:
                    return handler(self, **kwargs)
            except TypeError:
                if args:
                    logging.error(('Attempted to call event handler %s ' +
                                  'with %s arguments.') % (handler,
                                                           repr(args)))
                else:
                    logging.error(('Attempted to call event handler %s ' +
                                  'with %s arguments.') % (handler,
                                                           repr(kwargs)))
                raise
        else:
            logging.error('Invalid event name: %s' % name)

    def on_close(self):
        """Default on_close handler."""
        pass

    def send(self, message, callback=None, force_json=False):
        """Send message to the client.

        `message`
            Message to send.
        `callback`
            Optional callback. If passed, callback will be called
            when client received sent message and sent acknowledgment
            back.
        `force_json`
            Optional argument. If set to True (and message is a string)
            then the message type will be JSON (Type 4 in socket_io protocol).
            This is what you want, when you send already json encoded strings.
        """
        if self.is_closed:
            return

        if callback is not None:
            msg = proto.message(self.endpoint,
                                message,
                                self.queue_ack(callback, message), force_json)
        else:
            msg = proto.message(self.endpoint, message, force_json=force_json)

        self.session.send_message(msg)

    def emit(self, name, *args, **kwargs):
        """Send socket.io event.

        `name`
            Name of the event
        `kwargs`
            Optional event parameters
        """
        if self.is_closed:
            return

        msg = proto.event(self.endpoint, name, None, *args, **kwargs)
        self.session.send_message(msg)

    def emit_ack(self, callback, name, *args, **kwargs):
        """Send socket.io event with acknowledgment.

        `callback`
            Acknowledgment callback
        `name`
            Name of the event
        `kwargs`
            Optional event parameters
        """
        if self.is_closed:
            return

        msg = proto.event(self.endpoint,
                          name,
                          self.queue_ack(callback, (name, args, kwargs)),
                          *args,
                          **kwargs)
        self.session.send_message(msg)

    def close(self):
        """Forcibly close client connection"""
        self.session.close(self.endpoint)

        # TODO: Notify about unconfirmed messages?

    # ACKS
    def queue_ack(self, callback, message):
        """Queue acknowledgment callback"""
        ack_id = self.ack_id

        self.ack_queue[ack_id] = (time.time(),
                                  callback,
                                  message)

        self.ack_id += 1

        return ack_id

    def deque_ack(self, msg_id, ack_data):
        """Dequeue acknowledgment callback"""
        if msg_id in self.ack_queue:
            time_stamp, callback, message = self.ack_queue.pop(msg_id)

            callback(message, ack_data)
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
