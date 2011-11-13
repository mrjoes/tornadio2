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


def sync_engine(func):
    """Queued version of the ``gen.engine``.

    Prevents calling of the wrapped function if it was not completed before.
    Basically, function will be called synchronously without blocking io_loop.
    """
    def finished():
        data[0] = None

        try:
            args, kwargs = data[1].popleft()

            gen = func(*args, **kwargs)
            if isinstance(gen, types.GeneratorType):
                data[0] = SyncRunner(gen, finished)
                data[0].run()
        except IndexError:
            pass

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if data[0] is not None:
            data[1].append((args, kwargs))
        else:
            gen = func(*args, **kwargs)
            if isinstance(gen, types.GeneratorType):
                data[0] = SyncRunner(gen, finished)
                data[0].run()

    # TODO: use namedtuple in the future
    # 0 = current engine
    # 1 = call queue
    data = [None, deque()]
    return wrapper
