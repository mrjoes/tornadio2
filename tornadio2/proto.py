try:
    import simplejson as json
    json_decimal_args = {"use_decimal":True}
except ImportError:
    import json
    import decimal
    class DecimalEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, decimal.Decimal):
                return float(o)
            return super(DecimalEncoder, self).default(o)
    json_decimal_args = {"cls":DecimalEncoder}

DISCONNECT = 0
CONNECT = 1
HEARTBEAT = 2
MESSAGE = 3
JSON = 4
EVENT = 5
ACK = 6
ERROR = 7
NOOP = 8

def disconnect(endpoint=None):
    return '0::%s' % (
        endpoint or ''
        )

def connect(endpoint=None):
    return '1::%s' % (
        endpoint or ''
        )

def message(endpoint, msg, message_id=None):
    if (not isinstance(msg, (unicode, str)) and
        isinstance(msg, (object, dict)):
        if msg is not None:
            return '4:%s:%s:%s' % (
                message_id or '',
                endpoint or '',
                json.dumps(msg, **json_decimal_args)
                )
        else:
            # TODO: Log something
            return ''
    else:
        return '3:%s:%s:%s' % (
            message_id or '',
            endpoint or '',
            msg.encode('utf-8')
            )
