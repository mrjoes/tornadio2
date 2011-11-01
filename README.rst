=========
TornadIO2
=========

.WIP.

Contributors
------------

-  `Serge S. Koval <https://github.com/MrJoes/>`_

Introduction
------------

This is implementation of the `Socket.IO <http://socket.io>`_ realtime
transport library on top of the `Tornado <http://www.tornadoweb.org>`_ framework.

TornadIO2 is compatible with 0.7+ version of the Socket.IO and implements
most of the features found in original Socket.IO server software.

Getting Started
---------------
In order to start working with the TornadIO library, you need to know some basic Tornado
knowledge. If you don't know how to use it, please read Tornado tutorial, which can be found
`here <http://www.tornadoweb.org/documentation#tornado-walk-through>`_.

If you're familiar with Tornado, do following to add support for Socket.IO to your application:

1. Derive from tornadio.SocketConnection class and override on_message method (on_open/on_close are optional):
::

    class MyConnection(tornadio.SocketConnection):
        def on_message(self, message):
           pass

2. Create TornadIO2 server for your connection:
::

    MyServer = tornadio2.router.TornadioServer(MyConnection)

3. Add your handler routes to the Tornado application:
::

  application = tornado.web.Application(
    MyServer.urls,
    socket_io_port = 8000)

4. Start your application
5. You have your `socket.io` server running at port 8000. Simple, right?

Multiplexed connections
-----------------------

Starting from socket.io 0.7, there's new concept of multiplexed connections:
you can have multiple "virtual" connections working through one transport connection.
TornadIO2 supports this transparently, but you have to tell TornadIO how to route
multiplexed connection requests. To accomplish this, you can either use built-in
routing mechanism or implement your own.

To use built-in routing, declare and initialize `__endpoints__` dictionary in
your main connection class:
::
    class ChatConnection(SocketConnection):
        def on_message(self, msg):
            pass

    class PingConnection(SocketConnection):
        def on_message(self, msg):
            pass

    class MyRouterConnection(SocketConnection):
        __endpoints__ = {'/chat': ChatConnection,
                         '/ping': PingConnection}

        def on_message(self, msg):
            pass

    MyServer = tornadio2.router.TornadioServer(MyRouterConnection)

On client side, create two connections:
::
    var chat = io.connect('http://myserver/chat'),
        ping = io.connect('http://myserver/ping');

    chat.send('Hey Chat');
    ping.send('Hey Ping');

So, you have to have three connection classes for 2 virtual connections - that's how
socket.io works. If you want, you can send some messages to MyRouterConnection as well,
if you will connect like this:
::
    var conn = io.connect('http://myserver'),
        chat = io.connect('http://myserver/chat'),
        ping = io.connect('http://myserver/ping');

        conn.send('Hey Connection!')


Acknowledgments
---------------

New feature of the socket.io 0.7+. When you send message to the client,
you now have way to get notified when client received the message. To use this, pass a
callback function when sending a message:
::
    class MyConnection(SocketConnection):
        def on_message(self, msg):
            self.send(msg, self.my_callback)

        def my_callback(self, msg):
            print 'Got ack for my message: %s' % message


Events
------

Instead of having "just" messages, socket.io 0.7 introduced new concept of events.
Event is just a name and collection of parameters.

TornadIO2 provides easy-to-use syntax sugar which emulates RPC calls from the client
to your python code. Check following example:
::
    class MyConnection(SocketConnection):
        @event('hello')
        def test(self, name):
            print 'Hello %s' % name

            self.emit('thanks', name=name)

In your client code, to call this event, do something like:
::
    sock.emit('hello', {name: 'Joes'});

However, take care - if method signature does not match (missing parameters, extra
parameters, etc), your connection will blow up and self destruct.

If you don't like this event handling approach, just override `on_event` in your
socket connection class and handle them by yourself:
::
    class MyConnection(SocketConnection):
        def on_event(self, name, *args, **kwargs):
            if name == 'hello':
                print 'Hello %s' % (kwargs['name'])

            self.emit('thanks', name=kwargs['name'])

There's also some magic involved in event message parsing to make it easier to work
with events.

If you send data from client using following code:
::
    sock.emit('test', {a: 10, b: 10});


