Acknowledgments
===============

New feature of the socket.io 0.7+. When you send message to the client,
you now have way to get notified when client receives the message. To use this, pass a
callback function when sending a message:
::

    class MyConnection(SocketConnection):
        def on_message(self, msg):
            self.send(msg, self.my_callback)

        def my_callback(self, msg):
            print 'Got ack for my message: %s' % message


To send event with acknowledgement, use ``SocketConnection.emit_ack`` method:
::

    class MyConnection(SocketConnection):
        def on_message(self, msg):
            self.emit_ack(self.my_callback, 'hello')

        def my_callback(self, event):
            print 'Got ack for my message: %s' % msg
