
from uuid import UUID

from flask_jwt_extended import (
    jwt_required, get_jwt_identity
)

from ..db import Session
from ..mappings import *
from ..ipinfo import *
from ..models import ErrorMessage
from ..tasks import send_email

@jwt_required
def send_reminder_email(docId: str, email: str = None):
    ''' Send an email to the provided email address
        regarding fields for them within the given
        document. If no email address is provided,
        then an email is sent to all users who have
        a field that is still unfilled on the document.
    '''

    uid = UUID(hex=get_jwt_identity())

    doc_id = None
    try:
        doc_id = UUID(hex=docId)
    except ValueError:
        return ErrorMessage("Not Found"), 404

    session = Session()

    doc = (
        session
            .query(Document)
            .filter(Document.id == doc_id.bytes)
            .filter(Document.user_id == uid.bytes)
            .one_or_none()
    )

    if not doc:
        return ErrorMessage("Unauthorized"), 401

    if email:
        doc = (
            session
                .query(Field)
                .join(User)
                .filter(Field.document_id == doc_id.bytes)
                .filter(User.username == email)
                .one_or_none()
        )

        if not doc:
            return ErrorMessage("User is not associated with the document"), 400

    send_email.delay(docId, email)

    return None, 202
