from uuid import UUID
import json

from flask_jwt_extended import jwt_required, get_jwt_identity

from ... import config
from ...db import Session
from ...mappings import *
from ...ipinfo import *
from ...models import ErrorMessage
from ...helpers import verify_permission
from ...tasks import invoke_webhooks_fileusage

@jwt_required
@fetch_ip
def agree_tos(docId: str):
    """ Indicate that the user has agreed to the TOS
        this should be the last step after the user
        has filled out all the fields in the document
        although it doesn't have to be.

        Arguments:
            docId (str): The document ID

        Response:
            If successful, this endpoint will respond
            with HTTP status 204 and an empty body.

            If an error occurs then this will respond
            with a 4XX error code and a JSON body
            describing the error.
    """

    try:
        doc_id = UUID(hex=docId)
    except ValueError:
        return ErrorMessage("Invalid document ID"), 400

    session = Session()

    if not verify_permission(session, doc_id):
        return ErrorMessage("Not Authorized"), 401

    uid = UUID(hex=get_jwt_identity())

    field_ids = (
        session
            .query(Field)
            .filter(Field.document_id == doc_id.bytes)
            .filter(Field.user_id == uid.bytes)
            .with_entities(Field.id)
            .first()
    )

    if not field_ids:
        return ErrorMessage(
            "The current user does not have any fields to " +
            "sign on this document. They cannot agree to " +
            "the TOS for this document."
        ), 400

    username = (
        session
            .query(User)
            .filter(User.id == uid.bytes)
            .with_entities(User.username)
            .one()
    )[0]

    usage = FileUsage(
        document_id=doc_id.bytes,
        fileusage_type=config.FILE_USAGE_TYPE['agree-tos'],
        data=json.dumps({
            'ip': get_ip(),
            'user': username,
            'uid': uid.hex
        })
    )

    session.add(usage)
    session.commit()

    assert usage.id is not None
    invoke_webhooks_fileusage.delay(usage.id)

    return None, 204
