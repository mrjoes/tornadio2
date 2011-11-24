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
    def __init__(self, period=60):
        self.period = period
        self.stream = deque()
        self.sum = 0
        self.accumulator = 0
        self.last_average = 0

    def add(self, n):
        self.accumulator += n

    def flush(self):
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
    def __init__(self):
        self.periodic_callback = None
        self.start_time = datetime.now()

        # Sessions
        self.active_sessions = 0

        # Packets
        self.avg_packets_sent = MovingAverage()
        self.avg_packets_recv = MovingAverage()

    def session_opened(self):
        self.active_sessions += 1

    def session_closed(self):
        self.active_sessions -= 1

    def on_packet_sent(self, num):
        self.avg_packets_sent.add(num)

    def on_packet_recv(self, num):
        self.avg_packets_recv.add(num)

    def dump(self):
        return dict(active_sessions=self.active_sessions,
                    avg_packets_sent=self.avg_packets_sent.last_average,
                    avg_packets_recv=self.avg_packets_recv.last_average
                )

    def _update_averages(self):
        print datetime.now()

        self.avg_packets_sent.flush()
        self.avg_packets_recv.flush()

    def start(self, io_loop):
        # If started, will collect averages every second
        self.periodic_callback = ioloop.PeriodicCallback(self._update_averages, 1000, io_loop)
        self.periodic_callback.start()
