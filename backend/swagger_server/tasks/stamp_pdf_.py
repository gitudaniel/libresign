
from io import BytesIO
from uuid import UUID

import uuid
import json
import traceback
import requests

from sqlalchemy.sql import func

from .. import storage, config, app
from ..db import Session
from ..mappings import *
from ..ipinfo import *
from ..helpers import fetch_audit, download_blob_stream, type_check

from .render_pdf_ import render_pdf
from .invoke_webhook_ import invoke_webhooks_fieldusage

@type_check
def get_signed_fields(session, doc_id: UUID):
    '''Get all fields that have already been filled'''

    rownum = func.row_number().over(
        partition_by=FieldUsage.field_id,
        order_by=FieldUsage.timestamp.desc()
    ).label("row_number")

    subquery = (
        session
            .query(FieldUsage)
            .join(File, isouter=True)
            .join(Field)
            .filter(Field.document_id == doc_id.bytes)
            .filter(FieldUsage.fieldusage_type == config.FIELD_USAGE_TYPE['filled'])
            .filter(Field.field_type == config.FIELD_TYPE['signature'])
            .add_column(rownum)
            .with_entities(File.filename, Field.field_name, rownum)
            .subquery()
    )

    return (
        session
            .query(subquery)
            .filter(subquery.c.row_number == 1)
            .with_entities(subquery.c.filename, subquery.c.field_name)
            .all()
    )

@type_check
def get_text_fields(session, doc_id: UUID):
    '''Get all non-signature fields that have been filled'''

    rownum = func.row_number().over(
        partition_by=FieldUsage.field_id,
        order_by=FieldUsage.timestamp.desc()
    ).label("row_number")

    subquery = (
        session
            .query(FieldUsage)
            .join(Field)
            .filter(Field.document_id == doc_id.bytes)
            .filter(FieldUsage.fieldusage_type == config.FIELD_USAGE_TYPE['filled'])
            .filter(Field.field_type != config.FIELD_TYPE['signature'])
            .add_column(rownum)
            .with_entities(FieldUsage.data, Field.field_name, rownum)
            .subquery()
    )

    return map(
        lambda x: (json.loads(x[0]).get('value'), x[1]),
        session
            .query(subquery)
            .filter(subquery.c.row_number == 1)
            .with_entities(
                subquery.c.data,
                subquery.c.field_name
            )
            .all()
    )
@type_check
def get_unfilled_fields(session, doc_id: UUID):
    subquery = (
        session
            .query(Field)
            .join(FieldUsage)
            .join(FieldUsageType)
            .filter(FieldUsageType.name == 'filled')
            .filter(Field.document_id == doc_id.bytes)
            .with_entities(Field.id)
            .distinct()
    )

    return (
        session
            .query(Field)
            .filter(~Field.id.in_(subquery))
            .filter(Field.document_id == doc_id.bytes)
            .with_entities(
                Field.field_name
            )
            .all()
    )

@type_check
def get_document_file(session, doc_id: UUID):
    row = (
        session
            .query(FileUsage)
            .join(File)
            .filter(FileUsage.document_id == doc_id.bytes
                and (FileUsage.fileusage_type == config.FILE_USAGE_TYPES['created']
                or FileUsage.fileusage_type == config.FILE_USAGE_TYPES['updated']))
            .order_by(FileUsage.timestamp.asc())
            .with_entities(File.filename)
            .first()
    )

    # The document should never be null
    assert row

    return row[0]

@type_check
def do_stamp_pdf(session, container, doc_id: UUID):
    signatures = get_signed_fields(session, doc_id)
    textvals = get_text_fields(session, doc_id)
    empty = get_unfilled_fields(session, doc_id)
    doc_file = get_document_file(session, doc_id)

    descriptors = {
        x[1]: {
            'value': x[0],
            'type': 'blank' if x[0] is None else 'image'
        }
        for x in signatures
    }

    descriptors.update({
        x[1]: {
            'value': x[0],
            'type': 'blank' if x[0] is None else 'text'
        }
        for x in textvals
    })

    # Blank out unfilled fields
    descriptors.update({
        x[0]: {
            'value': '',
            'type': 'blank'
        }
        for x in empty
    })

    doc_blob = container.get_blob(doc_file)

    files = {
        'file': ('file', download_blob_stream(doc_blob), 'application/pdf'),
        'fields': (None, json.dumps(descriptors), 'application/json')
    }
    for (name, _) in signatures:
        if not name:
            continue

        blob = container.get_blob(name)
        files[name] = (
            name,
            download_blob_stream(blob),
            blob.content_type
        )

    resp = requests.post(
        config.PDF_SERVICE_URL + '/stamp',
        files=files
    )

    if resp.status_code != 200:
        raise Exception(resp.content)

    return BytesIO(resp.content)

@type_check
def do_get_audit_log(session, doc_id: UUID):
    log = fetch_audit(session, doc_id)
    r = requests.post('http://audit-gen/', json=[x.to_dict() for x in log])

    if r.status_code != 200:
        raise Exception(r.content)

    return BytesIO(r.content)

@type_check
def do_concat_pdf(a, b) -> BytesIO:
    r = requests.post(config.PDF_SERVICE_URL + '/concat', files=dict(a=a, b=b))

    if r.status_code != 200:
        raise Exception(r.content)

    return BytesIO(r.content)

@app.celery.task(autoretry_for=(Exception,), max_retries=5)
@type_check
def stamp_pdf(docId: str):
    doc_id = uuid.UUID(hex=docId)
    session = Session()
    fileid = uuid.uuid4()
    container = storage.container()
    persisted = False

    print("Starting stamp task for document {}".format(docId))
    try:
        stamped_pdf = do_stamp_pdf(session, container, doc_id)
        audit_log = do_get_audit_log(session, doc_id)

        final_pdf = do_concat_pdf(stamped_pdf, audit_log)

        container.upload_blob(
            final_pdf,
            blob_name=fileid.hex,
            content_type='application/pdf'
        )

        session.add(File(
            id=fileid.bytes,
            filename=fileid.hex
        ))

        session.commit()
        persisted = True

        session.add(FileUsage(
            file_id=fileid.bytes,
            document_id=doc_id.bytes,
            fileusage_type=config.FILE_USAGE_TYPES['endstamp']
        ))

        session.commit()

        render_pdf.delay(docId)
    except Exception as e:
        session.rollback()

        if not persisted:
            print(e)
            traceback.print_exc()
            raise

        usage = FileUsage(
            file_id=None,
            document_id=doc_id.bytes,
            fileusage_type=config.FILE_USAGE_TYPES['endstamp'],
            data=json.dumps({
                'error': str(e)
            })
        )
        session.add(usage)
        session.commit()
        session.refresh(usage)
        invoke_webhooks_fieldusage.delay(usage.id)


def queue_stamping(docId, _):
    stamp_pdf.delay(uuid.UUID(bytes=docId).hex)
