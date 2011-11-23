Acknowledgments
===============

New feature of the socket.io 0.7+. When you send message to the client,
you now have way to get notified when client receives the message. To use this, pass a
callback function when sending a message::

    class MyConnection(SocketConnection):
        def on_message(self, msg):
            self.send(msg, self.my_callback)

        def my_callback(self, msg, ack_data):
            print 'Got ack for my message: %s' % message

``ack_data`` contains acknowledgment data sent from the client, if any.

To send event with acknowledgement, use ``SocketConnection.emit_ack`` method::

    class MyConnection(SocketConnection):
        def on_message(self, msg):
            self.emit_ack(self.my_callback, 'hello')

        def my_callback(self, event, ack_data):
            print 'Got ack for my message: %s' % msg

If you want to send reverse confirmation with a message, just return value you want to send
from your event handler::

    class MyConnection(SocketConnection):
        @event('test')
        def test(self):
            return 'Joes'

and then, in your javascript code, you can do something like::

    sock.emit('test', function(data) {
        console.log(data);  // data will be 'Joes'
    });

If you want to return multiple arguments, return them as tuple::

    class MyConnection(SocketConnection):
        @event('test')
        def test(self):
            return 'Joes', 'Mike', 'Mary'

On client-side, you can access them by doing something like::

    sock.emit('test', function(name1, name2, name3) {
        console.log(name1, name2, name3);  // data will be 'Joes'
    });
