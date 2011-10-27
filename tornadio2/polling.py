# -*- coding: utf-8 -*-
"""
    tornadio2.polling
    ~~~~~~~~~~~~~~~~~

    This module implements socket.io polling transports.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import time

from tornado.web import RequestHandler, HTTPError, asynchronous

from tornadio2 import proto


class TornadioPollingHandlerBase(RequestHandler):
    def initialize(self, server):
        self.server = server
        self.session = None

    def _execute(self, transforms, *args, **kwargs):
        self.session = self.server.get_session(kwargs['session_id'])

        if self.session is None or self.session.is_closed:
            # TODO: clean me up
            raise HTTPError(401, 'Invalid session')

        super(TornadioPollingHandlerBase, self)._execute(transforms,
                                                         *args, **kwargs)

    @asynchronous
    def get(self, *args, **kwargs):
        """Default GET handler."""
        raise NotImplementedError()

    @asynchronous
    def post(self, *args, **kwargs):
        if not self.preflight():
            raise HTTPError(401, 'unauthorized')

        data = self.request.body

        # IE XDomainRequest support
        if data.startswith('data='):
            data = data(data[5:])

        # Process packets one by one
        packets = proto.decode_frames(data)
        for p in packets:
            try:
                self.session.raw_message(p)
            except Exception:
                # TODO: Do what?
                import traceback
                traceback.print_exc()

        self.set_header('Content-Type', 'text/plain; charset=UTF-8')
        #self.write('')
        self.finish()

    def send_messages(self, messages):
        """Called by the session when some data is available"""
        raise NotImplementedError()

    @asynchronous
    def options(self, *args, **kwargs):
        """XHR cross-domain OPTIONS handler"""
        self.preflight()
        self.finish()

    def preflight(self):
        """Handles request authentication"""
        if 'Origin' in self.request.headers:
            if self.verify_origin():
                self.set_header('Access-Control-Allow-Origin',
                                self.request.headers['Origin'])

                if 'Cookie' in self.request.headers:
                    self.set_header('Access-Control-Allow-Credentials', True)

                return True
            else:
                return False
        else:
            return True

    def verify_origin(self):
        """Verify if request can be served"""
        # TODO: Verify origin
        return True


class TornadioXHRPollingHandler(TornadioPollingHandlerBase):
    def initialize(self, server):
        super(TornadioXHRPollingHandler, self).initialize(server)

        self._timeout = None
        self._timeout_interval = self.server.settings['xhr_polling_timeout']

    @asynchronous
    def get(self, *args, **kwargs):
        # TODO: Remove try/catch
        try:
            # Assign handler
            if not self.session.set_handler(self):
                # TODO: Error logging
                raise HTTPError(401, 'Forbidden')

            if not self.session.send_queue:
                self._timeout = self.server.io_loop.add_timeout(
                    time.time() + self._timeout_interval,
                    self._polling_timeout)
            else:
                self.session.flush()
        except Exception:
            # TODO: Do what?
            import traceback
            traceback.print_exc()

    def _polling_timeout(self):
        print 'Polling timeout, closing'

        try:
            self.finish()
        except Exception:
            # Silenty ignore noop - if connection was already closed,
            # then ignore exception and silently detach
            pass
        finally:
            self._detach()

    def _detach(self):
        if self._timeout is not None:
            self.server.io_loop.remove_timeout(self._timeout)
            self.timeout = None

        if self.session:
            self.session.remove_handler(self)
            self.session = None

    def on_connection_close(self):
        self._detach()

    def send_messages(self, messages):
        # Encode multiple messages as UTF-8 string
        data = proto.encode_frames(messages)

        # Send data to client
        self.preflight()
        self.set_header('Content-Type', 'text/plain; charset=UTF-8')
        self.set_header('Content-Length', len(data))
        self.write(data)

        # Detach connection from session
        self._detach()

        # Close connection
        self.finish()


class TornadioXHRMultipartHandler(TornadioPollingHandlerBase):
    @asynchronous
    def get(self, *args, **kwargs):
        if not self.session.set_handler(self):
            # TODO: Error logging
            raise HTTPError(401, 'Forbidden')

        self.set_header('Content-Type',
                        'multipart/x-mixed-replace;boundary="socketio; charset=UTF-8"')
        self.set_header('Connection', 'keep-alive')
        self.write('--socketio\n')

        # Dump any queued messages
        self.session.flush()

        # We need heartbeats
        #self.session.reset_heartbeat()

    def on_connection_close(self):
        if self.session:
            #self.session.stop_heartbeat()
            self.session.remove_handler(self)

    def send_messages(self, messages):
        data = proto.encode_frames(messages)

        self.preflight()
        self.write("Content-Type: text/plain; charset=UTF-8\n\n")
        self.write(data + '\n')
        self.write('--socketio\n')
        self.flush()

        #self.session.delay_heartbeat()


class TornadioHtmlFileHandler(TornadioPollingHandlerBase):
    """IE HtmlFile protocol implementation.

    Uses hidden frame to stream data from the server in one connection.

    Unfortunately, it is unknown if this transport works, as socket.io
    client-side fails in IE7/8.
    """
    @asynchronous
    def get(self, *args, **kwargs):
        if not self.session.set_handler(self):
            raise HTTPError(401, 'Forbidden')

        self.set_header('Content-Type', 'text/html; charset=UTF-8')
        self.set_header('Connection', 'keep-alive')
        self.set_header('Transfer-Encoding', 'chunked')
        self.write('<html><body>%s' % (' ' * 244))

        # Dump any queued messages
        self.session.flush()

        # We need heartbeats
        #self.session.reset_heartbeat()

    def on_connection_close(self):
        if self.session:
            #self.session.stop_heartbeat()
            self.session.remove_handler(self)

    def send_messages(self, messages):
        data = proto.encode_frames(messages)

        self.write(
            '<script>parent.s_(%s),document);</script>' % proto.json_dumps(data)
            )
        self.flush()

        #self.session.delay_heartbeat()


class TornadioJSONPHandler(TornadioXHRPollingHandler):
    def __init__(self, router, session_id):
        self._index = None
        super(TornadioJSONPHandler, self).__init__(router, session_id)

    @asynchronous
    def get(self, *args, **kwargs):
        self._index = kwargs.get('jsonp_index', None)
        super(TornadioJSONPHandler, self).get(*args, **kwargs)

    @asynchronous
    def post(self, *args, **kwargs):
        self._index = kwargs.get('jsonp_index', None)
        super(TornadioJSONPHandler, self).post(*args, **kwargs)

    def send_raw(self, messages):
        if not self._index:
            raise HTTPError(401, 'unauthorized')

        data = proto.encode_frames(messages)

        message = 'io.JSONP[%s]._(%s);' % (
            self._index,
            proto.json_dumps(data)
            )

        self.preflight()
        self.set_header("Content-Type", "text/javascript; charset=UTF-8")
        self.set_header("Content-Length", len(message))
        self.write(message)

        # Detach connection
        self._detach()

        self.finish()

