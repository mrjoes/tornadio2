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
    tornadio2.stats
    ~~~~~~~~~~~~~~~

    Statistics module
"""
from datetime import datetime
from collections import deque

from tornado import ioloop


class MovingAverage(object):
    """Moving average class implementation"""
    def __init__(self, period=10):
        """Constructor.

        `period`
            Moving window size. Average will be calculated
            from the data in the window.
        """
        self.period = period
        self.stream = deque()
        self.sum = 0
        self.accumulator = 0
        self.last_average = 0

    def add(self, n):
        """Add value to the current accumulator

        `n`
            Value to add
        """
        self.accumulator += n

    def flush(self):
        """Add accumulator to the moving average queue
        and reset it. For example, called by the StatsCollector
        once per second to calculate per-second average.
        """
        n = self.accumulator
        self.accumulator = 0

        stream = self.stream
        stream.append(n)
        self.sum += n

        streamlen = len(stream)

        if streamlen > self.period:
            self.sum -= stream.popleft()
            streamlen -= 1

        if streamlen == 0:
            self.last_average = 0
        else:
            self.last_average = self.sum / float(streamlen)


class StatsCollector(object):
    """Statistics collector"""
    def __init__(self):
        self.periodic_callback = None
        self.start_time = datetime.now()

        # Sessions
        self.max_sessions = 0
        self.active_sessions = 0

        # Connections
        self.max_connections = 0
        self.active_connections = 0
        self.connections_ps = MovingAverage()

        # Packets
        self.packets_sent_ps = MovingAverage()
        self.packets_recv_ps = MovingAverage()

    # Sessions
    def session_opened(self):
        self.active_sessions += 1

        if self.active_sessions > self.max_sessions:
            self.max_sessions = self.active_sessions

    def session_closed(self):
        self.active_sessions -= 1

    # Connections
    def connection_opened(self):
        self.active_connections += 1

        if self.active_connections > self.max_connections:
            self.max_connections = self.active_connections

        self.connections_ps.add(1)

    def connection_closed(self):
        self.active_connections -= 1

    # Packets
    def on_packet_sent(self, num):
        self.packets_sent_ps.add(num)

    def on_packet_recv(self, num):
        self.packets_recv_ps.add(num)

    def dump(self):
        """Return current statistics"""
        return dict(
                # Sessions
                active_sessions=self.active_sessions,
                max_sessions=self.max_sessions,

                # Connections
                active_connections=self.active_connections,
                max_connections=self.max_connections,
                connections_ps=self.connections_ps.last_average,

                # Packets
                packets_sent_ps=self.packets_sent_ps.last_average,
                packets_recv_ps=self.packets_recv_ps.last_average
                )

    def _update_averages(self):
        self.packets_sent_ps.flush()
        self.packets_recv_ps.flush()
        self.connections_ps.flush()

    def start(self, io_loop):
        # If started, will collect averages every second
        self.periodic_callback = ioloop.PeriodicCallback(self._update_averages, 1000, io_loop)
        self.periodic_callback.start()
