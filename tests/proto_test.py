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
    eq_(proto.decode_frames(u'abc'), [u'abc'])

    # Multiplie strings
    eq_(proto.decode_frames(u'\ufffd3\ufffdabc\ufffd3\ufffddef'),
                            [u'abc', u'def'])


def test_message():
    # Test string message
    eq_(proto.message(None, 'abc'), u'3:::abc')

    eq_(proto.message('abc', 'def'), u'3::abc:def')

    eq_(proto.message(None, u'\u0403\u0404\u0405'),
                      u'3:::\u0403\u0404\u0405')

    # TODO: Multibyte encoding fix

    # TODO: Fix me
    eq_(proto.message(None, dict(a=1, b=2)),
                      u'4:::%s' % proto.json_dumps(dict(a=1, b=2)))


    # TODO: Add event unit tests
