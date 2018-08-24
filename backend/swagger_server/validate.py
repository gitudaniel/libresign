
import json

from flask import abort, Response

def validate_pdf(fielddata, fields):
    for key, _ in fielddata.items():
        if not key in fields:
            abort(Response(
                json.dumps({
                    'msg': 'Field {} not found in form, but present in description JSON'.format(key)
                }),
                status=400
            ))

    return None
