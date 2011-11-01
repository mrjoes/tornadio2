# -*- coding: utf-8 -*-
"""
    tornadio.flashserver
    ~~~~~~~~~~~~~~~~~~~~

    This module implements customized PeriodicCallback from tornado with
    support of the sliding window.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import time
import logging


class Callback(object):
    """Custom implementation of the Tornado.Callback with support
    of callback delays.
    """
    def __init__(self, callback, callback_time, io_loop):
        self.callback = callback
        self.callback_time = callback_time
        self.io_loop = io_loop
        self._running = False

        self.next_run = None

    def calculate_next_run(self):
        return time.time() + self.callback_time / 1000.0

    def start(self, timeout=None):
        self._running = True

        if timeout is None:
            timeout = self.calculate_next_run()

        self.io_loop.add_timeout(timeout, self._run)

    def stop(self):
        self._running = False

    def delay(self):
        self.next_run = self.calculate_next_run()

    def _run(self):
        if not self._running:
            return

        # Support for shifting callback window
        if self.next_run is not None and time.time() < self.next_run:
            self.start(self.next_run)
            self.next_run = None
            return

        next_call = None
        try:
            next_call = self.callback()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            logging.error("Error in periodic callback", exc_info=True)

        if self._running:
            self.start(next_call)
