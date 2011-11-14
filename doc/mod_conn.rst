``tornadio2.conn``
==================

Connection
----------

.. automodule:: tornadio2.conn

	.. autoclass:: SocketConnection

	Callbacks
	^^^^^^^^^

	.. automethod:: SocketConnection.on_open
	.. automethod:: SocketConnection.on_message
	.. automethod:: SocketConnection.on_event
	.. automethod:: SocketConnection.on_close

	Output
	^^^^^^

	.. automethod:: SocketConnection.send
	.. automethod:: SocketConnection.emit
	.. automethod:: SocketConnection.emit_ack

	Management
	^^^^^^^^^^

	.. automethod:: SocketConnection.close

	Endpoint management
	^^^^^^^^^^^^^^^^^^^

	.. automethod:: SocketConnection.get_endpoint

	Other
	^^^^^

	.. automethod:: SocketConnection.deque_ack


Events
------

.. autofunction:: tornadio2.conn.event
