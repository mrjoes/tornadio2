Migrating from previous TornadIO version
========================================

TornadIO2 has some incompatible API changes.

1. Instead of having one router handler, TornadIO2 exposes transports
as first-class Tornado handlers. This saves some memory per active connection,
because instead of having two handlers per request (router and transport), you will now have only one.
This change affects how TornadIO2 is initialized and plugged into your Tornado application::

    ChatServer = tornadio2.router.TornadioRouter(ChatConnection)
    # Fill your routes here
    routes = [(r"/", IndexHandler)]
    # Extend list of routes with Tornadio2 URLs
    routes.extend(ChatServer.urls)

    application = tornado.web.Application(routes)

or alternative approach::

    ChatServer = tornadio2.router.TornadioRouter(ChatConnection)
    application = tornado.web.Application(ChatServer.apply_routes([(r"/", IndexHandler)]))

2. `SocketConnection.on_open` was changed to accept single ``request`` parameter. This parameter
is instance of the ConnectionInfo class which contains some helper methods like
get_argument(), get_cookie(), etc. Also, if you return ``False`` from your ``on_open`` handler,
TornadIO2 will reject connection.

Example::

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

