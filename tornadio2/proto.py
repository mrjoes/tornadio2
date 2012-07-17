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
    tornadio2.proto
    ~~~~~~~~~~~~~~~

    Socket.IO protocol related functions
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

# socket.io frame separator
FRAME_SEPARATOR = u'\ufffd'


def disconnect(endpoint=None):
    """Generate disconnect packet.

    `endpoint`
        Optional endpoint name
    """
    return u'0::%s' % (
        endpoint or ''
        )


def connect(endpoint=None):
    """Generate connect packet.

    `endpoint`
        Optional endpoint name
    """
    return u'1::%s' % (
        endpoint or ''
        )


def heartbeat():
    """Generate heartbeat message.
    """
    return u'2::'


def message(endpoint, msg, message_id=None, force_json=False):
    """Generate message packet.

    `endpoint`
        Optional endpoint name
    `msg`
        Message to encode. If message is ascii/unicode string, will send message packet.
        If object or dictionary, will json encode and send as is.
    `message_id`
        Optional message id for ACK
    `force json`
        Disregard msg type and send the message with JSON type. Usefull for already
        JSON encoded strings.
    """
    if msg is None:
        # TODO: Log something ?
        return u''

    packed_message_tpl = u"%(kind)s:%(message_id)s:%(endpoint)s:%(msg)s"
    packed_data = {'endpoint': endpoint or u'',
                   'message_id': message_id or u''}

    # Trying to send a dict over the wire ?
    if not isinstance(msg, (unicode, str)) and isinstance(msg, (dict, object)):
        packed_data.update({'kind': JSON,
                            'msg': json.dumps(msg, **json_decimal_args)})

    # for all other classes, including objects. Call str(obj)
    # and respect forced JSON if requested
    else:
        packed_data.update({'kind': MESSAGE if not force_json else JSON,
                            'msg': msg if isinstance(msg, unicode) else str(msg).decode('utf-8')})

    return packed_message_tpl % packed_data


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

    return u'5:%s:%s:%s' % (
        message_id or '',
        endpoint or '',
        json.dumps(evt)
    )


def ack(endpoint, message_id, ack_response=None):
    """Generate ACK packet.

    `endpoint`
        Optional endpoint name
    `message_id`
        Message id to acknowledge
    `ack_response`
        Acknowledgment response data (will be json serialized)
    """
    if ack_response is not None:
        if not isinstance(ack_response, tuple):
            ack_response = (ack_response,)

        data = json_dumps(ack_response)

        return u'6::%s:%s+%s' % (endpoint or '',
                                 message_id,
                                 data)
    else:
        return u'6::%s:%s' % (endpoint or '',
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
    return u'7::%s:%s+%s' % (endpoint or '',
                             (reason or ''),
                             (advice or ''))


def noop():
    """Generate noop packet."""
    return u'8::'


def json_dumps(msg):
    """Dump object as a json string

    `msg`
        Object to dump
    """
    return json.dumps(msg)


def json_load(msg):
    """Load json-encoded object

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
    assert isinstance(data, unicode), 'frame is not unicode'

    if not data.startswith(FRAME_SEPARATOR):
        return [data]

    # Multiple messages
    idx = 0
    packets = []

    while data[idx:idx + 1] == FRAME_SEPARATOR:
        idx += 1

        # Grab message length
        len_start = idx
        idx = data.find(FRAME_SEPARATOR, idx)
        msg_len = int(data[len_start:idx])
        idx += 1

        # Grab message
        msg_data = data[idx:idx + msg_len]
        idx += msg_len

        packets.append(msg_data)

    return packets


# Encode expects packets in unicode
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
        return packets[0].encode('utf-8')

    # Multiple packets
    frames = u''.join(u'%s%d%s%s' % (FRAME_SEPARATOR, len(p),
                                     FRAME_SEPARATOR, p)
                      for p in packets)

    return frames.encode('utf-8')
