from os import path as op
from datetime import timedelta

from tornado import web, httpclient, ioloop

from tornadio2 import SocketConnection, TornadioRouter, SocketServer, event, gen


ROOT = op.normpath(op.dirname(__file__))


class IndexHandler(web.RequestHandler):
    """Regular HTTP handler to serve the chatroom page"""
    def get(self):
        self.render('index.html')


class SocketIOHandler(web.RequestHandler):
    def get(self):
        self.render('../socket.io.js')


class QueryConnection(SocketConnection):
    def long_running(self, value, callback):
        """Long running task implementation.
        Simply adds 3 second timeout and then calls provided callback method.
        """
        def finish():
            callback('Handled %s.' % value)

        ioloop.IOLoop.instance().add_timeout(timedelta(seconds=3), finish)

    @event
    def query(self, num):
        """Event implementation

        Because on_event() was wrapped with ``gen.sync_engine``, yield will be treated
        as asynchronous task.
        """
        response = yield gen.Task(self.long_running, num)
        self.emit('response', response)

    @gen.sync_engine
    def on_event(self, name, *args, **kwargs):
        """Wrapped ``on_event`` handler, which will queue events and will allow usage
        of the ``yield`` in the event handlers.

        If you want to use non-queued version, just wrap ``on_event`` with ``gen.engine``.
        """
        return super(QueryConnection, self).on_event(name, *args, **kwargs)

# Create tornadio router
QueryRouter = TornadioRouter(QueryConnection)

# Create socket application
application = web.Application(
    QueryRouter.apply_routes([(r"/", IndexHandler),
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
