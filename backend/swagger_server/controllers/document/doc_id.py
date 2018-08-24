from uuid import UUID
import requests

from flask import Response, stream_with_context, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from ... import storage, config, tasks
from ...db import Session
from ...mappings import *
from ...ipinfo import *
from ...models import ErrorMessage
from ...decorators import produces
from ...helpers import verify_permission, add_doc_audit_entry, type_check

@jwt_required
def delete(docId: str):
    """ Delete a document and all artifacts associated
        with the document (audit log, rendered pages,
        file usages, field usages, fields, etc.).
        This action is irreversible and will also
        delete the document without notice for all
        users who have fields to fill within the
        document.

        Arguments:
            docId (str): The document ID

        Response:
            If the document was successfully deleted
            this endpoint will respond with HTTP
            status 204 and an empty body.

            If an error occurrs then this will respond
            with a 4XX error code and a JSON body
            describing the error.
    """

    doc_id = None
    try:
        doc_id = UUID(hex=docId)
    except ValueError:
        return ErrorMessage(msg="Invalid document ID"), 400

    session = Session()

    if not verify_permission(session, doc_id, False):
        return ErrorMessage(msg="Not Authorized"), 401

    files = (
        session
            .query(FileUsage)
            .filter_by(document_id=doc_id.bytes)
            .with_entities(FileUsage.file_id)
    ).union_all(
        session
            .query(RenderedPage)
            .filter(RenderedPage.document_id == doc_id.bytes)
            .with_entities(RenderedPage.file_id)
    )

    names = map(
        lambda x: x[0],
        files
            .join(File)
            .with_entities(File.filename)
            .all()
    )
    fields = (
        session
            .query(FieldUsage)
            .join(Field)
            .filter_by(document_id=doc_id.bytes)
            .with_entities(FieldUsage.id)
    )

    (
        session
            .query(FileUsage)
            .filter_by(document_id=doc_id.bytes)
            .delete(synchronize_session=False)
    )

    (
        session
            .query(File)
            .filter(File.id.in_(files.subquery()))
            .delete(synchronize_session=False)
    )

    (
        session
            .query(FieldUsage)
            .filter(FieldUsage.id.in_(fields.subquery()))
            .delete(synchronize_session=False)
    )

    (
        session
            .query(Field)
            .filter_by(document_id=doc_id.bytes)
            .delete(synchronize_session=False)
    )

    (
        session
            .query(Document)
            .filter_by(id=doc_id.bytes)
            .delete(synchronize_session=False)
    )

    session.commit()

    tasks.delete_blobs.delay([x for x in names])

    return None, 204

@type_check
def get_as_pdf(session, doc_id: UUID):
    ''' Fetch the document as a PDF '''

    container = storage.container()
    uid = UUID(hex=get_jwt_identity())

    username = (
        session
            .query(User)
            .filter(User.id == uid.bytes)
            .with_entities(User.username)
            .one()
    )[0]

    add_doc_audit_entry(
        session,
        doc_id,
        config.FILE_USAGE_TYPES['viewed'],
        {
            'ip': get_ip(),
            'user': username
        }
    )

    session.commit()

    filename = (
        session
            .query(FileUsage)
            .join(File)
            .filter(FileUsage.document_id == doc_id.bytes)
            .filter(FileUsage.file_id.isnot(None))
            .order_by(FileUsage.timestamp.desc())
            .with_entities(File.filename)
            .first()
    )

    if not filename:
        return ErrorMessage("Not Found"), 404
    filename = filename[0]

    blob = container.get_blob(filename)
    url = blob.generate_download_url(expires=60)
    r = requests.get(url, stream=True)

    return Response(
        stream_with_context(r.iter_content(chunk_size=1024)),
        mimetype=r.headers['Content-Type'],
        status=200
    )
@type_check
def get_as_png(session, doc_id: UUID, page: int):
    ''' Fetch the page of a document as a PNG image '''
    container = storage.container()

    filename = (
        session
            .query(Document)
            .filter(Document.id == doc_id.bytes)
            .join(RenderedPage)
            .filter(RenderedPage.page == page)
            .join(File)
            .order_by(RenderedPage.id.desc())
            .with_entities(File.filename)
            .first()
    )

    if not filename:
        return ErrorMessage(msg="Not Found"), 404

    filename = filename[0]

    blob = container.get_blob(filename)
    url = blob.generate_download_url(expires=60)
    r = requests.get(url, stream=True)

    return Response(
        stream_with_context(r.iter_content(chunk_size=1024)),
        mimetype=r.headers['Content-Type'],
        status=200
    )

def query_best():
    # Return PDF if client did not provide accept headers
    if not 'Accept' in request.headers:
        return 'application/pdf'

    return request.accept_mimetypes.best_match(
        ['application/pdf', 'image/png'],
        None
    )

@jwt_required
@fetch_ip
@produces('application/pdf', 'image/png')
def get(docId: str, page: int = None):
    """ Fetch a document or page of a document.
        This endpoint will record that the document
        has been viewed in the audit log. The
        format that will returned is decided by the
        `Accept` header. The default format is
        application/pdf in cases where no accept
        header is provided.

        Formats:
            * application/pdf
            * image/png

        Arguments:
            docId (str): The document ID
            page (int):
                The page to be fetched, ignored if the client
                is not requesting an image.

        Response:
            If successful, this endpoint will respond
            with HTTP status 200 and the page/pdf document.

            For most errors this endpoint will respond
            with a 4XX error code and a JSON body describing
            the error. However, if the document has been
            created but the image for a page hasn't been
            rendered yet then this endpoint will respond
            with a 503 error code and the `Retry-After` header
            will contain a time after which the image is
            expected to be ready.
    """

    session = Session()
    try:
        doc_id = UUID(hex=docId)
    except ValueError:
        return ErrorMessage(
            "Invalid document ID"
        ), 400

    if not verify_permission(session, doc_id):
        return ErrorMessage(
            "Not Authorized"
        ), 401

    accept = query_best()

    if accept == 'application/pdf':
        return get_as_pdf(session, doc_id)
    elif accept == 'image/png':
        return get_as_png(session, doc_id, int(page))
    else:
        return jsonify(
            title='Not Acceptable',
            valid=['application/json', 'image/png']
        ), 406
