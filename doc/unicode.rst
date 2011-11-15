Unicode
=======

TornadIO2 supports unicode for all transports. When you send something, it will be automatically
converted to the unicode (assuming that it is not unicode already).

Few rules:

1. ``send`` has following logic in place:

	- If message is object or dictionary, it will be json encoded into unicode string

	- If message is unicode, it will be sent as is

	- If message is non-unicode, not an object and not a dictionary, it will be converted to string
	  and converted to unicode using utf-8 encoding. If your string is in some other encoding (multi-byte, etc),
	  it is up for you to handle encoding and pass your data in unicode (or utf-8 encoded).

2. ``emit`` has similar logic:

	- It will convert event name into unicode string (if it is not). It is expected that event name
	  will only use latin characters

	- All ``emit`` arguments will be json encoded into unicode string

3. All incoming messages will be automatically converted to unicode strings. You can expect to receive unicode
strings in your message handler and events.