TornadIO2 will unpack dictionary into `kwargs` parameters and pass it to the
`on_event` handler. However, if you pass more than one parameter, Tornadio2 won't
unpack them into `kwargs` and will just pass parameters as `args`. For example, this
code will lead to `args` being passed to `on_event` handler:
::
    sock.emit('test', 1, 2, 3, {a: 10, b: 10});


Goodies
-------

``SocketConnection`` class provides few overridable methods:

1. ``on_open`` called when new client connection was established.
2. ``on_message`` called when message was received from the client. If client sent JSON object,
   it will be automatically decoded into appropriate Python data structures.
3. ``on_close`` called when client connection was closed (due to network error, timeout or just client-side disconnect)

Each ``SocketConnection`` has ``send()`` method which is used to send data to the client. Input parameter can be one of the:

1. String/unicode string - sent as is (though with utf-8 encoding)
2. Arbitrary python object - encoded as JSON string, using utf-8 encoding

If you want to send event to the client, use ``emit()`` method. It accepts name
and optional parameters which will be passed as a function parameters.

Starting Up
-----------

Best Way: SocketServer
^^^^^^^^^^^^^^^^^^^^^^

We provide customized version (shamelessly borrowed from the SocketTornad.IO library) of the HttpServer, which
simplifies start of your TornadIO server.

To start it, do following (assuming you created application object before)::

  if __name__ == "__main__":
    socketio_server = SocketServer(application)

SocketServer will automatically start Flash policy server, if required.


Upgrading from previous TornadIO
--------------------------------
TornadIO2 has some incompatible API changes.

1. Instead of having one rule and a router handler, TornadIO2 exposes transports
as first-class Tornado handlers. This saves some memory per active connection,
because instead of having two handlers per request, you will now have only one.
This change affected how TornadIO2 is initialized and plugged into your Tornado application:
::
    ChatServer = tornadio2.router.TornadioServer(ChatConnection)
    # Fill your routes here
    routes = [(r"/", IndexHandler)]
    # Extend list of routes with Tornadio2 URLs
    routes.extend(ChatServer.urls)

    application = tornado.web.Application(routes)

or alternative approach:
::
    ChatServer = tornadio2.router.TornadioServer(ChatConnection)
    application = tornado.web.Application(ChatServer.apply_routes([(r"/", IndexHandler)]))

2. `SocketConnection.on_open` was changed to accept single `request` parameter. This parameter
is instance of the ConnectionInfo class which contains some helper methods like
get_argument(), get_cookie(), etc. Also, if you return `False` from your `on_open` handler,
TornadIO2 will reject connection.

Example:
::
    class MyConnection(SocketConnection):
        def on_open(self, request):
            self.user_id = request.get_argument('id')

            if not self.user_id:
                return False

This variable is also available for multiplexed connections and will contain query string
parameters from the socket.io endpoint connection request.

3. There's major behavioral change in exception handling. If something blows up and
it not handled, whole socket.io connection is closed. In previous TornadIO version,
it was silently dropping currently open transport connection and expecting for socket.io
to reconnect.

4. Socket.IO 0.7 dropped support for xhr-multipart transport, so you can safely remove it
from your configuration file

Bugs and Workarounds
--------------------

There are some known bugs in socket.io (last time I checked, it was 0.8.6)

Connect after disconnect
^^^^^^^^^^^^^^^^^^^^^^^^

Unfortunately, disconnection is bugged in socket.io. If you close socket connection,
`io.connect` to the same endpoint will silently fail. If you try to forcibly connect
associated socket, you will end up having your callbacks called twice, etc.

For now, if your main connection was closed, you have two options:
::
    var conn = io.connect(addr, {'force new connection': true});
or alternative approach:
::
    io.j = [];
    io.sockets = [];

If you use first approach, you will lose multiplexing for good.

If you use second approach, apart of it being quite hackish, it will clean up existing
sockets, so socket.io will have to create new one and will use it to connect to endpoints.
Also, instead of clearing `io.sockets`, you can remove socket which matches your URL.

On a side note, if you can avoid using `disconnect()` for socket, do so.

Examples
--------

Transports Example
^^^^^^^^^^^^^^^^^^

Simple ping/pong example with chat-like interface with selectable transports. It is in the
``examples/transports`` directory.
