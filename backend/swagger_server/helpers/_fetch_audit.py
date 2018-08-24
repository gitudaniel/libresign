
from uuid import UUID

import json
import heapq
import dateutil

from .. import config
from ..mappings import *
from ..models import AuditLogEntry
from ._type_check import type_check

@type_check
def get_audit_log(session, doc_id: UUID) -> list:
    def extract_timestamp(x):
        dateutil.parser.parse(x.timestamp)
    def audit_map(x):
        data = x.data
        if not isinstance(data, dict):
            data = json.loads(data)

        vals = {
            'status': config.FILE_USAGE_TYPES.inv[x.fileusage_type],
            'timestamp': x.timestamp.isoformat(),
            'data': data,
        }
        if vals['status'] == 'endstamp':
            if not x.file_id:
                vals['status'] = 'stamp_failed'
            else:
                vals['status'] = 'stamp_success'

        return vals
    def sig_audit_map(x):
        data = x.data
        if not isinstance(data, dict):
            data = json.loads(data)

        data['user'] = x.username

        return {
            'status': config.FIELD_USAGE_TYPE.inv[x.fieldusage_type],
            'timestamp': x.timestamp.isoformat(),
            # An empty dict is actually deserialized to a dict,
            # so convert it back to a str, this is a no-op in
            # the case where the data is already a string
            'data': data
        }

    audit = (
        session
            .query(FileUsage)
            .filter(FileUsage.document_id == doc_id.bytes)
            .filter(FileUsage.fileusage_type != config.FILE_USAGE_TYPES['describe-fields'])
            .order_by(FileUsage.timestamp.asc())
            .all()
    )

    sig_audit = (
        session
            .query(FieldUsage)
            .join(Field)
            .join(User)
            .filter(Field.document_id == doc_id.bytes)
            .order_by(FieldUsage.timestamp.asc())
            .with_entities(
                FieldUsage.fieldusage_type,
                FieldUsage.data,
                FieldUsage.timestamp,
                User.username
            )
            .all()
    )

    audit = (AuditLogEntry(**x) for x in map(audit_map, audit))
    sig_audit = (AuditLogEntry(**x) for x in map(sig_audit_map, sig_audit))

    return [x for x in heapq.merge(audit, sig_audit, key=extract_timestamp, reverse=True)]
