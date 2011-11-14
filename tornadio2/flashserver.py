# -*- coding: utf-8 -*-
#
# Copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
    tornadio2.flashserver
    ~~~~~~~~~~~~~~~~~~~~~

    Flash Socket policy server implementation. Merged with minor modifications
    from the SocketTornad.IO project.
"""
from __future__ import with_statement

import socket
import errno
import functools

from tornado import iostream


class FlashPolicyServer(object):
    """Flash Policy server, listens on port 843 by default (useless otherwise)
    """
    def __init__(self,
                 io_loop,
                 port=843,
                 policy_file='flashpolicy.xml'):
        """Constructor.

        `io_loop`
            IOLoop instance
        `port`
            Port to listen on (defaulted to 843)
        `policy_file`
            Policy file location
        """
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
