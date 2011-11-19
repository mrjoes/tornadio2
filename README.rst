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

1. Derive from tornadio2.SocketConnection class and override on_message method (on_open/on_close are optional)::
```python

    class MyConnection(tornadio2.SocketConnection):
        def on_message(self, message):
           pass
```

2. Create TornadIO2 server for your connection::
```python

    MyRouter = tornadio2.TornadioRouter(MyConnection)
```

3. Add your handler routes to the Tornado application::
```python

  application = tornado.web.Application(
    MyRouter.urls,
    socket_io_port = 8000)
```

4. Start your application
5. You have your `socket.io` server running at port 8000. Simple, right?

Starting Up
-----------

We provide customized version (shamelessly borrowed from the SocketTornad.IO library) of the ``HttpServer``, which
simplifies start of your TornadIO server.

To start it, do following (assuming you created application object before)::
```python

  if __name__ == "__main__":
    socketio_server = SocketServer(application)
```

SocketServer will automatically start Flash policy server, if required.

If you don't want to start ``IOLoop`` immediately, pass ``auto_start = False`` as one of the constructor options and
then manually start IOLoop.


More information
----------------

For more information, check `TornadIO2 documentation <http://readthedocs.org/docs/tornadio2/en/latest/>`_ and sample applications.


Examples
~~~~~~~~

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

RPC ping
^^^^^^^^

Ping which works through socket.io events. It is in the ``examples/rpcping`` directory.

Transports
^^^^^^^^^^

Simple ping/pong example with chat-like interface with selectable transports. It is in the
``examples/transports`` directory.
