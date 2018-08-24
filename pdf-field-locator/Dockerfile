FROM tiangolo/uwsgi-nginx-flask:python3.6-alpine3.7

RUN apk add --no-cache zlib libjpeg pdftk
RUN apk add --no-cache --virtual .build-deps \
    gcc musl-dev zlib-dev libjpeg-turbo-dev

WORKDIR /app

COPY requirements.txt /app/
RUN pip install -r requirements.txt --no-cache-dir
RUN apk del .build-deps

COPY . /app
