
from uuid import UUID

import json
import logging
import traceback
import requests

from requests.exceptions import ConnectionError as RequestsConnectionError, MissingSchema
from sqlalchemy.orm.exc import NoResultFound

from .. import app
from ..db import Session
from ..mappings import *
from ..helpers import type_check

def __invoke_webhooks(session, doc_id: bytes, data: dict):
    webhooks = (
        session
            .query(Document)
            .filter(Document.id == doc_id)
            .join(User)
            .join(Business)
            .join(BusinessConfig)
            .filter(BusinessConfig.key == 'webhook')
            .with_entities(BusinessConfig.values['url'].astext)
    )

    for (webhook,) in webhooks:
        try:
            r = requests.post(
                webhook,
                data=data,
                headers={
                    'Content-Type': 'application/json'
                }
            )

            if r.status_code < 200 or r.status_code >= 300:
                logging.warning(
                    "Webhook call returned status code %d with body:\b%s",
                    r.status_code,
                    r.content
                )
        except RequestsConnectionError:
            logging.warning(
                "Failed to post to webhook service '%s', does it exist?",
                webhook
            )
        except MissingSchema as e:
            logging.warning('Webhook failed with error: %s', str(e))
        except Exception as e:
            logging.error(
                'Unexpected error while calling webhooks:\n%s\n%s',
                str(e),
                traceback.format_exc()
            )

@app.celery.task(autoretry_for=(NoResultFound,), max_retries=5)
@type_check
def invoke_webhooks_fileusage(usage_id: int):
    ''' Call webhooks for a FileUsage entry.
        This will extract the relevant data from
        the database entry and then POST that data
        to all webhooks for the business of the
        document owner.

        Arguments:
            usage_id (int): FileUsage id that should be invoked.
    '''

    print('invoke_webhooks_fileusage called with {}'.format(usage_id))
    session = Session()

    (doc_id, type_name, timestamp, data) = (
        session
            .query(FileUsage)
            .join(FileUsageType)
            .filter(FileUsage.id == usage_id)
            .with_entities(
                FileUsage.document_id,
                FileUsageType.name,
                FileUsage.timestamp,
                FileUsage.data
            )
            .one()
    )

    post_data = json.dumps({
        'doc_id': UUID(bytes=doc_id).hex,
        'type': 'document',
        'usage_type': type_name,
        'timestamp': timestamp.isoformat(),
        'data': json.loads(data)
    })

    __invoke_webhooks(session, doc_id, post_data)

@app.celery.task(autoretry_for=(Exception,), max_retries=5)
@type_check
def invoke_webhooks_fieldusage(usage_id: int):
    ''' Call webhooks for a FieldUsage entry.
        This will extract the relevant data from
        the database entry and then POST that data
        to all webhooks for the business of the
        document owner.

        Arguments:
            usage_id (int): FieldUsage id that should be invoked.
    '''

    session = Session()
    print('invoke_webhooks_fieldusage called with {}'.format(usage_id))

    (doc_id, type_name, timestamp, data, field_id, user_id) = (
        session
            .query(FieldUsage)
            .join(FieldUsageType)
            .join(Field)
            .filter(FieldUsage.id == usage_id)
            .with_entities(
                Field.document_id,
                FieldUsageType.name,
                FieldUsage.timestamp,
                FieldUsage.data,
                Field.id,
                Field.user_id
            )
            .one()
    )

    post_data = json.dumps({
        'doc_id': UUID(bytes=doc_id).hex,
        'field_id': UUID(bytes=field_id).hex,
        # user_id is NULL for dependent fields
        'user_id': UUID(bytes=user_id).hex if user_id is not None else None,
        'type': 'field',
        'usage_type': type_name,
        'timestamp': timestamp.isoformat(),
        'data': json.loads(data)
    })

    __invoke_webhooks(session, doc_id, post_data)
