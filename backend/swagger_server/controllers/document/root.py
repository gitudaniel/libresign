import re
import json
import uuid
import requests

from uuid import UUID

from flask import request, jsonify, Response, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from validate_email import validate_email

from ... import validate, storage, config, tasks
from ...db import Session
from ...mappings import *
from ...ipinfo import *
from ...models import ErrorMessage
from ...helpers import type_check

# Document field referencing spec(ish):
# Fields that are meant to reference
# other fields must be filled with a
# reference tag. The reference tag will
# be formatted like this:
# { <tag-type> : <referenced-field> }
# Currently the only tag type that
# is available is the `date` field type
# but it is possible that others can be
# added in the future.

valid_field_types = [
    'date'
]

class FieldDescription:
    ''' Description for a field, this is the result of
        parsing the field description

        Fields:
            name (str): The field name
            type (str): The field type
            parent (str):
                The parent field name, if
                this field has a parent
    '''
    @type_check
    def __init__(self, name: str, ty: str, parent: str = None):
        self.name = name
        self.type = ty
        self.parent = parent

    def __str__(self):
        return str({
            'name': self.name,
            'type': self.type,
            'parent': self.parent
        })

    def validate_type(self) -> bool:
        return self.type in config.FIELD_TYPE

@type_check
def error_abort(fields: dict, status: int):
    ''' Shortcut to abort with a JSON error message '''
    abort(Response(json.dumps(fields), status, mimetype='application/json'))

@type_check
def content_type_is_pdf(file) -> bool:
    ''' Check to see if the content type is
        application/pdf or application/octet-stream
    '''
    return file.content_type == 'application/pdf' or \
        file.content_type == 'application/octet-stream'
def validate_content_type(file):
    ''' Check to see if the content type is valid
        and abort with HTTP 415 if it is not.
    '''

    if not content_type_is_pdf(file):
        error_abort(
            {
                'title': 'Unacceptable Content-Type',
                'description':
                    f'File had a content type of "{file.content_type}",'
                    f'was expecting "application/pdf" or "application/octet-stream"'
            },
            415
        )
def validate_content_length(file):
    ''' Verify the content length of the file,
        and abort with HTTP 413 if it is too
        large.
    '''
    # Note: content_length appears to always be 0
    # May need to require Content-Length header
    if file.content_length > config.MAX_FILE_SIZE:
        error_abort(
            {
                'title': 'File too large',
                'description':
                    f'Uploaded file had a size of '
                    f'{file.content_length / (1024 * 1024)} MB, '
                    f'the maximum permitted size is '
                    f'{config.MAX_FILE_SIZE / (1024 * 1024)} MB.'
            },
            413
        )

def json_is_acceptable() -> bool:
    ''' Check that the Accept header (if provided)
        allows us to return JSON.
    '''
    # If there is no accept header, then
    # we assume the client accepts JSON.
    # Otherwise, check to see if JSON is
    # acceptable by the client
    return not 'Accept' in request.headers or \
        'application/json' in request.accept_mimetypes

@type_check
def create_user(session, user: str, business: int):
    ''' Create a new user with no password which
        means that the user will not be able to
        log in except by using the /access endpoint.
    '''
    new_uid = uuid.uuid4()

    new_user = User(
        id=new_uid.bytes,
        username=user,
        password=None,
        business_id=business
    )

    session.add(new_user)
    session.flush()

    return (new_uid.bytes,)

@type_check
def get_document_fields(pdfdata) -> dict:
    ''' Query the field extractor service to get
        the fields within the provided service
    '''

    resp = requests.post(
        config.PDF_SERVICE_URL + '/fields',
        pdfdata,
        headers={'Content-Type': 'application/pdf'}
    )

    if resp.status_code != 200:
        error_abort({
            'title': 'Unable to parse PDF form',
            'details': resp.content
        }, 400)

    return {k.strip(): v.strip() for k, v in json.loads(resp.content).items()}

def strip_if_not_none(s: str) -> str:
    ''' Utility method to strip if not None '''
    if s:
        return s.strip()
    return s

