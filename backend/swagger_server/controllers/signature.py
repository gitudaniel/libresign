import json
import uuid

from uuid import UUID
from datetime import datetime

from flask import request, Response, abort, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from .. import storage, config
from ..db import Session
from ..mappings import *
from ..ipinfo import *
from ..tasks import stamp_pdf, invoke_webhooks_fieldusage, invoke_webhooks_fileusage
from ..helpers import type_check

@type_check
def error_abort(fields: dict, status: int):
    abort(Response(json.dumps(fields), status, mimetype='application/json'))

@type_check
def request_wants_pdf() -> bool:
    best = request.accept_mimetypes \
        .best_match(['application/pdf', 'image/png'], 'application/pdf')

    return best == 'application/pdf'

def validate_content_type(signature):
    if signature.content_type != 'image/png':
        error_abort(
            dict(
                msg='Signature content type was not image/png'
            ),
            415
        )
@type_check
def parse_field_id(fieldId: str) -> UUID:
    try:
        return UUID(hex=fieldId)
    except ValueError:
        error_abort(dict(msg='Not a valid Field ID'), 400)

@type_check
def create_fill_field_entry(session, field_id: UUID) -> UUID:
    file_id = uuid.uuid4()

    file = File(
        id=file_id.bytes,
        filename=file_id.hex,
        request_uri=None
    )
    usage = FieldUsage(
        field_id=field_id.bytes,
        fieldusage_type=config.FIELD_USAGE_TYPE['filled'],
        file_id=file_id.bytes,
        data=json.dumps({'ip': get_ip()})
    )

    session.add(file)
    session.add(usage)

    session.flush()
    assert usage.id is not None
    invoke_webhooks_fieldusage.delay(usage.id)

    return file_id
@type_check
def create_fill_field_entry_text(session, field_id: UUID, value: str):
    usage = FieldUsage(
        field_id=field_id.bytes,
        fieldusage_type=config.FIELD_USAGE_TYPE['filled'],
        data=json.dumps({
            'ip': get_ip(),
            'value': value
        })
    )

    session.add(usage)
    session.flush()

    assert usage.id is not None
    invoke_webhooks_fieldusage.delay(usage.id)

@type_check
def fill_dependant_date(session, dependant_id: bytes):
    # TODO: The timezone should be addressed for
    # this, for our usages simply changing it to
    # decide date by EST should be sufficient
    date = datetime.today().strftime("%Y-%m-%d")

    usage = FieldUsage(
        field_id=dependant_id,
        fieldusage_type=config.FIELD_USAGE_TYPE['filled'],
        file_id=None,
        data=json.dumps({'value': date})
    )

    session.add(usage)

    session.flush()
    assert usage.id is not None
    invoke_webhooks_fieldusage.delay(usage.id)
@type_check
def fill_dependant_fields(session, field_id: UUID):
    dependants = (
        session
            .query(Field)
            .filter(Field.parent == field_id.bytes)
            .with_entities(Field.id, Field.field_type)
            .all()
    )

    for dependant_id, field_type in dependants:
        if field_type == config.FIELD_TYPE['date']:
            fill_dependant_date(session, dependant_id)
        else:
            assert "Unrecognized field type {} for field {}"\
                .format(field_type, dependant_id)

@type_check
def validate_field_id(session, field_id: UUID, uid: UUID):
    sig_id = (
        session
            .query(Field)
            .filter_by(id=field_id.bytes)
            .filter_by(user_id=uid.bytes)
            .with_entities(Field.id)
            .one_or_none()
    )

    if not sig_id:
        error_abort(dict(title="Not Found"), 404)

@type_check
def check_all_fields_filled(session, doc_id: UUID):
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

    unsigned = (
        session
            .query(Field)
            .filter(~Field.id.in_(subquery))
            .filter(Field.document_id == doc_id.bytes)
            .filter(Field.user_id != None)
            .with_entities(Field.id)
            .first()
    )

    if not unsigned:
        usage = FileUsage(
            document_id=doc_id.bytes,
            fileusage_type=config.FILE_USAGE_TYPE['all-fields-filled']
        )

        session.add(usage)
        session.flush()
        invoke_webhooks_fileusage.delay(usage.id)

