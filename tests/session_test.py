from collections import deque

from nose.tools import eq_, raises

from tornadio2 import session, proto, conn, stats

from simplejson import JSONDecodeError


class DummyRequest(object):
    def __init__(self, **kwargs):
        self.arguments = kwargs
        self.cookies = dict()
        self.remote_ip = '127.0.0.1'


class DummyServer(object):
    def __init__(self, conn):
        self._connection = conn
        self.settings = dict(
                session_check_interval=15,
                session_expiry=30,
                heartbeat_interval=12,
                enabled_protocols=['websocket', 'flashsocket', 'xhr-polling',
                                   'jsonp-polling', 'htmlfile'],
                xhr_polling_timeout=20
        )
        self.stats = stats.StatsCollector()

    def create_session(self, handler):
        return session.Session(self._connection,
                               self,
                               handler,
                               self.settings.get('session_expiry'))


class DummyTransport(object):
    def __init__(self, session, request):
        self.session = session
        self.request = request

        self.outgoing = deque()
        self.is_open = True

    def send_messages(self, messages):
        self.outgoing.extend(messages)

    def session_closed(self):
        self.is_open = False

    # Manipulation
    def recv(self, message):
        self.session.raw_message(message)

    def pop_outgoing(self):
        return self.outgoing.popleft()


class DummyConnection(conn.SocketConnection):
    def __init__(self, session, endpoint=None):
        super(DummyConnection, self).__init__(session, endpoint)

        self.is_open = False

        self.incoming = deque()
        self.events = deque()

        self.request = None

    def on_open(self, request):
        self.is_open = True

        self.request = request

    def on_message(self, message):
        self.incoming.append(message)
        self.send(message)

    def on_event(self, name, args=[], kwargs=dict()):
        if args:
            self.events.append((name, args))
            self.emit(name, *args)        
        else:
            self.events.append((name, kwargs))
            self.emit(name, **kwargs)
        return name

    def on_close(self):
        self.is_open = False

    def get_endpoint(self, name):
        return DummyConnection

    # Helpers
    def pop_incoming(self):
        return self.incoming.popleft()

    def pop_event(self):
        return self.events.popleft()


class EventConnection(conn.SocketConnection):
    @conn.event('test')
    def test(self, a, b):
        self.emit('test', a=a, b=b)


def _get_test_environment(conn=None, **kwargs):
    # Create test environment
    request = DummyRequest(**kwargs)

    server = DummyServer(conn or DummyConnection)
    session = server.create_session(request)
    transport = DummyTransport(session, request)

    conn = session.conn

    # Attach handler and check if it was attached
    session.set_handler(transport)
    eq_(session.handler, transport)

    # Check if connection event was submitted
    session.flush()
    eq_(transport.pop_outgoing(), '1::')

    return server, session, transport, conn


def test_session_attach():
    # Create environment
    server, session, transport, conn = _get_test_environment(a=[10])

    # Check if connection opened
    eq_(conn.is_open, True)
    eq_(conn.request.arguments, {'a': [10]})
    eq_(conn.request.get_argument('a'), 10)

    # Send message and check if it was handled by connection
    transport.recv(proto.message(None, 'abc'))

    # Check if incoming queue has abc
    eq_(conn.pop_incoming(), 'abc')

    # Check if outgoing transport has abc
    eq_(transport.pop_outgoing(), '3:::abc')

    # Close session
    conn.close()

    # Check if it sent disconnect packet to the client
    eq_(transport.pop_outgoing(), '0::')

    # Detach
    session.remove_handler(transport)
    eq_(session.handler, None)

    # Check if session is still open
    eq_(transport.is_open, False)
    eq_(conn.is_open, False)
    eq_(session.is_closed, True)


def test_client_disconnect():
    # Create environment
    server, session, transport, conn = _get_test_environment()

    # Send disconnect message
    transport.recv(proto.disconnect())

    # Check if connection was closed
    eq_(transport.pop_outgoing(), '0::')

    eq_(conn.is_open, False)
    eq_(session.is_closed, True)


def test_json():
    # Create environment
    server, session, transport, conn = _get_test_environment()

    # Send json message
    transport.recv(proto.message(None, dict(a=10, b=20)))

    # Check incoming message
    eq_(conn.pop_incoming(), dict(a=10, b=20))

    # Check outgoing message
    eq_(transport.pop_outgoing(), proto.message(None, dict(a=10, b=20)))


