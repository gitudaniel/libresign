
from flask import request

_request_ip = None

def fetch_ip(fun):
    def wrapper(*args, **kwargs):
        # pylint disable:W0603
        global _request_ip

        if 'CF-Connecting-IP' in request.headers:
            _request_ip = request.headers['CF-Connecting-IP']
        elif request.environ.get('HTTP_X_FORWARDED_FOR') is None:
            _request_ip = request.environ['REMOTE_ADDR']
        else:
            _request_ip = request.environ['HTTP_X_FORWARDED_FOR']

        ret = fun(*args, **kwargs)

        _request_ip = None

        return ret

    return wrapper

def get_ip():
    return _request_ip
