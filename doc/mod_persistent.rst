``tornadio2.persistent``
========================

Persistent transports
---------------------

.. automodule:: tornadio2.persistent

	.. autoclass:: TornadioWebSocketHandler

	Callbacks
	^^^^^^^^^

	.. automethod:: TornadioWebSocketHandler.open
	.. automethod:: TornadioWebSocketHandler.on_message
	.. automethod:: TornadioWebSocketHandler.on_close

	.. automethod:: TornadioWebSocketHandler.session_closed

	Output
	^^^^^^

	.. automethod:: TornadioWebSocketHandler.send_messages

	.. autoclass:: TornadioFlashSocketHandler
