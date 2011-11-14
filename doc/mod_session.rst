``tornadio2.session``
=====================

Session
-------

.. automodule:: tornadio2.session

	.. autoclass:: Session

	Constructor
	^^^^^^^^^^^

	.. automethod:: Session.__init__

	Callbacks
	^^^^^^^^^

	.. automethod:: Session.on_delete

	Handlers
	^^^^^^^^

	.. automethod:: Session.set_handler
	.. automethod:: Session.remove_handler

	Output
	^^^^^^

	.. automethod:: Session.send_message
	.. automethod:: Session.flush

	State
	^^^^^

	.. automethod:: Session.close
	.. autoattribute:: Session.is_closed

	Heartbeats
	^^^^^^^^^^

	.. automethod:: Session.reset_heartbeat
	.. automethod:: Session.stop_heartbeat
	.. automethod:: Session.delay_heartbeat
	.. automethod:: Session._heartbeat

	Endpoints
	^^^^^^^^^

	.. automethod:: Session.connect_endpoint
	.. automethod:: Session.disconnect_endpoint

	Messages
	^^^^^^^^

	.. automethod:: Session.raw_message


	Connection information
	----------------------

	.. autoclass:: ConnectionInfo

		.. autoattribute: ip
		.. autoattribute: cookies
		.. autoattribute: arguments

		.. automethod:: get_argument
		.. automethod:: get_cookie
