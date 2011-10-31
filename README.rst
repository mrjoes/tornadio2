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

Tornadio2 is compatible with 0.7+ version of the Socket.IO and implements
most of the features found in original Socket.IO server software.

Upgrading from first TornadIO version
-------------------------------------
TornadIO has some incompatible API changes.

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

2. Socket.IO 0.7 dropped xhr-multipart transport, so you can safely remove it from your configuration files

Getting Started
---------------
In order to start working with the TornadIO library, you need to know some basic concepts
on how Tornado works. If you don't, please read Tornado tutorial, which can be found
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

Goodies
-------

``SocketConnection`` class provides few overridable methods:

1. ``on_open`` called when new client connection was established.
2. ``on_message`` called when message was received from the client. If client sent JSON object,
   it will be automatically decoded into appropriate Python data structures.
3. ``on_close`` called when client connection was closed (due to network error, timeout or just client-side disconnect)

Each ``SocketConnection`` has ``send()`` method which is used to send data to the client. Input parameter
can be one of the:

1. String/unicode string - sent as is (though with utf-8 encoding)
2. Arbitrary python object - encoded as JSON string, using utf-8 encoding

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

Examples
--------

Transports Example
^^^^^^^^^^^^^^^^^^

Simple ping/pong example with chat-like interface with selectable transports. It is in the
``examples/transports`` directory.
