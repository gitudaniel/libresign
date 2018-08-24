
from uuid import UUID

import json

from ..mappings import *

def add_doc_audit_entry(session, doc_id, status, data):
    """"Add an audit entry, requires that a commit
        be run on the session afterwards
    """

    if not isinstance(doc_id, UUID):
        raise ValueError("Expecting UUID")
    if not isinstance(data, dict):
        raise ValueError("Expecting dict")

    session.add(FileUsage(
        document_id=doc_id.bytes,
        fileusage_type=status,
        data=json.dumps(data)
    ))
