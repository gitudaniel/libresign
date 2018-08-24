
from functools import wraps
from flask import request, jsonify

def accepts(*args):
    mimetypes = []
    for arg in args:
        if isinstance(arg, list):
            mimetypes += arg
        else:
            mimetypes.append(arg)

    def is_acceptable():
        return not 'Accept' in request.headers or \
            any(x in request.accept_mimetypes for x in mimetypes)

    def decorator(fun):
        @wraps(fun)
        def wrapper(*args, **kwargs):
            if not is_acceptable():
                return jsonify(
                    msg="Unable to comply with Accept header, " +
                        "see mimetypes field for acceptable mimetypes",
                    mimetypes=mimetypes
                ), 406

            return fun(*args, **kwargs)
        return wrapper
    return decorator
