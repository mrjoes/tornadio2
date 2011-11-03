from os import path as op

import datetime

from tornado import web

from tornadio2 import SocketConnection, TornadioRouter, SocketServer


ROOT = op.normpath(op.dirname(__file__))


class IndexHandler(web.RequestHandler):
    """Regular HTTP handler to serve the chatroom page"""
    def get(self):
        self.render('index.html')


class SocketIOHandler(web.RequestHandler):
    def get(self):
        self.render('../socket.io.js')


class ChatConnection(SocketConnection):
    participants = set()
    unique_id = 0

    @classmethod
    def get_username(cls):
        cls.unique_id += 1
        return 'User%d' % cls.unique_id

    def on_open(self, info):
        print 'Chat', repr(info)

        # Give user unique ID
        self.user_name = self.get_username()
        self.participants.add(self)

        self.broadcast('%s joined chat.' % self.user_name)

    def on_message(self, message):
        self.broadcast('%s: %s' % (self.user_name, message))

    def on_close(self):
        self.participants.remove(self)

        self.broadcast('%s left chat.' % self.user_name)

    def broadcast(self, msg):
        for p in self.participants:
            p.send(msg)


class PingConnection(SocketConnection):
    def on_open(self, info):
        print 'Ping', repr(info)

    def on_message(self, message):
        now = datetime.datetime.now()

        message['server'] = [now.hour, now.minute, now.second, now.microsecond / 1000]
        self.send(message)


class RouterConnection(SocketConnection):
    __endpoints__ = {'/chat': ChatConnection,
                     '/ping': PingConnection}

    def on_open(self, info):
        print 'Router', repr(info)

# Create tornadio server
MyRouter = TornadioRouter(RouterConnection)

# Create socket application
application = web.Application(
    MyRouter.apply_routes([(r"/", IndexHandler),
                           (r"/socket.io.js", SocketIOHandler)]),
    flash_policy_port = 843,
    flash_policy_file = op.join(ROOT, 'flashpolicy.xml'),
    socket_io_port = 8001
)

if __name__ == "__main__":
    import logging
    logging.getLogger().setLevel(logging.DEBUG)

    # Create and start tornadio server
    SocketServer(application)
