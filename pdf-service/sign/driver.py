
import os

from tempfile import mkstemp

from flask import make_response, abort

from .fill_form import do_fill_form
from .stamp import fill_signatures, request_fields

def sign_and_fill(pdf, outfile, fields):
    """ Fills out the form fields within the pdf
    then stamps the image fields onto the pdf.
    """
    if not isinstance(fields, dict):
        raise TypeError('Expected dict, found {}'.format(type(fields)))

    with open(pdf, "rb") as pdffile:
        form_data = request_fields(pdffile)

    do_fill_form(pdf, outfile, fields)

    data = dict((k, v['value']) for k, v in fields.items() if v['type'] == 'image')
    return fill_signatures(outfile, data, form_data)

def save_all_files(tgtdir, files):
    for (name, file) in files.items():
        if file.content_type and not (
                file.content_type == 'application/pdf' or
                file.content_type == 'image/png'
            ):
            abort(make_response(
                "An attached file had a Content-Type " +
                "other than application/pdf or image/png"
            ), 415)

        fd, fname = mkstemp(dir=tgtdir)
        os.close(fd)

        with open(fname, "wb") as f:
            file.save(f)

        yield (name, fname)
