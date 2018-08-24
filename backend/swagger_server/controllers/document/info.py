import json
from uuid import UUID

from flask import Response, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from ...decorators import produces
from ...db import Session
from ...models import ErrorMessage
from ...mappings import Document, Field, FileUsage, FieldUsage
from ... import config
from ...helpers import verify_permission, type_check

@type_check
def get_filled(session, doc_id: UUID):
    ''' Get all fields that have been filled '''

    subquery = (
        session
            .query(FieldUsage)
            .filter(FieldUsage.field_id == Field.id)
            .filter(FieldUsage.fieldusage_type == config.FIELD_USAGE_TYPE["filled"])
    )

    return (
        session
            .query(Field)
            .filter(Field.document_id == doc_id.bytes)
            .filter(subquery.exists())
            .with_entities(Field.id)
            .all()
    )

@jwt_required
@produces('application/json')
def info_get(docId: str):
    ''' Fetch information about the document. This
        information is intended to be used by
        applications showing the fields to users
        and includes the location, size and status
        of various fields in the document and the
        dimensions of all pages within the document.
        Note that all sizes/locations are in PDF
        units.

        Arguments:
            docId (str): The document ID

        Response:
            If successful, this endpoint will respond
            with HTTP 200 and JSON describing the
            document fields/pages. The only fields
            carried within the document are those
            that the current user should sign. See
            the swagger specification for a schema
            of the returned JSON.

            If an error occurrs this endpoint will
            respond with a 4XX error code and a
            JSON body describing the error.
    '''

    uid = UUID(hex=get_jwt_identity())
    doc_id = None
    try:
        doc_id = UUID(hex=docId)
    except ValueError:
        return ErrorMessage("Not a valid document ID"), 400

    session = Session()

    if not verify_permission(session, doc_id):
        return ErrorMessage("Not Authorized"), 401

    field_data = (
        session
            .query(FileUsage)
            .filter(FileUsage.document_id == doc_id.bytes)
            .filter(FileUsage.fileusage_type == config.FILE_USAGE_TYPES['describe-fields'])
            .with_entities(FileUsage.data)
            .order_by(FileUsage.timestamp.asc())
            .first()
    )

    doc_title = (
        session
            .query(Document)
            .filter(Document.id == doc_id.bytes)
            .with_entities(Document.title)
            .one()
    )[0]

    if not field_data:
        # If the field data hasn't been created yet, then
        # return a 503 to indicate that the client should
        # retry at a later time
        return Response(
            json.dumps({'msg':"Field data is still being generated"}),
            headers={
                # This should hopefully be in the right area
                'Retry-After': 30
            }
        ), 503
    else:
        field_data = json.loads(field_data[0])

    # Assert on properties of json data
    assert isinstance(field_data, dict)
    assert 'fields' in field_data
    assert 'pages' in field_data
    assert isinstance(field_data['fields'], list)
    assert isinstance(field_data['pages'], list)

    fields_for_user = dict(
        session
            .query(Field)
            .filter(Field.document_id == doc_id.bytes)
            .filter(Field.user_id == uid.bytes)
            .with_entities(Field.field_name, Field.id)
            .all()
    )

    filled = set(UUID(bytes=x[0]) for x in get_filled(session, doc_id))

    print(filled)

    filtered = []
    for field in field_data['fields']:
        if field['name'] in fields_for_user:
            field_id = UUID(bytes=fields_for_user[field['name']])

            field['id'] = field_id.hex
            field['filled'] = field_id in filled
            field['optional'] = False

            filtered.append(field)

    field_data['fields'] = filtered
    field_data['title'] = doc_title

    return jsonify(field_data), 200
