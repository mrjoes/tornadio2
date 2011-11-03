# -*- coding: utf-8 -*-
"""
    tornadio2.proto
    ~~~~~~~~~~~~~~~

    Socket.IO protocol related functions

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import logging

try:
    import simplejson as json
    json_decimal_args = {"use_decimal": True}
except ImportError:
    import json
    import decimal

    class DecimalEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, decimal.Decimal):
                return float(o)
            return super(DecimalEncoder, self).default(o)
    json_decimal_args = {"cls": DecimalEncoder}

# Packet ids
DISCONNECT = '0'
CONNECT = '1'
HEARTBEAT = '2'
MESSAGE = '3'
JSON = '4'
EVENT = '5'
ACK = '6'
ERROR = '7'
NOOP = '8'

# utf-8 encoded frame separator
FRAME_SEPARATOR = u'\ufffd'.encode('utf-8')


def disconnect(endpoint=None):
    """Generate disconnect packet.

    `endpoint`
        Optional endpoint name
    """
    return '0::%s' % (
        endpoint or ''
        )


def connect(endpoint=None):
    """Generate connect packet.

    `endpoint`
        Optional endpoint name
    """
    return '1::%s' % (
        endpoint or ''
        )


def heartbeat():
    """Generate heartbeat message.
    """
    return '2::'


def message(endpoint, msg, message_id=None):
    """Generate message packet.

    `endpoint`
        Optional endpoint name
    `msg`
        Message to encode. If message is ascii/unicode string, will send message packet.
        If object or dictionary, will json encode and send as is.
    `message_id`
        Optional message id for ACK
    """
    if (not isinstance(msg, (unicode, str)) and
        isinstance(msg, (object, dict))):
        if msg is not None:
            return '4:%s:%s:%s' % (
                message_id or '',
                endpoint or '',
                json.dumps(msg, **json_decimal_args).encode('utf-8')
                )
        else:
            # TODO: Log something
            return ''
    else:
        return '3:%s:%s:%s' % (
            message_id or '',
            endpoint or '',
            msg.encode('utf-8') if isinstance(msg, unicode) else msg.decode('utf-8')
            )


def event(endpoint, name, message_id, *args, **kwargs):
    """Generate event message.

    `endpoint`
        Optional endpoint name
    `name`
        Event name
    `message_id`
        Optional message id for ACK
    `args`
        Optional event arguments.
    `kwargs`
        Optional event arguments. Will be encoded as dictionary.
    """
    if args:
        evt = dict(
            name=name,
            args=args
            )

        if kwargs:
            logging.error('Can not generate event() with args and kwargs.')
    else:
        evt = dict(
            name=name,
            args=[kwargs]
        )

    return '5:%s:%s:%s' % (
        message_id or '',
        endpoint or '',
        json.dumps(evt).encode('utf-8')
    )


def ack(endpoint, message_id):
    """Generate ACK packet.

    `endpoint`
        Optional endpoint name
    `message_id`
        Message id to acknowledge
    """
    return '6::%s:%s' % (endpoint or '',
                         message_id)


def error(endpoint, reason, advice=None):
    """Generate error packet.

    `endpoint`
        Optional endpoint name
    `reason`
        Error reason
    `advice`
        Error advice
    """
    return '7::%s:%s+%s' % (endpoint or '',
                            (reason or '').encode('utf-8'),
                            (advice or '').encode('utf-8'))


def noop():
    """Generate noop packet."""
    return '8::'


def json_dumps(msg):
    """Dump object as a json string

    `msg`
        Object to dump
    """
    return json.dumps(msg)


def json_load(msg):
    """Load json

    `msg`
        json encoded object
    """
    return json.loads(msg)


def decode_frames(data):
    """Decode socket.io encoded messages. Returns list of packets.

    `data`
        encoded messages

    """
    # Single message - nothing to decode here
    if not data.startswith(FRAME_SEPARATOR):
        return [data]

    # Multiple messages
    idx = 0
    packets = []

    frame_len = len(FRAME_SEPARATOR)

    while data[idx:idx + frame_len] == FRAME_SEPARATOR:
        idx += len(FRAME_SEPARATOR)

        # Grab message length
        len_start = idx
        idx = data.find(FRAME_SEPARATOR, idx)
        msg_len = int(data[len_start:idx])
        idx += len(FRAME_SEPARATOR)

        # Grab message
        msg_data = data[idx:idx + msg_len]
        idx += msg_len

        packets.append(msg_data)

    return packets


# Encode expects packets in UTF-8 encoding
def encode_frames(packets):
    """Encode list of packets.

    `packets`
        List of packets to encode
    """
    # No packets - return empty string
    if not packets:
        return ''

    # Exactly one packet - don't do any frame encoding
    if len(packets) == 1:
        return packets[0]

    # Multiple packets
    frames = ''

    for p in packets:
        frames += '%s%d%s%s' % (FRAME_SEPARATOR, len(p), FRAME_SEPARATOR, p)

    return frames
