
import os
from bidict import bidict

# Limit upload file size to 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024

PDF_SERVICE_URL = 'http://pdfservice:80'
FIELD_PARSER_URL = 'http://field-locator:80'
LOCALSTORAGE_KEY = '/var/pdfservice/storage'
GCP_AUTH_KEY_FILE = '/var/pdfservice/auth.json'
STORAGE_CONTAINER = 'pdf-esigner-file-storage'
PROPAGATE_EXCEPTIONS = True

CELERY_BROKER_URL = 'amqp://rabbitmq'
CELERY_RESULT_BACKEND = 'amqp://rabbitmq'
CELERY_TASK_PROTOCOL = 1
# Kill tasks after 3 mins if they haven't completed
CELERYD_TASK_TIME_LIMIT = 180

#DEBUG = True
SECRET_KEY = os.environ.get("SECRET_KEY", default="Test")
JWT_SECRET_KEY = SECRET_KEY

FILE_USAGE_TYPE = bidict({
    'created': 0,
    'updated': 1,
    'viewed': 2,
    'startstamp': 3,
    'endstamp': 4,
    'reminder-email-sent': 5,
    'describe-fields': 6,
    'agree-tos': 7,
    'all-fields-filled': 8
})
FILE_USAGE_TYPES = FILE_USAGE_TYPE

FIELD_TYPE = bidict({
    'signature': 0,
    'text': 1,
    'date': 2
})

FIELD_USAGE_TYPE = bidict({
    'filled': 0,
    'empty': 1,
    'agree-tos': 3,
})

SQLALCHEMY_ECHO = False
SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URI", default=None)
# Suppress warning since we don't use modification tracking
SQLALCHEMY_TRACK_MODIFICATIONS = False

MAIL_DEFAULT_SENDER = 'noreply@example.com'
REMINDER_TARGET_URL = 'http://localhost:3000/view'

DEFAULT_EMAIL_TEMPLATE_SUBJECT = "You have a document waiting to be signed"
DEFAULT_EMAIL_TEMPLATE_BODY = """
http://localhost:3000?{{params}}
"""

if not SQLALCHEMY_DATABASE_URI:
    raise ValueError("No database URI provided!")
