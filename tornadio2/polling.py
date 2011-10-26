# -*- coding: utf-8 -*-
"""
    tornadio2.polling
    ~~~~~~~~~~~~~~~~~

    This module implements socket.io polling transports.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import time

from urllib import unquote
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

        print 'Execute!'

        super(TornadioPollingHandlerBase, self)._execute(transforms,
                                                         *args, **kwargs)

    @asynchronous
    def get(self, *args, **kwargs):
        """Default GET handler."""
        raise NotImplementedError()

    @asynchronous
    def post(self, *args, **kwargs):
        """Default POST handler."""
        raise NotImplementedError()

    def raw_send(self, raw_data):
        """Called by the session when some data is available"""
        raise NotImplementedError()

    @asynchronous
    def options(self, *args, **kwargs):
        """XHR cross-domain OPTIONS handler"""
        self.preflight()
        self.finish()

    def preflight(self):
        """Handles request authentication"""
        if self.request.headers.has_key('Origin'):
            if self.verify_origin():
                self.set_header('Access-Control-Allow-Origin',
                                self.request.headers['Origin'])

                if self.request.headers.has_key('Cookie'):
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

class TornadioXHRPollingSocketHandler(TornadioPollingHandlerBase):
    def initialize(self, server):
        super(TornadioXHRPollingSocketHandler, self).initialize(server)

        self._timeout = None
        self._timeout_interval = self.server.settings['xhr_polling_timeout']

    @asynchronous
    def get(self, *args, **kwargs):
        try:
            if not self.session.set_handler(self):
                # Check to avoid double connections
                # TODO: Error logging
                raise HTTPError(401, 'Forbidden')

            print '1'

            if not self.session.send_queue:
                self._timeout = self.server.io_loop.add_timeout(
                    time.time() + self._timeout_interval,
                    self._polling_timeout)
            else:
                self.session.flush()

            print 'done'
        except Exception, p:
            import traceback
            traceback.print_exc()
            print p

    def _polling_timeout(self):
        try:
            self.raw_send([proto.noop()])
        except Exception, p:
            print p
        finally:
            self._detach()

    @asynchronous
    def post(self, *args, **kwargs):
        if not self.preflight():
            raise HTTPError(401, 'unauthorized')

        print 'POST'

        # Special case for IE XDomainRequest
        ctype = self.request.headers.get("Content-Type", "").split(";")[0]
        if ctype == '':
            data = None
            body = self.request.body

            if body.startswith('data='):
                data = unquote(body[5:])
        else:
            data = self.request.body

        print 'Data: ', repr(data)

        # Process packets one by one
        packets = proto.decode_frames(data)
        for p in packets:
            try:
                self.session.raw_message(p)
            except Exception, ex:
                print ex

        self.set_header('Content-Type', 'text/plain; charset=UTF-8')
        self.write('ok')
        self.finish()

    def _detach(self):
        if self.session:
            self.session.remove_handler(self)
            self.session = None

    def on_connection_close(self):
        self._detach()

    def raw_send(self, raw_data):
        # Encode multiple messages as UTF-8 string
        data = proto.encode_frames(raw_data)

        print repr(data)

        # Dump messages
        self.preflight()
        self.set_header('Content-Type', 'text/plain; charset=UTF-8')
        self.set_header('Content-Length', len(data))
        self.write(data)

        # Detach connection
        self._detach()

        self.finish()
