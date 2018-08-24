FROM tiangolo/uwsgi-nginx-flask:python3.6-alpine3.7

WORKDIR /app

COPY requirements.txt /app/
RUN pip install -r requirements.txt --no-cache-dir

COPY . /app
