from sqlalchemy import Column, Binary, String, ForeignKey, DateTime, Integer
from sqlalchemy import Boolean
from sqlalchemy.dialects.postgresql.json import JSONB
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, configure_mappers

from sqlalchemy_continuum import make_versioned

# pylint: disable=C0301

Base = declarative_base()

make_versioned(user_cls=None)

class FileUsageType(Base):
    __tablename__ = "fileusage_type"
    id = Column(Integer(), primary_key=True)
    name = Column(String(32), nullable=False)

    usages = relationship('FileUsage')

class FieldUsageType(Base):
    __tablename__ = "fieldusage_type"
    id = Column(Integer(), primary_key=True)
    name = Column(String(32), nullable=False)

    usages = relationship('FieldUsage')

class Business(Base):
    __tablename__ = "business"
    id = Column(Integer(), primary_key=True, autoincrement=True)

    users = relationship('User')
    config = relationship('BusinessConfig')

class FieldType(Base):
    __tablename__ = "field_type"
    id = Column(Integer(), primary_key=True)
    name = Column(String(32), nullable=False)

    usages = relationship('Field')

class User(Base):
    __tablename__ = 'user'
    __versioned__ = {}
    id = Column(Binary(16), primary_key=True, nullable=False)
    username = Column(String(256), nullable=False)
    password = Column(Binary(60), nullable=True)
    business_id = Column(Integer(), ForeignKey(Business.id), nullable=False)
    deleted = Column(Boolean(), nullable=False, server_default='0')

    emails = relationship('UserEmail')
    documents = relationship('Document')
    fields = relationship('Field')

class UserEmail(Base):
    __tablename__ = 'user_email'
    id = Column(Integer(), primary_key=True, autoincrement=True)
    user_id = Column(Binary(length=16), ForeignKey(User.id), nullable=False)
    email = Column(String(length=256), nullable=False)
    is_primary = Column(Boolean(), nullable=False, server_default='0')

class File(Base):
    __tablename__ = 'file'
    id = Column(Binary(length=16), nullable=False, primary_key=True)
    filename = Column(String(100), server_default=None)
    request_uri = Column(String(512), server_default=None)

    fileusages = relationship('FileUsage')
    fieldusages = relationship('FieldUsage')

class Document(Base):
    __tablename__ = 'document'
    id = Column(Binary(length=16), primary_key=True, nullable=False)
    title = Column(String(length=256), nullable=False)
    user_id = Column(Binary(length=16), ForeignKey(User.id, ondelete="CASCADE"), nullable=False)

    fields = relationship('Field')
    file_usages = relationship('FileUsage')
    pages = relationship('RenderedPage')
    access_uris = relationship('AccessURI')

class BusinessConfig(Base):
    __tablename__ = 'business_config'
    id = Column(Integer(), primary_key=True, autoincrement=True)
    business_id = Column(Integer(), ForeignKey(Business.id, ondelete="CASCADE"), nullable=False)
    key = Column(String(128), nullable=False)
    values = Column(JSONB, server_default="{}", nullable=False)

class FileUsage(Base):
    __tablename__ = 'fileusage'
    id = Column(Integer(), primary_key=True, nullable=False, autoincrement=True)
    timestamp = Column(DateTime(), server_default=func.now())
    file_id = Column(Binary(16), ForeignKey(File.id, ondelete="CASCADE"), server_default=None)
    document_id = Column(Binary(16), ForeignKey(Document.id, ondelete="CASCADE"), server_default=None)
    fileusage_type = Column(Integer(), ForeignKey(FileUsageType.id), nullable=False)
    data = Column(JSONB, server_default="{}", nullable=False)

class Field(Base):
    __tablename__ = 'field'
    id = Column(Binary(16), primary_key=True, nullable=False)
    user_id = Column(Binary(16), ForeignKey(User.id, ondelete="CASCADE"), nullable=True)
    document_id = Column(Binary(16), ForeignKey(Document.id, ondelete="CASCADE"), nullable=False)
    field_type = Column(Integer(), ForeignKey(FieldType.id), nullable=False)
    field_name = Column(String(512), nullable=False)
    parent = Column(Binary(16), ForeignKey('field.id'), nullable=True, server_default=None)
    required = Column(Boolean, server_default="1")

    usages = relationship('FieldUsage')
    dependants = relationship('Field')

class AccessURI(Base):
    __tablename__ = 'accessuri'
    id = Column(Integer(), primary_key=True, autoincrement=True)
    uri = Column(String(1024), nullable=False)
    user_id = Column(Binary(16), ForeignKey(User.id, ondelete="CASCADE"), nullable=False)
    document_id = Column(Binary(16), ForeignKey(Document.id, ondelete="CASCADE"), nullable=False)
    revoked = Column(Boolean(), nullable=False, server_default='0')

class FieldUsage(Base):
    __tablename__ = 'fieldusage'
    id = Column(Integer(), primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(), nullable=False, server_default=func.now())
    field_id = Column(Binary(16), ForeignKey(Field.id), nullable=False)
    fieldusage_type = Column(Integer(), ForeignKey(FieldUsageType.id), nullable=False)
    file_id = Column(Binary(16), ForeignKey(File.id), server_default=None)
    data = Column(JSONB, server_default="{}", nullable=False)

class RenderedPage(Base):
    __tablename__ = 'renderedpage'
    id = Column(Integer(), primary_key=True, autoincrement=True)
    file_id = Column(Binary(16), ForeignKey(File.id, ondelete="CASCADE"), nullable=False)
    document_id = Column(Binary(16), ForeignKey(Document.id, ondelete="CASCADE"), nullable=False)
    page = Column(Integer(), nullable=False)

# Setup for SQLAlchemy-Continuum
configure_mappers()

def init(engine):
    Base.metadata.create_all(engine)
