from os import path as op

import datetime

from tornado import web

from tornadio2 import SocketConnection, TornadioRouter, SocketServer, event


ROOT = op.normpath(op.dirname(__file__))


class IndexHandler(web.RequestHandler):
    """Regular HTTP handler to serve the ping page"""
    def get(self):
        self.render('index.html')


class SocketIOHandler(web.RequestHandler):
    def get(self):
        self.render('../socket.io.js')


class StatsHandler(web.RequestHandler):
    def get(self):
        self.render('stats.html')


class PingConnection(SocketConnection):
    @event
    def ping(self, client):
        now = datetime.datetime.now()
        return client, [now.hour, now.minute, now.second, now.microsecond / 1000]

    @event
    def stats(self):
        return self.session.server.stats.dump()

# Create tornadio router
PingRouter = TornadioRouter(PingConnection,
                            dict(enabled_protocols=['websocket', 'xhr-polling',
                                                    'jsonp-polling', 'htmlfile']))

# Create socket application
application = web.Application(
    PingRouter.apply_routes([(r"/", IndexHandler),
                             (r"/stats", StatsHandler),
                             (r"/socket.io.js", SocketIOHandler)]),
    flash_policy_port = 843,
    flash_policy_file = op.join(ROOT, 'flashpolicy.xml'),
    socket_io_port = 8001
)

if __name__ == "__main__":
    # Create and start tornadio server
    SocketServer(application)
