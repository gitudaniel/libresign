
import json

from io import BytesIO

from flask import Flask, request, Response
from flask_cors import CORS

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from raven.contrib.flask import Sentry

app = Flask(__name__)
CORS(app)
Sentry(app)

@app.route('/', methods=['POST'])
def create_audit_log():
    if request.content_type != 'application/json':
        return json.dumps({
            'msg': 'Request Content-Type must be application/json'
        }), 415

    entries = None
    try:
        entries = json.loads(request.data)
    except json.JSONDecodeError:
        return json.dumps({
            'msg': 'Request contained invalid JSON'
        }), 400

    if type(entries) != list:
        return json.dumps({
            'msg': 'Request JSON was not an array'
        }), 400

    stream = BytesIO()

    doc = SimpleDocTemplate(
        stream,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )

    story = []
    styles = getSampleStyleSheet()

    for entry in entries:
        if entry['status'] == 'viewed':
            story.append(Paragraph(
                'Viewed by {} at {} UTC, IP: {}'.format(
                    entry['data']['user'],
                    entry['timestamp'],
                    entry['data']['ip']),
                styles['Normal']
            ))
        elif entry['status'] == 'created':
            story.append(Paragraph(
                'Created by {} at {} UTC, IP: {}'.format(
                    entry['data']['user'],
                    entry['timestamp'],
                    entry['data']['ip']),
                styles['Normal']
            ))
        elif entry['status'] == 'filled':
            story.append(Paragraph(
                'Signed by {} at {} UTC, IP: {}'.format(
                    entry['data']['user'],
                    entry['timestamp'],
                    entry['data']['ip']),
                styles['Normal']
            ))

    doc.build(story)

    return Response(
        stream.getvalue(),
        mimetype='application/pdf',
        status=200
    )
    