def test_event():
    # Create environment
    server, session, transport, conn = _get_test_environment()

    # Send event
    transport.recv(proto.event(None, 'test', None, a=10, b=20))

    # Send event with multiple parameters
    transport.recv('5:::{"name":"test", "args":[10, 20]}')

    # Check incoming
    eq_(conn.pop_event(), ('test', dict(a=10, b=20)))

    # Check outgoing
    eq_(transport.pop_outgoing(), proto.event(None, 'test', None, a=10, b=20))


@raises(TypeError)
def test_failed_event():
    # Create environment
    server, session, transport, conn = _get_test_environment(EventConnection)

    # Send event
    transport.recv(proto.event(None, 'test', None, a=10, b=20))

    # Check response
    eq_(transport.pop_outgoing(), proto.event(None, 'test', None, a=10, b=20))

    # Throw invalid event
    transport.recv(proto.event(None, 'test', None, a=10))


@raises(JSONDecodeError)
def test_json_error():
    # Create environment
    server, session, transport, conn = _get_test_environment()

    # Send malformed JSON message
    transport.recv('4:::{asd')


def test_endpoint():
    # Create environment
    server, session, transport, conn = _get_test_environment()

    # Connect endpoint
    transport.recv(proto.connect('/test?a=123&b=456'))

    # Verify that client received connect message
    eq_(transport.pop_outgoing(), '1::/test')

    # Verify that connection object was created
    conn_test = session.endpoints['/test']
    eq_(conn_test.endpoint, '/test')
    eq_(conn_test.is_open, True)
    eq_(conn_test.request.arguments, dict(a=['123'], b=['456']))
    eq_(conn_test.request.get_argument('a'), '123')

    # Send message to endpoint and verify that it was received
    transport.recv(proto.message('/test', 'abc'))
    eq_(conn_test.pop_incoming(), 'abc')
    eq_(transport.pop_outgoing(), '3::/test:abc')

    # Close endpoint connection from client
    transport.recv(proto.disconnect('/test'))

    # Verify that everything was cleaned up
    eq_(transport.pop_outgoing(), '0::/test')
    eq_(conn_test.is_open, False)
    eq_(conn.is_open, True)
    eq_(session.is_closed, False)

    eq_(session.endpoints, dict())

    # Open another endpoint connection
    transport.recv(proto.connect('/test2'))

    # Verify that client received connect message
    eq_(transport.pop_outgoing(), '1::/test2')

    # Get connection
    conn_test = session.endpoints['/test2']
    eq_(conn_test.request.arguments, dict())

    # Close main connection
    transport.recv(proto.disconnect())

    # Check if connections were closed and sent out
    eq_(transport.pop_outgoing(), '0::/test2')
    eq_(transport.pop_outgoing(), '0::')

    eq_(conn_test.is_open, False)
    eq_(conn.is_open, False)
    eq_(session.is_closed, True)


def test_invalid_endpoint():
    # Create environment
    server, session, transport, conn = _get_test_environment()

    # Send message to unconnected endpoint
    transport.recv(proto.message('test', 'abc'))

    # Check if message was received by default endpoint
    eq_(len(conn.incoming), 0)


def test_ack():
    # Create environment
    server, session, transport, conn = _get_test_environment()

    # Send message with ACK
    transport.recv(proto.message(None, 'abc', 1))

    # Check that message was received by the connection
    eq_(conn.pop_incoming(), 'abc')

    # Check for ACK
    eq_(transport.pop_outgoing(), '3:::abc')
    eq_(transport.pop_outgoing(), '6:::1')

    # Send with ACK
    def handler(msg, data):
        eq_(msg, 'abc')
        eq_(data, None)

        conn.send('yes')

    conn.send('abc', handler)

    eq_(transport.pop_outgoing(), '3:1::abc')

    # Send ACK from client
    transport.recv('6:::1')

    # Check if handler was called
    eq_(transport.pop_outgoing(), '3:::yes')

    # Test ack with event
    # Send event with multiple parameters
    transport.recv(proto.event(None, 'test', 1, a=10, b=20))

    # Check outgoing
    eq_(transport.pop_outgoing(), proto.event(None, 'test', None, a=10, b=20))
    eq_(transport.pop_outgoing(), proto.ack(None, 1, 'test'))
