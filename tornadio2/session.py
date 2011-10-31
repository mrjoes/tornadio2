import urlparse
import time
import logging

from tornadio2 import sessioncontainer, proto, periodic


class Session(sessioncontainer.SessionBase):
    def __init__(self, conn, server, session_id=None, expiry=None):
        # Initialize session
        super(Session, self).__init__(session_id, expiry)

        self.server = server
        self.send_queue = []
        self.handler = None

        # Create connection instance
        self.conn = conn(self)
        self.send_message(proto.connect())

        # Heartbeat related stuff
        self._heartbeat_timer = None
        self._heartbeat_interval = self.server.settings['heartbeat_interval'] * 1000
        self._missed_heartbeats = 0

        # Endpoints
        self.endpoints = dict()

    def open(self, *args, **kwargs):
        self.conn.on_open(*args, **kwargs)

    # Session callbacks
    def on_delete(self, forced):
        # Do not remove connection if it was not forced and there's running connection
        if not forced and self.handler is not None and not self.is_closed:
            self.promote()
        else:
            self.close()

    # Add session
    def set_handler(self, handler, *args, **kwargs):
        if self.handler is not None:
            # Attempted to override handler
            return False

        self.handler = handler
        self.promote()

        return True

    def remove_handler(self, handler):
        if self.handler != handler:
            raise Exception('Attempted to remove invalid handler')

        self.handler = None
        self.promote()

    def send_message(self, pack):
        logging.debug('<<< ' + pack)

        self.send_queue.append(pack)
        self.flush()

    def flush(self):
        if self.handler is None:
            return

        if not self.send_queue:
            return

        self.handler.send_messages(self.send_queue)

        self.send_queue = []

        # If session was closed, detach connection
        if self.is_closed:
            self.handler.session_closed()

    # Close connection with all endpoints or just one endpoint
    def close(self, endpoint=None):
        if endpoint is None:
            if not self.conn.is_closed:
                # Close child connections
                for k in self.endpoints.keys():
                    self.disconnect_endpoint(k)

                # Close parent connections
                try:
                    self.conn.on_close()
                finally:
                    self.conn.is_closed = True

                # Send disconnection message
                self.send_message(proto.disconnect())

                # Notify transport that session was closed
                if self.handler is not None:
                    self.handler.session_closed()
        else:
            self.disconnect_endpoint(endpoint)

    @property
    def is_closed(self):
        return self.conn.is_closed

    # Heartbeats
    def reset_heartbeat(self):
        self.stop_heartbeat()

        self._heartbeat_timer = periodic.Callback(self._heartbeat,
                                                  self._heartbeat_interval,
                                                  self.io_loop)
        self._heartbeat_timer.start()

    def stop_heartbeat(self):
        if self._heartbeat_timer is not None:
            self._heartbeat_timer.stop()
            self._heartbeat_timer = None

    def delay_heartbeat(self):
        if self._heartbeat_timer is not None:
            self._heartbeat_timer.delay()

    def _heartbeat(self):
        self.send_message(proto.heartbeat())

        self._missed_heartbeats += 1

        # TODO: Configurable
        if self._missed_heartbeats > 5:
            self.close()

    # Endpoints
    def connect_endpoint(self, url):
        urldata = urlparse.urlparse(url)

        endpoint = urldata.path

        conn_class = self.conn.get_endpoint(endpoint)
        if conn_class is None:
            logging.error('There is no handler for endpoint %s' % endpoint)
            return

        conn = conn_class(self, endpoint)
        self.endpoints[endpoint] = conn

        self.send_message(proto.connect(endpoint))

        args = urlparse.parse_qs(urldata.query)

        # TODO: Add support for multiple arguments with same name
        final_args = dict((k,v[0]) for k,v in args.iteritems()) 

        conn.on_open(**final_args)

    def disconnect_endpoint(self, endpoint):
        if endpoint not in self.endpoints:
            logging.error('Invalid endpoint for disconnect %s' % endpoint)
            return

        conn = self.endpoints[endpoint]

        del self.endpoints[endpoint]

        conn.on_close()
        self.send_message(proto.disconnect(endpoint))

    def get_connection(self, endpoint):
        if endpoint:
            return self.endpoints.get(endpoint)
        else:
            return self.conn

    # Message handler
    def raw_message(self, msg):
        try:
            logging.debug('>>> ' + msg)

            parts = msg.split(':', 3)

            msg_type = parts[0]
            msg_id = parts[1]
            msg_endpoint = parts[2]
            msg_data = None
            if len(parts) > 3:
                msg_data = parts[3]

            # Packets that don't require valid connection
            if msg_type == proto.DISCONNECT:
                if not msg_endpoint:
                    self.close()
                else:
                    self.disconnect_endpoint(msg_endpoint)
                return
            elif msg_type == proto.CONNECT:
                if msg_endpoint:
                    self.connect_endpoint(msg_endpoint)
                else:
                    # TODO: Disconnect?
                    logging.error('Invalid connect without endpoint')
                return

            # All other packets need endpoints
            conn = self.get_connection(msg_endpoint)
            if conn is None:
                logging.error('Invalid endpoint: %s' % msg_endpoint)
                return

            if msg_type == proto.HEARTBEAT:
                self._missed_heartbeats = 0
            elif msg_type == proto.MESSAGE:
                # Handle text message
                conn.on_message(msg_data)

                if msg_id:
                    self.send_message(proto.ack(msg_endpoint, msg_id))
            elif msg_type == proto.JSON:
                # Handle json message
                conn.on_message(proto.json_load(msg_data))

                if msg_id:
                    self.send_message(proto.ack(msg_endpoint, msg_id))
            elif msg_type == proto.EVENT:
                # Javascript event
                event = proto.json_load(msg_data)
                conn.on_event(event['name'], **event['args'])

                if msg_id:
                    self.send_message(proto.ack(msg_endpoint, msg_id))
            elif msg_type == proto.ACK:
                # Handle ACK
                ack_data = msg_data.split('+', 2)

                # TODO: Support custom data sent from the server
                conn.deque_ack(int(ack_data[0]))
            elif msg_type == proto.ERROR:
                # TODO: Pass it to handler?
                logging.error('Incoming error: %s' % msg_data)            
            elif msg_type == proto.NOOP:
                pass
        except Exception, ex:
            logging.exception(ex)

            # TODO: Add global exception callback?

            raise