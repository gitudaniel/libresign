#!/bin/bash

#URL=http://localhost:8000/v1
URL=https://sign.kew.ca/v1

USERNAME=seanlynch144+test@gmail.com
PASSWORD=brak

TOKEN=$(curl $URL/auth -X POST -F username=$USERNAME -F password=$PASSWORD -s | jq .token)
AUTH="Authorization: Bearer $(eval echo $TOKEN)"

upload () {
    i=$1

    curl -X POST --header "$AUTH" -F docName=test-$i --silent               \
        -F 'signators={"sig1":"sean@lend88.com","name1":"sean@lend88.com"}' \
        -F file=@../../sample.pdf                                           \
        $URL/document > /dev/null

    echo Uploaded document $i
}

for i in $(seq 100); do 
    upload $i &
done

wait
