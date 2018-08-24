FROM tiangolo/uwsgi-nginx-flask:python3.6

RUN apt-get update \
    && apt-get install -y build-essential libffi-dev libpq-dev \
    && apt-get upgrade -y

RUN mkdir /usr/local/share/ca-certificates/cacert.org
RUN wget -P /usr/local/share/ca-certificates/cacert.org http://www.cacert.org/certs/root.crt http://www.cacert.org/certs/class3.crt
RUN update-ca-certificates

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

ADD requirements.txt /usr/src/app
RUN python3 -m pip install -r requirements.txt

ENV GOOGLE_APPLICATION_CREDENTIALS=/var/pdfservice/auth.json
ENV FLASK_CONFIG=/usr/src/app/swagger_server/config.py
ENV FLASK_APP=main:app
ENV FLASK_DEBUG=1

ADD . /usr/src/app
ADD pdfservice.json /var/pdfservice/auth.json

RUN python3 setup.py install

