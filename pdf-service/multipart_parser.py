
import io
import re
import email.message

from itertools import takewhile
from io import StringIO

class MalformedRequestException(Exception):
    pass

def _parse_boundary_str(bstr):
    if bstr[0] == b'"':
        idx = bstr[1:].find(b'"')
        assert idx != -1
        return bstr[1:idx]
    else:
        idx = bstr.find(b'/r/n')
        if idx == -1:
            return bstr
        else:
            return bstr[:idx]

def _parse_map(s):
    start_idx = s.find(b"start=")
    start_end = min(s[start_idx+6:].find(b'\r\n'), s[start_idx+6:].find(b';'))
    start = s[start_idx+6:start_end]

    start_info_idx = s.find(b"start_info=")
    start_info_end = min(s[start_info_idx+11:].find(b'\r\n'), s[start_info_idx+11:].find(b';'))
    start_info = s[start_info_idx+11:start_info_end]

    type_idx = s.find(b"type=")
    type_end = min(s[type_idx+5:].find(b'\r\n'), s[type_idx+5:].find(b';'))
    type_ = s[type_idx+5:type_end]

    return {
        'start': start,
        'start_info': start_info,
        'type': type_
    }

def _parse_content_type(headerval):
    rest = b';'.join(headerval.split(b';', 1)[1:])
    boundary = _parse_boundary_str(rest[rest.index(b'boundary=')+len(b'boundary='):])
    map = _parse_map(rest[len(boundary):])
    map['boundary'] = boundary

    return map


def _split_multipart_related(data, headers):
    info = _parse_content_type(headers['Content-Type'].encode('utf-8'))
    boundary = info['boundary']

    def strip_crlf(x):
        return x[2:]

    parts1 = data.split(b'\r\n--' + boundary)[1:]
    # Stop parsing after the final boundary
    parts2 = takewhile(lambda x: not x.startswith(b'--'), parts1)
    # Strip of the following CRLF that is part of the boundary
    parts3 = map(strip_crlf, parts2)

    return parts3

def parse_components(data, headers):
    for part in _split_multipart_related(data, headers):
        tmp = part.split(b'\r\n\r\n')
        pheaders = tmp[0]
        body = tmp[1]

        yield (
            email.message_from_bytes(pheaders),
            body
        )
