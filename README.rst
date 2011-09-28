========
Tornadio
========

Contributors
------------

-  `Serge S. Koval <https://github.com/MrJoes/>`_

Credits
-------

Authors of SocketTornad.IO project:

-  Brendan W. McAdams bwmcadams@evilmonkeylabs.com
-  `Matt Swanson <http://github.com/swanson>`_

This is implementation of the `Socket.IO <http://socket.io>`_ realtime
transport library on top of the `Tornado <http://www.tornadoweb.org>`_ framework.

Short Background
----------------

There's a library which already implements Socket.IO integration using Tornado
framework - `SocketTornad.IO <http://github.com/SocketTornad.IO/>`_, but
it was not finished, has several known bugs and not very well structured.

TornadIO is different from SocketTornad.IO library in following aspects:

- Simpler internal design, easier to maintain/extend
- No external dependencies (except of the Tornado itself and simplejson on python < 2.6)
- Properly handles on_open/on_close events for polling transports
- Proper Socket.IO protocol parser
- Proper unicode support
- Actively maintained

Introduction
------------

In order to start working with the TornadIO library, you need to know some basic concepts
on how Tornado works. If you don't, please read Tornado tutorial, which can be found
`here <http://www.tornadoweb.org/documentation#tornado-walk-through>`_.

If you're familiar with Tornado, do following to add support for Socket.IO to your application:

1. Derive from tornadio.SocketConnection class and override on_message method (on_open/on_close are optional):
::

  class MyConnection(tornadio.SocketConnection):
    def on_message(self, message):
      pass

2. Create handler object that will handle all `socket.io` transport related functionality:
::

  MyRouter = tornadio.get_router(MyConnection)

3. Add your handler routes to the Tornado application:
::

  application = tornado.web.Application(
    [MyRouter.route()],
    socket_io_port = 8000)

4. Start your application
5. You have your `socket.io` server running at port 8000. Simple, right?

Goodies
-------

``SocketConnection`` class provides three overridable methods:

1. ``on_open`` called when new client connection was established.
2. ``on_message`` called when message was received from the client. If client sent JSON object,
   it will be automatically decoded into appropriate Python data structures.
3. ``on_close`` called when client connection was closed (due to network error, timeout or just client-side disconnect)


Each ``SocketConnection`` has ``send()`` method which is used to send data to the client. Input parameter
can be one of the:

1. String/unicode string - sent as is (though with utf-8 encoding)
2. Arbitrary python object - encoded as JSON string automatically
3. List of python objects/strings - encoded as series of the socket.io messages using one of the rules above.

Configuration
-------------

You can configure your handler by passing settings to the ``get_router`` function as a ``dict`` object.

-  **enabled_protocols**: This is a ``list`` of the socket.io protocols the server will respond requests for.
   Possibilities are:
-  *websocket*: HTML5 WebSocket transport
-  *flashsocket*: Flash emulated websocket transport. Requires Flash policy server running on port 843.
-  *xhr-multipart*: Works with two connections - long GET connection with multipart transfer encoding to receive
   updates from the server and separate POST requests to send data from the client.
-  *xhr-polling*: Long polling AJAX request to read data from the server and POST requests to send data to the server.
   If message is available, it will be sent through open GET connection (which is then closed) or queued on the
   server otherwise.
-  *jsonp-polling*: Similar to the *xhr-polling*, but pushes data through the JSONp.
-  *htmlfile*: IE only. Creates HTMLFile control which reads data from the server through one persistent connection.
   POST requests are used to send data back to the server.


-  **session_check_interval**: Specifies how often TornadIO will check session container for expired session objects.
   In seconds.
-  **session_expiry**: Specifies session expiration interval, in seconds. For polling transports it is actually
   maximum time allowed between GET requests to consider virtual connection closed.
-  **heartbeat_interval**: Heartbeat interval for persistent transports. Specifies how often heartbeat events should
   be sent from the server to the clients.
