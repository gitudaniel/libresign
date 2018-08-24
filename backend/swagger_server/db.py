# Global is needed here
# pylint: disable=W0603

from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import event, DDL

from flask import request

from . import mappings, config

def _get_current_request_or_task():
    from .app import celery
    if request:
        return request
    return celery.current_task.request.id

Session = scoped_session(
    sessionmaker(autoflush=False, autocommit=False),
    scopefunc=_get_current_request_or_task
)
_configured = False

def init_db(engine):
    global Session
    global _configured

    if _configured:
        return Session

    _configured = True
    mappings.init(engine)
    Session.session_factory.configure(bind=engine)
    return Session

# Add initial config values to the database

def __decl_events():
    from .mappings import FieldUsageType, FieldType, FileUsageType, Business

    def get_values(x):
        values = []
        for name, val in x.items():
            values.append("({}, '{}')".format(val, name))
        return ', '.join(values)

    def make_ddl(tablename, x):
        return DDL(
            "INSERT INTO {} (id, name) VALUES {}"
                .format(tablename, get_values(x))
        )

    event.listen(
        FieldUsageType.__table__,
        'after_create',
        make_ddl(FieldUsageType.__tablename__, config.FIELD_USAGE_TYPE)
    )

    event.listen(
        FieldType.__table__,
        'after_create',
        make_ddl(FieldType.__tablename__, config.FIELD_TYPE)
    )

    event.listen(
        FileUsageType.__table__,
        'after_create',
        make_ddl(FileUsageType.__tablename__, config.FILE_USAGE_TYPE)
    )

    event.listen(
        Business.__table__,
        'after_create',
        DDL("INSERT INTO {} (id) VALUES (1)".format(Business.__tablename__))
    )

__decl_events()
