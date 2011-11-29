Events
======

Instead of having "just" messages, socket.io 0.7 introduced new concept of events.
Event is just a name and collection of parameters.

TornadIO2 provides easy-to-use syntax sugar which emulates RPC calls from the client
to your python code. Check following example:
::

    class MyConnection(SocketConnection):
        @event('hello')
        def test(self, name):
            print 'Hello %s' % name

            self.emit('thanks', name=name)
            self.emit('hello', name, 'foobar')

In your client code, to call this event, do something like:
::

    sock.emit('hello', {name: 'Joes'});

You can also use positional parameters. For previous example, you can also do something like:
::

    sock.emit('hello', 'Joes')

To handle event on client side, use following code:
::

    sock.on('thanks', function(data) {
        alert(data.name);
    });
    sock.on('hello', function(name, dummy) {
        alert('Hey ' + name + ' ' + dummy);
    });

However, take care - if method signature does not match (missing parameters, extra
parameters, etc), your connection will blow up and self destruct.

``event`` decorator can be used without parameter and it will use event handler name
in this case::

    class MyConnection(SocketConnection):
        @event
        def hello(self, name):
            print 'Hello %s' % name

If you don't like this event handling approach, just override ``on_event`` in your
socket connection class and handle them by yourself:
::

    class MyConnection(SocketConnection):
        def on_event(self, name, *args, **kwargs):
            if name == 'hello':
                print 'Hello %s' % (kwargs['name'])

            self.emit('thanks', name=kwargs['name'])

There's also some magic involved in event message parsing to make it easier to work
with events.

If you send data from client using following code:
::

    sock.emit('test', {a: 10, b: 10});


TornadIO2 will unpack dictionary into ``kwargs`` parameters and pass it to the
``on_event`` handler. However, if you pass more than one parameter, Tornadio2 won't
unpack them into ``kwargs`` and will just pass parameters as ``args``. For example, this
code will lead to ``args`` being passed to ``on_event`` handler:
::

    sock.emit('test', 1, 2, 3, {a: 10, b: 10});
