#!/bin/bash

#URL=http://localhost:8000/v1
URL=https://sign.kew.ca/v1

USERNAME=seanlynch144+test@gmail.com
PASSWORD=brak

TOKEN=$(curl $URL/auth -X POST -F username=$USERNAME -F password=$PASSWORD -s | jq .token)
AUTH="Authorization: Bearer $(eval echo $TOKEN)"

DOCUMENTS=$(curl -X GET --header "$AUTH" $URL/account/documents -s | jq '.[].id')
DOCUMENTS=$(eval echo $DOCUMENTS)

for id in $DOCUMENTS; do
    curl -X DELETE --header "$AUTH" $URL/document/$id
done

echo Deleted ${#DOCUMENTS[@]} documents
