#!/usr/bin/python3

# pylint: disable=W0603

import sys
import json
import argparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mappings import *

Session = sessionmaker(autoflush=False, autocommit=False)
session = None

def build_engine(dburi):
    global session

    engine = create_engine(dburi)
    Session.configure(bind=engine)
    session = Session()

def create_webhook(business, webhook):
    session.add(
        BusinessConfig(
            business_id=business,
            key="webhook",
            values=json.dumps({
                'url': webhook
            })
        )
    )

def create_email_template(
    business,
    subject,
    body,
    reply_to=None,
    server=None,
    sender=None,
    apikey=None
):
    prev = (
        session
            .query(BusinessConfig)
            .filter(BusinessConfig.key == "email-template")
            .filter(BusinessConfig.business_id == business)
            .order_by(BusinessConfig.id.desc())
            .with_entities(BusinessConfig.values)
            .first()
    )

    values = json.loads(prev[0]) if prev is not None else {}
    new_vals = {
        'body': body,
        'subject': subject,
        'reply-to': reply_to,
        'server': server,
        'sender': sender,
        'apikey': apikey,
    }

    new_vals = {k: v for k, v in new_vals.items() if v is not None}

    values.update(new_vals)

    # Delete all email templates for this business
    # since there can only be one email template
    prev = (
        session
            .query(BusinessConfig)
            .filter(BusinessConfig.key == "email-template")
            .filter(BusinessConfig.business_id == business)
            .delete()
    )

    session.add(
        BusinessConfig(
            business_id=business,
            key="email-template",
            values=json.dumps(values)
        )
    )

def parse_args(args):
    parser = argparse.ArgumentParser(
        description="Business configuration tool for LibreSign"
    )

    parser.add_argument('dburi', metavar='database-uri', action='store',
        help='The database URI (including user and password)')
    parser.add_argument('business', action='store',
        help='The relevant business ID')

    parser.add_argument('--email-body-file', dest='body', action='store',
        default=None, help='Body of the email template')
    parser.add_argument('--email-subject', dest='subject', action='store',
        default=None, help='Subject of the email template')
    parser.add_argument('--email-reply-to', dest='reply_to', action='store',
        default=None, help='Reply-To address for email template')
    parser.add_argument('--email-sender', dest='sender', action='store',
        default=None, help='Sender address for email template')
    parser.add_argument('--email-api-key', dest='apikey', action='store',
        default=None, help='Mailgun API key for mail server')
    parser.add_argument('--email-server', dest='server', action='store',
        default=None, help='Email server to send the mail from')

    parser.add_argument('--webhook', dest='webhooks', action='append',
        nargs='+', default=[], help='Add a webhook URL')

    return parser.parse_args(args)

def main():
    args = parse_args(sys.argv[1:])

    dburi = args.dburi
    business = args.business

    email_body = open(args.body, 'r').read() if args.body is not None else None
    email_subject = args.subject
    email_reply_to = args.reply_to
    email_sender = args.sender

    build_engine(dburi)

    if email_body or email_subject or email_reply_to or email_sender:
        create_email_template(
            business,
            subject=email_subject,
            body=email_body,
            reply_to=email_reply_to,
            sender=email_sender,
            server=args.server,
            apikey=args.apikey
        )

    for webhook in args.webhooks:
        create_webhook(business, webhook)

    session.commit()
    session.close()

if __name__ == '__main__':
    main()
