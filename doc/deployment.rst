Deployment
==========

Going big
---------

So, you've finished writting your application and want to share it with rest of the world, so you started
thinking about scalability, deployment options, etc.

Most of the Tornado servers are deployed behind the nginx, which also used to serve static content. Unfortunately,
older versions of the nginx did not support HTTP 1.1 and as a result, proxying of the websocket connections
did not work. However, starting from nginx 1.1 there's support of HTTP 1.1 protocol and websocket proxying
works. You can get more information `here <https://github.com/LearnBoost/socket.io/wiki/Nginx-and-Socket.io>`_.

Alternative solution is to use `HAProxy <http://haproxy.1wt.eu/>`_.
Sample HAProxy configuration file can be found `here <http://stackoverflow.com/questions/4360221/haproxy-websocket-disconnection/4737648#4737648>`_.
You can hide your application and TornadIO instances behind one HAProxy instance running on one port
to avoid cross-domain AJAX calls, which ensures greater compatibility.

However, HAProxy does not work on Windows, so if you plan to deploy your solution on Windows platform,
you might want to take look into `MLB <http://support.microsoft.com/kb/240997>`_.


Scalability
-----------

Scalability is completely different beast. It is up for you, as a developer, to design scalable architecture
of the application.

For example, if you need to have one large virtual server out of your multiple physical processes (or even servers),
you have to come up with some kind of the synchronization mechanism. This can be either common meeting point
(and also point of failure), like memcached, redis, etc. Or you might want to use some transporting mechanism to
communicate between servers, for example something `AMQP <http://www.amqp.org/>`_ based, `ZeroMQ <zeromq.org>`_ or
just plain sockets with your custom protocol.


Performance
-----------

Unfortunately, TornadIO2 was not properly benchmarked and this is something that will be accomplished in the future.