-  **xhr_polling_timeout**: Timeout for long running XHR connection for *xhr-polling* transport, in seconds. If no
   data was available during this time, connection will be closed on server side to avoid client-side timeouts.

Resources
^^^^^^^^^

You're not limited with one connection type per server - you can serve different clients in one server instance.

By default, all socket.io clients use same resource - 'socket.io'. You can change resource by passing `resource` parameter
to the `get_router` function:
::

  ChatRouter = tornadio.get_router(MyConnection, resource='chat')

In the client, provide resource you're connecting to, by passing `resource` parameter to `io.Socket` constructor:
::

  sock = new io.Socket(window.location.hostname, {
               port: 8001,
               resource: 'chat',
             });

As it was said before, you can have as many connection types as you want by having unique resources for each connection type:
::

  ChatRouter = tornadio.get_router(ChatConnection, resource='chat')
  PingRouter = tornadio.get_router(PingConnection, resource='ping')
  MapRouter = tornadio.get_router(MapConnection, resource='map')

  application = tornado.web.Application(
    [ChatRouter.route(), PingRouter.route(), MapRouter.route()],
    socket_io_port = 8000)

Extra parameters
^^^^^^^^^^^^^^^^

If you need some kind of user authentication in your application, you have two choices:

1. Send authentication token as a first message from the client
2. Provide authentication token as part of the `resource` parameter

TornadIO has support for extra data passed through the `socket.io` resources.

You can provide regexp in `extra_re` parameter of the `get_router` function and matched data can be accessed
in your `on_open` handler as `kwargs['extra']`. For example:
::

  class MyConnection(tornadio.SocketConnection):
    def on_open(self, *args, **kwargs):
      print 'Extra: %s' % kwargs['extra']

  ChatRouter = tornadio.get_router(MyConnection, resource='chat', extra_re='\d+', extra_sep='/')

and on the client-side:
::

  sock = new io.Socket(window.location.hostname, {
               port: 8001,
               resource: 'chat/123',
             });

If you will run this example and connect with sample client, you should see 'Extra: 123' printed out.

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

Going big
---------

So, you've finished writting your application and want to share it with rest of the world, so you started
thinking about scalability, deployment options, etc.

Most of the Tornado servers are deployed behind the nginx, which also used to serve static content. This
won't work very well with TornadIO, as nginx does not support HTTP/1.1, does not support websockets and
XHR-Multipart transport just won't work.

So, to load balance your TornadIO instances, use alternative solutions like `HAProxy <http://haproxy.1wt.eu/>`_.
However, HAProxy does not work on Windows, so if you plan to deploy your solution on Windows platform,
you might want to take look into `MLB <http://support.microsoft.com/kb/240997>`_.

Scalability is completely different beast. It is up for you, as a developer, to design scalable architecture
of the application.

For example, if you need to have one large virtual server out of your multiple physical processes (or even servers),
you have to come up with some kind of the synchronization mechanism. This can be either common meeting point
(and also point of failure), like memcached, redis, etc. Or you might want to use some transporting mechanism to
communicate between servers, for example something `AMQP <http://www.amqp.org/>`_ based, `ZeroMQ <zeromq.org>`_ or
just plain sockets with your protocol.

For example, with message queues, you can treat TornadIO as a message gateway between your clients and your server backend(s).

Examples
--------

Chatroom Example
^^^^^^^^^^^^^^^^

There is a chatroom example application from the SocketTornad.IO library, contributed by
`swanson <http://github.com/swanson>`_. It is in the ``examples/chatroom`` directory.

Ping Example
^^^^^^^^^^^^

Simple ping/pong example to measure network performance. It is in the ``examples/ping`` directory.

Transports Example
^^^^^^^^^^^^^^^^^^

Simple ping/pong example with chat-like interface with selectable transports. It is in the
``examples/transports`` directory.
