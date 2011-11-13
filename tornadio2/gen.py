# -*- coding: utf-8 -*-
"""
    tornadio2.gen
    ~~~~~~~~~~~~~

    Generator-based interface to maek it easier to work in an asynchronous environment.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""

import functools
import types

from collections import deque

from tornado.gen import engine, Runner, Task, Wait, WaitAll, Callback


class SyncRunner(Runner):
    """Overloaded ``tornado.gen.Runner`` with callback upon run completion
    """
    def __init__(self, gen, callback):
        self._callback = callback

        super(SyncRunner, self).__init__(gen)

    def run(self):
        if self.running or self.finished:
            return

        try:
            super(SyncRunner, self).run()
        finally:
            if self.finished:
                self._callback()


class CallQueue(object):
    __slots__ = ('runner', 'queue')

    def __init__(self):
        self.runner = None
        self.queue = deque()


def sync_engine(func):
    """Queued version of the ``gen.engine``.

    Prevents calling of the wrapped function if it was not completed before.
    Basically, function will be called synchronously without blocking io_loop.

    This decorator can only be used on class methods, as it requires ``self``
    to make sure that calls are scheduled on instance level (connection) instead
    of class level (method).
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # Run method
        def run(args, kwargs):
            gen = func(self, *args, **kwargs)
            if isinstance(gen, types.GeneratorType):
                data.runner = SyncRunner(gen, finished)
                data.runner.run()

        # Completion callback
        def finished():
            data.runner = None

            try:
                args, kwargs = data.queue.popleft()
                run(args, kwargs)
            except IndexError:
                pass

        # Get call queue for this instance and wrapped method
        queue = getattr(self, '_call_queue', None)
        if queue is None:
            queue = self._call_queue = dict()

        data = queue.get(func, None)
        if data is None:
            queue[func] = data = CallQueue()

        # If there's something running, queue call
        if data.runner is not None:
            data.queue.append((args, kwargs))
        else:
            # Otherwise run it
            run(args, kwargs)

    return wrapper