@jwt_required
@fetch_ip
def fill_signature(fieldId: str, fieldData):
    """ Start the signature of a document. This
        marks the given field as filled and starts
        a task to re-render the document with the
        new signature added. This endpoint will
        also fill out fields dependant on the one
        being signed.

        Arguments:
            fieldId (str): The field ID
            fieldData: A PNG image containing the signature.

        Responses:
            Responds with HTTP 204 on success, a 4XX
            code on error.
    """

    # Translate here so that variable names are correct
    signature = fieldData

    validate_content_type(signature)

    uid = UUID(hex=get_jwt_identity())
    field_id = parse_field_id(fieldId)

    session = Session()
    container = storage.container()

    validate_field_id(session, field_id, uid)

    file_id = create_fill_field_entry(session, field_id)
    fill_dependant_fields(session, field_id)

    container.upload_blob(
        filename=signature.stream,
        content_type=signature.content_type,
        blob_name=file_id.hex)

    doc_id = (
        session
            .query(Field)
            .filter(Field.id == field_id.bytes)
            .with_entities(Field.document_id)
            .one()
    )[0]

    check_all_fields_filled(session, UUID(bytes=doc_id))

    session.commit()
    stamp_pdf.delay(UUID(bytes=doc_id).hex)

    return None, 204

@jwt_required
@fetch_ip
def fill_text(fieldId: str, value: str):
    """ Start the filling of a text field within a
        document. This marks the given field as filled
        and starts a task to re-render the document
        with the field filled. This endpoint will also
        fill out fields dependant on the one being filled.

        Arguments:
            fieldId (str): The field ID
            value: The new text value of the field

        Responses:
            Responds with HTTP 204 on success, a 4XX
            code on error.
    """

    uid = UUID(hex=get_jwt_identity())
    field_id = parse_field_id(fieldId)

    session = Session()

    validate_field_id(session, field_id, uid)

    create_fill_field_entry_text(session, field_id, value)
    fill_dependant_fields(session, field_id)

    doc_id = (
        session
            .query(Field)
            .filter(Field.id == field_id.bytes)
            .with_entities(Field.document_id)
            .one()
    )[0]

    check_all_fields_filled(session, UUID(bytes=doc_id))

    session.commit()

    stamp_pdf.delay(UUID(bytes=doc_id).hex)

    return None, 204

@jwt_required
@fetch_ip
def bulk_fill_impl(**kwargs):
    """ Fill multiple fields at once, this
        allows multiple fields to be filled
        while only adding one audit entry.

        Arguments:
            All arguments form a key-value dictionary
            where the keys are the field ids and the
            values are either strings to fill in or
            images to stamp.
    """

    from werkzeug.datastructures import FileStorage

    uid = UUID(hex=get_jwt_identity())

    session = Session()
    container = storage.container()

    for fieldId, value in kwargs.items():
        field_id = parse_field_id(fieldId)
        validate_field_id(session, field_id, uid)

        if isinstance(value, FileStorage):
            if value.mimetype != 'image/png':
                return jsonify({
                    'title': 'Signature was not a PNG image',
                    'description':
                        f'field ${fieldId} had a mimetype'
                        f' of ${value.mimetype} instead of image/png'
                }), 415

            file_id = create_fill_field_entry(session, field_id)
            fill_dependant_fields(session, field_id)

            container.upload_blob(
                filename=value.stream,
                content_type=value.mimetype,
                blob_name=file_id.hex
            )
        else:
            create_fill_field_entry_text(session, field_id, value)
            fill_dependant_fields(session, field_id)

    doc_id = (
        session
            .query(Field)
            .filter(Field.id == field_id.bytes)
            .with_entities(Field.document_id)
            .one()
    )[0]

    check_all_fields_filled(session, UUID(bytes=doc_id))

    session.commit()
    stamp_pdf.delay(UUID(bytes=doc_id).hex)

    return None, 204

def bulk_fill():
    print(request.files)

    form = request.form.to_dict(flat=True)
    form.update(request.files.to_dict(flat=True))

    return bulk_fill_impl(**form)
