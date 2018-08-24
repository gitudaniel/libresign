
# pylint: disable=E1101

from io import StringIO, BytesIO

import json
import sh
import requests

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader

from PyPDF2 import PdfFileReader, PdfFileWriter

from PIL import Image

URL = 'http://field-locator/locate-fields'

class FieldExtractionFailedException(Exception):
    def __init__(self, data, status):
        super().__init__()
        self.data = data
        self.status = status

def request_fields(pdf):
    r = requests.post(URL, pdf, headers={'Content-Type': 'application/pdf'})

    if r.status_code != 200:
        raise FieldExtractionFailedException(
            data=r.content,
            status=r.status_code
        )

    pdf.seek(0)
    return json.loads(r.content)

class Attachement:
    def __init__(self, data, dimensions):
        img = Image.open(data)
        self.img = img
        self.dimensions = dimensions

        # Discard alpha channel, if it exists
        if img.mode == "RGBA":
            self.img = Image.new("RGB", img.size, (255, 255, 255))
            mask = img.split()[-1]
            self.img.paste(img, mask=mask)

    def pdf(self):
        stream = BytesIO()

        pdf = Canvas(stream)
        pdf.drawImage(ImageReader(self.img), *self.dimensions)
        pdf.save()

        return PdfFileReader(stream).getPage(0)


def exec_pdftk(filename):
    stdout = BytesIO()
    stderr = StringIO()

    sh.pdftk(
        filename,
        'output', '-',
        'dont_ask',
        'flatten',
        _out=stdout,
        _err=stderr
    )

    stderr = stderr.getvalue()
    if stderr.strip():
        raise IOError(stderr)

    return stdout

def create_watermarks(fields, data):
    field_map = {}
    for field in fields['fields']:
        field_map[field['name']] = field

    for (key, val) in data.items():
        if not key in field_map:
            continue

        field = field_map[key]

        dimensions = (
            field['rect']['x'],
            field['rect']['y'],
            field['rect']['w'],
            field['rect']['h']
        )
        page = field['page']
        pdf = Attachement(val, dimensions=dimensions).pdf()

        yield (page, pdf)


def create_attachments(pdf, filename, data, fields=None):
    if not fields:
        fields = request_fields(pdf)
    flattened = PdfFileReader(exec_pdftk(filename))

    for pgnum, watermark in create_watermarks(fields, data):
        page = flattened.getPage(pgnum)
        page.mergePage(watermark)

    output = PdfFileWriter()
    pages = range(flattened.getNumPages())
    for p in pages:
        output.addPage(flattened.getPage(p))

    return output

def fill_signatures(filename, data, fields=None):
    with open(filename, 'rb') as pdf:
        return create_attachments(pdf, filename, data, fields)