@type_check
def parse_field(name: str, value: str):
    ''' Given a field name and value, parse out
        the type and parent field specifiers
        into a FieldDescription object.
    '''

    match = re.match(
        r'\s*\{\s*((?:\w|\d|[._,?+=\-&*\^%$#@! ])+)\s*(?::\s*((?:\w|\d|\.| )+)\s*)?\}\s*',
        value
    )

    if not match:
        return None

    return FieldDescription(
        name=name,
        parent=strip_if_not_none(match.group(2)),
        ty=strip_if_not_none(match.group(1))
    )

def parse_reference_field(name: str, value: str) -> FieldDescription:
    return parse_field(name, value)
@type_check
def get_reference_fields(fields: dict) -> list:
    ''' Get all reference fields from the list of fields
    '''

    refs = []
    for k, v in fields.items():
        field = parse_field(k, v)
        if field and field.parent:
            refs.append(field)

    return refs
@type_check
def validate_reference_fields(fields: dict, refs: list):
    ''' Validates that all reference fields
        have valid parents and types and
        aborts with a message if this is not
        true for all fields
    '''

    for ref in refs:
        if not ref.parent in fields:
            error_abort({
                'title': 'Invalid reference field',
                'detail':
                    f"Field {ref.name} references field "
                    f"{ref.parent}, which doesn't exist"
            }, 400)
        if not ref.type in valid_field_types:
            error_abort({
                'title': 'Invalid field type',
                'description': (
                    'Field {} has an invalid type of {}, ' +
                    ' see the valid field for valid field types'
                ).format(
                    ref.name,
                    ref.type
                )
            }, 400)

@type_check
def validate_user_filled_fields(fields: dict, signators: dict):
    ''' Verify that all fields that are linked to
        signators actually have corresponding fields
        within the document and that those fields
        are actually fillable (contain a field specifier).
        This method aborts with HTTP 400 if the conditions
        are violated.
    '''

    for sig_field in signators.keys():
        if not sig_field in fields:
            error_abort(dict(
                title='Description JSON contained a signature' +
                    ' field not present in the PDF document.',
                field=sig_field
            ), 400)

        desc = parse_field(sig_field, fields[sig_field])

        if not desc:
            error_abort(dict(
                title='Field in description JSON was in the document' +
                    ', but did not contain a field specifier.',
                field=sig_field
            ), 400)

        if not desc.validate_type():
            error_abort({
                'title': 'Field contained an invalid type',
                'field': sig_field,
                'field-type': desc.type,
                'valid-types': config.FIELD_TYPE
            }, 400)

        if desc.parent and desc.type != 'date':
            error_abort({
                'title': "A reference field had a type other than 'date'",
                'field': sig_field,
                'field-type': desc.type
            }, 400)

    validate.validate_pdf(signators, fields)

@type_check
def parse_signators(strval: str) -> dict:
    ''' Convert the signators parameter to JSON
        and abort if the JSON parsing fails.
    '''

    try:
        return json.loads(strval)
    except json.JSONDecodeError:
        error_abort(dict(
            title="Invalid JSON",
            description="Signators parameter contained invalid JSON"
        ), 400)

@type_check
def create_field(
    session,
    doc_id: UUID,
    name: str,
    user, # str|NoneType
    parent: bytes = None,
    field_type: int = config.FIELD_TYPE['signature'],
    business: int = None
) -> UUID:
    ''' Create a new field with the given
        type, parent, for the given document.

        This function will also create the
        user if one with the given username
        does not exist.
    '''

    uid = None

    # If this field won't have a user associated
    # with it, then don't create a new user
    if user:
        uid = (
            session
                .query(User)
                .filter_by(username=user)
                .with_entities(User.id)
                .one_or_none()
        )

        # Create user if they don't exist yet
        if not uid:
            uid = create_user(session, user, business)

        uid = uid[0]

    field_id = uuid.uuid4()

    field = Field(
        id=field_id.bytes,
        user_id=uid,
        document_id=doc_id.bytes,
        field_type=field_type,
        field_name=name,
        parent=parent
    )
    fieldusage = FieldUsage(
        field_id=field_id.bytes,
        fieldusage_type=config.FIELD_USAGE_TYPE['empty']
    )

    session.add(field)
    session.add(fieldusage)

    return field_id

