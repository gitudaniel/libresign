
from io import StringIO

import sh

from fdfgen import forge_fdf

class InvalidFieldTypeError(ValueError):
    def __init__(self, field, ty):
        super().__init__("Invalid field type {}".format(ty))

        self.ty = ty
        self.field = field

def _exec_pdftk(pdf, items, outfile):
    stderr = StringIO()
    fdf = forge_fdf("", items, [], [], [])

    # pylint: disable=E1101
    sh.pdftk(
        pdf,
        "fill_form", "-",
        "output", outfile,
        "dont_ask",
        "flatten",
        _in=fdf,
        _err=stderr
    )

    stderr = stderr.getvalue()
    if stderr.strip():
        raise IOError(stderr)

def _build_field_desc(fields):
    """Generate a sequence of (string, value) pairs
    suitable for putting into forge_fdf"""

    if not isinstance(fields, dict):
        raise TypeError("Expecting dict")

    for name, field in fields.items():
        if not isinstance(field, dict):
            raise TypeError("Field elements should be dict")

        if field['type'] == 'text':
            yield (name, field['value'])
        elif field['type'] == 'image':
            yield (name, '')
        elif field['type'] == 'blank':
            yield (name, '')
        else:
            raise InvalidFieldTypeError(name, field['type'])

def do_fill_form(pdf, outfile, fields):
    _exec_pdftk(
        pdf,
        _build_field_desc(fields),
        outfile
    )
