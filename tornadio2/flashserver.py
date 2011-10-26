# -*- coding: utf-8 -*-
"""
    tornadio2.flashserver
    ~~~~~~~~~~~~~~~~~~~~~

    Flash Socket policy server implementation. Merged with minor modifications
    from the SocketTornad.IO project.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
from __future__ import with_statement

import socket
import errno
import functools

from tornado import iostream

class FlashPolicyServer(object):
    """Flash Policy server, listens on port 843 by default (useless otherwise)
    """
    def __init__(self, io_loop, port=843, policy_file='flashpolicy.xml'):
        self.policy_file = policy_file
        self.port = port

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(0)
        sock.bind(('', self.port))
        sock.listen(128)

        self.io_loop = io_loop
        callback = functools.partial(self.connection_ready, sock)
        self.io_loop.add_handler(sock.fileno(), callback, self.io_loop.READ)

    def connection_ready(self, sock, _fd, _events):
        """Connection ready callback"""
        while True:
            try:
                connection, address = sock.accept()
            except socket.error, ex:
                if ex[0] not in (errno.EWOULDBLOCK, errno.EAGAIN):
                    raise
                return
            connection.setblocking(0)
            self.stream = iostream.IOStream(connection, self.io_loop)
            self.stream.read_bytes(22, self._handle_request)

    def _handle_request(self, request):
        """Send policy response"""
        if request != '<policy-file-request/>':
            self.stream.close()
        else:
            with open(self.policy_file, 'rb') as file_handle:
                self.stream.write(file_handle.read() + '\0')