@type_check
def create_document(session, user_id: UUID, title: str):
    ''' Create a new document '''

    file_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    username = (
        session
            .query(User)
            .filter(User.id == user_id.bytes)
            .with_entities(User.username)
            .one()
    )[0]

    file_db = File(
        id=file_id.bytes,
        filename=file_id.hex)
    doc_db = Document(
        id=doc_id.bytes,
        title=title,
        user_id=user_id.bytes
    )
    fileusage_db = FileUsage(
        file_id=file_id.bytes,
        document_id=doc_id.bytes,
        fileusage_type=config.FILE_USAGE_TYPES['created'],
        data=json.dumps({
            'ip': get_ip(),
            'user': username
        })
    )

    session.add(file_db)
    session.add(doc_db)
    session.add(fileusage_db)

    session.flush()
    assert fileusage_db.id is not None
    tasks.invoke_webhooks_fileusage.delay(fileusage_db.id)

    return (doc_id, file_id)

@jwt_required
@fetch_ip
def document_post(docName: str, signators: str, file):
    ''' Create a new document. Specifically, validate
        that all fields provided within the signators
        are present and valid, that all reference fields
        within the document are present and valid. This
        will also create new user accounts for users
        that are provided to sign the document but
        don't currently have an account in the system.

        Arguments:
            docName (str): The name of the new document.
            signators (str):
                JSON object mapping all fields that
                should be directly signed to the email
                of a signator, if the field should be
                left blank then `null` should be used
                instead of an email. See the swagger
                spec for a schema of this object.
            file (FileStorage):
                The document as a PDF form.

        Response:
            If successful, this endpoint will respond
            with HTTP status 200 and a JSON object
            containing a document ID and any warnings
            that were issued while creating the document.

            If an error occurs then this will respond
            with a 4XX error code and a JSON body
            describing the error.
    '''

    warnings = []

    validate_content_type(file)
    validate_content_length(file)

    signatures = parse_signators(signators)

    for email in signatures.values():

        if email is not None and not validate_email(email):
            return ErrorMessage(
                '{} is not a valid email address'.format(email)
            ), 400

    fields = get_document_fields(file)
    refs = get_reference_fields(fields)

    validate_user_filled_fields(fields, signatures)
    validate_reference_fields(fields, refs)

    session = Session()
    container = storage.container()
    user_id = uuid.UUID(hex=get_jwt_identity())

    business = (
        session
            .query(User)
            .filter(User.id == user_id.bytes)
            .join(Business)
            .with_entities(Business.id)
            .one()
    )[0]

    doc_id, file_id = create_document(session, user_id, docName)

    file.stream.seek(0)

    container.upload_blob(
        filename=file.stream,
        content_type='application/pdf',
        blob_name=file_id.hex)

    field_ids = {}

    # Create signatures
    for field, user in signatures.items():
        field_type = parse_field(field, fields[field]).type
        field_id = create_field(
            session,
            doc_id,
            field,
            user,
            field_type=config.FIELD_TYPE[field_type],
            business=business
        )
        field_ids[field] = field_id

    for ref_field in refs:
        if ref_field.parent not in field_ids:
            warnings.append(dict(
                msg=(
                    'Parent field {} of field {} was not present. ' +
                    "Check to make sure that it doesn't depend on " +
                    "a different reference field or that the parent " +
                    "field exists."
                ).format(
                    ref_field.parent,
                    ref_field.name
                )
            ))
        else:
            create_field(
                session,
                doc_id,
                ref_field.name,
                user=None,
                parent=field_ids[ref_field.parent].bytes,
                field_type=config.FIELD_TYPE[ref_field.type],
                business=business
            )

    session.commit()

    # Launch celery task to add a FileUsage entry
    # containing the fields for the new document
    tasks.get_field_info.delay(doc_id.hex)
    tasks.stamp_pdf.delay(doc_id.hex)

    # TODO: Change raw JSON into an object binding
    return jsonify(docId=doc_id.hex, warnings=warnings), 200
