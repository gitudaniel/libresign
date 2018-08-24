
import logging
from raven import Client
from raven.contrib.celery import register_signal, register_logger_signal
import swagger_server.app as swagger_app

swagger_app.main()

app = swagger_app.app
flask_app = swagger_app.flask_app
celery = swagger_app.celery

# Register sentry hooks
client = Client()

# register a custom filter to filter out duplicate logs
register_logger_signal(client)

# The register_logger_signal function can also take an optional argument
# `loglevel` which is the level used for the handler created.
# Defaults to `logging.ERROR`
register_logger_signal(client, loglevel=logging.INFO)

# hook into the Celery error handler
register_signal(client)

# The register_signal function can also take an optional argument
# `ignore_expected` which causes exception classes specified in Task.throws
# to be ignored
register_signal(client, ignore_expected=True)
