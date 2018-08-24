
docker build backend -f backend/Dockerfile -t lend88/pdf-esigner-backend
docker build backend -f backend/Dockerfile-Celery -t lend88/pdf-esigner-celery
docker build pdf-audit-log -t lend88/pdf-esigner-audit-gen
docker build pdf-field-locator -t lend88/pdf-esigner-field-locator
docker build pdf-service -t lend88/pdf-esigner-pdfservice

docker push lend88/pdf-esigner-backend
docker push lend88/pdf-esigner-celery
docker push lend88/pdf-esigner-audit-gen
docker push lend88/pdf-esigner-field-locator
docker push lend88/pdf-esigner-pdfservice
