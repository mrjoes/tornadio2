Bugs and Workarounds
====================

There are some known bugs in socket.io (valid for socket.io-client 0.8.6). I consider
them "show-stoppers", but you can work around them with some degree of luck.

Connect after disconnect
^^^^^^^^^^^^^^^^^^^^^^^^

Unfortunately, disconnection is bugged in socket.io client. If you close socket connection,
``io.connect()`` to the same endpoint will silently fail. If you try to forcibly connect
associated socket, it will work, but you have to make sure that you're not setting up
callbacks again, as you will end up having your callbacks called twice.

Link: https://github.com/LearnBoost/socket.io-client/issues/251

For now, if your main connection was closed, you have few options:
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

Current implementation of socket.io client stores query string
parameters on session level. So, if you have multiplexed connections and want to pass
parameters to them - it is not possible.

See related bug report: https://github.com/LearnBoost/socket.io-client/issues/331

So, you can not expect query string parametes to be passed to your virtual connections and
will have to structure your JS code, so first ``io.connect()`` will include anything you
want to pass to the server.

Windows and anti-virus software
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It is known that some anti-virus software (I'm lookin at you, Avast) is messing up
with websockets protocol if it is going through the port 80. Avast proxies all traffic
through local proxy which does some on-the-fly traffic analysis and their proxy does
not support websockets - all messages sent from server are queued in their proxy,
connection is kept alive, etc.

Unfortunately, socket.io does not support this situation and won't fallback to other
protocol.

There are few workarounds:
1. Disable websockets for everyone (duh)
2. Run TornadIO2 (or your proxy/load balancer) on two different ports and have simple logic
   on client side to switch to another port if connection fails

Socket.IO developers are aware of the problem and next socket.io version will provide
official workaround.

Here's more detailed article on the matter: `https://github.com/LearnBoost/socket.io/wiki/Socket.IO-and-firewall-software <https://github.com/LearnBoost/socket.io/wiki/Socket.IO-and-firewall-software>`_.
