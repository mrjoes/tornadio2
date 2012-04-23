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
    tornadio2.gen
    ~~~~~~~~~~~~~

    Generator-based interface to make it easier to work in an asynchronous environment.
"""

import functools
import types

from collections import deque

from tornado.gen import engine, Runner, Task, Wait, WaitAll, Callback


class SyncRunner(Runner):
    """Customized ``tornado.gen.Runner``, which will notify callback about
    completion of the generator.
    """
    def __init__(self, gen, callback):
        """Constructor.

        `gen`
            Generator
        `callback`
            Function that should be called upon generator completion
        """
        self._callback = callback

        super(SyncRunner, self).__init__(gen)

    def run(self):
        """Overloaded run function"""
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
    """Queued version of the ``tornado.gen.engine``.

    Prevents calling of the wrapped function if there is already one instance of
    the function running asynchronously. Function will be called synchronously
    without blocking io_loop.

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
            else:
                return gen

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
