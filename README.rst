=========
TornadIO2
=========

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
In order to start working with the TornadIO2 library, you have to have some basic Tornado
knowledge. If you don't know how to use it, please read Tornado tutorial, which can be found
`here <http://www.tornadoweb.org/documentation#tornado-walk-through>`_.

If you're familiar with Tornado, do following to add support for Socket.IO to your application:

1. Derive from tornadio2.SocketConnection class and override on_message method (on_open/on_close are optional):
::

    class MyConnection(tornadio2.SocketConnection):
        def on_message(self, message):
           pass

2. Create TornadIO2 server for your connection:
::

    MyRouter = tornadio2.TornadioRouter(MyConnection)

3. Add your handler routes to the Tornado application:
::

  application = tornado.web.Application(
    MyRouter.urls,
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

To use built-in routing, declare and initialize ``__endpoints__`` dictionary in
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

    MyRouter = tornadio2.router.TornadioRouter(MyRouterConnection)

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
you now have way to get notified when client receives the message. To use this, pass a
callback function when sending a message:
::

    class MyConnection(SocketConnection):
        def on_message(self, msg):
            self.send(msg, self.my_callback)

        def my_callback(self, msg):
            print 'Got ack for my message: %s' % message


To send event with acknowledgement, use ``SocketConnection.emit_ack`` method:
::

    class MyConnection(SocketConnection):
        def on_message(self, msg):
            self.emit(self.my_callback, 'hello')

        def my_callback(self, event):
            print 'Got ack for my message: %s' % message


Events
------

Instead of having "just" messages, socket.io 0.7 introduced new concept - event.
Event is just a name and collection of parameters.

TornadIO2 provides easy-to-use syntax sugar which emulates RPC calls from the client
to your python code. Check following example:
::

    class MyConnection(SocketConnection):
        @event('hello')
        def test(self, name):
            print 'Hello %s' % name

            self.emit('thanks', name=name)
            self.emit('hello', name, 'foobar')

In your client code, to call this event, do something like:
::

    sock.emit('hello', {name: 'Joes'});

You can also use positional parameters. For previous example, you can also do something like:
::

    sock.emit('hello', 'Joes')

To handle event on client side, use following code:
::

    sock.on('thanks', function(data) {
        alert(data.name);
    });
    sock.on('hello', function(name, dummy) {
        alert('Hey ' + name + ' ' + dummy);
    });

However, take care - if method signature does not match (missing parameters, extra
parameters, etc), your connection will blow up and self destruct.

If you don't like this event handling approach, just override ``on_event`` in your
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


TornadIO2 will unpack dictionary into ``kwargs`` parameters and pass it to the
``on_event`` handler. However, if you pass more than one parameter, Tornadio2 won't
unpack them into ``kwargs`` and will just pass parameters as ``args``. For example, this
code will lead to ``args`` being passed to ``on_event`` handler:
::

    sock.emit('test', 1, 2, 3, {a: 10, b: 10});


Generator-based asynchronous interface
--------------------------------------

``tornadio2.gen`` module is a wrapper around ``tornado.gen`` API. You might want to take a
look at Tornado documentation for this module, which can be `found here <http://www.tornadoweb.org/documentation/gen.html>`_.

In most of the cases, it is not very convenient to use Tornado ``engine()``, because it makes your code truly
asynchronous. For example, if client sends two packets: A and B, and if it takes some time for A to handle, B will be executed
out of order.

To prevent this situation, TornadIO2 provides helper: ``tornadio2.gen.sync_engine``. ``sync_engine`` will queue incoming
calls if there's another instance of the function running. So, as a result, it will call your method synchronously without
blocking the io_loop.

Lets check following example:
::

    from tornadio2 import gen

    class MyConnection(SocketConnection):
        @gen.sync_engine
        def on_message(self, query):
            http_client = AsyncHTTPClient()
            response = yield gen.Task(http_client.fetch, 'http://google.com?q=' + query)
            self.send(response.body)

If client will quickly send two messages, it will work "synchronously" - ``on_message`` won't be called for second message
till handling of first message is finished.

However, if you will change decorator to ``gen.engine``, message handling will be asynchronous and might be out of order:
::

    from tornadio2 import gen

    class MyConnection(SocketConnection):
        @gen.sync_engine
        def on_message(self, query):
            http_client = AsyncHTTPClient()
            response = yield gen.Task(http_client.fetch, 'http://google.com?q=' + query)
            self.send(response.body)

If client will quickly send two messages, server will send response as soon as response is ready and if it takes longer to
handle first message, response for second message will be sent first.

As a nice feature, you can also decorate your event handlers or even wrap main ``on_event`` method, so
all events can be synchronous when using asynchronous calls.

``tornadio2.gen`` API will only work with the ``yield`` based methods (methods that produce generators). If you implement your
asynchronous code using explicit callbacks, it is up for you how to synchronize order of the execution for them.

TBD: performance considerations, python iterator performance.

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
    ChatServer = tornadio2.router.TornadioRouter(ChatConnection)
    # Fill your routes here
    routes = [(r"/", IndexHandler)]
    # Extend list of routes with Tornadio2 URLs
    routes.extend(ChatServer.urls)

    application = tornado.web.Application(routes)

or alternative approach:
::

    ChatServer = tornadio2.router.TornadioRouter(ChatConnection)
    application = tornado.web.Application(ChatServer.apply_routes([(r"/", IndexHandler)]))

2. `SocketConnection.on_open` was changed to accept single ``request`` parameter. This parameter
is instance of the ConnectionInfo class which contains some helper methods like
get_argument(), get_cookie(), etc. Also, if you return ``False`` from your ``on_open`` handler,
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
is not handled, whole connection is closed (including any running multiplexed connections).
In previous TornadIO version it was silently dropping currently open transport connection
and expecting for socket.io to reconnect.

4. Persistent connections are not dropped immediately - there's a chance that person
might reconnect with same session id and we will want to pick it up.

5. Socket.IO 0.7 dropped support for xhr-multipart transport, so you can safely remove it
from your configuration file.

Bugs and Workarounds
--------------------

There are some known bugs in socket.io (valid for socket.io-client 0.8.6). I consider
them "show-stoppers", but you can work around them with some degree of luck.

Connect after disconnect
^^^^^^^^^^^^^^^^^^^^^^^^

Unfortunately, disconnection is bugged in socket.io. If you close socket connection,
``io.connect()`` to the same endpoint will silently fail. If you try to forcibly connect
associated socket, it will work, but you have to make sure that you're not setting up
callbacks again, as you will end up having your callbacks called twice.

Link: https://github.com/LearnBoost/socket.io-client/issues/251

For now, if your main connection was closed, you have two options:
::

    var conn = io.connect(addr, {'force new connection': true});
    conn.on('message', function(msg) { alert('msg') });

or alternative approach:
::

    io.j = [];
    io.sockets = [];

    var conn = io.connect(addr);
    conn.on('message', function(msg) { alert('msg') });

or separate reconnection from initial connection:
::
    var conn = io.connect(addr);
    conn.on('disconnect', function(msg) { conn.socket.reconnect(); });

If you use first approach, you will lose multiplexing for good.

If you use second approach, apart of it being quite hackish, it will clean up existing
sockets, so socket.io will have to create new one and will use it to connect to endpoints.
Also, instead of clearing ``io.sockets``, you can remove socket which matches your URL.

If you use third approach, make sure you're not setting up events again.

On a side note, if you can avoid using ``disconnect()`` for socket, do so.

Query string parameters
^^^^^^^^^^^^^^^^^^^^^^^

Current implementation of socket.io client (still valid as of 0.8.5) stores query string
parameters on session level. So, if you have multiplexed connections and want to pass
parameters to them - it is not possible.

See related bug report: https://github.com/LearnBoost/socket.io-client/issues/331

So, you can not expect query string parametes to be passed to your virtual connections and
will have to structure your JS code, so first ``io.connect()`` will include anything you
want to pass to the server.

Examples
--------

Transports Example
^^^^^^^^^^^^^^^^^^

Simple ping/pong example with chat-like interface with selectable transports. It is in the
``examples/transports`` directory.
