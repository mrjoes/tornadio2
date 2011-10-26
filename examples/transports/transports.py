from os import path as op

import tornado.web
import tornadio2
import tornadio2.router
import tornadio2.server
import tornadio2.conn

ROOT = op.normpath(op.dirname(__file__))


class IndexHandler(tornado.web.RequestHandler):
    """Regular HTTP handler to serve the chatroom page"""
    def get(self):
        self.render('index.html')


class SocketIOHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('socket.io.js')


class ChatConnection(tornadio2.conn.SocketConnection):
    # Class level variable
    participants = set()

    def on_open(self, *args, **kwargs):
        self.send("Welcome from the server.")

    def on_message(self, message):
        # Pong message back
        self.send(message)

#use the routes classmethod to build the correct resource
ChatServer = tornadio2.router.TornadioServer(ChatConnection)

#configure the Tornado application
routes = [(r"/", IndexHandler), (r"/socket.io.js", SocketIOHandler)]
routes.extend(ChatServer.urls)

application = tornado.web.Application(
    routes,
    flash_policy_port = 843,
    flash_policy_file = op.join(ROOT, 'flashpolicy.xml'),
    socket_io_port = 8001
)

if __name__ == "__main__":
    import logging
    logging.getLogger().setLevel(logging.DEBUG)

    tornadio2.server.SocketServer(application)
