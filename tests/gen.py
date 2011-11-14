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


def init_environment():
    global _queue
    _queue = deque()


def run_sync(test, callback):
    callback(test)


def queue_async(test, callback):
    global _queue
    _queue.append((callback, test))


def step_async():
    callback = _queue.popleft()
    callback[0](callback[1])


def run_async():
    global _queue

    while True:
        try:
            step_async()
        except IndexError:
            break


def run_async_oor():
    global _queue

    while True:
        try:
            callback = _queue.pop()
            callback[0](callback[1])
        except IndexError:
            break


class Dummy():
    def __init__(self, queue_type):
        self.v = None
        self.queue_type = queue_type

    @gen.sync_engine
    def test(self, value):
        self.v = yield gen.Task(self.queue_type, value)


class DummyList():
    def __init__(self, queue_type):
        self.v = []
        self.queue_type = queue_type

    @gen.sync_engine
    def test(self, value):
        self.v.append((yield gen.Task(self.queue_type, value)))


class DummyListOutOfOrder():
    def __init__(self, queue_type):
        self.v = []
        self.queue_type = queue_type

    @gen.engine
    def test(self, value):
        self.v.append((yield gen.Task(self.queue_type, value)))


class DummyLoop():
    def __init__(self, queue_type):
        self.v = 0
        self.queue_type = queue_type

    @gen.sync_engine
    def test(self, value):
        for n in xrange(2):
            self.v += (yield gen.Task(self.queue_type, value))

def test():
    init_environment()

    dummy = Dummy(run_sync)
    dummy.test('test')

    eq_(dummy.v, 'test')


def test_async():
    init_environment()

    dummy = Dummy(queue_async)
    dummy.test('test')
    run_async()

    # Verify value
    eq_(dummy.v, 'test')


def test_sync_queue():
    init_environment()

    dummy = DummyList(queue_async)
    dummy.test('1')
    dummy.test('2')
    dummy.test('3')
    run_async()

    # Verify value
    eq_(dummy.v, ['1', '2', '3'])


def test_sync_queue_oor():
    init_environment()

    dummy = DummyList(queue_async)
    dummy.test('1')
    dummy.test('2')
    dummy.test('3')
    run_async_oor()

    # Verify value
    eq_(dummy.v, ['1', '2', '3'])


def test_async_queue_oor():
    init_environment()

    dummy = DummyListOutOfOrder(queue_async)
    dummy.test('1')
    dummy.test('2')
    dummy.test('3')
    run_async_oor()

    # Verify value
    eq_(dummy.v, ['3', '2', '1'])
