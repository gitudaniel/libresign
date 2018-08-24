
from uuid import UUID
from flask_jwt_extended import get_jwt_identity

from ..mappings import Document, Field

def verify_permission(session, doc_id, signer_accessible=True):
    if not isinstance(doc_id, UUID):
        raise ValueError("doc_id should be a UUID object")

    uid = UUID(hex=get_jwt_identity())

    owner = (
        session
            .query(Document)
            .filter(Document.id == doc_id.bytes)
            .filter(Document.user_id == uid.bytes)
            .first()
        is not None
    )

    return owner or (signer_accessible and (
        session
            .query(Field)
            .filter(Field.document_id == doc_id.bytes)
            .filter(Field.user_id == uid.bytes)
            .first()
        is not None
    ))
