from os import path as op

import tornado
import tornado.web
import tornado.httpserver
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
        self.render('../socket.io.js')


class ChatConnection(tornadio2.conn.SocketConnection):
    # Class level variable
    participants = set()

    def on_open(self, info):
        self.send("Welcome from the server.")
        self.participants.add(self)

    def on_message(self, message):
        # Pong message back
        for p in self.participants:
            p.send(message)

    def on_close(self):
        self.participants.remove(self)

# Create tornadio server
ChatRouter = tornadio2.router.TornadioRouter(ChatConnection)

# Create socket application
sock_app = tornado.web.Application(
    ChatRouter.urls,
    flash_policy_port = 843,
    flash_policy_file = op.join(ROOT, 'flashpolicy.xml'),
    socket_io_port = 8002
)

# Create HTTP application
http_app = tornado.web.Application(
    [(r"/", IndexHandler), (r"/socket.io.js", SocketIOHandler)]
)

if __name__ == "__main__":
    import logging
    logging.getLogger().setLevel(logging.DEBUG)

    # Create http server on port 8001
    http_server = tornado.httpserver.HTTPServer(http_app)
    http_server.listen(8001)

    # Create tornadio server on port 8002, but don't start it yet
    tornadio2.server.SocketServer(sock_app, auto_start=False)

    # Start both servers
    tornado.ioloop.IOLoop.instance().start()
