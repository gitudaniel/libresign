#!/usr/bin/env python3

# pylint: disable=W0601,W0603,W0611,C0301

import logging
import connexion

from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy

from celery import Celery

from raven.contrib.flask import Sentry

from . import encoder, db

jwt = JWTManager()
bcrypt = Bcrypt()
mail = Mail()
sqldb = SQLAlchemy()
sentry = Sentry(dsn='https://20a04cdea8984143ad0b5273742683c0:3cb83bf84c6b4fa2b82c37bf12fc0624@sentry.io/1260435')

def main():
    global app
    global flask_app
    global jwt
    global bcrypt
    global mail
    global celery
    global sqldb

    app = connexion.App(
        __name__,
        specification_dir='/usr/src/app/swagger_server/swagger',
        debug=True
    )

    CORS(app.app)

    app.app.config.from_envvar('FLASK_CONFIG')

    app.app.json_encoder = encoder.JSONEncoder

    # JWT, BCrypt and Mail
    jwt.init_app(app.app)
    bcrypt.init_app(app=app.app)
    mail.init_app(app.app)
    sqldb.init_app(app.app)
    sentry.init_app(app.app)

    flask_app = app.app

    # Create and wrap celery
    celery = Celery(
        app.app.import_name,
        backend=app.app.config['CELERY_RESULT_BACKEND'],
        broker=app.app.config['CELERY_BROKER_URL']
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                # Ensure the db is initialized
                # this will only allow it to be
                # initialized once so it's safe
                # to call it every time
                db.init_db(sqldb.engine)
                # Initialize session
                db.Session()
                try:
                    return self.run(*args, **kwargs)
                finally:
                    db.Session.remove()

    celery.conf.update(app.app.config)
    celery.Task = ContextTask

    @app.app.before_first_request
    def _init_sqlalchemy():
        db.init_db(sqldb.engine)

    @app.app.before_request
    def _create_session():
        # Ensure that the db adapter has
        # been created, the init_db method
        # will only initialize the database
        # the first time it is called
        db.init_db(sqldb.engine)
        db.Session()

    @app.app.after_request
    def _remove_session(res):
        db.Session.remove()
        return res

    app.add_api('swagger.yaml', arguments={'title': 'PDF Service'})

    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    #logging.getLogger().setLevel(logging.INFO)
