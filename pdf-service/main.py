
import os
import shutil
import json

from json import JSONDecodeError
from io import BytesIO
from tempfile import mkstemp, mkdtemp
from pdfminer.pdfparser import PDFSyntaxError

from flask import (
    Flask, request, jsonify, Response, after_this_request, send_file
)
from flask_cors import CORS

from raven.contrib.flask import Sentry

from field_parser import get_fields
from concat import concat_pdfs
from sign.stamp import FieldExtractionFailedException
from sign import sign_and_fill, save_all_files, InvalidFieldTypeError

app = Flask(__name__)
CORS(app)
Sentry(app, dsn='')

@app.route('/fields', methods=['POST'])
def _get_fields():
    try:
        if not 'Content-Type' in request.headers:
            return Response(
                jsonify(msg='No Content-Type provided.'),
                mimetype='application/json'
            ), 400

        return Response(
            get_fields(request.stream),
            mimetype='application/json'
        ), 200
    except Exception as e:
        print(str(e))
        raise

@app.route('/stamp', methods=['POST'])
def stamp():
    if not 'Content-Type' in request.headers:
        return jsonify(msg="Missing Content-Type header"), 400

    tmpdir = mkdtemp()
    fd, outname = mkstemp(dir=tmpdir)
    os.close(fd)

    # pylint: disable=W0612
    @after_this_request
    def cleanup(response):
        shutil.rmtree(tmpdir)
        return response

    fields = None
    try:
        fields = json.loads(request.form['fields'])
    except JSONDecodeError as e:
        return jsonify(msg=e.msg), 400

    if not isinstance(fields, dict):
        return jsonify(msg='fields was not an object'), 400

    name_map = {
        v['value']: k for k, v in fields.items() if v['value'] is not None
    }

    pdf = None
    for (name, fname) in save_all_files(tmpdir, request.files):
        if name == 'file':
            if pdf is not None:
                return jsonify(
                    msg="There may not be multiple PDFs to stamp within the same request"
                ), 400
            pdf = fname
        elif name == 'fields':
            return jsonify(msg='Fields was not JSON'), 400
        else:
            fields[name_map[name]]['value'] = fname

    if not pdf:
        return jsonify(msg="No PDF was provided to stamp"), 400

    try:
        writer = sign_and_fill(pdf, outname, fields)
        pdfdata = BytesIO()
        writer.write(pdfdata)

        return Response(
            pdfdata.getvalue(),
            mimetype='application/pdf',
        ), 200

    except PDFSyntaxError as e:
        return jsonify(msg=e.msg), 400
    except FieldExtractionFailedException as e:
        return e.data, e.status
    except InvalidFieldTypeError as e:
        return jsonify(
            msg=("Field {} had an invalid type of {}, see " +
                "valid field for valid field types.").format(e.field, e.ty),
            valid=[
                "image",
                "text",
                "blank"
            ]
        ), 400
    except TypeError:
        return jsonify('field description was invalid'), 400

@app.route('/concat', methods=['POST'])
def concat():
    files = [request.files.get(x) for x in request.files]

    outname = concat_pdfs(*files)

    # pylint: disable=W0612
    @after_this_request
    def cleanup(response):
        os.unlink(outname)
        return response

    return send_file(
        open(outname, 'rb'),
        mimetype='application/pdf',
        conditional=False
    )
