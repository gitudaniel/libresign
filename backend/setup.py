# coding: utf-8

from setuptools import setup, find_packages

NAME = "swagger_server"
VERSION = "0.0.1"

# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

REQUIRES = [
    "connexion",
    "python_dateutil",
    "flask_jwt_extended",
    "flask_bcrypt",
    "flask_cors",
    "flask_mail",
    "flask_sqlalchemy",
    "flask",
    "cloudstorage",
    "bidict",
    "requests",
    "celery",
    "psycopg2-binary",
    "sqlalchemy-continuum"
]

setup(
    name=NAME,
    version=VERSION,
    description="PDF Service",
    author_email="",
    url="",
    keywords=["Swagger", "PDF Service"],
    install_requires=REQUIRES,
    packages=find_packages(),
    package_data={'': ['swagger/swagger.yaml']},
    include_package_data=True
)

