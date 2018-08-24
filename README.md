# LibreSign

LibreSign is a REST API that is designed to allow front-end
apps to embed a esigning workflow. It allows for a document
owner to send out a document to multiple users (who aren't
required to make an account) and have them sign the document.
It also provides webhooks for controlling applications to
be notified whenever an event happens.

## Running

The easiest way to run a LibreSign server is using docker via
docker-compose. This can be done by running the following
command in the repository root (the `-d` parameter is optional
and runs the containers in the backend)

```sh
docker-compose up -d
```

This will create a complete LibreSign service. For production
uses, the `docker-compose-prod.yml` file has a different
setup that is more suitable for public facing applications.
Note that the `.env` file in the root controls the database
username and password, which should be changed when used in
a production environment.

To bring down the service, run the following command in the
root directory

```sh
docker-compose down
```

## API Reference

The LibreSign API is defined using an OpenAPI 2.0 (aka Swagger)
spec. This spec can be found
[here](backend/swagger_server/swagger/swagger.yaml) and api
docs for the service can be at `<service-host>/v1/ui` once
the service is running. The reference application is deployed
at `https://sign.kew.ca` and thus the API docs are available
[here](https://sign.kew.ca/v1/ui).

## Configuration

The owner of a business can configure various events and templates
for that business. At the moment the following things can be
configured:

- Webhooks to be invoked for each event on a document owned by a
  user within the business
- Email templates for document signature reminder requests.

## Deployment

The production instance updates automatically new images are
passed to the corresponding images within the lend88 docker
hub repository. The `build.bat` file within the root of
this repository will build and push the new docker images,
and should be straightforward to translate to a shell script
if necessary.

## Webhooks

LibreSign can be configured with webhooks that will be invoked
for each event occurring on a document owned by a user within
a business. These will receive a `POST` request when event
occurs. The body of the request will be as follows

```text
TODO
```

## License

Libresign is licensed under the MIT license.
