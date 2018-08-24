
# Disable method presence checking
# since pylint is unable to find method
# definitions for sh
# pylint: disable=E1101

from uuid import UUID

import uuid
import re
import logging
import shutil
import tempfile
import traceback
import sh

from .. import app, storage
from ..db import Session
from ..mappings import *
from ..helpers import type_check

def render_pdf_impl(docId: str):
    ''' Render the PDF associated with the document
        using GhostScript and store the resulting
        images within the 'renderedpage' table of
        the db.

        Arguments:
            docId (str): The document ID, as a hex UUID descriptor.
    '''

    session = Session()
    container = storage.container()

    print("Starting render_pdf task for document {}".format(docId))

    doc_id = UUID(hex=docId)

    fileName = (
        session
            .query(FileUsage)
            .filter(FileUsage.document_id == doc_id.bytes)
            .join(File)
            .order_by(FileUsage.timestamp.desc())
            .with_entities(File.filename)
            .first()
    )

    # There should always be at least one file revision
    # at the time this task is run
    assert fileName

    tmpdir = tempfile.mkdtemp()

    try:
        (_, pdf_file) = tempfile.mkstemp(suffix='.pdf', dir=tmpdir)

        with open(pdf_file, "wb") as file:
            blob = container.get_blob(fileName[0])
            blob.download(file)

        def process_line(line):
            match = re.match(r'^Page ([0-9]+)', line)

            if not match:
                return

            pagenum = int(match.group(1))
            file_id = uuid.uuid4()

            filename = "{}/page-{}.png".format(tmpdir, pagenum)
            with open(filename, "rb") as file:
                container.upload_blob(
                    file,
                    blob_name=file_id.hex,
                    content_type='image/png'
                )

            file = File(
                id=file_id.bytes,
                filename=file_id.hex
            )

            page = RenderedPage(
                file_id=file_id.bytes,
                document_id=doc_id.bytes,
                page=pagenum,
            )

            return (file, page)

        lines = sh.gs(
            '-r300',
            '-dNOPAUSE',
            '-dBATCH',
            '-sDEVICE=png16m',
            '-sOutputFile={}/page-%d.png'.format(tmpdir),
            pdf_file,
        )

        lines = [x for x in lines]
        files = []
        pages = []

        for line in lines:
            ln = process_line(line)

            if not ln:
                continue

            file, page = ln
            files.append(file)
            pages.append(page)

        session.add_all(files)
        session.flush()
        session.add_all(pages)

        session.commit()
    except sh.ErrorReturnCode_1 as e:
        logging.error(str(e) + '\n' + traceback.format_exc())
        return
    finally:
        shutil.rmtree(tmpdir)

@app.celery.task(autoretry_for=(Exception,), max_retries=5)
@type_check
def render_pdf(docId: str):
    ''' Render the PDF associated with the document
        using GhostScript and store the resulting
        images within the 'renderedpage' table of
        the db.

        Arguments:
            docId (str): The document ID, as a hex UUID descriptor.
    '''

    render_pdf_impl(docId)
