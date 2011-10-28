# -*- coding: utf-8 -*-
"""
    tornadio2.tests.proto_test
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""

from nose.tools import eq_

from tornadio2 import proto


def test_encode_frames():
    # Test string encode
    eq_(proto.encode_frames(['abc']), 'abc')

    # Test multiple strings encode
    eq_(proto.encode_frames(['abc', 'def']),
                            u'\ufffd3\ufffdabc\ufffd3\ufffddef'.encode('utf-8'))


def test_decode_frames():
    # Single string
    eq_(proto.decode_frames('abc'), ['abc'])

    # Multiplie strings
    eq_(proto.decode_frames(u'\ufffd3\ufffdabc\ufffd3\ufffddef'.encode('utf-8')),
                            ['abc', 'def'])


def test_message():
    # Test string message
    eq_(proto.message(None, 'abc'), '3:::abc')

    eq_(proto.message('abc', 'def'), '3::abc:def')

    eq_(proto.message(None, u'\u0403\u0404\u0405'),
                      u'3:::\u0403\u0404\u0405'.encode('utf-8'))

    # TODO: Fix me
    eq_(proto.message(None, dict(a=1, b=2)),
                      '4:::%s' % proto.json_dumps(dict(a=1, b=2)))


    # TODO: Cover event