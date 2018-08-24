
import os
import shutil
import tempfile
import sh

def _invoke_pdftk(*args, outname):
    assert outname
    sh.pdftk(
        *args,
        "cat",
        "output",
        outname
    )

def _write_files(*pdfs):
    for stream in list(pdfs):
        _, name = tempfile.mkstemp('.pdf')

        with open(name, 'wb') as file:
            shutil.copyfileobj(stream, file)

        yield name

def concat_pdfs(*pdfs):
    _, outfile = tempfile.mkstemp('.pdf')

    inputs = [x for x in _write_files(*pdfs)]

    _invoke_pdftk(*inputs, outname=outfile)

    for name in inputs:
        os.unlink(name)

    return outfile
