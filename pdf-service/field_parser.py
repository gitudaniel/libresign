
# pylint: disable=E1101

from io import StringIO

import os
import json
import tempfile
import sh

def parse_fields_alt(output):
    out = {}
    for field in output.split('---'):
        fields = {}
        for line in field.split('\n'):
            if not ':' in line:
                continue
            parts = line.split(':', 1)
            fields[parts[0]] = parts[1]
        if 'FieldName' in fields:
            out[fields['FieldName'][1:]] = fields.get('FieldValue', ' ')[1:]
    return out

def run_pdftk(file):
    buf = StringIO()
    sh.pdftk(file, 'dump_data_fields_utf8', _out=buf)
    return buf.getvalue()

def get_fields(filestream):
    (fd, name) = tempfile.mkstemp(suffix='.pdf', dir='./')

    try:
        with open(fd, "wb", closefd=True) as file:
            file.write(filestream.read())

        return json.dumps(parse_fields_alt(run_pdftk(name)))
    finally:
        os.unlink(name)
