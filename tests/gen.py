# -*- coding: utf-8 -*-
"""
    tornadio2.tests.gen
    ~~~~~~~~~~~~~~~~~~~

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""

from collections import deque

from nose.tools import eq_

from tornadio2 import gen

_queue = None
_v = None


def init_environment():
    global _queue, _v
    _queue = deque()
    _v = None


def dummy_sync(test, callback):
    callback(test)


def dummy_async(test, callback):
    global _queue
    _queue.append((callback, test))


def run_async():
    global _queue
    callback = _queue.popleft()
    callback[0](callback[1])


def run_async_oor():
    global _queue
    callback = _queue.pop()
    callback[0](callback[1])


def test():
    global _v
    _v = None

    @gen.sync_engine
    def func(value):
        global _v

        _v = yield gen.Task(dummy_sync, value)

    # Call function
    func('test')

    eq_(_v, 'test')


def test_async():
    global _v
    _v = None

    init_environment()

    @gen.sync_engine
    def func(value):
        global _v

        _v = yield gen.Task(dummy_async, value)

    # Call function
    func('test')

    # Finish it
    run_async()

    # Verify value
    eq_(_v, 'test')


def test_sync_queue():
    global _v

    init_environment()

    # Prepare result queue
    _v = []

    @gen.sync_engine
    def func(value):
        global _v

        _v.append((yield gen.Task(dummy_async, value)))

    # Call function three times
    func('1')
    func('2')
    func('3')

    # Finish it
    run_async()
    run_async()
    run_async()

    # Verify value
    eq_(_v, ['1', '2', '3'])


def test_sync_queue_oor():
    global _v

    init_environment()

    # Prepare result queue
    _v = []

    @gen.sync_engine
    def func(value):
        global _v

        _v.append((yield gen.Task(dummy_async, value)))

    # Call function three times
    func('1')
    func('2')
    func('3')

    # Finish it
    run_async_oor()
    run_async_oor()
    run_async_oor()

    # Verify value
    eq_(_v, ['1', '2', '3'])


def test_async_queue_oor():
    global _v

    init_environment()

    # Prepare result queue
    _v = []

    @gen.engine
    def func(value):
        global _v

        _v.append((yield gen.Task(dummy_async, value)))

    # Call function three times
    func('1')
    func('2')
    func('3')

    # Finish it
    run_async_oor()
    run_async_oor()
    run_async_oor()

    # Verify value
    eq_(_v, ['3', '2', '1'])
