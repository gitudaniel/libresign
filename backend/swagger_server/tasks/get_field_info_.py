
from uuid import UUID
from io import BytesIO

import json
import logging
import requests

from .. import storage, config, app
from ..db import Session
from ..mappings import *
from ..ipinfo import *
from ..helpers import type_check

@app.celery.task(autoretry_for=(Exception,), max_retries=5)
@type_check
def get_field_info(docId: str):
    ''' Use the field locator service to parse out
        the locations of all form fields within the
        given document. It then stores the resulting
        JSON data in a FileUsage entry which has
        the type 'describe-fields'.

        Arguments:
            docId (str): The document ID, as a hex UUID descriptor.
    '''

    session = Session()
    container = storage.container()
    print("Starting get_field_info task for {}".format(docId))

    doc_id = UUID(hex=docId)

    fileName = (
        session
            .query(FileUsage)
            .filter(FileUsage.document_id == doc_id.bytes)
            .join(File)
            .order_by(FileUsage.timestamp.asc())
            .with_entities(File.filename)
            .first()
    )

    fields = (
        session
            .query(Field)
            .filter(Field.document_id == doc_id.bytes)
            .with_entities(Field.field_name, Field.field_type)
            .all()
    )

    # There should always be a file revision
    # before this is called
    assert fileName

    stream = BytesIO()
    blob = container.get_blob(fileName[0])
    blob.download(stream)
    stream.seek(0)

    resp = requests.post(
        config.FIELD_PARSER_URL + '/locate-fields',
        stream,
        headers={'Content-Type':'application/pdf'}
    )

    if resp.status_code != 200:
        logging.error(
            'Field locator service returned error:\n%s',
            str(resp.content)
        )

        # There should always be a fileusage entry,
        # so we add an empty one when the service
        # fails. This can be changed in the future
        # if it is deemed not necessary
        session.add(FileUsage(
            document_id=doc_id.bytes,
            fileusage_type=config.FILE_USAGE_TYPES['describe-fields'],
            data="{}"
        ))
    else:
        content = json.loads(resp.content.decode('utf8'))

        index = {}
        for i, field in enumerate(content['fields']):
            index[field['name']] = i

        for (name, ty) in fields:
            content['fields'][index[name]]['type'] = config.FIELD_TYPE.inv[ty]

        session.add(FileUsage(
            document_id=doc_id.bytes,
            fileusage_type=config.FILE_USAGE_TYPES['describe-fields'],
            data=json.dumps(content)
        ))

    session.commit()
