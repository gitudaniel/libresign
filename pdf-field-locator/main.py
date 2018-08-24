
from io import BytesIO
import simplejson as json

from flask import Flask, request
from flask_cors import CORS

from pdfminer.pdfparser import PDFSyntaxError
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
from pdfminer.pdftypes import PDFObjRef

from raven.contrib.flask import Sentry

app = Flask(__name__)
CORS(app)
Sentry(app, dsn='')

class Rect:
    def __init__(self, rect):
        self.x = rect[0]
        self.y = rect[1]
        self.w = rect[2] - self.x
        self.h = rect[3] - self.y

    def to_dict(self):
        return {
            'x': self.x,
            'y': self.y,
            'w': self.w,
            'h': self.h
        }


def read_value(ref):
    ''' Get the current text value of the form
        as a str.
    '''

    return ref['V']

def read_name(ref):
    return ref['T']

def read_rect(ref):
    return Rect(ref['Rect'])

def field_desc(ref, pgnum):
    ''' Checks to see if the current ref is a text
        form field with value corresponding to a
        fill tag.

        This method only works on form fields since the
        value and size of the form field is easily available.
        Support for fill tags in general text is not avaliable
        at this time.

        ref:
            Reference to a form field.

        returns:
            A dictionary with 'name' and 'rect' fields.
    '''

    return {
        'name': read_name(ref),
        'rect': read_rect(ref).to_dict(),
        'page': pgnum,
    }

def parse_annotations(page, pgnum):
    annots = page.annots
    if isinstance(annots, PDFObjRef):
        annots = page.annots.resolve()

    annots = (
        r.resolve() for r in annots if isinstance(r, PDFObjRef)
    )

    widgets = (
        r for r in annots if r['Subtype'].name == 'Widget' and 'T' in r
    )

    def field_desc_wrapper(page):
        return field_desc(page, pgnum)

    return map(field_desc_wrapper, widgets)

def parse_all_annotations(pdf, interpreter):
    for pgnum, page in enumerate(PDFPage.get_pages(pdf)):
        interpreter.process_page(page)

        if page.annots:
            for annot in parse_annotations(page, pgnum):
                yield annot

def parse_all_page_sizes(pdf, interpreter):
    for page in PDFPage.get_pages(pdf):
        interpreter.process_page(page)

        rect = page.mediabox

        yield {
            'width': rect[2],
            'height': rect[3]
        }

def parse_pdf(pdf):
    rsrcmgr = PDFResourceManager()
    device = PDFDevice(rsrcmgr)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    return {
        'pages': parse_all_page_sizes(pdf, interpreter),
        'fields': parse_all_annotations(pdf, interpreter)
    }


@app.route('/locate-fields', methods=['POST'])
def locate_fields():
    if request.content_type != 'application/pdf':
        return json.dumps({
            'msg': 'Request did not have content type "application/pdf"'
        }), 415

    try:
        return json.dumps(
            parse_pdf(BytesIO(request.stream.read())),
            iterable_as_array=True
        ), 200

    except PDFSyntaxError as e:
        return json.dumps({
            'msg': 'Invalid PDF',
            'err': str(e)
        }), 400
