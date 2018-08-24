""""""

from uuid import UUID

import requests
import dateutil.parser

from flask import request, Response
from flask_jwt_extended import jwt_required

from ...db import Session
from ...mappings import *
from ...models import ErrorMessage
from ...helpers import fetch_audit, verify_permission, type_check

def extract_timestamp(x):
    dateutil.parser.parse(x.timestamp)

@type_check
def get_audit_log_json(session, doc_id: UUID):
    ''' Fetch the audit log as a json serializable object'''

    return fetch_audit(session, doc_id), 200

@type_check
def get_audit_log_pdf(session, doc_id: UUID):
    ''' Fetch the audit log as a PDF'''

    log = fetch_audit(session, doc_id)
    r = requests.post('http://audit-gen/', json=[x.to_dict() for x in log])

    if r.status_code != 200:
        return Response(
            r.content,
            mimetype=r.headers['Content-Type'],
            status=500
        )

    return Response(
        r.content,
        mimetype='application/pdf',
        status=200
    )

@jwt_required
def audit_get(docId: str):
    """ Fetch the audit log for a given document.
        This endpoint can fetch the audit log in
        multiple formats depending on the mimetypes
        given by the client in the `Accept` header.

        Formats:
            * `application/pdf`
            * `application/json`

        Arguments:
            docId (str): The document ID

        Response:
            If successful, this endpoint will respond
            with HTTP status 200 and the body will
            contain the audit log in the requested
            format.

            If an error occurs then this will respond
            with a 4XX error code and a JSON body
            describing the error.
    """

    session = Session()
    try:
        doc_id = UUID(hex=docId)
    except ValueError:
        return ErrorMessage("Invalid document ID"), 400

    if not verify_permission(session, doc_id):
        return ErrorMessage("Not Authorized"), 401

    doc_exists = (
        session
            .query(Document)
            .filter(Document.id == doc_id.bytes)
            .with_entities(Document.id)
            .one_or_none()
        is not None
    )

    if not doc_exists:
        return ErrorMessage("Not Found"), 404

    # TODO: Properly do content negotiation
    if 'application/json' in request.accept_mimetypes:
        return get_audit_log_json(session, doc_id)
    elif 'application/pdf' in request.accept_mimetypes:
        return get_audit_log_pdf(session, doc_id)

    return ErrorMessage(
        msg='Acceptable types are "application/pdf" or "application/json"'
    ), 406
    