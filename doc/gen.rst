======================================
Generator-based asynchronous interface
======================================

``tornadio2.gen`` module is a wrapper around ``tornado.gen`` API. You might want to take a
look at Tornado documentation for this module, which can be `found here <http://www.tornadoweb.org/documentation/gen.html>`_.

In most of the cases, it is not very convenient to use Tornado ``engine()``, because it makes your code truly
asynchronous. For example, if client sends two packets: A and B, and if it takes some time for A to handle, B will be executed
out of order.

To prevent this situation, TornadIO2 provides helpful decorator: ``tornadio2.gen.sync_engine``. ``sync_engine`` will queue incoming
calls if there's another instance of the function running. So, as a result, it will call your method synchronously without
blocking the io_loop. This decorator only works with class methods, don't try to use it for functions - it requires ``self``
to properly function.

Lets check following example:
::

    from tornadio2 import gen

    class MyConnection(SocketConnection):
        @gen.sync_engine
        def on_message(self, query):
            http_client = AsyncHTTPClient()
            response = yield gen.Task(http_client.fetch, 'http://google.com?q=' + query)
            self.send(response.body)

If client will quickly send two messages, it will work "synchronously" - ``on_message`` won't be called for second message
till handling of first message is finished.

However, if you will change decorator to ``gen.engine``, message handling will be asynchronous and might be out of order:
::

    from tornadio2 import gen

    class MyConnection(SocketConnection):
        @gen.sync_engine
        def on_message(self, query):
            http_client = AsyncHTTPClient()
            response = yield gen.Task(http_client.fetch, 'http://google.com?q=' + query)
            self.send(response.body)

If client will quickly send two messages, server will send response as soon as response is ready and if it takes longer to
handle first message, response for second message will be sent first.

As a nice feature, you can also decorate your event handlers or even wrap main ``on_event`` method, so
all events can be synchronous when using asynchronous calls.

``tornadio2.gen`` API will only work with the ``yield`` based methods (methods that produce generators). If you implement your
asynchronous code using explicit callbacks, it is up for you how to synchronize order of the execution for them.

TBD: performance considerations, python iterator performance.
