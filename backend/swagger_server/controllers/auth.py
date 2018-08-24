import uuid
import urllib

from flask import request
from flask_jwt_extended import (
    create_access_token
)

from ..db import Session
from ..mappings import *
from ..jwt_claims import TokenObject
from ..models import AuthResult, ErrorMessage

def auth_post(username: str, password: str = None):
    """ Log in as a user. Responds with a JWT
        if the authentication succeeds otherwise
        returns an error message detailing.
    """

    from ..app import bcrypt

    session = Session()

    account = (
        session
            .query(User)
            .filter(User.username == username)
            .filter(User.deleted != True)
            .one_or_none()
    )

    if account and not account.password and not password:
        uid = uuid.UUID(bytes=account.id)
        token = create_access_token(identity=uid)
        return AuthResult(token=token)
    if account and account.password and password and\
            bcrypt.check_password_hash(account.password, password):
        uid = uuid.UUID(bytes=account.id)
        token = create_access_token(identity=uid, expires_delta=False)
        return AuthResult(token=token)

    return ErrorMessage('Invalid username or password'), 401

def auth_access_id_post():
    """ Authorize using an access id. """
    session = Session()
    accessId = request.headers['accessId']

    access_id = urllib.parse.unquote(accessId)

    account = (
        session
            .query(AccessURI)
            .filter(AccessURI.uri == access_id)
            .one_or_none()
    )

    if not account:
        return ErrorMessage(
            msg="Invalid Access ID"
        ), 401

    if account.revoked:
        return ErrorMessage(
            msg="Access ID has been revoked"
        ), 401

    uid = uuid.UUID(bytes=account.user_id)
    doc = uuid.UUID(bytes=account.document_id)

    token = create_access_token(TokenObject(
        uid=uid,
        tgt_doc=doc
    ))

    return AuthResult(token=token), 200
