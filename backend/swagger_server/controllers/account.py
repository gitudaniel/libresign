import uuid
from uuid import UUID

from flask import jsonify
from flask_jwt_extended import (
    jwt_required, create_access_token, get_jwt_identity
)
from validate_email import validate_email

from .. import config
from ..db import Session
from ..mappings import *
from ..models import ErrorMessage, DocumentID, SignatureID
from ..app import bcrypt

@jwt_required
def account_fields_get():
    """ Fetch all fields for the current user.

        Response:
            If successful returns HTTP 200 and
            a JSON list containg details about
            each field for the user. See the
            swagger spec for the JSON object
            schema.

            If an error occurs then an HTTP 4XX
            status will be returned.
    """

    uid = UUID(hex=get_jwt_identity())

    session = Session()

    user = session.query(User.id).filter_by(id=uid.bytes).one_or_none()
    if not user:
        return ErrorMessage('User does not exist'), 400

    signatures = (
        session
            .query(FieldUsage)
            .join(Field)
            .join(Document)
            .filter(Field.user_id == uid.bytes)
            .order_by(FieldUsage.timestamp.desc())
            .with_entities(
                Field.id,
                FieldUsage.fieldusage_type,
                Document.title,
                FieldUsage.timestamp
            )
            .all()
    )

    idmap = set()

    output = []
    for sig, status, title, timestamp in signatures:
        sig = UUID(bytes=sig).hex

        if sig in idmap:
            continue
        idmap.add(sig)

        output.append(SignatureID(
            id=sig,
            status=config.FIELD_USAGE_TYPE.inv[status],
            title=title,
            timestamp=timestamp.isoformat()
        ))

    return output

@jwt_required
def account_change_password_post(newPassword: str):
    """ Change the current user's password
        to the given password.

        Arguments:
            newPassword (str): The new password

        Response:
            If successful, this endpoint will return
            HTTP 204 with no body.

            If an error occurs then this endpoint will
            return a HTTP 4XX status code and a JSON
            body describing the error
    """

    try:
        if newPassword == '':
            return jsonify({'title': 'No password provided'}), 400

        uid = uuid.UUID(hex=get_jwt_identity())
        pwhash = bcrypt.generate_password_hash(newPassword)

        session = Session()

        count = (
            session
                .query(User)
                .filter_by(id=uid.bytes)
                .filter(User.deleted != False)
                .update({'password': pwhash}, synchronize_session=False)
        )

        if count == 0:
            return jsonify({'title': 'User does not exist'}), 400
        elif count > 1:
            raise AssertionError("Multiple users with id {} in database".format(hash))

        return None, 204

    except Exception as e:
        print(str(e))
        raise

def account_create_post(username: str, password: str, business: int):
    """ Create a new account with the given
        username and password and attach it
        to the given business.

        Arguments:
            username (str): The new user's username.
            password (str): The new user's password.
            business (int):
                The business that the user
                account will be attached to.

        Response:
            If successful, responds with HTTP 200 and a
            JWT that the new user can use to authenticate
            with other API endpoints.

            If an error occurs, responds with an HTTP 4XX
            status and a JSON body containing details
            about the error.
    """

    if username == '':
        return ErrorMessage('Username was empty'), 400
    if password == '':
        return ErrorMessage('Password was empty'), 400

    if not validate_email(username):
        return ErrorMessage('Invalid email address'), 400

    session = Session()

    existing = session.query(User).filter_by(username=username).one_or_none()
    business = session.query(Business).filter_by(id=int(business)).one_or_none()

    if existing:
        return ErrorMessage('User already exists'), 400
    if not business:
        return ErrorMessage('Business does not exist'), 400

    uid = uuid.uuid4()
    new_user = User(
        id=uid.bytes,
        username=username,
        password=bcrypt.generate_password_hash(password),
        business_id=business.id
    )

    session.add(new_user)
    session.commit()

    return jsonify(token=create_access_token(identity=uid.hex))

@jwt_required
def account_delete_post():
    """ Mark an account for deletion, this will keep
        the account info until all documents owned by
        other accounts that reference it are deleted.
        The account can be brought back using the
        /account/resurrect endpoint while it has not
        been fully deleted. This endpoint will also
        revoke all access URIs for the user, if the
        account is resurrected it will have to get new
        access URIs from document owners.

        Responses:
            If successful, responds with an HTTP 202
            status and an empty body.

            If an error occurs, responds with an
            HTTP 4XX status code and a JSON body
            giving details about the error message.
    """

    # TODO: Delete all documents owned by the user being deleted.

    uid = uuid.UUID(hex=get_jwt_identity())

    session = Session()

    numrows = (
        session
            .query(User)
            .filter(User.id == uid.bytes)
            .filter(User.deleted != True)
            .update({'deleted': True}, synchronize_session=False)
    )

    if numrows == 0:
        return ErrorMessage("User already deleted or not found"), 400

    # Revoke all AccessURIs for this account,
    # undeleting the account does not make them
    # accessible again
    (
        session
            .query(AccessURI)
            .filter(AccessURI.user_id == uid.bytes)
            .update({'revoked': True}, synchronize_session=False)
    )

    session.commit()

    return None, 202

@jwt_required
def account_documents_get():
    """ Fetch a list of all documents owned by the
        current user with some details for each
        document. See the swagger specification
        for the schema used.

        Responses:
            If successful returns HTTP 200 with
            the JSON objects containing details
            about each document.

            If an error occurrs then it returns
            an HTTP 4XX error code with a JSON
            body detailing the response.
    """

    uid = uuid.UUID(hex=get_jwt_identity())

    session = Session()

    user = session.query(User.id).filter_by(id=uid.bytes).one_or_none()
    if not user:
        return jsonify(title='User does not exist'), 400

    docs = (
        session
            .query(Document)
            .filter_by(user_id=uid.bytes)
            .all()
    )

    result = [
        DocumentID(
            id=uuid.UUID(bytes=doc.id).hex,
            title=doc.title
        )
    for doc in docs]

    return result, 200

def account_resurrect_post(username: str, password: str):
    ''' Resurrect an account that has been deleted.
        Note that this can only be done to accounts
        that had a password before being deleted.

        Responses:
            If successful, returns HTTP 204.

            If an error occurrs returns an HTTP 4XX status
            and a JSON body containing details about the
            error.
    '''
    session = Session()

    account = (
        session
            .query(User)
            .filter(User.username == username)
            .one_or_none()
    )

    if not account:
        return ErrorMessage("No such user exists"), 404

    if not account.deleted:
        return ErrorMessage("This user is not deleted"), 400

    if not account.password:
        return ErrorMessage("This user may not be resurrected"), 400

    if not bcrypt.check_password_hash(account.password, password):
        return ErrorMessage("Invalid password"), 401

    return None, 204
