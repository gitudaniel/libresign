import os
import re
import json
import base64
import logging

from uuid import UUID
from urllib.parse import urlencode
from email.message import EmailMessage

import requests

from .. import config, app
from ..db import Session
from ..mappings import *
from ..ipinfo import *
from ..tasks import invoke_webhooks_fileusage
from ..helpers import type_check

@type_check
def _load_dict(val) -> dict:
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        return json.loads(val)
    return None

@type_check
def _get_template(session, business: int) -> dict:
    ''' Retrieve the template from the business config
        or take default values from the config if it
        isn't present.
    '''

    template = (
        session
            .query(BusinessConfig)
            .filter(BusinessConfig.business_id == business)
            .filter(BusinessConfig.key == "email-template")
            .with_entities(BusinessConfig.values)
            .one_or_none()
    )

    default = {
        'subject': config.DEFAULT_EMAIL_TEMPLATE_SUBJECT,
        'body': config.DEFAULT_EMAIL_TEMPLATE_BODY,
        'server': None,
        'sender': 'nobody@example.com',
        'reply-to': 'nobody@example.com',
        'apikey': None
    }

    if not template:
        return default

    default.update(_load_dict(template[0]))

    return default

@type_check
def _fill_body_template(template: str, access_uri: str, docid: bytes) -> str:
    ''' Replace template strings with their associated
        values.

        There is currently only one template string that
        is used: {{params}} which is replaced with an
        urlencoded dictionary containing the auth token
        and doc (docid) parameters. Note that auth is
        meant to be used with the access endpoint.

        Arguments:
            template (str): Email template string
            access_uri (str): Auth token
            docid (bytes): Document ID

        Returns:
            The template string with all template sequences
            replaced.
    '''

    params = urlencode({
        'auth': access_uri,
        'doc': UUID(bytes=docid).hex
    })

    return re.sub(r'\{\{params\}\}', params, template)

@type_check
def _add_audit_entry(session, email: str, sender: str, docid: bytes):
    '''Insert a FileUsage entry recording that a reminder email was sent'''

    entry = FileUsage(
        document_id=docid,
        fileusage_type=config.FILE_USAGE_TYPES['reminder-email-sent'],
        data=json.dumps({
            'sender': sender,
            'target': email
        })
    )

    session.add(entry)

    session.flush()
    invoke_webhooks_fileusage.delay(entry.id)

@type_check
def _send_individual_email(session, business: int, tgtemail: str, uid: bytes, docid: bytes):
    ''' Send one email to a user '''

    # Generate a cryptographically secure uri
    access_uri = base64.b64encode(os.urandom(66)).decode('utf8')

    session.add(AccessURI(
        uri=access_uri,
        user_id=uid,
        document_id=docid
    ))

    template = _get_template(session, business)

    text = _fill_body_template(
        template['body'],
        access_uri,
        docid
    )

    # If no server is configured then
    # we don't send an email
    if not template['server'] or not template['apikey']:
        # But we still log it since this is most likely an error
        logging.error(
            "Attempted to send email to %s but no email server was configured",
            tgtemail
        )
        return

    msg = EmailMessage()
    msg.set_content(text)

    msg['Subject'] = template['subject']
    msg['From'] = template['sender']
    msg['To'] = tgtemail.strip()
    if 'reply-to' in template and template['reply-to']:
        msg['Reply-To'] = template['reply-to']

    r = requests.post(
        'https://api.mailgun.net/v3/' + template['server'] + '/messages.mime',
        auth=('api', template['apikey']),
        data={
            'to': tgtemail.strip()
        },
        files={
            'message': ('email', msg.as_bytes(), 'multipart/mixed')
        }
    )

    r.raise_for_status()

@type_check
def _send_email_internal(docId: str, tgtemail):
    doc_id = UUID(hex=docId)
    session = Session()

    print("Starting email task for document {}".format(docId))

    business = (
        session
            .query(Document)
            .join(User)
            .join(Business)
            .filter(Document.id == doc_id.bytes)
            .with_entities(Business.id)
            .one()
    )[0]

    emails = {}
    if not tgtemail:
        result = (
            session
                .query(Field)
                .join(User)
                .filter(Field.document_id == doc_id.bytes)
                .with_entities(User.username, User.id)
                .distinct()
        )

        for (email, uid) in result:
            emails[email] = uid
    else:
        result = (
            session
                .query(Field)
                .join(User)
                .filter(Field.document_id == doc_id.bytes)
                .filter(User.username == email)
                .with_entities(User.username, User.id)
                .distinct()
        )

        for (addr, uid) in result:
            emails[addr] = uid

    for (tgtemail, uid) in emails.items():
        _send_individual_email(session, business, tgtemail, uid, doc_id.bytes)
        _add_audit_entry(session, tgtemail, tgtemail, doc_id.bytes)

    session.commit()

@app.celery.task
@type_check
def send_email(docId: str, email=None):
    ''' Send an email to the specified address
        using the email template within the database.
        If no email is provided (email is None) then
        send out the email to all users who still have
        an unfilled field within the document.

        If no template is provided then use the default
        template from the config.

        Arguments:
            docId (str): The document ID regarding which we are
                sending emails.
            email (str|None): The email that we are sending this to,
                or none for all users that still have an empty field
                on the document.
    '''

    _send_email_internal(docId, email)
