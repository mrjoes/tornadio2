Multiplexed connections
=======================

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
