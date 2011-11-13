====================
Bugs and Workarounds
====================

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

Current implementation of socket.io client stores query string
parameters on session level. So, if you have multiplexed connections and want to pass
parameters to them - it is not possible.

See related bug report: https://github.com/LearnBoost/socket.io-client/issues/331

So, you can not expect query string parametes to be passed to your virtual connections and
will have to structure your JS code, so first ``io.connect()`` will include anything you
want to pass to the server.
