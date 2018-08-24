#!/bin/bash

#URL=http://localhost:8000/v1
URL=https://sign.kew.ca/v1

USERNAME=seanlynch144+test@gmail.com
PASSWORD=brak

TOKEN=$(curl $URL/auth -X POST -F username=$USERNAME -F password=$PASSWORD -s | jq .token)
AUTH="Authorization: Bearer $(eval echo $TOKEN)"

DOCUMENT_JSON=$(\
    curl -X POST --header "$AUTH" $URL/document --silent \
    -F docName="test-document" \
    -F 'signators={"Text Box 2":"sean@lend88.com", "text":"sean@lend88.com"}' \
    -F file=@../../all-types.pdf \
)

echo $DOCUMENT_JSON

DOCUMENT=$(echo "$DOCUMENT_JSON" | jq .docId)
DOCUMENT=$(eval echo $DOCUMENT)

#echo "Document ID: $DOCUMENT"

curl -X POST --header "$AUTH" "$URL/document/$DOCUMENT/send-reminder-email"
