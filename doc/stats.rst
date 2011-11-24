Statistics
==========

TornadIO2 captures some counters:

================== =======================================
Name               Description
================== =======================================
**Sessions**
----------------------------------------------------------
max_sessions       Maximum number of sessions
active_sessions    Number of currently active sessions

**Connections**
----------------------------------------------------------
max_connections    Maximum number of connections
active_connections Number of currently active connections
connections_ps     Number of opened connections per second

**Packets**
----------------------------------------------------------
packets_sent_ps    Packets sent per second
packets_recv_ps    Packets received per second
================== =======================================

Stats are captured by the router object and can be accessed
through the ``stats`` property::

	MyRouter = tornadio2.TornadioRouter(MyConnection)

	print MyRouter.stats.dump()

For more information, check stats module API or ``stats``
example.
