=========
TornadIO2
=========

Contributors
------------

-  `Serge S. Koval <https://github.com/MrJoes/>`_

Introduction
------------

This is python server implementation of the `Socket.IO <http://socket.io>`_ realtime
transport library on top of the `Tornado <http://www.tornadoweb.org>`_ framework.

TornadIO2 is compatible with 0.7+ version of the Socket.IO and implements
most of the features found in original Socket.IO server software.

Key features:

- Supports Socket.IO 0.8 protocol and related features
- Full unicode support
- Support for generator-based asynchronous code (tornado.gen API)
- Statistics capture (packets per second, etc)
- Actively maintained

What is Socket.IO?
------------------

Socket.IO aims to make realtime apps possible in every browser and mobile device, blurring the differences between the different transport mechanisms. It's care-free realtime 100% in JavaScript.

You can use it to build push service, games, etc. Socket.IO will adapt to the clients browser and will use most effective transport
protocol available.

Getting Started
---------------
In order to start working with the TornadIO2 library, you have to have some basic Tornado
knowledge. If you don't know how to use it, please read Tornado tutorial, which can be found
`here <http://www.tornadoweb.org/documentation#tornado-walk-through>`_.

If you're familiar with Tornado, do following to add support for Socket.IO to your application:

1. Derive from tornadio2.SocketConnection class and override on_message method (on_open/on_close are optional)::

    class MyConnection(tornadio2.SocketConnection):
        def on_message(self, message):
            pass

2. Create TornadIO2 server for your connection::

    MyRouter = tornadio2.TornadioRouter(MyConnection)

3. Add your handler routes to the Tornado application::

    application = tornado.web.Application(
        MyRouter.urls,
        socket_io_port = 8000)

4. Start your application
5. You have your `socket.io` server running at port 8000. Simple, right?

Starting Up
-----------

We provide customized version (shamelessly borrowed from the SocketTornad.IO library) of the ``HttpServer``, which
simplifies start of your TornadIO server.

To start it, do following (assuming you created application object before)::

    if __name__ == "__main__":
        socketio_server = SocketServer(application)

SocketServer will automatically start Flash policy server, if required.

If you don't want to start ``IOLoop`` immediately, pass ``auto_start = False`` as one of the constructor options and
then manually start IOLoop.


More information
----------------

For more information, check `TornadIO2 documentation <http://readthedocs.org/docs/tornadio2/en/latest/>`_ and sample applications.


Examples
~~~~~~~~

Acknowledgment
^^^^^^^^^^^^^^

Ping sample which shows how to use events to work in request-response mode. It is in the ``examples/ackping`` directory.

Cross site
^^^^^^^^^^

Chat sample which demonstrates how cross-site communication works
(chat server is running on port 8002, while HTTP server runs on port 8001). It is in the ``examples/crosssite`` directory.

Events and generator-based async API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example which shows how to use events and generator-based API to work with asynchronous code. It is in the ``examples/gen`` directory.

Multiplexed
^^^^^^^^^^^

Ping and chat demo running through one connection. You can see it in ``examples/multiplexed`` directory.

Stats
^^^^^

TornadIO2 collects some counters that you can use to troubleshoot your application performance.
Example in ``examples/stats`` directory gives an idea how you can use these stats to plot realtime graph.

RPC ping
^^^^^^^^

Ping which works through socket.io events. It is in the ``examples/rpcping`` directory.

Transports
^^^^^^^^^^

Simple ping/pong example with chat-like interface with selectable transports. It is in the
``examples/transports`` directory.
